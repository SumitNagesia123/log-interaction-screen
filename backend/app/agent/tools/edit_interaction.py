import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.db.models import Interaction, Product, InteractionSample, AuditLog

def edit_interaction_tool(interaction_id: int, diff: Dict[str, Any], db: Session) -> Interaction:
    """
    Mutates an existing interaction log and creates audit logs.
    Ensures all edits are explicitly logged to audit_logs.
    """
    db_interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not db_interaction:
        raise ValueError(f"Interaction with ID {interaction_id} not found")

    source = diff.get("source", "ai")
    confidence = diff.get("confidence_score", 0.9)

    def log_change(field_name: str, old_val: Any, new_val: Any):
        if old_val != new_val:
            audit = AuditLog(
                interaction_id=interaction_id,
                action="UPDATE",
                field_name=field_name,
                old_value=str(old_val) if old_val is not None else "",
                new_value=str(new_val),
                source=source,
                confidence_score=confidence,
                changed_by="Sales Rep"
            )
            db.add(audit)

    if "type" in diff and diff["type"] is not None:
        log_change("type", db_interaction.type, diff["type"])
        db_interaction.type = diff["type"]

    if "datetime" in diff and diff["datetime"] is not None:
        log_change("datetime", db_interaction.datetime, diff["datetime"])
        db_interaction.datetime = diff["datetime"]

    if "discussion_notes" in diff and diff["discussion_notes"] is not None:
        log_change("discussion_notes", db_interaction.discussion_notes, diff["discussion_notes"])
        db_interaction.discussion_notes = diff["discussion_notes"]

    if "sentiment" in diff and diff["sentiment"] is not None:
        log_change("sentiment", db_interaction.sentiment, diff["sentiment"])
        db_interaction.sentiment = diff["sentiment"]

    if "attendees" in diff and diff["attendees"] is not None:
        log_change("attendees", db_interaction.attendees, diff["attendees"])
        db_interaction.attendees = diff["attendees"]

    if "materials_shared" in diff and diff["materials_shared"] is not None:
        log_change("materials_shared", db_interaction.materials_shared, diff["materials_shared"])
        db_interaction.materials_shared = diff["materials_shared"]

    if "follow_up_required" in diff and diff["follow_up_required"] is not None:
        log_change("follow_up_required", db_interaction.follow_up_required, diff["follow_up_required"])
        db_interaction.follow_up_required = diff["follow_up_required"]

    if "follow_up_date" in diff and diff["follow_up_date"] is not None:
        log_change("follow_up_date", db_interaction.follow_up_date, diff["follow_up_date"])
        db_interaction.follow_up_date = diff["follow_up_date"]

    if "follow_up_notes" in diff and diff["follow_up_notes"] is not None:
        log_change("follow_up_notes", db_interaction.follow_up_notes, diff["follow_up_notes"])
        db_interaction.follow_up_notes = diff["follow_up_notes"]

    if "product_ids" in diff and diff["product_ids"] is not None:
        old_ids = [p.id for p in db_interaction.products]
        if set(old_ids) != set(diff["product_ids"]):
            log_change("products", old_ids, diff["product_ids"])
            products = db.query(Product).filter(Product.id.in_(diff["product_ids"])).all()
            db_interaction.products = products

    if "samples" in diff and diff["samples"] is not None:
        old_samples = {s.product_id: s.quantity for s in db_interaction.samples}
        new_samples = {s["product_id"]: s["quantity"] for s in diff["samples"]}
        if old_samples != new_samples:
            log_change("samples", str(old_samples), str(new_samples))
            db.query(InteractionSample).filter(InteractionSample.interaction_id == interaction_id).delete()
            for s in diff["samples"]:
                db_sample = InteractionSample(
                    interaction_id=interaction_id,
                    product_id=s["product_id"],
                    quantity=s["quantity"]
                )
                db.add(db_sample)

    db_interaction.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction
