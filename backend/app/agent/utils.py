import re
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.db.models import Product

def fuzzy_match(query: str, target: str) -> float:
    """Returns a simple matching ratio between query and target (0.0 to 1.0)."""
    if not query or not target:
        return 0.0
    query = query.lower().strip()
    target = target.lower().strip()
    if query == target:
        return 1.0
    if query in target or target in query:
        return len(query) / len(target) if len(query) < len(target) else len(target) / len(query)
    q_words = set(query.split())
    t_words = set(target.split())
    if not q_words or not t_words:
        return 0.0
    intersection = q_words.intersection(t_words)
    return len(intersection) / max(len(q_words), len(t_words))

def resolve_product_entity(prod_query: str, db: Session) -> Optional[Product]:
    """Matches a product name against the database."""
    if not prod_query:
        return None
    products = db.query(Product).all()
    best_match = None
    best_score = 0.0
    for prod in products:
        score = fuzzy_match(prod_query, prod.name)
        if score > best_score:
            best_score = score
            best_match = prod
    if best_score > 0.5:
        return best_match
    return None
