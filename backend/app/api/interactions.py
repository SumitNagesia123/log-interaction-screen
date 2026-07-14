import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any

from backend.app.db.session import get_db
from backend.app.db.models import HCP, Product, Interaction, InteractionSample, AuditLog
from backend.app.schemas.interaction import (
    InteractionCreate,
    InteractionUpdate,
    InteractionResponse,
    AuditLog as AuditLogSchema,
    FieldMetadata,
    InteractionMetadata
)
from backend.app.api.auth import get_current_user

router = APIRouter()

# =====================================================================
# Helper Functions
# =====================================================================

def reconstruct_metadata(interaction: Interaction, db: Session) -> InteractionMetadata:
    logs = db.query(AuditLog).filter(AuditLog.interaction_id == interaction.id).all()
    fields_meta = {}
    standard_fields = [
        "hcp_id", "type", "datetime", "discussion_notes", "sentiment",
        "follow_up_required", "follow_up_date", "follow_up_notes",
        "product_ids", "samples"
    ]
    
    for f in standard_fields:
        fields_meta[f] = FieldMetadata(source="manual", confidence=1.0)
        
    logs.sort(key=lambda x: x.timestamp)
    first_log = logs[0] if logs else None
    if first_log and first_log.action == "CREATE" and first_log.source == "ai":
        for f in standard_fields:
            fields_meta[f] = FieldMetadata(source="ai", confidence=first_log.confidence_score or 0.90)

    for log in logs:
        if log.action == "UPDATE" and log.field_name:
            field = log.field_name
            if field == "products":
                field = "product_ids"
            if field in fields_meta:
                fields_meta[field] = FieldMetadata(
                    source=log.source,
                    confidence=log.confidence_score or 1.0
                )
                
    return InteractionMetadata(**fields_meta)

def build_interaction_response(interaction: Interaction, meta: InteractionMetadata) -> InteractionResponse:
    return InteractionResponse(
        id=interaction.id,
        hcp_id=interaction.hcp_id,
        hcp=interaction.hcp,
        type=interaction.type,
        datetime=interaction.datetime,
        discussion_notes=interaction.discussion_notes,
        sentiment=interaction.sentiment,
        follow_up_required=interaction.follow_up_required,
        follow_up_date=interaction.follow_up_date,
        follow_up_notes=interaction.follow_up_notes,
        products=interaction.products,
        samples=interaction.samples,
        metadata_fields=meta,
        created_at=interaction.created_at,
        updated_at=interaction.updated_at
    )

# =====================================================================
# Router Endpoints
# =====================================================================

@router.get("/api/interactions", response_model=List[InteractionResponse])
def get_interactions(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    interactions = db.query(Interaction).order_by(Interaction.datetime.desc()).all()
    res = []
    for inter in interactions:
        meta = reconstruct_metadata(inter, db)
        res.append(build_interaction_response(inter, meta))
    return res

@router.get("/api/interactions/{id}", response_model=InteractionResponse)
def get_interaction(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inter = db.query(Interaction).filter(Interaction.id == id).first()
    if not inter:
        raise HTTPException(status_code=404, detail="Interaction not found")
    meta = reconstruct_metadata(inter, db)
    return build_interaction_response(inter, meta)

@router.post("/api/interactions", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
def create_interaction(data: InteractionCreate, source: str = "manual", confidence: float = 1.0, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    hcp = db.query(HCP).filter(HCP.id == data.hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")

    db_interaction = Interaction(
        hcp_id=data.hcp_id,
        type=data.type,
        datetime=data.datetime or datetime.datetime.utcnow(),
        discussion_notes=data.discussion_notes,
        sentiment=data.sentiment,
        follow_up_required=data.follow_up_required,
        follow_up_date=data.follow_up_date,
        follow_up_notes=data.follow_up_notes
    )
    db.add(db_interaction)
    db.flush()

    if data.product_ids:
        products = db.query(Product).filter(Product.id.in_(data.product_ids)).all()
        db_interaction.products = products

    if data.samples:
        for s in data.samples:
            db_sample = InteractionSample(
                interaction_id=db_interaction.id,
                product_id=s.product_id,
                quantity=s.quantity
            )
            db.add(db_sample)

    db.commit()
    db.refresh(db_interaction)

    audit = AuditLog(
        interaction_id=db_interaction.id,
        action="CREATE",
        source=source,
        confidence_score=confidence if source == "ai" else 1.0,
        changed_by=current_user.get("username", "Sales Rep"),
        old_value=None,
        new_value=f"Created log for HCP {hcp.name}"
    )
    db.add(audit)
    db.commit()

    meta = reconstruct_metadata(db_interaction, db)
    return build_interaction_response(db_interaction, meta)

@router.put("/api/interactions/{id}", response_model=InteractionResponse)
def update_interaction(id: int, data: InteractionUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_interaction = db.query(Interaction).filter(Interaction.id == id).first()
    if not db_interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    edits = []
    source = data.source or "manual"
    confidence = data.confidence_score if source == "ai" else 1.0

    def check_change(field_name: str, new_val: Any, old_val: Any):
        if new_val is not None and new_val != old_val:
            edits.append(AuditLog(
                interaction_id=id,
                action="UPDATE",
                field_name=field_name,
                old_value=str(old_val) if old_val is not None else "",
                new_value=str(new_val),
                source=source,
                confidence_score=confidence,
                changed_by=current_user.get("username", "Sales Rep")
            ))
            return True
        return False

    if data.hcp_id is not None:
        if check_change("hcp_id", data.hcp_id, db_interaction.hcp_id):
            db_interaction.hcp_id = data.hcp_id

    if data.type is not None:
        if check_change("type", data.type, db_interaction.type):
            db_interaction.type = data.type

    if data.datetime is not None:
        if check_change("datetime", data.datetime, db_interaction.datetime):
            db_interaction.datetime = data.datetime

    if data.discussion_notes is not None:
        if check_change("discussion_notes", data.discussion_notes, db_interaction.discussion_notes):
            db_interaction.discussion_notes = data.discussion_notes

    if data.sentiment is not None:
        if check_change("sentiment", data.sentiment, db_interaction.sentiment):
            db_interaction.sentiment = data.sentiment

    if data.follow_up_required is not None:
        if check_change("follow_up_required", data.follow_up_required, db_interaction.follow_up_required):
            db_interaction.follow_up_required = data.follow_up_required

    if data.follow_up_date is not None:
        if check_change("follow_up_date", data.follow_up_date, db_interaction.follow_up_date):
            db_interaction.follow_up_date = data.follow_up_date

    if data.follow_up_notes is not None:
        if check_change("follow_up_notes", data.follow_up_notes, db_interaction.follow_up_notes):
            db_interaction.follow_up_notes = data.follow_up_notes

    if data.product_ids is not None:
        old_prod_ids = [p.id for p in db_interaction.products]
        if set(old_prod_ids) != set(data.product_ids):
            check_change("products", list(data.product_ids), old_prod_ids)
            products = db.query(Product).filter(Product.id.in_(data.product_ids)).all()
            db_interaction.products = products

    if data.samples is not None:
        old_samples_dict = {s.product_id: s.quantity for s in db_interaction.samples}
        new_samples_dict = {s.product_id: s.quantity for s in data.samples}
        
        if old_samples_dict != new_samples_dict:
            check_change("samples", str(new_samples_dict), str(old_samples_dict))
            db.query(InteractionSample).filter(InteractionSample.interaction_id == id).delete()
            for s in data.samples:
                db_sample = InteractionSample(
                    interaction_id=id,
                    product_id=s.product_id,
                    quantity=s.quantity
                )
                db.add(db_sample)

    for edit in edits:
        db.add(edit)

    db_interaction.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(db_interaction)

    meta = reconstruct_metadata(db_interaction, db)
    return build_interaction_response(db_interaction, meta)

@router.get("/api/interactions/{id}/audit", response_model=List[AuditLogSchema])
def get_interaction_audit(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return db.query(AuditLog).filter(AuditLog.interaction_id == id).order_by(AuditLog.timestamp.desc()).all()
