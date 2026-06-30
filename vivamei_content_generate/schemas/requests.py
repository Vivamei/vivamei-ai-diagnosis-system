"""
schemas/requests.py

Request models for API endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field


class AnalyzeUrlRequest(BaseModel):
    """Request to analyze an image via public URL."""
    image_url: str = Field(..., description="Publicly accessible image URL")
    user_id: Optional[str] = Field(default=None, description="Optional user ID")
