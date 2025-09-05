import asyncio
import os
from grading_manager import gradingManager
from polling_logic import fetch_latest_transcript
from email_logic import EmailAgent
from processedFile_handling import postprocess_latest_file



def poll_transcripts(event, context):
    grader = gradingManager()

    # Use your test folder ID (shared with service account)
    folder_id = os.environ.get("TRANSCRIPT_FOLDER_ID")

    file_name, transcript = fetch_latest_transcript(folder_id)

    if not transcript:
        transcript = "⚠️ No transcript found in test folder."

    # Run grading
    results, synthesis_result = asyncio.run(grader.grade_all(transcript))

    # Save locally (inside Cloud Function container → /tmp)
    grader.save_results_to_file(results, synthesis_result, filename="/tmp/results.txt")

    # Email results
    agent = EmailAgent()
    outcome = agent.run(results, synthesis_result)

    postprocess_latest_file(folder_id)

    print(f"🎉 Processed transcript {file_name}, emailed results: {outcome}")
