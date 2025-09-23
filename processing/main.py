import asyncio
import os
import json
import logging
from pubsub_logic import parse_pubsub_event, fetch_transcript_by_id
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


        future = publisher.publish(EMAILER_TOPIC, data=data)
        message_id = future.result(timeout=timeout)
        logger.info("✅ Published to Pub/Sub. message_id=%s fileName=%s",
                   message_id, payload.get("fileName"))
        return message_id
    except Exception:
        logger.exception("❌ Failed to publish emailer payload: %s", payload)
        raise



def pubsub_handler(event, context):

    task = parse_pubsub_event(event)
    file_id = task.get("fileId")
    file_name = task.get("fileName")
    rep = task.get("rep")
    manager_email = task.get("managerEmail", "gusdaskalakis@gmail.com")


    transcript = fetch_transcript_by_id(file_id)
    
    # Check if transcript is missing or empty
    if not transcript or not transcript.strip():
        logger.warning(f"⚠️ No transcript available for file {file_id} ({file_name}), skipping processing")
        return {"status": "skipped", "reason": "no_transcript"}
       
    # 3. Run grading
    grader = gradingManager()
    results, synthesis_result = {}, None
    results, synthesis_result = grader.grade_all(transcript)
    
    # Debug: Check what's in results
    logger.info(f"🔍 DEBUG: results type: {type(results)}")
    logger.info(f"🔍 DEBUG: results keys: {list(results.keys())}")
    logger.info(f"🔍 DEBUG: results values types: {[type(v) for v in results.values()]}")


 
    
    try:
        emailer_payload = {
            "fileId": file_id,
            "fileName": file_name,
            "rep": rep,
            "managerEmail": manager_email,
            "timestamp": getattr(context, "timestamp", None),
            "transcript": transcript,
            "grading_results": {
                "individual_scores": {
                    skill_name: {
                        "grade": skill_result.items[0].grade if skill_result.items else "N/A",
                        "reasoning": skill_result.items[0].reasoning if skill_result.items else "No reasoning available"
                    } for skill_name, skill_result in results.items()
                },
                "final_synthesis": (
                    {
                        "grade": synthesis_result.items[0].grade if synthesis_result and synthesis_result.items else "N/A",
                        "reasoning": synthesis_result.items[0].reasoning if synthesis_result and synthesis_result.items else "No synthesis reasoning available"
                    } if synthesis_result else
                    {"grade": "ERROR", "reasoning": "No synthesis"}
                )
            },
            "metadata": {
                "processed_at": getattr(context, "timestamp", None),
                "execution_id": getattr(context, "event_id", None),
                "processing_status": "completed" if results else "failed"
            }
        } 
    except Exception as e:
        logger.error("❌ Failed to build emailer payload: %s", e)
        logger.exception("Payload build error details:")
        return "Failed to build payload"

    # 6. Publish payload
    logger.info(f"🔍 DEBUG: Complete emailer payload being sent:")
    logger.info(f"🔍 DEBUG: {json.dumps(emailer_payload, indent=2)}")
   
    message_id = publish_emailer_payload(emailer_payload)
    return message_id