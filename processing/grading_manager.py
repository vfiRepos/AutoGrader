import os, time
from datetime import datetime
from pathlib import Path
from unittest import result

from agent_logic import run_synthesizer
from agent_logic import discovery_agent
from agent_logic import icp_agent
from agent_logic import value_prop_agent
from agent_logic import call_control_agent
from agent_logic import capex_agent


class gradingManager: 
    @staticmethod
    def read(): 
        with open("transcript.txt", "r", encoding="utf-8") as f:
            transcript = f.read()
            return transcript

    
    def grade_all(self, transcript: str):
        print(f"🔄 Grading transcript...")

        results = {
            "call_control": call_control_agent.run(transcript),
            "cap_ex": capex_agent.run(transcript),
            "discovery": discovery_agent.run(transcript),
            "icp": icp_agent.run(transcript),
            "value_prop": value_prop_agent.run(transcript),
        }

        synthesis_result = run_synthesizer(results, "gemini-1.5-flash")

        # 📊 Detailed results output
        print("📊 GRADING RESULTS:")
        for skill, report in results.items():
            print(f"  • {skill}: {report.items[0].grade} — {report.items[0].reasoning}")

        print("\n📝 FINAL SYNTHESIS:")
        print(f"  Final Grade: {synthesis_result.items[0].grade}")
        print(f"  Reasoning: {synthesis_result.items[0].reasoning}")

        return results, synthesis_result





def main():
    grader = gradingManager()
    try:
        transcript = grader.read()
    except FileNotFoundError:
        transcript = "No transcript file found. Using placeholder for grading."

    results, synthesis_result = grader.grade_all(transcript)

    return results, synthesis_result