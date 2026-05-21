from typing import List, Dict
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from recruitai.state import RecruitAIState


class InterviewPrediction(BaseModel):
    interview_probability: float = Field(description="Probability of receiving an interview call 0–100")
    skill_match_score: float = Field(description="Skill overlap with job requirements 0–100")
    experience_match_score: float = Field(description="Experience relevance score 0–100")
    education_match_score: float = Field(description="Education fit score 0–100")
    project_relevance_score: float = Field(description="Project/portfolio relevance 0–100")
    interview_strengths: List[str] = Field(description="Top 3–5 reasons this candidate gets an interview")
    interview_weaknesses: List[str] = Field(description="Top 3–5 gaps that reduce interview chances")
    top_recommendation: str = Field(description="Single most impactful action to boost interview chances")


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a senior technical recruiter with 10+ years of experience at top tech companies.
Predict interview probability based on realistic hiring criteria.
Factor in: skill match, experience relevance, education, project quality, and ATS score.
Be honest — overinflating scores helps no one.""",
    ),
    (
        "human",
        """JOB DESCRIPTION:
{job_description}

CANDIDATE PROFILE:
- Name: {name}
- Years of Experience: {years_exp}
- Technical Skills: {technical_skills}
- Domain Expertise: {domain_expertise}
- Education: {education}
- ATS Score: {ats_score}/100

Predict interview probability with a detailed breakdown.""",
    ),
])


def create_interview_predictor(llm: BaseChatModel):
    chain = _PROMPT | llm.with_structured_output(InterviewPrediction)

    def node(state: RecruitAIState) -> dict:
        if not state.get("job_description"):
            return {
                "log": ["Interview prediction skipped — no job description provided"],
                "completed_steps": ["interview_predictor"],
            }
        try:
            result: InterviewPrediction = chain.invoke({
                "job_description": state["job_description"],
                "name": state.get("candidate_name", "Candidate"),
                "years_exp": state.get("years_of_experience", 0),
                "technical_skills": ", ".join(state.get("technical_skills", [])),
                "domain_expertise": ", ".join(state.get("domain_expertise", [])),
                "education": state.get("education_text", "Not provided"),
                "ats_score": state.get("ats_score", 0),
            })
            return {
                "interview_probability": result.interview_probability,
                "probability_breakdown": {
                    "Skill Match": result.skill_match_score,
                    "Experience Match": result.experience_match_score,
                    "Education Fit": result.education_match_score,
                    "Project Relevance": result.project_relevance_score,
                },
                "interview_strengths": result.interview_strengths,
                "interview_weaknesses": result.interview_weaknesses,
                "log": [f"Interview probability: {result.interview_probability:.1f}%"],
                "completed_steps": ["interview_predictor"],
            }
        except Exception as e:
            return {
                "errors": [f"interview_predictor: {e}"],
                "log": ["Interview prediction failed"],
                "completed_steps": ["interview_predictor"],
            }

    return node
