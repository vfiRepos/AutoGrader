import os, time
import logging
from datetime import datetime
from pathlib import Path

from agent_logic import run_synthesizer
from agent_logic import discovery_agent
from agent_logic import icp_agent
from agent_logic import value_prop_agent
from agent_logic import call_control_agent
from agent_logic import capex_agent
from agent_logic import filler_use_agent
from agent_logic import missedOpportunity_agent
from agent_logic import trueDiscovery_agent
from agent_logic import processCompliance_agent
from agent_logic import segmentAwareness_agent
from pydantic_formating import SkillReport, GradeItem, FlexibleSkillReport
import logging


class gradingManager: 
    @staticmethod
    def read(): 
        with open("transcript.txt", "r", encoding="utf-8") as f:
            transcript = f.read()
            return transcript

    @staticmethod
    def convert_to_skill_report(agent_result, skill_name):
        """Convert agent result to SkillReport format, handling both old and new formats."""
        try:
            # Check if it's already a SkillReport (old format)
            if hasattr(agent_result, 'items') and isinstance(agent_result.items, list):
                return agent_result
            
            # Handle new AI response format
            if isinstance(agent_result, dict):
                # Extract data from the new AI response structure
                overall_grade = "N/A"
                overall_reasoning = "No reasoning available"
                examples = []
                count = None
                ratio = None
                
                # Boolean fields for specific criteria
                segment_identified = None
                tailored_questions = None
                positioning_aligned = None
                differentiators_reinforced = None
                positioned_as_partner = None
                connected_to_situation = None
                distinguished_from_banks = None
                emphasized_fixed_assets = None
                explained_liquidity = None
                aligned_with_priorities = None
                
                # Look for direct grade in the response
                if 'grade' in agent_result:
                    overall_grade = agent_result['grade']
                
                # Look for reasoning in various possible fields
                reasoning_fields = ['reasoning', 'call_control', 'deal_handling', 'analysis', 'explanation', 'notes']
                for field in reasoning_fields:
                    if field in agent_result and agent_result[field]:
                        if overall_reasoning == "No reasoning available":
                            overall_reasoning = str(agent_result[field])
                        else:
                            overall_reasoning += f" {str(agent_result[field])}"
                
                # Extract metrics based on skill type and available fields
                if skill_name == 'call_control':
                    # For call control, look for talk ratios and validate they add up to 100%
                    rep_ratio = agent_result.get('rep_talk_ratio', 0)
                    prospect_ratio = agent_result.get('prospect_talk_ratio', 0)
                    
                    # Validate and fix ratios if they don't add up to 100%
                    total_ratio = rep_ratio + prospect_ratio
                    if total_ratio > 0:
                        if abs(total_ratio - 100) > 1:  # Allow 1% tolerance
                            # Normalize ratios to add up to 100%
                            original_rep = rep_ratio
                            original_prospect = prospect_ratio
                            rep_ratio = (rep_ratio / total_ratio) * 100
                            prospect_ratio = (prospect_ratio / total_ratio) * 100
                            logging.warning(f"⚠️ Talk ratios didn't add up to 100% (was {total_ratio:.1f}%), normalized from rep: {original_rep:.1f}%, prospect: {original_prospect:.1f}% to rep: {rep_ratio:.1f}%, prospect: {prospect_ratio:.1f}%")
                        else:
                            logging.info(f"✅ Talk ratios add up correctly: rep {rep_ratio:.1f}%, prospect {prospect_ratio:.1f}% (total: {total_ratio:.1f}%)")
                    else:
                        logging.warning(f"⚠️ Both talk ratios are 0, setting default 50/50 split")
                        rep_ratio = 50.0
                        prospect_ratio = 50.0
                    
                    # Use rep ratio as the primary ratio for display
                    ratio = rep_ratio
                    
                    # Store both ratios in agent_result for emailer
                    agent_result['rep_talk_ratio'] = rep_ratio
                    agent_result['prospect_talk_ratio'] = prospect_ratio
                elif skill_name == 'filler_use':
                    # For filler use, look for count
                    if 'filler_count' in agent_result:
                        count = agent_result['filler_count']
                    elif 'count' in agent_result:
                        count = agent_result['count']
                elif skill_name == 'missed_opportunity':
                    # For missed opportunities, look for examples or missed_opportunities
                    if 'examples' in agent_result:
                        if isinstance(agent_result['examples'], list):
                            examples = agent_result['examples']
                        else:
                            examples = [str(agent_result['examples'])]
                    elif 'missed_opportunities' in agent_result:
                        # Handle the complex missed_opportunities structure
                        if isinstance(agent_result['missed_opportunities'], list):
                            examples = []
                            for opp in agent_result['missed_opportunities']:
                                if isinstance(opp, dict):
                                    opportunity = opp.get('opportunity', 'Unknown opportunity')
                                    corrective = opp.get('corrective', 'No corrective action')
                                    examples.append(f"{opportunity}: {corrective}")
                                else:
                                    examples.append(str(opp))
                        else:
                            examples = [str(agent_result['missed_opportunities'])]
                elif skill_name == 'discovery':
                    # For discovery agent, use total questions as count and discovery score as ratio
                    if 'total_questions' in agent_result:
                        count = agent_result['total_questions']
                    elif 'count' in agent_result:
                        count = agent_result['count']
                    elif 'surface_questions' in agent_result:
                        count = agent_result['surface_questions']
                    elif 'deep_questions' in agent_result:
                        count = agent_result['deep_questions']
                    
                    # Look for discovery score as ratio
                    if 'discovery_score' in agent_result:
                        ratio = agent_result['discovery_score']
                    elif 'percentage_of_questions' in agent_result:
                        ratio = agent_result['percentage_of_questions']
                elif skill_name == 'true_discovery':
                    # For true discovery agent, look for question counts and scores
                    if 'count' in agent_result:
                        count = agent_result['count']
                    elif 'surface_questions' in agent_result:
                        count = agent_result['surface_questions']
                    elif 'deep_questions' in agent_result:
                        count = agent_result['deep_questions']
                    
                    # Look for discovery score as ratio
                    if 'discovery_score' in agent_result:
                        ratio = agent_result['discovery_score']
                    elif 'percentage_of_questions' in agent_result:
                        ratio = agent_result['percentage_of_questions']
                    
                    # Look for examples
                    if 'examples' in agent_result:
                        if isinstance(agent_result['examples'], list):
                            examples = agent_result['examples']
                        else:
                            examples = [str(agent_result['examples'])]
                
                # Extract boolean fields based on skill type
                if skill_name == 'segment_awareness':
                    segment_identified = agent_result.get('segment_identified')
                    tailored_questions = agent_result.get('tailored_questions')
                    positioning_aligned = agent_result.get('positioning_aligned')
                elif skill_name == 'value_prop':
                    differentiators_reinforced = agent_result.get('differentiators_reinforced')
                    positioned_as_partner = agent_result.get('positioned_as_partner')
                    connected_to_situation = agent_result.get('connected_to_situation')
                elif skill_name == 'cap_ex':
                    distinguished_from_banks = agent_result.get('distinguished_from_banks')
                    emphasized_fixed_assets = agent_result.get('emphasized_fixed_assets')
                    explained_liquidity = agent_result.get('explained_liquidity')
                    aligned_with_priorities = agent_result.get('aligned_with_priorities')
                
                # If we still don't have a grade, mark as unable to run agent
                if overall_grade == "N/A":
                    overall_grade = "Unable to run agent"
                    overall_reasoning = "Agent failed to provide a grade or reasoning"
                
                # Create GradeItem with extracted data
                grade_item = GradeItem(
                    skill=skill_name,
                    grade=overall_grade,
                    reasoning=overall_reasoning,
                    count=count,
                    examples=examples if examples else None,
                    ratio=ratio,
                    segment_identified=segment_identified,
                    tailored_questions=tailored_questions,
                    positioning_aligned=positioning_aligned,
                    differentiators_reinforced=differentiators_reinforced,
                    positioned_as_partner=positioned_as_partner,
                    connected_to_situation=connected_to_situation,
                    distinguished_from_banks=distinguished_from_banks,
                    emphasized_fixed_assets=emphasized_fixed_assets,
                    explained_liquidity=explained_liquidity,
                    aligned_with_priorities=aligned_with_priorities
                )
                return SkillReport(items=[grade_item])
            else:
                # Fallback for unexpected format
                print(f"⚠️ Unexpected format for {skill_name}: {type(agent_result)}")
                fallback_item = GradeItem(
                    skill=skill_name,
                    grade="N/A",
                    reasoning="Unexpected response format"
                )
                return SkillReport(items=[fallback_item])
                
        except Exception as e:
            print(f"⚠️ Error converting {skill_name} result: {e}")
            # Fallback: create a basic SkillReport
            fallback_item = GradeItem(
                skill=skill_name,
                grade="N/A",
                reasoning=f"Failed to parse agent response: {str(e)}"
            )
            return SkillReport(items=[fallback_item])

    
    def grade_all(self, transcript: str):
        print(f"🔄 Grading transcript...")

        # Run all agents
        raw_results = {
            "call_control": call_control_agent.run(transcript, include_metrics=True),  # Talk ratio tracking
            "cap_ex": capex_agent.run(transcript),
            "discovery": discovery_agent.run(transcript),
            "icp": icp_agent.run(transcript),
            "value_prop": value_prop_agent.run(transcript),
            "filler_use": filler_use_agent.run(transcript, include_metrics=True),  # Count filler words
            "missed_opportunity": missedOpportunity_agent.run(transcript, include_metrics=True),  # List specific examples
            "true_discovery": trueDiscovery_agent.run(transcript, include_metrics=True),  # Count discovery questions
            "process_compliance": processCompliance_agent.run(transcript),  # Structured process check
            "segment_awareness": segmentAwareness_agent.run(transcript),  # Prospect type analysis
        }

        # Convert all results to consistent SkillReport format
        results = {}
        for skill_name, raw_result in raw_results.items():
            results[skill_name] = self.convert_to_skill_report(raw_result, skill_name)

        synthesis_result = run_synthesizer(results, "gemini-2.0-flash")
        # The synthesizer returns a dict, not a SkillReport, so we don't need to convert it

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
        if synthesis_result and isinstance(synthesis_result, dict):
            print(f"  Final Grade: {synthesis_result.get('final_grade', 'N/A')}")
            print(f"  Assessment: {synthesis_result.get('final_assessment', 'No assessment available')}")
            if synthesis_result.get('strengths'):
                print(f"  Strengths: {', '.join(synthesis_result['strengths'][:3])}")  # Show first 3
            if synthesis_result.get('weaknesses'):
                print(f"  Weaknesses: {', '.join(synthesis_result['weaknesses'][:3])}")  # Show first 3
        else:
            print(f"  Final Grade: N/A")
            print(f"  Assessment: No synthesis available")

        return results, synthesis_result





def main():
    grader = gradingManager()
    try:
        transcript = grader.read()
    except FileNotFoundError:
        transcript = "No transcript file found. Using placeholder for grading."

    results, synthesis_result = grader.grade_all(transcript)

    return results, synthesis_result