from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from recruitai.state import RecruitAIState


class ClassifiedSkills(BaseModel):
    technical_skills: List[str] = Field(
        description="Programming languages, frameworks, libraries, tools, cloud platforms, databases"
    )
    soft_skills: List[str] = Field(
        description="Interpersonal and professional skills: leadership, communication, etc."
    )
    domain_expertise: List[str] = Field(
        description="Domain knowledge areas: AI/ML, finance, healthcare, e-commerce, etc."
    )


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a talent acquisition expert. Classify the candidate's skills into three categories:
1. Technical skills: specific technologies, languages, frameworks, tools, platforms
2. Soft skills: interpersonal and professional competencies
3. Domain expertise: industry verticals and knowledge domains
Extract comprehensively — include skills implied by the experience, not just those explicitly listed.""",
    ),
    (
        "human",
        "Resume text:\n{resume_text}\n\nAlready extracted skills: {raw_skills}\n\nClassify all skills comprehensively.",
    ),
])


def create_skills_extractor(llm: BaseChatModel):
    chain = _PROMPT | llm.with_structured_output(ClassifiedSkills)

    def node(state: RecruitAIState) -> dict:
        try:
            result: ClassifiedSkills = chain.invoke({
                "resume_text": state.get("resume_text", ""),
                "raw_skills": ", ".join(state.get("raw_skills", [])),
            })
            return {
                "technical_skills": result.technical_skills,
                "soft_skills": result.soft_skills,
                "domain_expertise": result.domain_expertise,
                "log": [f"Skills classified — {len(result.technical_skills)} technical, {len(result.soft_skills)} soft"],
                "completed_steps": ["skills_extractor"],
            }
        except Exception as e:
            return {
                "errors": [f"skills_extractor: {e}"],
                "log": ["Skills extraction failed"],
                "completed_steps": ["skills_extractor"],
            }

    return node
