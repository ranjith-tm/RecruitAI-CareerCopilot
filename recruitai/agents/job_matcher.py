from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from recruitai.state import RecruitAIState


class JobRanking(BaseModel):
    job_title: str = Field(description="Job title extracted from the description")
    company: str = Field(default="Unknown", description="Company name if mentioned")
    match_score: float = Field(description="Overall match score 0–100")
    matching_skills: List[str] = Field(description="Skills that match the JD requirements")
    missing_skills: List[str] = Field(description="Required skills the candidate lacks")
    recommendation: str = Field(description="Should Apply / Worth Considering / Skip")
    reason: str = Field(description="Brief 1–2 sentence reasoning for the recommendation")


class JobRankings(BaseModel):
    rankings: List[JobRanking]


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a job matching expert. Analyse a candidate's profile against multiple job descriptions.
Score each role 0–100 based on skill overlap, experience fit, and domain alignment.
70+ = strong match (Should Apply), 50–70 = decent fit (Worth Considering), <50 = significant gaps (Skip).""",
    ),
    (
        "human",
        """CANDIDATE PROFILE:
- Technical Skills: {technical_skills}
- Domain Expertise: {domain_expertise}
- Years of Experience: {years_exp}
- Education: {education}

JOBS TO RANK:
{job_descriptions}

Rank each job and provide actionable recommendations.""",
    ),
])


def create_job_matcher(llm: BaseChatModel):
    chain = _PROMPT | llm.with_structured_output(JobRankings)

    def node(state: RecruitAIState) -> dict:
        job_descriptions = state.get("job_descriptions", [])
        if not job_descriptions:
            return {
                "log": ["Job matching skipped — no additional job descriptions provided"],
                "completed_steps": ["job_matcher"],
            }

        formatted = "\n\n---\n\n".join(
            f"JOB {i + 1}:\n{jd[:1200]}" for i, jd in enumerate(job_descriptions[:10])
        )

        try:
            result: JobRankings = chain.invoke({
                "technical_skills": ", ".join(state.get("technical_skills", [])),
                "domain_expertise": ", ".join(state.get("domain_expertise", [])),
                "years_exp": state.get("years_of_experience", 0),
                "education": state.get("education_text", "Not provided"),
                "job_descriptions": formatted,
            })
            rankings = sorted(
                [
                    {
                        "job_title": r.job_title,
                        "company": r.company,
                        "match_score": r.match_score,
                        "matching_skills": r.matching_skills,
                        "missing_skills": r.missing_skills,
                        "recommendation": r.recommendation,
                        "reason": r.reason,
                    }
                    for r in result.rankings
                ],
                key=lambda x: x["match_score"],
                reverse=True,
            )
            return {
                "job_rankings": rankings,
                "log": [f"Ranked {len(rankings)} jobs by match score"],
                "completed_steps": ["job_matcher"],
            }
        except Exception as e:
            return {
                "errors": [f"job_matcher: {e}"],
                "log": ["Job matching failed"],
                "completed_steps": ["job_matcher"],
            }

    return node
