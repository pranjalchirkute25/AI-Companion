"""
Reasoning Map router: generates a personalized markdown summary built
ONLY from the user's confirmed acknowledgments and answers.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.request_schemas import ReasoningMapRequest
from app.schemas.response_schemas import ReasoningMapResponse
from app.services.session_service import SessionService, get_session_service
from app.validators.security import sanitize_text_input

logger = logging.getLogger("blindspot.routers.map")

router = APIRouter(prefix="/api", tags=["Reasoning Map"])


@router.post(
    "/reasoning-map",
    response_model=ReasoningMapResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate 'My Reasoning Map' from user's confirmed acknowledgments",
)
async def generate_reasoning_map_endpoint(
    request: ReasoningMapRequest,
    session_service: SessionService = Depends(get_session_service),
) -> ReasoningMapResponse:
    """
    Constructs a structured markdown map built solely from the user's confirmed points.
    Strictly ends with an empty 'My decision:' line to reinforce user agency.
    """
    try:
        sanitized_assumptions = [
            sanitize_text_input(a, max_length=1000) for a in request.confirmed_assumptions if a.strip()
        ]
        sanitized_conflicts = [
            sanitize_text_input(c, max_length=1000) for c in request.acknowledged_conflicts if c.strip()
        ]
        sanitized_questions = [
            sanitize_text_input(q, max_length=1000) for q in request.open_questions if q.strip()
        ]
        sanitized_notes = (
            sanitize_text_input(request.user_notes, max_length=3000) if request.user_notes else None
        )

        # Update session state
        session_service.update_reasoning_map_state(
            session_id=request.session_id,
            confirmed_assumptions=sanitized_assumptions,
            acknowledged_conflicts=sanitized_conflicts,
            open_questions=sanitized_questions,
            user_notes=sanitized_notes,
        )

        session = session_service.get_session(request.session_id)
        decision_title = "Decision Thinking Session"
        if session and session.get("intake_data"):
            desc = session["intake_data"].get("decision_description", "")
            if desc:
                decision_title = desc[:60] + ("..." if len(desc) > 60 else "")

        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Build Markdown document
        md_lines = [
            f"# My Reasoning Map: {decision_title}",
            f"*Generated on {now_str} via The Blind Spot Cognitive Mirror*",
            "",
            "> **Thinking Aid Notice**: This map represents your own examined thoughts, confirmed assumptions, ",
            "> and acknowledged tensions. The final evaluation and choice are solely yours to make.",
            "",
            "---",
            "",
            "## 1. Confirmed Unstated Assumptions",
        ]

        if sanitized_assumptions:
            for idx, item in enumerate(sanitized_assumptions, 1):
                md_lines.append(f"{idx}. [x] **{item}**")
        else:
            md_lines.append("*No assumptions explicitly confirmed yet.*")

        md_lines.extend(["", "## 2. Acknowledged Internal Conflicts & Tensions"])
        if sanitized_conflicts:
            for idx, item in enumerate(sanitized_conflicts, 1):
                md_lines.append(f"{idx}. [!] **{item}**")
        else:
            md_lines.append("*No internal conflicts selected.*")

        md_lines.extend(["", "## 3. Open Probing Questions to Keep in Mind"])
        if sanitized_questions:
            for idx, item in enumerate(sanitized_questions, 1):
                md_lines.append(f"{idx}. [?] {item}")
        else:
            md_lines.append("*No open questions flagged.*")

        if sanitized_notes:
            md_lines.extend(["", "## 4. Personal Reflection Notes", "", sanitized_notes])

        md_lines.extend([
            "",
            "---",
            "",
            "## 5. Decision Space",
            "",
            "My decision: __________________________________________________",
            "",
            "*(This line is intentionally left blank. The system never decides for you.)*",
            "",
        ])

        markdown_output = "\n".join(md_lines)

        return ReasoningMapResponse(
            markdown_content=markdown_output,
            confirmed_assumptions_count=len(sanitized_assumptions),
            acknowledged_conflicts_count=len(sanitized_conflicts),
            open_questions_count=len(sanitized_questions),
            empty_decision_line="My decision: __________________________________________________",
        )

    except Exception as exc:
        logger.error(f"Error generating reasoning map: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while compiling your reasoning map.",
        ) from exc
