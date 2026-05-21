from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from recruitai.state import RecruitAIState


class RewrittenBullet(BaseModel):
    original: str = Field(description="The original bullet point text")
    rewritten: str = Field(description="Improved, quantified, action-verb-led bullet point")
    improvement_note: str = Field(description="One-line explanation of why this rewrite is stronger")


class RewrittenBullets(BaseModel):
    bullets: List[RewrittenBullet]


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an elite resume writer specialising in tech and AI roles.
Transform weak, vague bullet points into impactful, quantified achievements.

Rules:
- Begin with a strong action verb (Architected, Developed, Reduced, Increased, Led, Deployed)
- Add realistic metrics where possible — e.g. "reduced latency by 40%", "served 50k users"
- Surface the business or engineering impact
- Weave in relevant technologies from the job description
- Keep each bullet under two lines
- Never fabricate specific numbers; use realistic estimates when real data is absent""",
    ),
    (
        "human",
        "TARGET ROLE: {target_role}\n\nJOB REQUIREMENTS (excerpt):\n{job_description}\n\nBULLETS TO REWRITE:\n{bullets}\n\nRewrite each bullet to be more impactful and relevant.",
    ),
])


def create_resume_rewriter(llm: BaseChatModel):
    chain = _PROMPT | llm.with_structured_output(RewrittenBullets)

    def node(state: RecruitAIState) -> dict:
        bullets = state.get("experience_bullets", [])
        if not bullets:
            return {
                "log": ["Resume rewriting skipped — no experience bullets found"],
                "completed_steps": ["resume_rewriter"],
            }

        bullets_text = "\n".join(f"- {b}" for b in bullets[:8])
        jd = state.get("job_description", "General tech / AI engineering role")

        try:
            result: RewrittenBullets = chain.invoke({
                "target_role": state.get("target_role") or jd[:150],
                "job_description": jd[:600],
                "bullets": bullets_text,
            })
            rewritten = [
                {
                    "original": b.original,
                    "rewritten": b.rewritten,
                    "improvement_note": b.improvement_note,
                }
                for b in result.bullets
            ]
            return {
                "rewritten_bullets": rewritten,
                "log": [f"Rewrote {len(rewritten)} resume bullets"],
                "completed_steps": ["resume_rewriter"],
            }
        except Exception as e:
            return {
                "errors": [f"resume_rewriter: {e}"],
                "log": ["Resume rewriting failed"],
                "completed_steps": ["resume_rewriter"],
            }

    return node
