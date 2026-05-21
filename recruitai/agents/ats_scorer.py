from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from recruitai.state import RecruitAIState


class ATSAnalysis(BaseModel):
    ats_score: float = Field(description="Overall ATS match score 0–100")
    keyword_match_score: float = Field(description="Keyword matching score 0–100")
    format_score: float = Field(description="Resume format/structure score 0–100")
    relevance_score: float = Field(description="Overall relevance to role 0–100")
    recruiter_readability_score: float = Field(description="Human recruiter readability 0–100")
    missing_keywords: List[str] = Field(description="Important JD keywords missing from resume")
    present_keywords: List[str] = Field(description="Key matching keywords found in resume")
    keyword_density: float = Field(description="Keyword density percentage 0–100")
    improvement_suggestions: List[str] = Field(description="Specific actions to raise the ATS score")


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert ATS (Applicant Tracking System) analyst and HR consultant.
Score resume–job fit with precision. Be realistic — do not inflate scores.
70+ = strong match, 50–70 = decent fit, below 50 = significant gaps.""",
    ),
    (
        "human",
        "JOB DESCRIPTION:\n{job_description}\n\nCANDIDATE RESUME:\n{resume_text}\n\nCANDIDATE SKILLS: {technical_skills}\n\nProvide comprehensive ATS analysis.",
    ),
])


def create_ats_scorer(llm: BaseChatModel):
    chain = _PROMPT | llm.with_structured_output(ATSAnalysis)

    def node(state: RecruitAIState) -> dict:
        if not state.get("job_description"):
            return {
                "log": ["ATS scoring skipped — no job description provided"],
                "completed_steps": ["ats_scorer"],
            }
        try:
            result: ATSAnalysis = chain.invoke({
                "job_description": state["job_description"],
                "resume_text": state.get("resume_text", ""),
                "technical_skills": ", ".join(state.get("technical_skills", [])),
            })
            return {
                "ats_score": result.ats_score,
                "ats_breakdown": {
                    "Keyword Match": result.keyword_match_score,
                    "Format & Structure": result.format_score,
                    "Role Relevance": result.relevance_score,
                    "Recruiter Readability": result.recruiter_readability_score,
                },
                "missing_keywords": result.missing_keywords,
                "keyword_density": result.keyword_density,
                "recruiter_readability_score": result.recruiter_readability_score,
                "log": [f"ATS score: {result.ats_score:.1f}/100"],
                "completed_steps": ["ats_scorer"],
            }
        except Exception as e:
            return {
                "errors": [f"ats_scorer: {e}"],
                "log": ["ATS scoring failed"],
                "completed_steps": ["ats_scorer"],
            }

    return node
