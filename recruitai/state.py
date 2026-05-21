from typing import TypedDict, List, Dict, Any, Annotated
import operator


class RecruitAIState(TypedDict, total=False):
    # Inputs ──────────────────────────────────────────────
    resume_text: str
    job_description: str
    job_descriptions: List[str]
    target_role: str

    # Parsed Resume ────────────────────────────────────────
    candidate_name: str
    candidate_email: str
    candidate_phone: str
    candidate_linkedin: str
    candidate_github: str
    candidate_location: str
    candidate_summary: str
    experience_bullets: List[str]
    education_text: str
    raw_skills: List[str]
    years_of_experience: float

    # Classified Skills ────────────────────────────────────
    technical_skills: List[str]
    soft_skills: List[str]
    domain_expertise: List[str]

    # ATS Analysis ────────────────────────────────────────
    ats_score: float
    ats_breakdown: Dict[str, Any]
    missing_keywords: List[str]
    keyword_density: float
    recruiter_readability_score: float

    # Interview Prediction ─────────────────────────────────
    interview_probability: float
    probability_breakdown: Dict[str, float]
    interview_strengths: List[str]
    interview_weaknesses: List[str]

    # Resume Improvements ──────────────────────────────────
    rewritten_bullets: List[Dict[str, str]]

    # Skill Gap ────────────────────────────────────────────
    critical_skill_gaps: List[str]
    nice_to_have_gaps: List[str]
    learning_recommendations: List[Dict[str, str]]

    # Cover Letter ─────────────────────────────────────────
    cover_letter: str

    # Job Matching ─────────────────────────────────────────
    job_rankings: List[Dict[str, Any]]

    # Pipeline Metadata (append-reducers) ──────────────────
    log: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
    completed_steps: Annotated[List[str], operator.add]
