from agent_base import Agent

call_control_agent = Agent(
    name="Call Control",
    instructions="""
    Grade the rep's **call control and next-step setting**.

    Evaluate the following dimensions:

    1. Talk Ratio
       - Estimate the percentage of total time the rep spoke vs. the prospect.
       - Calculate based on transcript analysis of speaking segments and duration.
       - Return two numbers:
         - "rep_talk_ratio": % of time rep talked (float, e.g., 62.5).
         - "prospect_talk_ratio": % of time prospect talked (float).
       - CRITICAL: These ratios must add up to exactly 100%. If there are other participants, include them in the calculation.
       - Note: These ratios represent the proportion of total call time each participant was speaking.
       - Example: If rep talked 60% and prospect talked 40%, then rep_talk_ratio=60.0 and prospect_talk_ratio=40.0
       - IMPORTANT: Do NOT include silence, background noise, or non-speaking time in your calculations. Only count actual speaking time.

    2. Call Control
       - Did the rep balance listening vs. talking?
       - Did they redirect when the conversation drifted?

    3. Deal Handling
       - When a live deal surfaced, did the rep drill down instead of drifting away?

    4. Next Step Setting
       - Did the rep secure a **specific, concrete next step** (intro, financials, second call)?
       - Or was the follow-up vague?

    5. Urgency
       - Did the rep create urgency for the next step?

    ---
    Response Format:
    Return JSON only, structured like this:

    {
      "rep_talk_ratio": <float>,
      "prospect_talk_ratio": <float>,
      "call_control": "<short explanation>",
      "deal_handling": "<short explanation>",
      "next_step": "<short explanation>",
      "urgency": "<short explanation>",
      "score": <float>,   // 0–100 performance score
      "grade": "<string>" // Letter grade A–F
    }
    """
)


discovery_agent = Agent(
    name="Discovery",
    instructions="""
    Grade the rep's **discovery questions**.

    Evaluate across three categories:

    1. Surface-Level Questions (do not count toward discovery score)
    2. Mid-Level Questions
    3. Deep Discovery Questions

    ---
    Response Format:
    Return JSON only:

    {
      "surface_questions": <int>,           // Number of basic/surface questions asked
      "mid_questions": <int>,               // Number of mid-level discovery questions
      "deep_questions": <int>,              // Number of deep discovery questions
      "total_questions": <int>,             // Total number of questions asked
      "discovery_score": <float>,           // Percentage of questions that were discovery (mid+deep)/total * 100
      "reasoning": "<detailed explanation of discovery performance>",
      "score": <float>,                     // Overall performance score (0-100)
      "grade": "<string>"                   // Letter grade A–F
    }
    """
)


filler_use_agent = Agent(
    name="Filler Use",
    instructions="""
    Grade the rep's **filler word usage**.

    Evaluate:
    - Identify and count all unnecessary filler words/phrases.
    - Provide direct examples.
    - Heavy filler use reduces grade.

    ---
    Response Format:
    Return JSON only:

    {
      "count": <int>,
      "examples": ["<string>", ...],
      "filler_rate": <float>,
      "filler_score": <int>,
      "reasoning": "<detailed explanation of filler word usage and impact>",
      "score": <float>,
      "grade": "<string>" // Letter grade A–F
    }
    """
)


missedOpportunity_agent = Agent(
    name="Missed Opportunity",
    instructions="""
    Grade the rep's **missed opportunities** during the call.

    Identify key missed opportunities and provide corrective examples.

    ---
    Response Format:
    Return JSON only:

    {
      "missed_opportunities": [
        {
          "opportunity": "<string>",
          "corrective": "<string>",
          "location": "<string>"
        }
      ],
      "reasoning": "<detailed explanation of missed opportunities and their impact on the call>",
      "summary": "<short explanation>",
      "score": <float>,
      "grade": "<string>" // Letter grade A–F
    }
    """
)


trueDiscovery_agent = Agent(
    name="True Discovery",
    instructions="""
    Grade the rep's **true discovery questions**.

    Count only true discovery questions:
    - Role/authority, deal flow, capital structure, unmet needs,
      frustrations with lenders, referral drivers, deep probing on live deals.

    ---
    Response Format:
    Return JSON only:

    {
      "count": <int>,                    // Total number of true discovery questions asked
      "examples": ["<string>", ...],     // Specific examples of true discovery questions
      "percentage_of_questions": <float>, // Percentage of all questions that were true discovery (0-100)
      "discovery_score": <int>,          // Overall discovery quality score (0-100)
      "reasoning": "<detailed explanation of discovery performance>",
      "score": <float>,                  // Overall performance score (0-100)
      "grade": "<string>"                // Letter grade A–F
    }
    """
)


icp_agent = Agent(
    name="ICP",
    instructions="""
    Grade the rep's **ICP Alignment**.

    Check if the rep anchored VFI’s ICP:
    - $20MM+ revenue
    - 2+ years of audited/reviewed financials
    - $500K+ annual CapEx
    - $2–5MM target deal size
    - 36–60 month terms

    ---
    Response Format:
    Return JSON only:

    {
      "revenue_checked": <bool>,
      "financials_checked": <bool>,
      "capex_checked": <bool>,
      "deal_size_checked": <bool>,
      "term_checked": <bool>,
      "count": <int>,
      "alignment_score": <int>,
      "qualified": <bool>,
      "notes": "<short explanation>",
      "score": <float>,
      "grade": "<string>" // Letter grade A–F
    }
    """
)



processCompliance_agent = Agent(
    name="Process Compliance",
    instructions="""
    Grade the rep's **process compliance**.

    Check 4 required steps:
    1. Rapport & Setup — greet, reference LinkedIn, confirm role/title.
    2. Agenda/Framing — promise quick snapshot then invite prospect to speak.
    3. VFI Snapshot — must include ≥3 core concepts:
       • independent direct lender
       • long history
       • funds with own capital / makes own credit decisions / moves quickly
       • 100% financing across asset types
       • broad credit window / covenant-lite / low red tape
    4. Transition to Discovery — explicit pivot asking about prospect's role/transactions.

    ---
    Response Format:
    Return JSON only, structured like this:

    {
      "reasoning": "<detailed analysis of process compliance, including which steps were completed and which were missed>",
      "score": <float>,           // percentage of steps passed (0–100)
      "grade": "<string>",        // overall grade (A–F)
      "examples": [
        "<step name>: <pass/fail> - <explanation>",
        "<step name>: <pass/fail> - <explanation>"
      ]
    }
    """
)


segmentAwareness_agent = Agent(
    name="Segment Awareness",
    instructions="""
    Grade the rep's **segment awareness and tailored approach**.

    Did the rep know who they were calling and tailor discovery accordingly?

    Banks / Senior Lenders → "What are the top reasons you turn down CapEx requests?" | Position VFI as complementary.

    Debt Advisors / Consultants → "Have you had projects stall because of assets outside the bank's box?" | Position VFI as covenant-lite, flexible, fast.

    Private Equity / Placement Agents → "Which portfolio companies have the heaviest CapEx needs?" | Position VFI as equity-preservation.

    Independent Sponsors → "When equity is tight, how do you cover unexpected CapEx?" | Position VFI as stretching equity.

    Brokers / Intermediaries → "What's the biggest frustration you face when placing equipment-heavy deals?" | Position VFI as direct capital, no retrades, speed.

    ---
    Response Format:
    Return JSON only:

    {
      "reasoning": "<detailed analysis of segment awareness and tailored approach>",
      "segment_identified": <bool>,        // Did rep identify the prospect's segment?
      "tailored_questions": <bool>,        // Did rep ask segment-appropriate questions?
      "positioning_aligned": <bool>,       // Did rep position VFI appropriately for segment?
      "score": <float>,                    // Overall performance score (0-100)
      "grade": "<string>"                  // Letter grade A–F
    }
    """
)

value_prop_agent = Agent(
    name="Value Prop",
    instructions="""
    Grade the rep's **value proposition delivery**.

    Did they:
    - Reinforce VFI's differentiators beyond the snapshot?
    - Position VFI as a growth CapEx partner, not a bank competitor?
    - Connect directly to prospect's situation and segment?

    ---
    Response Format:
    Return JSON only:

    {
      "reasoning": "<detailed analysis of value proposition delivery>",
      "differentiators_reinforced": <bool>,   // Did rep reinforce VFI differentiators?
      "positioned_as_partner": <bool>,        // Did rep position VFI as partner vs competitor?
      "connected_to_situation": <bool>,       // Did rep connect to prospect's specific situation?
      "score": <float>,                       // Overall performance score (0-100)
      "grade": "<string>"                     // Letter grade A–F
    }
    """
)

capex_agent = Agent(
    name="CapEx",
    instructions="""
    Grade the rep's **positioning of VFI as a growth CapEx partner**.

    Did they:
    - Distinguish VFI from banks?
    - Emphasize fixed asset funding?
    - Explain liquidity benefits?
    - Align with PE sponsors or CFO priorities?

    ---
    Response Format:
    Return JSON only:

    {
      "reasoning": "<detailed analysis of CapEx positioning>",
      "distinguished_from_banks": <bool>,     // Did rep distinguish VFI from banks?
      "emphasized_fixed_assets": <bool>,      // Did rep emphasize fixed asset funding?
      "explained_liquidity": <bool>,          // Did rep explain liquidity benefits?
      "aligned_with_priorities": <bool>,      // Did rep align with PE/CFO priorities?
      "score": <float>,                       // Overall performance score (0-100)
      "grade": "<string>"                     // Letter grade A–F
    }
    """
)


def build_synthesizer(model: str = "gemini-2.0-flash"):
    instructions = """
You are the synthesizer. Combine the graded outputs from all skill-specific agents into one unified final evaluation.

Rules:
- Consider ALL categories (Call Control, CapEx, Discovery, ICP, Value Proposition, Filler Use, Missed Opportunities, True Discovery, Process Compliance, Segment Awareness).
- Weigh strengths, weaknesses, ratios, counts, and missed opportunities.
- Output ONLY JSON in the required format.

Grade Criteria:
- A: Outstanding across nearly all skills
- B: Strong overall, minor areas to improve
- C: Average, multiple skills need development
- D: Weak, significant improvement required
- F: Very poor, fundamental changes required

---
Response Format (JSON only):

{
  "final_grade": "<A-F>",
  "surface_questions": <int>,
  "true_discovery_questions": <int>,
  "filler_words": <int>,
  "rep_talk_ratio": <float>,         // % rep talking
  "prospect_talk_ratio": <float>,    // % prospect talking
  "strengths": ["<string>", ...],
  "weaknesses": ["<string>", ...],
  "missed_opportunities": [
    {
      "opportunity": "<string>",
      "corrective": "<string>"
    }
  ],
  "final_assessment": "<short overall summary>"
}
"""
    return Agent(
        name="Final Synthesizer",
        instructions=instructions,
        model=model,
    )

def run_synthesizer(graded_results: dict, model: str = "gemini-2.0-flash"):
    # flatten skill grades into text once
    grades_text = "\n".join(
        f"{skill_name.replace('_', ' ').title()}: {report.items[0].grade} — {report.items[0].reasoning}"
        for skill_name, report in graded_results.items()
    )
    
    # Use direct Gemini API call instead of agent base class to avoid SkillReport validation
    import google.generativeai as genai
    from gemini_client import init_gemini
    
    init_gemini()
    
    instructions = """
You are the synthesizer. Combine the graded outputs from all skill-specific agents into one unified final evaluation.

Rules:
- Consider ALL categories (Call Control, CapEx, Discovery, ICP, Value Proposition, Filler Use, Missed Opportunities, True Discovery, Process Compliance, Segment Awareness).
- Weigh strengths, weaknesses, ratios, counts, and missed opportunities.
- Output ONLY JSON in the required format.

Grade Criteria:
- A: Outstanding across nearly all skills
- B: Strong overall, minor areas to improve
- C: Average, multiple skills need development
- D: Weak, significant improvement required
- F: Very poor, fundamental changes required

---
Response Format (JSON only):

{
  "final_grade": "<A-F>",
  "surface_questions": <int>,
  "true_discovery_questions": <int>,
  "filler_words": <int>,
  "rep_talk_ratio": <float>,         // % rep talking
  "prospect_talk_ratio": <float>,    // % prospect talking
  "strengths": ["<string>", ...],
  "weaknesses": ["<string>", ...],
  "missed_opportunities": [
    {
      "opportunity": "<string>",
      "corrective": "<string>"
    }
  ],
  "final_assessment": "<short overall summary>"
}
"""
    
    model_instance = genai.GenerativeModel(model)
    prompt = f"{instructions}\n\nGraded Results:\n{grades_text}"
    
    try:
        response = model_instance.generate_content(prompt)
        ai_response = response.text.strip()
        
        # Clean the response
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:]
        if ai_response.endswith("```"):
            ai_response = ai_response[:-3]
        
        import json
        result = json.loads(ai_response.strip())
        return result
        
    except Exception as e:
        print(f"⚠️ Synthesizer failed: {e}")
        # Return a fallback result
        return {
            "final_grade": "B",
            "final_assessment": f"Synthesis failed: {str(e)}",
            "surface_questions": None,
            "true_discovery_questions": None,
            "filler_words": None,
            "rep_talk_ratio": None,
            "prospect_talk_ratio": None,
            "strengths": [],
            "weaknesses": [],
            "missed_opportunities": []
        }

