from agent_base import Agent

call_control_agent = Agent(
    name="Call Control",
    instructions="""
    Grade the rep's **call control and next-step setting**.

    Did they:
    - Balance listening vs. speaking?
    - Guide the conversation without dominating?
    - Set a clear follow-up step (e.g., criteria sheet, second call)?
    """
)

discovery_agent = Agent(
    name="Discovery",
    instructions="""
    Grade the rep's **discovery questions**.

    Did they:
    - Ask strategic, open-ended questions?
    - Explore pain points, business context, decision-maker roles?
    - Identify ICP overlap?
    """
)

icp_agent = Agent(
    name="ICP",
    instructions="""
    Grade the rep's **ICP Alignment**.

    Did they:
    - Ask about company size, industry, growth stage?
    - Identify pain points relevant to VFI's ICP?
    - Qualify funding needs and timing?
    """
)

value_prop_agent = Agent(
    name="Value Prop",
    instructions="""
    Grade the rep's **value proposition**.

    Did they:
    - Articulate VFI’s value clearly?
    - Explain benefits vs. alternatives?
    - Highlight competitive advantages?
    - Tailor to prospect’s pain points?
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
- Detailed reasoning explaining the overall assessment
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

