import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.db.models import HCP
from backend.app.agent.utils import fuzzy_match

def search_hcp_tool(query: str, db: Session) -> List[Dict[str, Any]]:
    """
    Fuzzy search over the hcps table.
    Returns ranked candidates for resolving a doctor name.
    """
    if not query:
        return []
    hcps = db.query(HCP).all()
    matches = []
    clean_query = re.sub(r'\b(dr|dr\.|doctor)\b', '', query, flags=re.IGNORECASE).strip()
    
    for hcp in hcps:
        score = fuzzy_match(clean_query, hcp.name)
        if score > 0.4:
            matches.append({
                "id": hcp.id,
                "name": hcp.name,
                "specialty": hcp.specialty,
                "score": score
            })
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches
