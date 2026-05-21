import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from app.schemas.models import (
    AnalysisInput, AnalysisResult, CandidateProfile, ATSAnalysis,
    InterviewPrediction, ResumeBullet, SkillGaps, JobRanking
)
from recruitai.config import get_llm
from recruitai.graph import build_graph

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)


def _run_graph_sync(input_data: AnalysisInput) -> dict:
    llm = get_llm(
        provider=input_data.provider,
        model=input_data.model,
        api_key=input_data.api_key or None,
    )
    graph = build_graph(llm)

    initial_state: dict = {"resume_text": input_data.resume_text}
    if input_data.job_description:
        initial_state["job_description"] = input_data.job_description
    if input_data.job_descriptions:
        initial_state["job_descriptions"] = input_data.job_descriptions
    if input_data.target_role:
        initial_state["target_role"] = input_data.target_role

    return graph.invoke(initial_state)


def _map_state_to_result(state: dict) -> AnalysisResult:
    profile = CandidateProfile(
        name=state.get("candidate_name"),
        email=state.get("candidate_email"),
        phone=state.get("candidate_phone"),
        linkedin=state.get("candidate_linkedin"),
        github=state.get("candidate_github"),
        location=state.get("candidate_location"),
        summary=state.get("candidate_summary"),
        years_of_experience=state.get("years_of_experience"),
        technical_skills=state.get("technical_skills") or [],
        soft_skills=state.get("soft_skills") or [],
        domain_expertise=state.get("domain_expertise") or [],
        education=state.get("education_text"),
    )

    ats = ATSAnalysis(
        score=state.get("ats_score"),
        breakdown=state.get("ats_breakdown"),
        missing_keywords=state.get("missing_keywords") or [],
        keyword_density=state.get("keyword_density"),
        readability_score=state.get("recruiter_readability_score"),
    )

    interview = InterviewPrediction(
        probability=state.get("interview_probability"),
        breakdown=state.get("probability_breakdown"),
        strengths=state.get("interview_strengths") or [],
        weaknesses=state.get("interview_weaknesses") or [],
    )

    bullets: list[ResumeBullet] = []
    for b in state.get("rewritten_bullets") or []:
        bullets.append(ResumeBullet(
            original=b.get("original", ""),
            rewritten=b.get("rewritten", ""),
            improvement_note=b.get("improvement_note", b.get("note", "")),
        ))

    skill_gaps = SkillGaps(
        critical=state.get("critical_skill_gaps") or [],
        nice_to_have=state.get("nice_to_have_gaps") or [],
        learning_recommendations=state.get("learning_recommendations") or [],
    )

    rankings: list[JobRanking] = []
    for job in state.get("job_rankings") or []:
        rankings.append(JobRanking(
            rank=job.get("rank", 0),
            title=job.get("title") or job.get("job_title"),
            match_score=job.get("match_score"),
            recommendation=job.get("recommendation"),
            matched_skills=job.get("matched_skills") or [],
            missing_skills=job.get("missing_skills") or [],
        ))

    return AnalysisResult(
        profile=profile,
        ats=ats,
        interview=interview,
        resume_bullets=bullets,
        skill_gaps=skill_gaps,
        cover_letter=state.get("cover_letter"),
        job_rankings=rankings,
        completed_steps=state.get("completed_steps") or [],
        errors=state.get("errors") or [],
    )


async def run_analysis(input_data: AnalysisInput) -> AnalysisResult:
    logger.info("Starting analysis for provider=%s model=%s", input_data.provider, input_data.model)
    loop = asyncio.get_event_loop()
    state = await loop.run_in_executor(_executor, _run_graph_sync, input_data)
    result = _map_state_to_result(state)
    logger.info("Analysis complete. Steps: %s", result.completed_steps)
    return result
