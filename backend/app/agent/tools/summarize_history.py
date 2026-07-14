from sqlalchemy.orm import Session
from backend.app.db.models import HCP, Interaction

def summarize_history_tool(hcp_id: int, db: Session) -> str:
    """
    Pulls recent visits for HCP and generates a clean summary of previous sessions.
    """
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        return f"HCP with ID {hcp_id} not found."
    interactions = db.query(Interaction).filter(Interaction.hcp_id == hcp_id).order_by(Interaction.datetime.desc()).limit(3).all()
    if not interactions:
        return f"No previous interactions logged for {hcp.name}."
    
    summary = f"Summary of recent visits to {hcp.name} ({hcp.specialty}):\n"
    for idx, inter in enumerate(interactions, 1):
        prods = ", ".join([p.name for p in inter.products])
        samps = ", ".join([f"{s.product.name} (x{s.quantity})" for s in inter.samples])
        summary += f"  {idx}. {inter.type} on {inter.datetime.strftime('%Y-%m-%d')}: '{inter.discussion_notes}'. Sentiment: {inter.sentiment}."
        if prods:
            summary += f" Products discussed: {prods}."
        if samps:
            summary += f" Samples: {samps}."
        if inter.follow_up_required:
            summary += f" Follow-up on {inter.follow_up_date}."
        summary += "\n"
    return summary
