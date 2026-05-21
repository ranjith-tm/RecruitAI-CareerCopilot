from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from recruitai.state import RecruitAIState


class ParsedResume(BaseModel):
    candidate_name: str = Field(description="Full name of the candidate")
    candidate_email: str = Field(default="", description="Email address")
    candidate_phone: str = Field(default="", description="Phone number including country code if present")
    candidate_linkedin: str = Field(default="", description="LinkedIn profile URL or username if present")
    candidate_github: str = Field(default="", description="GitHub profile URL or username if present")
    candidate_location: str = Field(default="", description="City/country location")
    candidate_summary: str = Field(default="", description="Professional summary or objective")
    experience_bullets: List[str] = Field(
        default_factory=list, description="All work experience bullet points and achievements"
    )
    education_text: str = Field(default="", description="Education background as a single string")
    raw_skills: List[str] = Field(default_factory=list, description="All skills mentioned in the resume")
    years_of_experience: float = Field(default=0.0, description="Total years of professional experience")


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert resume parser. Extract structured information from resumes with high accuracy.
For experience_bullets, extract EVERY bullet point and achievement from all work experience sections.
Estimate years_of_experience from the work history dates (present = 2026).""",
    ),
    ("human", "Parse this resume:\n\n{resume_text}"),
])


def create_resume_parser(llm: BaseChatModel):
    chain = _PROMPT | llm.with_structured_output(ParsedResume)

    def node(state: RecruitAIState) -> dict:
        try:
            result: ParsedResume = chain.invoke({"resume_text": state["resume_text"]})
            return {
                "candidate_name": result.candidate_name,
                "candidate_email": result.candidate_email,
                "candidate_phone": result.candidate_phone,
                "candidate_linkedin": result.candidate_linkedin,
                "candidate_github": result.candidate_github,
                "candidate_location": result.candidate_location,
                "candidate_summary": result.candidate_summary,
                "experience_bullets": result.experience_bullets,
                "education_text": result.education_text,
                "raw_skills": result.raw_skills,
                "years_of_experience": result.years_of_experience,
                "log": ["Resume parsed successfully"],
                "completed_steps": ["resume_parser"],
            }
        except Exception as e:
            return {
                "errors": [f"resume_parser: {e}"],
                "log": ["Resume parsing failed"],
                "completed_steps": ["resume_parser"],
            }

    return node
