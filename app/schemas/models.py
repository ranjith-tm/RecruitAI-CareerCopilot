from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────────

class AnalysisInput(BaseModel):
    resume_text: str
    job_description: Optional[str] = None
    job_descriptions: Optional[List[str]] = None
    target_role: Optional[str] = None
    provider: str = "openai"
    model: Optional[str] = None
    api_key: Optional[str] = None


# ── Response ──────────────────────────────────────────────────────────────────

class CandidateProfile(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    years_of_experience: Optional[float] = None
    technical_skills: List[str] = []
    soft_skills: List[str] = []
    domain_expertise: List[str] = []
    education: Optional[str] = None


class ATSAnalysis(BaseModel):
    score: Optional[float] = None
    breakdown: Optional[Dict[str, Any]] = None
    missing_keywords: List[str] = []
    keyword_density: Optional[float] = None
    readability_score: Optional[float] = None


class InterviewPrediction(BaseModel):
    probability: Optional[float] = None
    breakdown: Optional[Dict[str, float]] = None
    strengths: List[str] = []
    weaknesses: List[str] = []


class ResumeBullet(BaseModel):
    original: str = ""
    rewritten: str = ""
    improvement_note: str = ""


class SkillGaps(BaseModel):
    critical: List[str] = []
    nice_to_have: List[str] = []
    learning_recommendations: List[Dict[str, str]] = []


class JobRanking(BaseModel):
    rank: int = 0
    title: Optional[str] = None
    match_score: Optional[float] = None
    recommendation: Optional[str] = None
    matched_skills: List[str] = []
    missing_skills: List[str] = []


class AnalysisResult(BaseModel):
    profile: CandidateProfile = Field(default_factory=CandidateProfile)
    ats: ATSAnalysis = Field(default_factory=ATSAnalysis)
    interview: InterviewPrediction = Field(default_factory=InterviewPrediction)
    resume_bullets: List[ResumeBullet] = []
    skill_gaps: SkillGaps = Field(default_factory=SkillGaps)
    cover_letter: Optional[str] = None
    job_rankings: List[JobRanking] = []
    completed_steps: List[str] = []
    errors: List[str] = []


class AnalysisResponse(BaseModel):
    success: bool = True
    data: Optional[AnalysisResult] = None
    message: str = "Analysis complete"


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    providers: List[str] = ["openai", "groq"]
