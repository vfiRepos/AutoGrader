import asyncio
import os
import json
from pubsub_logic import parse_pubsub_event, fetch_transcript_by_id
from processedFile_handling import mark_processed
from grading_manager import gradingManager
import logging
from gemini_client import init_gemini

# Add this import for publishing to emailer
from google.cloud import pubsub_v1

# Configure logging to reduce noise
logging.getLogger().setLevel(logging.WARNING)  # Only show warnings and errors
logging.getLogger('httplib2').setLevel(logging.ERROR)  # Silence httplib2 noise
logging.getLogger('google').setLevel(logging.ERROR)  # Silence Google API noise

# Initialize Gemini globally
init_gemini()

# Emailer configuration
EMAILER_TOPIC = os.environ.get("EMAILER_TOPIC", "projects/sales-transcript-grader/topics/email_report")
_emailer_publisher = None

def get_emailer_publisher():
    """Get or create emailer publisher client."""
    global _emailer_publisher
    if _emailer_publisher is None:
        _emailer_publisher = pubsub_v1.PublisherClient()
    return _emailer_publisher

def publish_emailer_payload(payload: dict, timeout: int = 30):
    """
    Publish grading results to emailer topic.
    Returns message_id or raises.
    """
    try:
        publisher = get_emailer_publisher()
        data = json.dumps(payload).encode("utf-8")
        logger.info("Publishing to emailer topic: %s", EMAILER_TOPIC)

        future = publisher.publish(EMAILER_TOPIC, data=data)
        message_id = future.result(timeout=timeout)
        logger.info("Published emailer message_id=%s for file=%s",
                   message_id, payload.get("fileName"))
        return message_id
    except Exception:
        logger.exception("Failed to publish emailer payload: %s", payload)
        raise

# main.py (excerpt)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Keep our app logs at INFO level

def pubsub_handler(event, context):
    # 1. Parse event
    logger.info("🚀 PROCESSOR FUNCTION STARTED")
    logger.info("🔧 Checking Gemini AI client initialization...")

    # Check if Gemini API key is available
    api_key = os.environ.get("GENAI_API_KEY")
    if api_key:
        logger.info("✅ GENAI_API_KEY is configured (starts with %s...)", api_key[:6])
    else:
        logger.error("❌ GENAI_API_KEY is NOT configured!")

    logger.info("📨 Received Pub/Sub event, parsing...")

    try:
        task = parse_pubsub_event(event)
        logger.info("✅ Successfully parsed Pub/Sub event")
    except Exception as e:
        logger.error("❌ FAILED to parse Pub/Sub event: %s", str(e))
        logger.exception("Parse error details:")
        return ("Bad Request: invalid event format", 400)

    file_id = task.get("fileId")
    file_name = task.get("fileName", "<unknown>")
    rep = task.get("rep", "<unknown>")
    manager_email = task.get("managerEmail", "gusdaskalakis@gmail.com")  # Default recipient

    logger.info("📋 Extracted task details:")
    logger.info("   • File ID: %s", file_id)
    logger.info("   • File Name: %s", file_name)
    logger.info("   • Representative: %s", rep)
    logger.info("   • Manager Email: %s", manager_email)

    logger.info("📩 Processing transcript: %s (rep: %s)", file_name, rep)

    # sanity checks
    if not file_id:
        logger.error("No fileId in task; aborting.")
        return ("Bad Request: missing fileId", 400)

    # 2. Fetch transcript
    logger.info("📄 STEP 2: Fetching transcript content...")
    logger.info("🔍 Calling fetch_transcript_by_id(%s)...", file_id)

    try:
        transcript = fetch_transcript_by_id(file_id) or "⚠️ No transcript content available."
        transcript_length = len(transcript) if transcript else 0
        logger.info("✅ Transcript fetched successfully (%d characters)", transcript_length)

        if transcript and len(transcript) > 100:
            logger.info("📝 Transcript preview: %s...", transcript[:100].replace('\n', ' ').replace('\r', ' '))
        elif transcript:
            logger.info("📝 Full transcript: %s", transcript)
        else:
            logger.warning("⚠️ No transcript content available")

    except Exception as e:
        logger.error("❌ FAILED to fetch transcript: %s", str(e))
        logger.exception("Transcript fetch error details:")
        transcript = "⚠️ Error fetching transcript content."

    # 3. Run grading
    logger.info("🎯 STEP 3: Running AI grading analysis...")
    logger.info("🤖 Initializing grading manager...")

    grader = gradingManager()
    logger.info("✅ Grading manager initialized")

    try:
        logger.info("🚀 Calling grader.grade_all() - this may take several seconds...")
        results, synthesis_result = grader.grade_all(transcript)
        logger.info("✅ Grading completed successfully!")

        # Log grading results summary
        if results:
            logger.info("📊 Individual skill assessments completed:")
            for skill_name, report in results.items():
                if hasattr(report, 'items') and report.items:
                    grade = report.items[0].grade
                    logger.info("   • %s: %s", skill_name, grade)
                else:
                    logger.info("   • %s: Error in grading", skill_name)
        else:
            logger.warning("⚠️ No individual skill results generated")

        # Log synthesis result
        if synthesis_result and hasattr(synthesis_result, 'items') and synthesis_result.items:
            synthesis_grade = synthesis_result.items[0].grade
            logger.info("🎯 Final synthesis grade: %s", synthesis_grade)
        else:
            logger.warning("⚠️ No synthesis result generated")

    except Exception as e:
        logger.error("❌ GRADING FAILED for file=%s: %s", file_id, str(e))
        logger.exception("Grading error details:")
        # still continue to build a payload with an error marker if you want:
        results = {}
        synthesis_result = {"error": str(e)}
        logger.info("⚠️ Continuing with error payload despite grading failure")

    # 4. Mark processed (optional)
    logger.info("📝 STEP 4: Marking file as processed...")
    try:
        mark_processed(file_id)
        logger.info("✅ Successfully marked file processed: %s", file_id)
    except Exception:
        logger.error("❌ FAILED to mark file as processed: %s", file_id)
        logger.exception("mark_processed error details:")

    # 5. Create comprehensive payload for emailer
    logger.info("📦 STEP 5: Creating emailer payload...")
    emailer_payload = {
        "fileId": file_id,
        "fileName": file_name,
        "rep": rep,
        "managerEmail": manager_email,
        "timestamp": context.timestamp if context else None,
        "transcript": transcript,  # Full transcript
        "grading_results": {
            "individual_scores": {
                skill_name: {
                    "grade": report.items[0].grade,
                    "reasoning": report.items[0].reasoning
                } for skill_name, report in results.items()
            },
            "final_synthesis": {
                "grade": synthesis_result.items[0].grade if synthesis_result and hasattr(synthesis_result, 'items') else "ERROR",
                "reasoning": synthesis_result.items[0].reasoning if synthesis_result and hasattr(synthesis_result, 'items') else str(synthesis_result)
            }
        },
        "metadata": {
            "processed_at": context.timestamp if context else None,
            "execution_id": context.event_id if context else None,
             "processing_status": "completed" if (not synthesis_result or (isinstance(synthesis_result, dict) and not synthesis_result.get("error"))) else "failed"
        }
    }

    logger.info("✅ Emailer payload created successfully")
    logger.info("📧 Payload contains %d characters of transcript", len(emailer_payload.get("transcript", "")))
    logger.info("📧 Will send email to: %s", emailer_payload.get("managerEmail", "unknown"))

    # 6. Publish to emailer topic
    logger.info("📨 STEP 6: Publishing to emailer topic...")
    try:
        logger.info("🚀 STARTING EMAIL PUBLICATION for %s", file_name)
        logger.info("📨 Calling publish_emailer_payload()...")

        message_id = publish_emailer_payload(emailer_payload)

        logger.info("✅ SUCCESS: Published grading results to emailer!")
        logger.info("✅ Message ID: %s", message_id)
        logger.info("✅ Email will be sent to: %s", emailer_payload.get("managerEmail") or "default recipient")
        logger.info("🎯 EMAIL PUBLICATION COMPLETE for %s", file_name)

        # Final success summary
        logger.info("🎉 PROCESSOR FUNCTION COMPLETED SUCCESSFULLY!")
        logger.info("📊 Summary:")
        logger.info("   • File: %s", file_name)
        logger.info("   • Rep: %s", rep)
        logger.info("   • Transcript: %d chars", len(emailer_payload.get("transcript", "")))
        logger.info("   • Emailer Message ID: %s", message_id)

    except Exception as e:
        logger.error("❌ FAILED to publish to emailer for file=%s: %s", file_id, str(e))
        logger.exception("Emailer publication error details:")
        logger.error("❌ Email will NOT be sent for this grading report")
        logger.info("⚠️ Function will continue despite emailer failure")
        # Don't fail the whole function if emailer fails

    logger.info("🏁 PROCESSOR FUNCTION FINISHING")
    return(results, synthesis_result)
