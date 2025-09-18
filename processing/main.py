import asyncio
import os
import json
import logging
from pubsub_logic import parse_pubsub_event, fetch_transcript_by_id
from processedFile_handling import mark_processed
from grading_manager import gradingManager
from gemini_client import init_gemini
from google.cloud import pubsub_v1
import sys

logging.basicConfig(
    level=logging.DEBUG,       # show all levels
    stream=sys.stdout,         # make sure logs go to stdout
    force=True                 # override any previous settings
)
logger = logging.getLogger(__name__)

# Initialize Gemini globally
init_gemini()

# Emailer configuration
EMAILER_TOPIC = os.environ.get("EMAILER_TOPIC", "projects/sales-transcript-grader/topics/receive-grading")
_emailer_publisher = None

def get_emailer_publisher():
    """Get or create emailer publisher client."""
    global _emailer_publisher
    if _emailer_publisher is None:
        logger.info("🔧 Creating new Pub/Sub publisher client...")
        _emailer_publisher = pubsub_v1.PublisherClient()
    return _emailer_publisher

def publish_emailer_payload(payload: dict, timeout: int = 30):
    """Publish grading results to emailer topic."""
    try:
        publisher = get_emailer_publisher()
        data = json.dumps(payload).encode("utf-8")
        logger.info("📨 Publishing payload to emailer topic: %s", EMAILER_TOPIC)
        logger.info("📦 Payload JSON length: %d", len(data))
        logger.info("📦 Payload preview: %s", json.dumps(payload, indent=2)[:1000])

        future = publisher.publish(EMAILER_TOPIC, data=data)
        message_id = future.result(timeout=timeout)
        logger.info("✅ Published to Pub/Sub. message_id=%s fileName=%s",
                   message_id, payload.get("fileName"))
        return message_id
    except Exception:
        logger.exception("❌ Failed to publish emailer payload: %s", payload)
        raise

def safe_grade(report, skill_name="unknown"):
    """Extract grade and reasoning safely from a report object."""
    try:
        logger.info(f"🔍 Inspecting report for skill={skill_name}: type={type(report)} repr={repr(report)}")
        if hasattr(report, 'items') and report.items:
            logger.info(f"✅ Report for skill={skill_name} has items, extracting first one...")
            grade = report.items[0].grade
            reasoning = report.items[0].reasoning
            logger.info(f"✅ Extracted grade={grade} reasoning={reasoning[:60]}...")
            return {"grade": grade, "reasoning": reasoning}
        else:
            logger.warning(f"⚠️ Report for skill={skill_name} has no items: {repr(report)}")
    except Exception as e:
        logger.warning(f"⚠️ Could not extract grade for skill={skill_name}: {e}")
        logger.warning(f"⚠️ Raw report object: {repr(report)}")

    return {"grade": "ERROR", "reasoning": "No grading data"}

def pubsub_handler(event, context):
    logger.info("🚀 PROCESSOR FUNCTION STARTED")
    logger.info("📨 Raw event type: %s", type(event))
    logger.info("📨 Raw event content (truncated): %s", str(event)[:500])

    # 1. Parse event
    try:
        task = parse_pubsub_event(event)
        logger.info("✅ Successfully parsed Pub/Sub event")
        logger.info("📋 Parsed task: %s", task)
    except Exception as e:
        logger.error("❌ FAILED to parse Pub/Sub event: %s", str(e))
        logger.exception("Parse error details:")
        return "Bad Request: invalid event format"

    file_id = task.get("fileId")
    file_name = task.get("fileName", "<unknown>")
    rep = task.get("rep", "<unknown>")
    manager_email = task.get("managerEmail", "gusdaskalakis@gmail.com")

    logger.info("📋 Extracted details:")
    logger.info("   • fileId: %s", file_id)
    logger.info("   • fileName: %s", file_name)
    logger.info("   • rep: %s", rep)
    logger.info("   • managerEmail: %s", manager_email)

    if not file_id:
        logger.error("❌ Missing fileId in task; aborting.")
        return "Bad Request: missing fileId"

    # Check if file is already processed (but allow inflight files to be processed)
    try:
        from processedFile_handling import get_drive_service
        drive = get_drive_service()
        file_metadata = drive.files().get(
            fileId=file_id,
            fields="appProperties",
            supportsAllDrives=True
        ).execute()
        
        app_props = file_metadata.get("appProperties", {}) or {}
        if app_props.get("processed") == "true":
            logger.warning(f"🚫 SKIPPING: File {file_id} already processed")
            return {
                "status": "skipped",
                "reason": "already_processed",
                "file_id": file_id,
                "file_name": file_name
            }
        # Allow inflight files to be processed (they might be stuck)
    except Exception as e:
        logger.warning(f"⚠️ Could not check file status for {file_id}: {e}")
        # Continue processing if we can't check status

    # 2. Fetch transcript
    try:
        logger.info("📄 Fetching transcript for fileId=%s...", file_id)
        transcript = fetch_transcript_by_id(file_id) or "⚠️ No transcript content available."
        logger.info("✅ Transcript fetched. Length=%d", len(transcript))
        logger.info("📝 Transcript preview: %s...", transcript[:200].replace("\n", " "))
    except Exception as e:
        logger.error("❌ FAILED to fetch transcript: %s", str(e))
        logger.exception("Transcript fetch error details:")
        transcript = "⚠️ Error fetching transcript content."

    # 3. Run grading
    grader = gradingManager()
    results, synthesis_result = {}, None
    try:
        logger.info("🤖 Running grader.grade_all()...")
        results, synthesis_result = grader.grade_all(transcript)
        logger.info("✅ Grading completed.")
        logger.info("📊 Results object type: %s", type(results))
        logger.info("📊 Results keys: %s", list(results.keys()))
        logger.info("📊 Synthesis result type: %s", type(synthesis_result))
        logger.info("📊 Synthesis result repr: %s", repr(synthesis_result))
    except Exception as e:
        logger.error("❌ Grading failed: %s", str(e))
        logger.exception("Grading error details:")
        synthesis_result = {"error": str(e)}

    # 4. Mark processed
    try:
        logger.info("📝 Marking file as processed: %s", file_id)
        mark_processed(file_id)
        logger.info("✅ File marked processed.")
    except Exception:
        logger.error("❌ Failed to mark file processed: %s", file_id)
        logger.exception("mark_processed error details:")

    logger.info(f"📤 Publishing transcript length: {len(transcript) if transcript else 0}")

    # Check if transcript is valid before sending email
    if (not transcript or 
        transcript.startswith("⚠️") or 
        "No transcript content" in transcript or
        "No transcript provided" in transcript or
        len(transcript.strip()) < 50):  # Too short to be a real transcript
        logger.warning(f"🚫 SKIPPING EMAIL: Invalid transcript for file {file_id}")
        logger.warning(f"🚫 Transcript content: {transcript}")
        return {
            "status": "skipped",
            "reason": "invalid_transcript",
            "file_id": file_id,
            "file_name": file_name,
            "transcript_preview": transcript[:100] if transcript else "None"
        }

    logger.info("📦 Building emailer payload...")
    try:
        emailer_payload = {
            "fileId": file_id,
            "fileName": file_name,
            "rep": rep,
            "managerEmail": manager_email,
            "timestamp": getattr(context, "timestamp", None),
            "transcript": transcript if transcript is not None else "⚠️ Transcript missing (processor error)",
            "grading_results": {
                "individual_scores": {
                    skill_name: safe_grade(report, skill_name) for skill_name, report in results.items()
                },
                "final_synthesis": (
                    safe_grade(synthesis_result, "synthesis") if synthesis_result else
                    {"grade": "ERROR", "reasoning": "No synthesis"}
                )
            },
            "metadata": {
                "processed_at": getattr(context, "timestamp", None),
                "execution_id": getattr(context, "event_id", None),
                "processing_status": "completed" if results else "failed"
            }
        }
        logger.info("✅ Emailer payload built successfully.")
        logger.info("📦 Full payload (truncated to 1000 chars): %s",
                    json.dumps(emailer_payload, indent=2)[:1000])
    except Exception as e:
        logger.error("❌ Failed to build emailer payload: %s", e)
        logger.exception("Payload build error details:")
        return "Failed to build payload"

    # 6. Publish payload
    try:
        logger.info("📨 Publishing payload to emailer...")
        message_id = publish_emailer_payload(emailer_payload)
        logger.info("✅ Emailer publish complete. message_id=%s", message_id)
    except Exception as e:
        logger.error("❌ FAILED to publish to emailer: %s", str(e))
        logger.exception("Emailer publish error details:")
        return "Failed to publish emailer payload"

    logger.info("🏁 PROCESSOR FUNCTION FINISHING OK")
    return "OK"
