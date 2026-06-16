"""Health check route for the receiver service."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return receiver health status."""

    return {"status": "ok", "service": "receiver"}
