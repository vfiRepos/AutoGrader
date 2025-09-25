# pydantic_formating.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, RootModel

class GradeItem(BaseModel):
    skill: str = Field(description="The skill area being graded, e.g. 'discovery'.")
    grade: str = Field(description="Letter grade (A-F) or N/A if agent failed to grade.")
    reasoning: str = Field(default="No reasoning provided", description="Why this grade was assigned.")
    # Optional fields for more detailed reporting
    count: Optional[int] = Field(default=None, description="Count for quantifiable metrics (e.g., filler words, questions)")
    examples: Optional[List[str]] = Field(default=None, description="Specific examples or missed opportunities")
    ratio: Optional[float] = Field(default=None, description="Ratio/percentage metrics (e.g., talk ratio)")
    # Boolean fields for specific criteria evaluation
    segment_identified: Optional[bool] = Field(default=None, description="Did rep identify the prospect's segment?")
    tailored_questions: Optional[bool] = Field(default=None, description="Did rep ask segment-appropriate questions?")
    positioning_aligned: Optional[bool] = Field(default=None, description="Did rep position VFI appropriately for segment?")
    differentiators_reinforced: Optional[bool] = Field(default=None, description="Did rep reinforce VFI differentiators?")
    positioned_as_partner: Optional[bool] = Field(default=None, description="Did rep position VFI as partner vs competitor?")
    connected_to_situation: Optional[bool] = Field(default=None, description="Did rep connect to prospect's specific situation?")
    distinguished_from_banks: Optional[bool] = Field(default=None, description="Did rep distinguish VFI from banks?")
    emphasized_fixed_assets: Optional[bool] = Field(default=None, description="Did rep emphasize fixed asset funding?")
    explained_liquidity: Optional[bool] = Field(default=None, description="Did rep explain liquidity benefits?")
    aligned_with_priorities: Optional[bool] = Field(default=None, description="Did rep align with PE/CFO priorities?")

class SkillReport(BaseModel):
    items: List[GradeItem] = Field(description="Grades for individual skills.")

class FinalGrade(BaseModel):
    overall_grade: str = Field(description="Final synthesized grade for the call.")
    reasoning: str = Field(description="Reasoning for the final grade, referencing strengths and weaknesses.")

class FinalReport(BaseModel):
    skills: SkillReport
    final: FinalGrade

# New models for the updated AI response format
class SkillComponent(BaseModel):
    result: Optional[str] = Field(default=None, description="Result of the skill component (e.g., 'pass', 'fail')")
    quote: Optional[str] = Field(default=None, description="Relevant quote from the transcript")
    timestamp: Optional[str] = Field(default=None, description="Timestamp of the quote")
    confidence: Optional[float] = Field(default=None, description="Confidence score for the assessment")
    reasoning: Optional[str] = Field(default=None, description="Reasoning for the assessment")
    grade: Optional[str] = Field(default=None, description="Grade for this component")

class NewSkillReport(RootModel[Dict[str, Any]]):
    """New format that matches the AI response structure using Pydantic v2 RootModel"""
    root: Dict[str, Any] = Field(description="Dynamic skill components")

class FlexibleSkillReport(BaseModel):
    """Flexible model that can handle both old and new formats"""
    # For old format
    items: Optional[List[GradeItem]] = Field(default=None, description="Grades for individual skills (old format)")
    
    # For new format - allow any structure
    root: Optional[Dict[str, Any]] = Field(default=None, description="Dynamic skill data (new format)")
    
    class Config:
        extra = "allow"
