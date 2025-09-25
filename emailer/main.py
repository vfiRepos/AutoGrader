import os
import json
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
import sys


logging.basicConfig(
    level=logging.DEBUG,       # show all levels
    stream=sys.stdout,         # make sure logs go to stdout
    force=True                 # override any previous settings
)
logger = logging.getLogger(__name__)

# Gmail OAuth configuration (set via Cloud Function secrets)
GMAIL_SA_CLIENT_ID = os.environ.get("CLIENT_ID")
GMAIL_SA_CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Sender/recipient defaults
DOMAIN_SENDER = os.environ.get("FROM_EMAIL", "gdaskalakis@vfi.net")
RECIPIENT_EMAIL = os.environ.get("managerEmail", "gusdaskalakis@gmail.com")

# No cache needed - we'll use Google Drive file metadata


def gmail_service():
    """Return a Gmail API client using OAuth client + refresh token."""
    creds = Credentials(
        None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_SA_CLIENT_ID,
        client_secret=GMAIL_SA_CLIENT_SECRET,
        scopes=GMAIL_SCOPES,
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def drive_service():
    """Return a Drive API client using OAuth client + refresh token."""
    creds = Credentials(
        None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_SA_CLIENT_ID,
        client_secret=GMAIL_SA_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)




def normalize_grade_class(grade: str) -> str:
    """Normalize grade strings into safe CSS class suffixes."""
    if not grade:
        return "grade-NA"
    g = grade.upper().strip()

    # Handle special cases
    if "UNABLE TO RUN AGENT" in g:
        return "grade-ERROR"
    
    # Handle common variants
    if g.startswith("A"):
        return "grade-A"
    elif g.startswith("B"):
        return "grade-B"
    elif g.startswith("C"):
        return "grade-C"
    elif g.startswith("D"):
        return "grade-D"
    elif g.startswith("F"):
        return "grade-F"
    else:
        return "grade-NA"

def format_grading_html(payload, timestamp):
    """Format grading results as HTML for email body."""
    logger.info(f"🔍 DEBUG: Formatting grading HTML for payload keys: {list(payload.keys())}")
    results = payload['grading_results']
    logger.info(f"🔍 DEBUG: grading_results keys: {list(results.keys())}")
    logger.info(f"🔍 DEBUG: individual_scores type: {type(results.get('individual_scores', 'MISSING'))}")
    logger.info(f"🔍 DEBUG: final_synthesis type: {type(results.get('final_synthesis', 'MISSING'))}")
    
    file_name = payload['fileName']
    rep = payload['rep']

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
            .skill-card {{ background: #ecf0f1; margin: 10px 0; padding: 15px; border-radius: 5px; }}
            .grade {{ font-size: 24px; font-weight: bold; }}
            .grade-A {{ color: #27ae60; }}
            .grade-B {{ color: #f39c12; }}
            .grade-C {{ color: #e67e22; }}
            .grade-D {{ color: #e74c3c; }}
            .grade-F {{ color: #c0392b; }}
            .grade-ERROR {{ color: #8e44ad; font-style: italic; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Sales Transcript Grading Results</h1>
            <p><strong>File:</strong> {file_name}</p>
            <p><strong>Representative:</strong> {rep}</p>
            <p><strong>Email ID:</strong> {timestamp}</p>
        </div>

        <h2>Individual Skill Assessments</h2>
    """

    # Add individual skill results
    for skill_name, skill_data in results['individual_scores'].items():
        grade = skill_data['grade']
        reasoning = skill_data['reasoning']
        grade_class = normalize_grade_class(grade)

        html += f"""
        <div class="skill-card">
            <h3>{skill_name.replace('_', ' ').title()}</h3>
            <div class="grade {grade_class}">{grade}</div>
            <p><strong>Analysis:</strong> {reasoning}</p>
        """

        # Add additional details if available
        if 'examples' in skill_data and skill_data['examples']:
            if skill_name == 'missed_opportunity':
                # Special formatting for missed opportunities
                html += f"<p><strong>Missed Opportunities:</strong></p>"
                html += f"<ul>"
                for example in skill_data['examples']:
                    html += f"<li>{example}</li>"
                html += f"</ul>"
            else:
                html += f"<p><strong>Examples:</strong> {skill_data['examples']}</p>"
        
        if 'ratio' in skill_data and skill_data['ratio'] is not None:
            # Provide context for what the ratio represents based on skill type
            if skill_name == 'call_control':
                html += f"<p><strong>Talk Time Ratio:</strong> {skill_data['ratio']:.1f}% (Rep speaking time vs. total call time)</p>"
            elif skill_name == 'discovery':
                html += f"<p><strong>Discovery Score:</strong> {skill_data['ratio']:.1f}% (Percentage of questions that were discovery-focused)</p>"
            elif skill_name == 'true_discovery':
                html += f"<p><strong>Discovery Quality Score:</strong> {skill_data['ratio']:.1f}% (Overall discovery performance score)</p>"
            else:
                html += f"<p><strong>Ratio:</strong> {skill_data['ratio']}</p>"
        
        # For call control, also show both ratios from synthesis if available
        if skill_name == 'call_control':
            synthesis = results.get('final_synthesis', {})
            if synthesis.get('rep_talk_ratio') is not None and synthesis.get('prospect_talk_ratio') is not None:
                html += f"<p><strong>Detailed Talk Ratios:</strong></p>"
                html += f"<ul>"
                html += f"<li><strong>Rep Talk Ratio:</strong> {synthesis['rep_talk_ratio']:.1f}% (Percentage of call time rep was speaking)</li>"
                html += f"<li><strong>Prospect Talk Ratio:</strong> {synthesis['prospect_talk_ratio']:.1f}% (Percentage of call time prospect was speaking)</li>"
                html += f"</ul>"
        
        if 'count' in skill_data and skill_data['count'] is not None:
            if skill_name == 'discovery':
                html += f"<p><strong>Total Questions Asked:</strong> {skill_data['count']} (Total number of questions during discovery phase)</p>"
            elif skill_name == 'true_discovery':
                html += f"<p><strong>True Discovery Questions Asked:</strong> {skill_data['count']} (Number of deep discovery questions)</p>"
            elif skill_name == 'filler_use':
                html += f"<p><strong>Filler Words Count:</strong> {skill_data['count']} (Number of unnecessary filler words/phrases)</p>"
            else:
                html += f"<p><strong>Count:</strong> {skill_data['count']}</p>"

        # Add boolean criteria display
        boolean_criteria = []
        if skill_name == 'segment_awareness':
            if skill_data.get('segment_identified') is not None:
                boolean_criteria.append(("Segment Identified", skill_data['segment_identified']))
            if skill_data.get('tailored_questions') is not None:
                boolean_criteria.append(("Tailored Questions", skill_data['tailored_questions']))
            if skill_data.get('positioning_aligned') is not None:
                boolean_criteria.append(("Positioning Aligned", skill_data['positioning_aligned']))
        elif skill_name == 'value_prop':
            if skill_data.get('differentiators_reinforced') is not None:
                boolean_criteria.append(("Differentiators Reinforced", skill_data['differentiators_reinforced']))
            if skill_data.get('positioned_as_partner') is not None:
                boolean_criteria.append(("Positioned as Partner", skill_data['positioned_as_partner']))
            if skill_data.get('connected_to_situation') is not None:
                boolean_criteria.append(("Connected to Situation", skill_data['connected_to_situation']))
        elif skill_name == 'cap_ex':
            if skill_data.get('distinguished_from_banks') is not None:
                boolean_criteria.append(("Distinguished from Banks", skill_data['distinguished_from_banks']))
            if skill_data.get('emphasized_fixed_assets') is not None:
                boolean_criteria.append(("Emphasized Fixed Assets", skill_data['emphasized_fixed_assets']))
            if skill_data.get('explained_liquidity') is not None:
                boolean_criteria.append(("Explained Liquidity", skill_data['explained_liquidity']))
            if skill_data.get('aligned_with_priorities') is not None:
                boolean_criteria.append(("Aligned with Priorities", skill_data['aligned_with_priorities']))
        
        if boolean_criteria:
            html += f"<p><strong>Criteria Assessment:</strong></p>"
            html += f"<ul>"
            for criterion, result in boolean_criteria:
                icon = "✅" if result else "❌"
                html += f"<li>{icon} <strong>{criterion}:</strong> {'Yes' if result else 'No'}</li>"
            html += f"</ul>"

        html += "</div>"

    # Add final synthesis
    synthesis = results['final_synthesis']
    synthesis_grade = synthesis['grade']
    synthesis_reasoning = synthesis['reasoning']
    synthesis_class = normalize_grade_class(synthesis_grade)

    html += f"""
        <h2>🎯 Final Synthesis</h2>
        <div class="skill-card">
            <h3>Overall Performance</h3>
            <div class="grade {synthesis_class}">{synthesis_grade}</div>
            <p><strong>Assessment:</strong> {synthesis_reasoning}</p>
        </div>
    """

    # Add detailed metrics in a separate section if available
    has_metrics = any([
        synthesis.get('surface_questions') is not None,
        synthesis.get('true_discovery_questions') is not None,
        synthesis.get('filler_words') is not None,
        synthesis.get('rep_talk_ratio') is not None,
        synthesis.get('prospect_talk_ratio') is not None
    ])
    
    if has_metrics:
        html += """
        <h2>📊 Performance Metrics</h2>
        <div class="skill-card">
        """
        if synthesis.get('surface_questions') is not None:
            html += f"<p><strong>Surface Questions:</strong> {synthesis['surface_questions']} (Basic questions that don't count toward discovery score)</p>"
        if synthesis.get('true_discovery_questions') is not None:
            html += f"<p><strong>True Discovery Questions:</strong> {synthesis['true_discovery_questions']} (Deep discovery questions about role, authority, deal flow, etc.)</p>"
        if synthesis.get('filler_words') is not None:
            html += f"<p><strong>Filler Words:</strong> {synthesis['filler_words']}</p>"
        if synthesis.get('rep_talk_ratio') is not None:
            html += f"<p><strong>Rep Talk Ratio:</strong> {synthesis['rep_talk_ratio']:.1f}% (Percentage of call time rep was speaking)</p>"
        if synthesis.get('prospect_talk_ratio') is not None:
            html += f"<p><strong>Prospect Talk Ratio:</strong> {synthesis['prospect_talk_ratio']:.1f}% (Percentage of call time prospect was speaking)</p>"
        html += "</div>"

    # Add strengths in a separate section if available
    if synthesis.get('strengths') and len(synthesis['strengths']) > 0:
        html += """
        <h2>✅ Key Strengths</h2>
        <div class="skill-card">
        """
        for strength in synthesis['strengths'][:5]:  # Show first 5
            html += f"<p>• {strength}</p>"
        html += "</div>"

    # Add weaknesses in a separate section if available
    if synthesis.get('weaknesses') and len(synthesis['weaknesses']) > 0:
        html += """
        <h2>⚠️ Areas for Improvement</h2>
        <div class="skill-card">
        """
        for weakness in synthesis['weaknesses'][:5]:  # Show first 5
            html += f"<p>• {weakness}</p>"
        html += "</div>"

    # Add missed opportunities in a separate section if available
    if synthesis.get('missed_opportunities') and len(synthesis['missed_opportunities']) > 0:
        html += """
        <h2>🎯 Missed Opportunities</h2>
        <div class="skill-card">
        """
        for opp in synthesis['missed_opportunities'][:3]:  # Show first 3
            opportunity = opp.get('opportunity', 'Opportunity')
            corrective = opp.get('corrective', 'No corrective action specified')
            html += f"<p><strong>{opportunity}:</strong><br>{corrective}</p>"
        html += "</div>"

    html += """
        <p><em>The full transcript is attached to this email.</em></p>
    </body>
    </html>
    """

    return html

def build_email_with_attachment(to_email, subject, html_body, transcript_text, file_name, sender):
    """Build email with HTML body and transcript attachment."""
    message = MIMEMultipart()
    message["to"] = to_email
    message["from"] = sender
    message["subject"] = subject

    # HTML part
    message.attach(MIMEText(html_body, "html"))

    # Transcript as attachment
    attachment = MIMEBase("text", "plain")
    attachment.set_payload(transcript_text.encode("utf-8"))
    encoders.encode_base64(attachment)
    safe_name = file_name.replace(" ", "_").replace("/", "_")
    attachment.add_header("Content-Disposition", "attachment", filename=f"{safe_name}_transcript.txt")
    message.attach(attachment)

    return message
def send_grading_email(payload):
    """Send grading results email with transcript attachment."""


    file_name = payload['fileName']
    rep = payload['rep']
    transcript = payload['transcript']

 
    to_email = RECIPIENT_EMAIL


    # Create email subject + body with unique timestamp
    import time
    timestamp = int(time.time() * 1000)  # milliseconds
    subject = f"Sales Transcript Grading: {file_name} - {rep} [{timestamp}]"


    html_body = format_grading_html(payload, timestamp)

    email_message = build_email_with_attachment(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        transcript_text=transcript,
        file_name=file_name,
        sender=DOMAIN_SENDER
    )

    # Encode properly for Gmail API
    raw_message = base64.urlsafe_b64encode(email_message.as_bytes()).decode("utf-8")

    logger.info("📧 Creating Gmail service...")
    service = gmail_service()

    logger.info("📧 Sending email via Gmail API...")
    send_result = service.users().messages().send(
        userId="me",
        body={"raw": raw_message}
    ).execute()


    return send_result



def email_handler(event, context):
    # Parse Pub/Sub message
    decoded = base64.b64decode(event["data"]).decode("utf-8")
    if not decoded.strip():
        raise ValueError("Empty Pub/Sub message")
    payload = json.loads(decoded)
    
    file_id = payload.get('fileId')
    file_name = payload.get('fileName', 'unknown')
    transcript = payload.get('transcript', '')
    
    # Check if transcript is missing or empty
    if not transcript or not transcript.strip():
        logger.warning(f"⚠️ No transcript available for file {file_id} ({file_name}), skipping email")
        return {"status": "skipped", "reason": "no_transcript"}
    
    # Check if email already sent for this file
    try:
        drive = drive_service()
        file_metadata = drive.files().get(
            fileId=file_id,
            fields="appProperties",
            supportsAllDrives=True
        ).execute()
        
        app_props = file_metadata.get('appProperties', {})
        if app_props.get('email_sent') == 'true':
            logger.info(f"📧 Email already sent for file {file_id}, skipping")
            return {"status": "skipped", "reason": "already_sent"}
    except Exception as e:
        logger.warning(f"⚠️ Could not check email status for {file_id}: {e}")
    
    # Send the email
    result = send_grading_email(payload)
    
    # Mark as email sent
    try:
        drive.files().update(
            fileId=file_id,
            body={'appProperties': {'email_sent': 'true'}},
            supportsAllDrives=True
        ).execute()
        logger.info(f"✅ Marked file {file_id} as email sent")
    except Exception as e:
        logger.warning(f"⚠️ Could not mark email sent for {file_id}: {e}")
    
    return result
    
