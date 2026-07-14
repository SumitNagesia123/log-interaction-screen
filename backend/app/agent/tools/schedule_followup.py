import datetime
from sqlalchemy.orm import Session
from backend.app.db.models import Interaction, AuditLog

def schedule_followup_tool(interaction_id: int, due_date: str, notes: str, db: Session) -> Interaction:
    """
    Schedules a follow-up action.
    Updates the follow-up variables inside the Interaction record.
    """
    db_interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not db_interaction:
        raise ValueError(f"Interaction {interaction_id} not found")

    parsed_date = datetime.datetime.strptime(due_date, "%Y-%m-%d").date() if isinstance(due_date, str) else due_date

    db_interaction.follow_up_required = True
    db_interaction.follow_up_date = parsed_date
    db_interaction.follow_up_notes = notes

    # Audit log
    audit = AuditLog(
        interaction_id=interaction_id,
        action="UPDATE",
        field_name="follow_up",
        old_value="follow_up_required=False",
        new_value=f"follow_up_required=True, date={due_date}, notes={notes}",
        source="ai",
        confidence_score=0.9,
        changed_by="Sales Rep"
    )
    db.add(audit)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction
