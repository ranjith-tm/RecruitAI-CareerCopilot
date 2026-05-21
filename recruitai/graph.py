from langgraph.graph import StateGraph, START, END
from langchain_core.language_models import BaseChatModel

from recruitai.state import RecruitAIState
from recruitai.agents.resume_parser import create_resume_parser
from recruitai.agents.skills_extractor import create_skills_extractor
from recruitai.agents.ats_scorer import create_ats_scorer
from recruitai.agents.interview_predictor import create_interview_predictor
from recruitai.agents.resume_rewriter import create_resume_rewriter
from recruitai.agents.skill_gap import create_skill_gap_analyzer
from recruitai.agents.cover_letter import create_cover_letter_generator
from recruitai.agents.job_matcher import create_job_matcher


# Routing functions ────────────────────────────────────────────────────────

def _route_after_skills(state: RecruitAIState) -> str:
    """
    After skills extraction decide which path to take:
    - Primary job description present  → full analysis pipeline (ATS → Interview → ...)
    - Only multiple JDs present        → job ranking only
    - Nothing                          → end
    """
    if state.get("job_description"):
        return "ats_scorer"
    elif state.get("job_descriptions"):
        return "job_matcher"
    return END


def _route_after_ats(state: RecruitAIState) -> str:
    """After ATS scoring, optionally rank additional jobs before continuing."""
    if state.get("job_descriptions"):
        return "job_matcher"
    return "interview_predictor"


def _route_after_job_matcher(state: RecruitAIState) -> str:
    """After job matching, continue analysis if a primary JD exists."""
    if state.get("job_description") and "ats_scorer" in state.get("completed_steps", []):
        return "interview_predictor"
    return END


# Graph builder ────────────────────────────────────────────────────────────

def build_graph(llm: BaseChatModel):
    """Build and compile the RecruitAI multi-agent LangGraph workflow."""

    builder = StateGraph(RecruitAIState)

    # Register nodes
    builder.add_node("resume_parser", create_resume_parser(llm))
    builder.add_node("skills_extractor", create_skills_extractor(llm))
    builder.add_node("ats_scorer", create_ats_scorer(llm))
    builder.add_node("interview_predictor", create_interview_predictor(llm))
    builder.add_node("resume_rewriter", create_resume_rewriter(llm))
    builder.add_node("skill_gap_analyzer", create_skill_gap_analyzer(llm))
    builder.add_node("cover_letter_generator", create_cover_letter_generator(llm))
    builder.add_node("job_matcher", create_job_matcher(llm))

    # Entry → parse → classify
    builder.add_edge(START, "resume_parser")
    builder.add_edge("resume_parser", "skills_extractor")

    # Conditional split after skills
    builder.add_conditional_edges(
        "skills_extractor",
        _route_after_skills,
        {"ats_scorer": "ats_scorer", "job_matcher": "job_matcher", END: END},
    )

    # After ATS scoring — optionally rank jobs too
    builder.add_conditional_edges(
        "ats_scorer",
        _route_after_ats,
        {"job_matcher": "job_matcher", "interview_predictor": "interview_predictor"},
    )

    # After job matching — continue or end
    builder.add_conditional_edges(
        "job_matcher",
        _route_after_job_matcher,
        {"interview_predictor": "interview_predictor", END: END},
    )

    # Linear pipeline: interview → rewrite → gaps → cover letter
    builder.add_edge("interview_predictor", "resume_rewriter")
    builder.add_edge("resume_rewriter", "skill_gap_analyzer")
    builder.add_edge("skill_gap_analyzer", "cover_letter_generator")
    builder.add_edge("cover_letter_generator", END)

    return builder.compile()
