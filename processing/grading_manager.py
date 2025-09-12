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
from agent_logic import fillerUse_agent
from agent_logic import missedOpportunity_agent
from agent_logic import trueDiscovery_agent
from agent_logic import processCompliance_agent
from agent_logic import segmentAwareness_agent


class gradingManager: 
    @staticmethod
    def read(): 
        with open("transcript.txt", "r", encoding="utf-8") as f:
            transcript = f.read()
            return transcript

    
    def grade_all(self, transcript: str):
        print(f"🔄 Grading transcript...")

        results = {
            "call_control": call_control_agent.run(transcript, include_metrics=True),  # Talk ratio tracking
            "cap_ex": capex_agent.run(transcript),
            "discovery": discovery_agent.run(transcript),
            "icp": icp_agent.run(transcript),
            "value_prop": value_prop_agent.run(transcript),
            "filler_use": fillerUse_agent.run(transcript, include_metrics=True),  # Count filler words
            "missed_opportunity": missedOpportunity_agent.run(transcript, include_metrics=True),  # List specific examples
            "true_discovery": trueDiscovery_agent.run(transcript, include_metrics=True),  # Count discovery questions
            "process_compliance": processCompliance_agent.run(transcript),  # Structured process check
            "segment_awareness": segmentAwareness_agent.run(transcript),  # Prospect type analysis
        }

        synthesis_result = run_synthesizer(results, "gemini-1.5-flash")

        # 📊 Detailed results output
        print("📊 GRADING RESULTS:")
        for skill, report in results.items():
            item = report.items[0]
            print(f"  • {skill}: {item.grade}")

            # Show enhanced metrics if available
            if hasattr(item, 'count') and item.count is not None:
                print(f"    📊 Count: {item.count}")
            if hasattr(item, 'ratio') and item.ratio is not None:
                print(f"    📊 Ratio: {item.ratio:.1f}%")
            if hasattr(item, 'examples') and item.examples:
                print(f"    📝 Examples: {', '.join(item.examples[:3])}")  # Show first 3 examples

            print(f"    💬 {item.reasoning}")
            print()

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