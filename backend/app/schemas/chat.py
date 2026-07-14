from pydantic import BaseModel
from typing import List, Optional
from backend.app.schemas.interaction import InteractionMetadata

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[List[dict]] = None

class PreviewCard(BaseModel):
    hcp_id: Optional[int] = None
    hcp_name: Optional[str] = None
    type: Optional[str] = None  # Visit, Call, etc.
    datetime: Optional[str] = None
    discussion_notes: Optional[str] = None
    sentiment: Optional[str] = None
    products: List[str] = []
    samples: List[dict] = []  # e.g., [{"product_name": "CardioX", "quantity": 2}]
    follow_up_required: bool = False
    follow_up_date: Optional[str] = None
    follow_up_notes: Optional[str] = None
    metadata_fields: Optional[InteractionMetadata] = None
    is_edit_operation: bool = False
    target_interaction_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    preview_card: Optional[PreviewCard] = None
    needs_disambiguation: bool = False
    disambiguation_options: List[dict] = []
