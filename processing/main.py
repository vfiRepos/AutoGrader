import asyncio
import os
import json
import logging
from pubsub_logic import parse_pubsub_event, fetch_transcript_by_id
from grading_manager import gradingManager
from gemini_client import init_gemini
from processedFile_handling import move_file_to_processed
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
    folder_id = task.get("folderId")
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
                        "reasoning": skill_result.items[0].reasoning if skill_result.items else "No reasoning available",
                        "count": skill_result.items[0].count if skill_result.items and skill_result.items[0].count is not None else None,
                        "examples": skill_result.items[0].examples if skill_result.items and skill_result.items[0].examples else None,
                        "ratio": skill_result.items[0].ratio if skill_result.items and skill_result.items[0].ratio is not None else None,
                        # Boolean fields for specific criteria
                        "segment_identified": skill_result.items[0].segment_identified if skill_result.items and skill_result.items[0].segment_identified is not None else None,
                        "tailored_questions": skill_result.items[0].tailored_questions if skill_result.items and skill_result.items[0].tailored_questions is not None else None,
                        "positioning_aligned": skill_result.items[0].positioning_aligned if skill_result.items and skill_result.items[0].positioning_aligned is not None else None,
                        "differentiators_reinforced": skill_result.items[0].differentiators_reinforced if skill_result.items and skill_result.items[0].differentiators_reinforced is not None else None,
                        "positioned_as_partner": skill_result.items[0].positioned_as_partner if skill_result.items and skill_result.items[0].positioned_as_partner is not None else None,
                        "connected_to_situation": skill_result.items[0].connected_to_situation if skill_result.items and skill_result.items[0].connected_to_situation is not None else None,
                        "distinguished_from_banks": skill_result.items[0].distinguished_from_banks if skill_result.items and skill_result.items[0].distinguished_from_banks is not None else None,
                        "emphasized_fixed_assets": skill_result.items[0].emphasized_fixed_assets if skill_result.items and skill_result.items[0].emphasized_fixed_assets is not None else None,
                        "explained_liquidity": skill_result.items[0].explained_liquidity if skill_result.items and skill_result.items[0].explained_liquidity is not None else None,
                        "aligned_with_priorities": skill_result.items[0].aligned_with_priorities if skill_result.items and skill_result.items[0].aligned_with_priorities is not None else None
                    } for skill_name, skill_result in results.items()
                },
                       "final_synthesis": (
                           {
                               "grade": synthesis_result.get("final_grade", "N/A") if synthesis_result else "N/A",
                               "reasoning": synthesis_result.get("final_assessment", "No synthesis reasoning available") if synthesis_result else "No synthesis reasoning available",
                               "surface_questions": synthesis_result.get("surface_questions") if synthesis_result else None,
                               "true_discovery_questions": synthesis_result.get("true_discovery_questions") if synthesis_result else None,
                               "filler_words": synthesis_result.get("filler_words") if synthesis_result else None,
                               "rep_talk_ratio": synthesis_result.get("rep_talk_ratio") if synthesis_result else None,
                               "prospect_talk_ratio": synthesis_result.get("prospect_talk_ratio") if synthesis_result else None,
                               "strengths": synthesis_result.get("strengths") if synthesis_result else None,
                               "weaknesses": synthesis_result.get("weaknesses") if synthesis_result else None,
                               "missed_opportunities": synthesis_result.get("missed_opportunities") if synthesis_result else None
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
    
    # 7. Move file to processed folder after successful completion
    try:
        logger.info(f"📁 Moving file {file_id} to processed folder...")
        move_file_to_processed(file_id, folder_id)
        logger.info(f"✅ Successfully moved file {file_id} to processed folder")
    except Exception as e:
        logger.error(f"❌ Failed to move file {file_id} to processed folder: {e}")
        # Don't fail the entire process if file move fails
    
    return message_id