from agent_base import Agent

call_control_agent = Agent(
    name="Call Control",
    instructions="""
    Grade the rep's **call control and next-step setting**.

    Did they:
    - Balance listening vs. talking?
    - When a live deal surfaced, did they drill down instead of drifting away?
    - Secure a specific next step (intro, financials, second call), not vague follow-up?
    - Create urgency?

    IMPORTANT: In your JSON response, include:
    - "ratio": estimated rep vs. prospect talk ratio as percentage (e.g., 60.0 for 60% rep talking)
    """
)

discovery_agent = Agent(
    name="Discovery",
    instructions="""
    Grade the rep's **discovery questions**.

    

Surface-Level Questions (do not count toward discovery total)
• Small talk (“How’s it going?”)
• Simple confirmations (“Is that correct?”)
• Non-strategic asks without probing deeper.

"""
)
fillerUse_agent = Agent(
    name="Filler Use",
    instructions="""
    Grade the rep's **filler use**.
    - Track number of unnecessary filler words (e.g., "honestly," "to be frank," "it's one where," "so yeah," "go ahead and…").
    - Heavy filler reduces grade — it weakens authority and clarity.

    IMPORTANT: In your JSON response, include:
    - "count": exact number of filler words found
    - "examples": list of specific filler phrases used
    """
)

missedOpportunity_agent = Agent(
    name="Missed Opportunity",
    instructions="""
    Grade the rep's **missed opportunity**.

    List every key missed opportunity.

    For each, provide a corrective example of what should have been said.

    IMPORTANT: In your JSON response, include:
    - "examples": array of STRINGS, where each string combines the missed opportunity and corrective example

    Format each example as a single string like:
    "Rep didn't stress VFI's edge in oil & gas - Should have said: 'Most lenders are pulling back in oil & gas — that's exactly where VFI's broad credit window comes in. We can evaluate this $15MM compressor deal quickly and give your client a real option.'"

    Each item in the examples array should be ONE string that includes both the problem and the solution.
    """
)
trueDiscovery_agent = Agent(
    name="True Discovery",
    instructions="""
    Grade the rep's **true discovery questions**.
    True Discovery Questions (counted)
    • Role & decision-making authority.
    • Deal flow: frequency, size, sectors.
    • Capital structure & unmet CapEx needs.
    • Frustrations with banks/lenders (kick-outs, retrades, covenants).
    • Referral drivers (speed, flexibility, certainty).
    • Deep probing on live deals (financials, timing, collateral specifics).

    IMPORTANT: In your JSON response, include:
    - "count": exact number of true discovery questions asked
    - "examples": list of the specific discovery questions used

    """
)

icp_agent = Agent(
    name="ICP",
    instructions="""
    Grade the rep's **ICP Alignment**.

    Did they:
    - Did they anchor VFI’s ICP correctly:
    - $20MM+ revenue.
    - 2+ years of audited/reviewed financials.
    - $500K+ annual CapEx.
    - 2–5MM target deal size, 36–60 month terms.

Did they qualify/disqualify based on ICP?
    """
)

processCompliance_agent = Agent(
    name="Process",
    instructions="""
    Grade the rep's **process**.
    Task: check 4 steps (Rapport & Setup; Agenda/Framing; VFI Snapshot; Transition to Discovery), extract exact excerpt if present, and output a compact JSON + 1-line human verdict.


    Rapport & Setup — greet, reference LinkedIn, confirm role/title.

    Agenda/Framing — promise quick snapshot then invite prospect to speak.

    VFI Snapshot — must include ≥3 core concepts (independent direct lender; long history; funds with own capital/makes own credit decisions/moves quickly; 100% financing across asset types; broad credit window / covenant-lite / low red tape).

    Transition to Discovery — explicit pivot asking about prospect’s role/transactions.

    If no evidence for a step → result="fail", quote="", timestamp=null, confidence≤0.4.
    """
)

segmentAwareness_agent = Agent(
    name="Segment Awareness",
    instructions="""
    Did the rep know who they were calling and tailor discovery accordingly?

    Banks / Senior Lenders → “What are the top reasons you turn down CapEx requests?” | Position VFI as complementary.

    Debt Advisors / Consultants → “Have you had projects stall because of assets outside the bank’s box?” | Position VFI as covenant-lite, flexible, fast.

    Private Equity / Placement Agents → “Which portfolio companies have the heaviest CapEx needs?” | Position VFI as equity-preservation.

    Independent Sponsors → “When equity is tight, how do you cover unexpected CapEx?” | Position VFI as stretching equity.

    Brokers / Intermediaries → “What’s the biggest frustration you face when placing equipment-heavy deals?” | Position VFI as direct capital, no retrades, speed.
"""
)

value_prop_agent = Agent(
    name="Value Prop",
    instructions="""
    Grade the rep's **value proposition**.

    Did they:
    - Did they reinforce VFI’s differentiators beyond the snapshot?

    - Did they position VFI as a growth CapEx partner, not a bank competitor?

    - Did they connect directly to prospect’s situation and segment?
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
    """
)


def build_synthesizer(model: str = "gemini-1.5-flash"):
    instructions = """
You are the synthesizer. Combine the following graded skill areas into one final evaluation.

Based on the individual skill grades and reasoning, provide an overall assessment of the sales representative's performance.

Grade Criteria:
- A: Outstanding performance across all skills with excellent execution
- B: Strong performance with good skills and minor areas for improvement
- C: Average performance with room for development in multiple areas
- D: Below average performance requiring significant improvement
- F: Poor performance needing fundamental changes

Provide only:
- A final grade (A–F)

# of surface-level questions

# of true discovery questions

# of filler words used

- Rep vs. prospect talk ratio (%)

-Strengths

- Weaknesses

- Missed opportunities (with what should have been said)

- Final assessment

Evaluate all skill areas including:
- Call Control: listening vs. talking balance, next-step setting, urgency creation
- CapEx: positioning VFI as growth CapEx partner vs. banks
- Discovery: strategic questioning quality and depth
- ICP: alignment with VFI's ideal customer profile
- Value Proposition: differentiation and prospect-specific tailoring
- Filler Use: unnecessary filler words that reduce authority
- Missed Opportunities: key moments where better responses could have been given
- True Discovery: deep probing questions about role, deal flow, capital structure
- Process Compliance: adherence to call structure (Rapport, Agenda, VFI Snapshot, Discovery transition)
- Segment Awareness: tailoring approach based on prospect type (banks, PE, sponsors, etc.)
"""
    return Agent(
        name="Final Synthesizer",
        instructions=instructions,
        model=model,
    )

def run_synthesizer(graded_results: dict, model: str = "gemini-1.5-flash"):
    # flatten skill grades into text once
    grades_text = "\n".join(
        f"{skill_name.replace('_', ' ').title()}: {report.items[0].grade} — {report.items[0].reasoning}"
        for skill_name, report in graded_results.items()
    )
    agent = build_synthesizer(model)
    return agent.run(grades_text)   # 👈 always pass grades at runtime

