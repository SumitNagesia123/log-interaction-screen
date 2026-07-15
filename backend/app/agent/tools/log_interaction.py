import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.db.models import Interaction, Product, InteractionSample, AuditLog

def log_interaction_tool(data: Dict[str, Any], db: Session) -> Interaction:
    """
    Persists a structured interaction log to the database.
    Includes products, samples, and automatic audit creation.
    """
    db_interaction = Interaction(
        hcp_id=data["hcp_id"],
        type=data.get("type", "Visit"),
        datetime=data.get("datetime") or datetime.datetime.now(datetime.timezone.utc),
        discussion_notes=data.get("discussion_notes"),
        sentiment=data.get("sentiment", "Neutral"),
        attendees=data.get("attendees"),
        materials_shared=data.get("materials_shared"),
        follow_up_required=data.get("follow_up_required", False),
        follow_up_date=data.get("follow_up_date"),
        follow_up_notes=data.get("follow_up_notes")
    )
    db.add(db_interaction)
    db.flush()

    if data.get("product_ids"):
        products = db.query(Product).filter(Product.id.in_(data["product_ids"])).all()
        db_interaction.products = products

    if data.get("samples"):
        for s in data["samples"]:
            db_sample = InteractionSample(
                interaction_id=db_interaction.id,
                product_id=s["product_id"],
                quantity=s["quantity"]
            )
            db.add(db_sample)

    db.commit()
    db.refresh(db_interaction)

    # Log to audit trail
    audit = AuditLog(
        interaction_id=db_interaction.id,
        action="CREATE",
        source="ai",
        confidence_score=data.get("confidence_score", 0.9),
        changed_by="Sales Rep",
        old_value=None,
        new_value=f"Created log for HCP {db_interaction.hcp.name} via AI Chat Assistant"
    )
    db.add(audit)
    db.commit()
    return db_interaction
