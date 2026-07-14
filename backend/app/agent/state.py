from typing import TypedDict, Optional, List, Dict, Any
from backend.app.schemas.chat import PreviewCard

class AgentState(TypedDict):
    message: str
    session_id: str
    intent: Optional[str]
    extracted_fields: Optional[Dict[str, Any]]
    candidate_hcps: List[Dict[str, Any]]
    active_interaction_id: Optional[int]
    pending_confirmation: bool
    response: Optional[str]
    preview_card: Optional[PreviewCard]
