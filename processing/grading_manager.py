import os, time
from datetime import datetime
from pathlib import Path

from Synthesizer_agent import build_synthesizer
from callControl import call_control_agent
from capEx import positioning_agent
from discovery_grader_agent import discovery_agent
from ideal_customer_agent import icp_agent
from VFI_value_agent import value_prop_agent
from email_logic import EmailAgent


class gradingManager: 
    @staticmethod
    def read(): 
        with open("transcript.txt", "r", encoding="utf-8") as f:
            transcript = f.read()
            return transcript

    def grade_all(self, transcript: str) -> dict:
        start_time = time.time()
        print("🚀 Starting Troy Project - Full Grading...")

        # Run graders sequentially (they’re already encapsulated in Agent.run)
        results = {
            "call_control": call_control_agent.run(transcript),
            "positioning": positioning_agent.run(transcript),
            "discovery": discovery_agent.run(transcript),
            "icp": icp_agent.run(transcript),
            "value_prop": value_prop_agent.run(transcript),
        }

        # Print results
        print("\n📊 GRADING RESULTS:")
        for skill, report in results.items():
            item = report.items[0]
            print(f"  • {skill.replace('_', ' ').title()}: {item.grade} — {item.reasoning}")

        # Synthesize results
        synth_agent = build_synthesizer(results)
        synthesis_result = synth_agent.run("")

        total_time = time.time() - start_time
        print(f"\n✅ Full grading completed in {total_time:.2f}s")

        return results, synthesis_result

    def save_results_to_file(self, results: dict, synthesis_result: str, filename: str = None):
        """Save grading results to a text file on desktop"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            desktop_path = Path.home() / "Desktop"
            filename = desktop_path / f"{timestamp}.txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write("SALES CALL GRADING RESULTS\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("SKILL GRADES:\n")
            f.write("-" * 20 + "\n")
            for skill, report in results.items():
                item = report.items[0]
                f.write(f"{skill.replace('_', ' ').title()}: {item.grade}\n")
                f.write(f"Reasoning: {item.reasoning}\n")
                f.write("-" * 40 + "\n")
            
            f.write("\nFINAL SYNTHESIS:\n")
            f.write("-" * 20 + "\n")
            f.write(f"{synthesis_result}\n")
            f.write("-" * 40 + "\n")
            
            f.write(f"\nResults saved to: {filename}\n")

        print(f"💾 Results saved to: {filename}")
        return filename


def main():
    grader = gradingManager()
    try:
        transcript = grader.read()
    except FileNotFoundError:
        transcript = "No transcript file found. Using placeholder for grading."

    results, synthesis_result = grader.grade_all(transcript)
    grader.save_results_to_file(results, synthesis_result)

    # Run the email agent
    agent = EmailAgent()
    outcome = agent.run(results, synthesis_result)

    print(f"🎉 Grading + Email outcome: {outcome}")


if __name__ == "__main__":
    main()
