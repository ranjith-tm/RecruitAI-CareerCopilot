from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from recruitai.state import RecruitAIState


class LearningResource(BaseModel):
    skill: str = Field(description="The skill to learn")
    resource_type: str = Field(description="Course / Book / Project / Certification / Practice")
    recommendation: str = Field(description="Specific resource or concrete action to take")
    priority: str = Field(description="High / Medium / Low")


class SkillGapAnalysis(BaseModel):
    critical_skill_gaps: List[str] = Field(
        description="Must-have skills from the JD that the candidate completely lacks — these are blockers"
    )
    nice_to_have_gaps: List[str] = Field(
        description="Beneficial skills from the JD that are missing but not dealbreakers"
    )
    learning_recommendations: List[LearningResource] = Field(
        description="Prioritised, actionable learning plan for the top critical gaps"
    )
    estimated_prep_time: str = Field(
        description="Realistic time estimate to close the critical gaps (e.g. '3–4 weeks')"
    )


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a senior engineering mentor and career development expert.
Identify skill gaps honestly and provide practical, actionable learning plans.
For learning recommendations, suggest specific courses (Coursera, fast.ai, etc.),
open-source projects to build, or certifications to pursue.""",
    ),
    (
        "human",
        """JOB DESCRIPTION:
{job_description}

CANDIDATE SKILLS:
- Technical: {technical_skills}
- Domain: {domain_expertise}
- Soft: {soft_skills}

YEARS OF EXPERIENCE: {years_exp}

Identify gaps and provide a concrete, prioritised learning plan.""",
    ),
])


def create_skill_gap_analyzer(llm: BaseChatModel):
    chain = _PROMPT | llm.with_structured_output(SkillGapAnalysis)

    def node(state: RecruitAIState) -> dict:
        if not state.get("job_description"):
            return {
                "log": ["Skill gap analysis skipped — no job description provided"],
                "completed_steps": ["skill_gap_analyzer"],
            }
        try:
            result: SkillGapAnalysis = chain.invoke({
                "job_description": state["job_description"],
                "technical_skills": ", ".join(state.get("technical_skills", [])),
                "domain_expertise": ", ".join(state.get("domain_expertise", [])),
                "soft_skills": ", ".join(state.get("soft_skills", [])),
                "years_exp": state.get("years_of_experience", 0),
            })
            recs = [
                {
                    "skill": r.skill,
                    "resource_type": r.resource_type,
                    "recommendation": r.recommendation,
                    "priority": r.priority,
                }
                for r in result.learning_recommendations
            ]
            return {
                "critical_skill_gaps": result.critical_skill_gaps,
                "nice_to_have_gaps": result.nice_to_have_gaps,
                "learning_recommendations": recs,
                "log": [
                    f"Found {len(result.critical_skill_gaps)} critical gaps — est. prep: {result.estimated_prep_time}"
                ],
                "completed_steps": ["skill_gap_analyzer"],
            }
        except Exception as e:
            return {
                "errors": [f"skill_gap_analyzer: {e}"],
                "log": ["Skill gap analysis failed"],
                "completed_steps": ["skill_gap_analyzer"],
            }

    return node
