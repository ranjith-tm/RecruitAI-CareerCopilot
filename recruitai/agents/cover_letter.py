from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from recruitai.state import RecruitAIState


class CoverLetterOutput(BaseModel):
    cover_letter: str = Field(
        description="Complete, fully-formatted cover letter ready to copy-paste and send — "
                    "includes header, recipient block, salutation, 4-5 body paragraphs, and sign-off"
    )
    subject_line: str = Field(description="Email subject line for the application")


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert career coach who writes cover letters that get interviews.

You write cover letters that are:
- Fully formatted and ready to send — no placeholders, no "[Company Name]" blanks
- Deeply personalised: every paragraph references specific skills, projects, or achievements from the CV that match the JD
- Metric-driven: always include concrete numbers (years of experience, team size, performance gains, scale of systems built)
- Warm but professional — use "Hi [Recruiter Name]," if a name is given, otherwise "Dear Hiring Team,"
- Structured exactly as follows:

---
[Candidate Full Name]
[Phone] | [Email] | [LinkedIn URL — only if provided] | [GitHub URL — only if provided]

[Recruiter Name (if known)]
[Company Name]

Re: [Exact Job Title]

Hi [Recruiter Last Name], / Dear Hiring Team,

[PARAGRAPH 1 — 3-4 sentences. Who the candidate is (degree/field + years of experience), what role they are applying for, and one sharp sentence on why they are a strong fit. Never start with "I am writing to apply".]

[PARAGRAPH 2 — 4-5 sentences. Experience match: 2-3 specific achievements from work history that directly address what the JD asks for. Use real project names, company names, and metrics from the CV. Show explicitly how past experience maps to the role requirements.]

[PARAGRAPH 3 — 4-5 sentences. Technical depth: reference specific technologies, tools, and personal/academic projects from the CV that match the JD tech stack. Name the projects explicitly. If GitHub is provided, mention it naturally as evidence of hands-on work.]

[PARAGRAPH 4 — 3-4 sentences. Company motivation: show genuine knowledge of the company's mission, product, or industry. Connect the candidate's background or passion to what the company does. Specific — not generic enthusiasm.]

[PARAGRAPH 5 — 2-3 sentences. Closing: confident call to action + availability. Include any brief practical context if relevant (visa status, start date, etc.).]

Thank you for considering my application.

Best regards,
[Candidate Full Name]
---

Critical rules:
- STRICT LENGTH: 400–480 words for the body text (paragraphs only, excluding header/sign-off). This must fit on one page.
- Never leave blanks or placeholders — omit a field gracefully if not provided (e.g. no LinkedIn → don't show it)
- Every claim must be grounded in the CV data — do not invent skills, companies, or projects
- If the JD mentions specific tools, confirm against the CV before referencing them
- The letter must feel written for THIS specific role at THIS specific company — not a template
- Do not pad with filler phrases — every sentence must add value""",
    ),
    (
        "human",
        """--- CANDIDATE CV DATA ---
Name: {name}
Email: {email}
Phone: {phone}
LinkedIn: {linkedin}
GitHub: {github}
Location: {location}
Education: {education}
Years of Experience: {years_exp}

Technical Skills: {technical_skills}
Soft Skills: {soft_skills}
Domain Expertise: {domain_expertise}

Work Experience & Achievements:
{achievements}

Critical Skill Gaps (for this role): {skill_gaps}

--- JOB DESCRIPTION ---
{job_description}

--- INSTRUCTIONS ---
Write a complete, ready-to-send cover letter for this candidate applying to the role above.
Use all CV data provided to draw specific, accurate connections to the job requirements.
Do not invent anything not present in the CV data.""",
    ),
])


def create_cover_letter_generator(llm: BaseChatModel):
    chain = _PROMPT | llm.with_structured_output(CoverLetterOutput)

    def node(state: RecruitAIState) -> dict:
        if not state.get("job_description"):
            return {
                "log": ["Cover letter skipped — no job description provided"],
                "completed_steps": ["cover_letter_generator"],
            }

        # Use rewritten bullets if available, else fall back to raw experience bullets
        rewritten = state.get("rewritten_bullets", [])
        if rewritten:
            achievements = "\n".join(
                f"• {b['rewritten']}" + (f" ({b['improvement_note']})" if b.get("improvement_note") else "")
                for b in rewritten
            )
        else:
            raw = state.get("experience_bullets", [])
            achievements = "\n".join(f"• {b}" for b in raw) if raw else "Not provided"

        critical_gaps = state.get("critical_skill_gaps", [])
        skill_gaps_text = ", ".join(critical_gaps) if critical_gaps else "None identified"

        try:
            result: CoverLetterOutput = chain.invoke({
                "name": state.get("candidate_name", ""),
                "email": state.get("candidate_email", ""),
                "phone": state.get("candidate_phone", ""),
                "linkedin": state.get("candidate_linkedin", ""),
                "github": state.get("candidate_github", ""),
                "location": state.get("candidate_location", ""),
                "education": state.get("education_text", ""),
                "years_exp": state.get("years_of_experience", 0),
                "technical_skills": ", ".join(state.get("technical_skills", [])),
                "soft_skills": ", ".join(state.get("soft_skills", [])),
                "domain_expertise": ", ".join(state.get("domain_expertise", [])),
                "achievements": achievements,
                "skill_gaps": skill_gaps_text,
                "job_description": state["job_description"],
            })
            return {
                "cover_letter": result.cover_letter,
                "log": ["Cover letter generated"],
                "completed_steps": ["cover_letter_generator"],
            }
        except Exception as e:
            return {
                "errors": [f"cover_letter_generator: {e}"],
                "log": ["Cover letter generation failed"],
                "completed_steps": ["cover_letter_generator"],
            }

    return node
