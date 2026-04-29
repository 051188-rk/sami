from fastapi import APIRouter, HTTPException

from app.services.summary_service import get_summary

router = APIRouter(tags=["summary"])


@router.get("/summary/{session_id}")
async def fetch_summary(session_id: str):
    """
    Retrieve the structured conversation summary for a given session.
    The summary is generated when end_conversation tool is called.
    """
    summary = get_summary(session_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"No summary found for session '{session_id}'. "
                   "The conversation may still be in progress.",
        )
    return summary
