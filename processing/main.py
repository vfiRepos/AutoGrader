import asyncio
import os
from grading_manager import gradingManager
from polling_logic import fetch_latest_transcript
from email_logic import EmailAgent
from processedFile_handling import postprocess_latest_file




import asyncio
from pubsub_logic import parse_pubsub_event, fetch_transcript_by_id
from grading_manager import gradingManager
from email_logic import EmailAgent
from processedFile_handling import mark_processed


import asyncio
import json
import base64
from pubsub_logic import parse_pubsub_event, fetch_transcript_by_id
from grading_manager import gradingManager
from processedFile_handling import mark_processed
from google.cloud import pubsub_v1

# Pub/Sub topic for emailer
EMAILER_TOPIC = "projects/YOUR_PROJECT_ID/topics/transcripts.processed"


def _pubsub_client():
    return pubsub_v1.PublisherClient()


def publish_email_task(payload: dict):
    """
    Publishes results to the emailer Pub/Sub topic.
    """
    client = _pubsub_client()
    data = json.dumps(payload).encode("utf-8")
    future = client.publish(EMAILER_TOPIC, data=data)
    future.result()  # wait for publish
    print(f"📨 Published email task for {payload['fileName']} to {EMAILER_TOPIC}")


def pubsub_handler(event, context):
    """
    Cloud Function entrypoint: processes one transcript task from Pub/Sub.
    """
    # 1. Parse event
    task = parse_pubsub_event(event)
    file_id = task["fileId"]
    file_name = task["fileName"]
    rep = task["rep"]
    manager_email = task["managerEmail"]

    print(f"📩 Received transcript task for {file_name} (rep={rep})")

    # 2. Fetch transcript text
    transcript = fetch_transcript_by_id(file_id)
    if not transcript:
        transcript = "⚠️ No transcript content available."

    # 3. Run grading
    grader = gradingManager()
    results, synthesis_result = asyncio.run(grader.grade_all(transcript))

    # 4. Mark file processed in Drive
    mark_processed(file_id)

    # 5. Publish results for the emailer
    publish_email_task({
        "rep": rep,
        "fileId": file_id,
        "fileName": file_name,
        "managerEmail": manager_email,
        "results": results,
        "synthesisResult": synthesis_result,
    })

    print(f"🎉 Finished {file_name}, published email task for manager {manager_email}")

    

    
