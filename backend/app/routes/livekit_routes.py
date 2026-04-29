import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

load_dotenv()

router = APIRouter(tags=["livekit"])


class TokenRequest(BaseModel):
    room_name: str = ""
    participant_name: str = "patient"


class TokenResponse(BaseModel):
    token: str
    room_name: str
    livekit_url: str


@router.post("/token", response_model=TokenResponse)
async def generate_token(req: TokenRequest):
    """
    Generate a LiveKit JWT token for a patient to join a voice session.
    If room_name is not provided, a new UUID-based room name is generated.
    """
    api_key = os.getenv("LIVEKIT_API_KEY", "")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "")
    livekit_url = os.getenv("LIVEKIT_URL", "")

    if not all([api_key, api_secret, livekit_url]):
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured on server.",
        )

    room_name = req.room_name or f"session-{uuid.uuid4().hex[:12]}"
    participant_identity = f"patient-{uuid.uuid4().hex[:8]}"

    try:
        from livekit.api import AccessToken, VideoGrants

        token = (
            AccessToken(api_key=api_key, api_secret=api_secret)
            .with_identity(participant_identity)
            .with_name(req.participant_name)
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .to_jwt()
        )

        return TokenResponse(token=token, room_name=room_name, livekit_url=livekit_url)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {exc}")
