# grading_manager.py
import os, asyncio, time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from openAI_client import get_client

load_dotenv()  # load first

from Synthesizer_agent import synthesize
from openai import OpenAI
from callControl import callControl_grader_agent
from capEx import positioning_grader_agent
from discovery_grader_agent import discovery_grader_agent
from ideal_customer_agent import idealCustomer_grader_agent
from VFI_value_agent import VFIValue_grader_agent
from email_logic import EmailAgent
# Read the key

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")


# Define the client


class gradingManager: 

    
    @staticmethod
    def read(): 
        with open("transcript.txt", "r", encoding="utf-8") as f:
            transcript =  f.read()
            return transcript

    async def grade_all(self, transcript: str) -> dict:
        start_time = time.time()
        print("🚀 Starting Troy Project - Full Grading...")
        
        results = {}

        # Run all grading tasks concurrently
        tasks = [
            callControl_grader_agent(transcript),
            positioning_grader_agent(transcript),
            discovery_grader_agent(transcript),
            idealCustomer_grader_agent(transcript),
            VFIValue_grader_agent(transcript)
        ]
        
        # Wait for all tasks to complete
        grading_results = await asyncio.gather(*tasks)
        
        # Map results to their respective keys
        skill_names = ["call_control", "positioning", "discovery", "icp", "value_prop"]
        results = dict(zip(skill_names, grading_results))

        # Print results
        print("\n📊 GRADING RESULTS:")
        for skill, report in results.items():
            item = report.items[0]   # each SkillReport contains a GradeItem
            print(f"  • {skill.replace('_', ' ').title()}: {item.grade} — {item.reasoning}")

        # Synthesize results
        synthesis_result = synthesize(results)
        
        total_time = time.time() - start_time
        print(f"\n✅ Full grading completed in {total_time:.2f}s")
        
        return results, synthesis_result

    def save_results_to_file(self, results: dict, synthesis_result: str, filename: str = None):
        """Save grading results to a text file on desktop"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Save to desktop with just timestamp as filename
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



async def main():
    
    grader = gradingManager()
    try:
        transcript = grader.read()
    except FileNotFoundError:
        transcript = "No transcript file found. Using placeholder for grading."

    results, synthesis_result = await grader.grade_all(transcript)

    grader.save_results_to_file(results, synthesis_result)

    # Run the agent
    agent = EmailAgent()
    outcome = agent.run(results, synthesis_result)

    print(f"🎉 Grading + Email outcome: {outcome}")

if __name__ == "__main__":
    asyncio.run(main())