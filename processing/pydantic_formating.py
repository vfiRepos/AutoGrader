# pydantic_formating.py
from typing import List
from pydantic import BaseModel, Field

class GradeItem(BaseModel):
    skill: str = Field(description="The skill area being graded, e.g. 'discovery'.")
    grade: str = Field(description="Letter grade (A-F) or N/A if agent failed to grade.")
    reasoning: str = Field(description="Why this grade was assigned.")
    # Optional fields for more detailed reporting
    count: int = Field(default=None, description="Count for quantifiable metrics (e.g., filler words, questions)")
    examples: List[str] = Field(default=None, description="Specific examples or missed opportunities")
    ratio: float = Field(default=None, description="Ratio/percentage metrics (e.g., talk ratio)")

class SkillReport(BaseModel):
    items: List[GradeItem] = Field(description="Grades for individual skills.")

class FinalGrade(BaseModel):
    overall_grade: str = Field(description="Final synthesized grade for the call.")
    reasoning: str = Field(description="Reasoning for the final grade, referencing strengths and weaknesses.")

class FinalReport(BaseModel):
    skills: SkillReport
    final: FinalGrade
