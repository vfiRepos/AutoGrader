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
    task = parse_pubsub_event(event)
    file_id = task.get("fileId")
    file_name = task.get("fileName", "<unknown>")
    rep = task.get("rep", "<unknown>")
    manager_email = task.get("managerEmail")  # keep None vs "" to detect missing

    logger.info(f"📩 Processing transcript: {file_name} (rep: {rep})")

    # sanity checks
    if not file_id:
        logger.error("No fileId in task; aborting.")
        return ("Bad Request: missing fileId", 400)

    # 2. Fetch transcript
    transcript = fetch_transcript_by_id(file_id) or "⚠️ No transcript content available."

    # 3. Run grading
    grader = gradingManager()
    try:
        results, synthesis_result = grader.grade_all(transcript)
    except Exception as e:
        logger.exception("Grading failed for file=%s", file_id)
        # still continue to build a payload with an error marker if you want:
        results = {}
        synthesis_result = {"error": str(e)}

    # 4. Mark processed (optional)
    try:
        mark_processed(file_id)
        logger.info(f"✅ Marked file processed: {file_id}")
    except Exception:
        logger.exception("mark_processed failed for file=%s", file_id)

    # 5. Create comprehensive payload for emailer
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

    # 6. Publish to emailer topic
    try:
        logger.info("🚀 STARTING EMAIL PUBLICATION for %s", file_name)
        logger.info("📧 Emailer Payload for %s:", file_name)
        logger.info("📧 Payload: %s", json.dumps(emailer_payload, indent=2, default=str))

        logger.info("📨 Calling publish_emailer_payload()...")
        message_id = publish_emailer_payload(emailer_payload)
        logger.info("✅ SUCCESS: Published grading results to emailer!")
        logger.info("✅ Message ID: %s", message_id)
        logger.info("✅ Email will be sent to: %s", emailer_payload.get("managerEmail") or "default recipient")
        logger.info("🎯 EMAIL PUBLICATION COMPLETE for %s", file_name)
    except Exception as e:
        logger.exception("❌ FAILED to publish to emailer for file=%s: %s", file_id, e)
        logger.error("❌ Email will NOT be sent for this grading report")
        # Don't fail the whole function if emailer fails

    return(results, synthesis_result)
