import json
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.schemas.models import AnalysisInput, AnalysisResponse, ErrorResponse
from app.services.analysis_service import run_analysis
from app.utils.pdf_utils import extract_text_from_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analysis"])
settings = get_settings()


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Run full AI career analysis",
)
async def analyze(
    resume_file: Optional[UploadFile] = File(None, description="Resume PDF"),
    resume_text: Optional[str] = Form(None, description="Resume plain text (alternative to PDF)"),
    job_description: Optional[str] = Form(None),
    job_descriptions: Optional[str] = Form(None, description="JSON array of additional JD strings"),
    target_role: Optional[str] = Form(None),
    provider: str = Form("groq", description="LLM provider: openai | groq"),
    model: Optional[str] = Form(None, description="Override model name"),
    api_key: Optional[str] = Form(None, description="API key (overrides env var)"),
):
    # Resolve resume text
    final_resume_text = resume_text or ""
    if resume_file and resume_file.filename:
        if not resume_file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        content = await resume_file.read()
        max_bytes = settings.max_pdf_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(status_code=400, detail=f"PDF exceeds {settings.max_pdf_size_mb} MB limit.")
        final_resume_text = extract_text_from_pdf(content)

    if not final_resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is required — upload a PDF or paste plain text.")

    # Resolve API key (form > env)
    resolved_key = api_key or (
        settings.openai_api_key if provider == "openai" else settings.groq_api_key
    ) or None

    if not resolved_key:
        if provider == "openai":
            raise HTTPException(status_code=400, detail="OpenAI API key is required. Enter it in the API Key field.")
        else:
            raise HTTPException(status_code=400, detail="GROQ_API_KEY is not set in the server environment.")

    # Parse optional multiple JDs
    parsed_jds: Optional[list] = None
    if job_descriptions:
        try:
            parsed_jds = json.loads(job_descriptions)
            if not isinstance(parsed_jds, list):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=400, detail="job_descriptions must be a valid JSON array of strings.")

    input_data = AnalysisInput(
        resume_text=final_resume_text,
        job_description=job_description or None,
        job_descriptions=parsed_jds,
        target_role=target_role or None,
        provider=provider,
        model=model or None,
        api_key=resolved_key,
    )

    try:
        result = await run_analysis(input_data)
        return AnalysisResponse(success=True, data=result, message="Analysis complete")
    except Exception as exc:
        logger.exception("Analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
