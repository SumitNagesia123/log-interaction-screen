import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from backend.app.db.session import get_db
from backend.app.db.models import Product
from backend.app.schemas.chat import ChatRequest, ChatResponse, PreviewCard
from backend.app.schemas.interaction import InteractionResponse
from backend.app.agent.graph import parse_and_process_chat, compiled_graph
from backend.app.agent.tools.log_interaction import log_interaction_tool
from backend.app.agent.tools.edit_interaction import edit_interaction_tool
from backend.app.api.interactions import reconstruct_metadata, build_interaction_response
from backend.app.api.auth import get_current_user

router = APIRouter()

class ChatConfirmRequest(BaseModel):
    session_id: Optional[str] = "default"
    preview_card: PreviewCard

class ChatConfirmResponse(BaseModel):
    response: str
    interaction: InteractionResponse

@router.post("/api/chat", response_model=ChatResponse)
async def chat_interaction(request: ChatRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    response = await parse_and_process_chat(request.message, db, request.session_id or "default")
    return response

@router.post("/api/chat/confirm", response_model=ChatConfirmResponse)
async def chat_confirm(request: ChatConfirmRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    card = request.preview_card
    
    if not card.hcp_id:
         raise HTTPException(status_code=400, detail="HCP must be resolved before confirmation.")

    # Map product name strings to database IDs
    product_ids = []
    if card.products:
        prods = db.query(Product).filter(Product.name.in_(card.products)).all()
        product_ids = [p.id for p in prods]

    # Map samples to product IDs
    samples_payload = []
    for s in card.samples:
        pid = s.get("product_id")
        if not pid and s.get("product_name"):
            prod = db.query(Product).filter_by(name=s["product_name"]).first()
            if prod:
                pid = prod.id
        if pid:
            samples_payload.append({
                "product_id": pid,
                "quantity": s.get("quantity", 1)
            })

    # Convert ISO datetime string safely
    dt_val = datetime.datetime.now(datetime.timezone.utc)
    if card.datetime:
        try:
            # Handle standard ISO Z format
            clean_dt = card.datetime.replace('Z', '+00:00')
            dt_val = datetime.datetime.fromisoformat(clean_dt)
        except Exception:
            pass

    # Extract follow-up details
    follow_up_date_val = None
    if card.follow_up_required and card.follow_up_date:
        try:
            follow_up_date_val = datetime.datetime.strptime(card.follow_up_date, "%Y-%m-%d").date()
        except Exception:
            pass

    payload = {
        "hcp_id": card.hcp_id,
        "type": card.type or "Visit",
        "datetime": dt_val,
        "discussion_notes": card.discussion_notes,
        "sentiment": card.sentiment or "Neutral",
        "attendees": card.attendees,
        "materials_shared": card.materials_shared,
        "follow_up_required": card.follow_up_required,
        "follow_up_date": follow_up_date_val,
        "follow_up_notes": card.follow_up_notes,
        "product_ids": product_ids,
        "samples": samples_payload,
        "confidence_score": 0.90
    }

    # Route operation to appropriate tool based on is_edit_operation flag
    if card.is_edit_operation and card.target_interaction_id:
        db_interaction = edit_interaction_tool(card.target_interaction_id, payload, db)
        response_text = f"Successfully updated interaction for Dr. {card.hcp_name}!"
    else:
        db_interaction = log_interaction_tool(payload, db)
        response_text = f"Successfully logged new interaction for Dr. {card.hcp_name}!"

    meta = reconstruct_metadata(db_interaction, db)
    interaction_resp = build_interaction_response(db_interaction, meta)

    return ChatConfirmResponse(
        response=response_text,
        interaction=interaction_resp
    )
