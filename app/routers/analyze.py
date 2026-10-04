"""
Analysis endpoint router: processes user decision scenarios and returns Socratic blind spots.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.schemas.request_schemas import IntakeRequest
from app.schemas.response_schemas import BlindSpotAnalysisResponse
from app.services.gemini_service import GeminiService, get_gemini_service
from app.services.session_service import SessionService, get_session_service
from app.validators.security import sanitize_text_input

logger = logging.getLogger("blindspot.routers.analyze")

router = APIRouter(prefix="/api", tags=["Analysis"])


@router.post(
    "/analyze",
    response_model=BlindSpotAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze decision for cognitive blind spots",
)
async def analyze_decision_endpoint(
    request: IntakeRequest,
    req: Request,
    gemini_service: GeminiService = Depends(get_gemini_service),
    session_service: SessionService = Depends(get_session_service),
) -> BlindSpotAnalysisResponse:
    """
    Analyzes user-provided decision details and identifies:
    - What factors the user emphasized
    - Overlooked factors and why they matter
    - Unstated assumptions and how to test them
    - Internal conflicts with user quotes
    - Strongest case for the opposing perspective
    - Socratic probing questions
    Strictly forbids verdict or advice rendering.
    """
    try:
        # Sanitize text inputs
        sanitized_desc = sanitize_text_input(request.decision_description, max_length=5000)
        sanitized_drawing = sanitize_text_input(request.drawing_factors, max_length=2000)
        sanitized_options = sanitize_text_input(request.options_considered, max_length=2000) if request.options_considered else None
        sanitized_deadline = sanitize_text_input(request.deadline_or_stakes, max_length=1000) if request.deadline_or_stakes else None

        cleaned_request = IntakeRequest(
            decision_description=sanitized_desc,
            drawing_factors=sanitized_drawing,
            options_considered=sanitized_options,
            deadline_or_stakes=sanitized_deadline,
            session_id=request.session_id,
        )

        # Initialize or retrieve session
        session_id = session_service.create_or_update_session(
            session_id=cleaned_request.session_id,
            intake_data=cleaned_request.model_dump(),
        )

        # Execute Socratic analysis
        analysis_response = await gemini_service.analyze_decision(
            request=cleaned_request,
            session_id=session_id,
        )

        # Update session with analysis result
        session_service.create_or_update_session(
            session_id=session_id,
            intake_data=cleaned_request.model_dump(),
            initial_analysis=analysis_response.model_dump(),
        )

        return analysis_response

    except ValueError as ve:
        logger.warning(f"Validation error in analyze endpoint: {ve}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        ) from ve
    except Exception as exc:
        logger.error(f"Unexpected error during analysis: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your reasoning analysis. Please try again.",
        ) from exc
