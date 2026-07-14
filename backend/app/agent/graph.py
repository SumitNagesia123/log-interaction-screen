import re
import datetime
import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

from backend.app.config import GROQ_API_KEY, GEMINI_API_KEY
from backend.app.db.models import HCP, Product, Interaction
from backend.app.schemas.chat import PreviewCard, ChatResponse
from backend.app.schemas.interaction import InteractionMetadata, FieldMetadata
from backend.app.agent.state import AgentState
from backend.app.agent.llm import call_llm
from backend.app.agent.utils import resolve_product_entity
from backend.app.agent.tools.search_hcp import search_hcp_tool
from backend.app.agent.tools.summarize_history import summarize_history_tool

# =====================================================================
# High-Fidelity Heuristic Fallback Parser
# =====================================================================

def extract_entities_fallback(text: str, db: Session) -> Dict[str, Any]:
    text_lower = text.lower()
    is_edit = any(word in text_lower for word in ["change", "edit", "correct", "update", "modify"])
    
    hcp_match = re.search(r'\b(?:dr\.?|doctor)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)', text, re.IGNORECASE)
    hcp_name = hcp_match.group(1).strip() if hcp_match else None
    
    if not hcp_name:
        hcps = db.query(HCP).all()
        for h in hcps:
            last_name = h.name.split()[-1]
            if last_name.lower() in text_lower:
                hcp_name = h.name
                break

    products = db.query(Product).all()
    discussed_products = []
    for p in products:
        if p.name.lower() in text_lower:
            discussed_products.append(p.name)
            
    samples = []
    for p in products:
        pattern1 = rf'(\d+)\s+(?:boxes|box|samples|qty)?\s+(?:of\s+)?{p.name}'
        pattern2 = rf'{p.name}\s*[:,-]?\s*(\d+)'
        m1 = re.search(pattern1, text, re.IGNORECASE)
        m2 = re.search(pattern2, text, re.IGNORECASE)
        qty = 0
        if m1:
            qty = int(m1.group(1))
        elif m2:
            qty = int(m2.group(1))
        if qty > 0:
            samples.append({"product_name": p.name, "quantity": qty})

    sentiment = "Neutral"
    if any(w in text_lower for w in ["positive", "happy", "excited", "good", "great", "interested"]):
        sentiment = "Positive"
    elif any(w in text_lower for w in ["negative", "unhappy", "angry", "bad", "concerned", "skeptical"]):
        sentiment = "Negative"
        
    interaction_type = "Visit"
    if "call" in text_lower:
        interaction_type = "Call"
    elif "email" in text_lower:
        interaction_type = "Email"
    elif "conference" in text_lower or "meeting" in text_lower:
        interaction_type = "Conference"
    elif "sample" in text_lower and len(samples) > 0 and len(discussed_products) == 0:
        interaction_type = "Sample Drop"
        
    follow_up_required = any(w in text_lower for w in ["follow up", "follow-up", "next step", "schedule"])
    follow_up_notes = None
    follow_up_date = None
    
    if follow_up_required:
        if "2 weeks" in text_lower:
            follow_up_date = (datetime.date.today() + datetime.timedelta(weeks=2)).isoformat()
            follow_up_notes = "Schedule follow-up in 2 weeks"
        elif "1 week" in text_lower or "next week" in text_lower:
            follow_up_date = (datetime.date.today() + datetime.timedelta(weeks=1)).isoformat()
            follow_up_notes = "Schedule follow-up next week"
        elif "tomorrow" in text_lower:
            follow_up_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
            follow_up_notes = "Call tomorrow"
        else:
            follow_up_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
            follow_up_notes = "Follow up with details requested"

    interaction_date = datetime.datetime.now().isoformat()
    if "yesterday" in text_lower:
        interaction_date = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        
    target_interaction_id = None
    if is_edit:
        hcp_obj = None
        if hcp_name:
            cands = search_hcp_tool(hcp_name, db)
            if cands:
                hcp_obj = db.query(HCP).filter_by(id=cands[0]["id"]).first()
        if hcp_obj:
            last_interaction = db.query(Interaction).filter_by(hcp_id=hcp_obj.id).order_by(Interaction.id.desc()).first()
            if last_interaction:
                target_interaction_id = last_interaction.id

    return {
        "is_edit_operation": is_edit,
        "hcp_name": hcp_name,
        "type": interaction_type,
        "datetime": interaction_date,
        "discussion_notes": text,
        "sentiment": sentiment,
        "products": discussed_products,
        "samples": samples,
        "follow_up_required": follow_up_required,
        "follow_up_date": follow_up_date,
        "follow_up_notes": follow_up_notes,
        "target_interaction_id": target_interaction_id
    }

# =====================================================================
# Graph Nodes
# =====================================================================

async def classify_intent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    message = state["message"]
    intent = "new_log"
    
    text_lower = message.lower()
    if any(w in text_lower for w in ["change", "edit", "correct", "update", "modify"]):
        intent = "edit_request"
    elif any(w in text_lower for w in ["history", "summarize", "last time", "recent", "past"]):
        intent = "query"
    elif any(w in text_lower for w in ["follow up", "schedule", "remind"]):
        intent = "followup"

    if GROQ_API_KEY or GEMINI_API_KEY:
        prompt = [
            {"role": "system", "content": (
                "You are an intent classifier for a Life Science CRM Chat Assistant.\n"
                "Categorize the user message into exactly one of these strings:\n"
                "- 'new_log': User describes a doctor visit or interaction they want to log.\n"
                "- 'edit_request': User wants to change, edit, update, or correct an interaction.\n"
                "- 'followup': User specifically wants to schedule a follow-up action.\n"
                "- 'query': User wants to review previous visits or request a summary.\n"
                "- 'unclear': Message is general greeting, chit-chat or ambiguous.\n"
                "\n"
                "You MUST return a JSON object with key 'intent'. E.g. {\"intent\": \"new_log\"}"
            )},
            {"role": "user", "content": message}
        ]
        try:
            res = await call_llm(prompt, json_mode=True)
            parsed = json.loads(res)
            intent = parsed.get("intent", intent)
        except Exception as e:
            print(f"Failed LLM intent classification: {e}. Fallback to: {intent}")

    return {"intent": intent}

async def extract_entities_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    message = state["message"]
    db = config["configurable"]["db"]
    extracted = {}

    if GROQ_API_KEY or GEMINI_API_KEY:
        system_prompt = (
            "You are a structured clinical CRM details extractor. Parse the visit text and extract:\n"
            "- is_edit_operation: boolean\n"
            "- hcp_name: string (e.g. 'Dr. Sharma')\n"
            "- type: string ('Visit', 'Call', 'Email', 'Sample Drop', 'Conference')\n"
            "- datetime: string (ISO format or null. If user says 'yesterday', calculate relative to now)\n"
            "- discussion_notes: string (summary of clinical discussion)\n"
            "- sentiment: string ('Positive', 'Neutral', 'Negative')\n"
            "- products: list of strings (brand names of products discussed)\n"
            "- samples: list of objects with keys 'product_name' and 'quantity'\n"
            "- follow_up_required: boolean\n"
            "- follow_up_date: string (YYYY-MM-DD or null)\n"
            "- follow_up_notes: string or null\n"
            "- target_interaction_id: integer or null\n"
            "\n"
            "Respond ONLY with a valid JSON object matching these keys."
        )
        try:
            res = await call_llm([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ], json_mode=True)
            extracted = json.loads(res)
        except Exception as e:
            print(f"LLM extraction failed: {e}. Falling back to regex.")
            extracted = extract_entities_fallback(message, db)
    else:
        extracted = extract_entities_fallback(message, db)

    return {"extracted_fields": extracted}

async def resolve_entities_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    extracted = state["extracted_fields"] or {}
    db = config["configurable"]["db"]
    
    hcp_name = extracted.get("hcp_name")
    candidate_hcps = []
    resolved_hcp_id = None
    resolved_hcp_name = hcp_name

    if hcp_name:
        candidates = search_hcp_tool(hcp_name, db)
        if len(candidates) == 1:
            resolved_hcp_id = candidates[0]["id"]
            resolved_hcp_name = candidates[0]["name"]
        elif len(candidates) > 1:
            if candidates[0]["score"] > 0.85 and (candidates[0]["score"] - candidates[1]["score"]) > 0.2:
                resolved_hcp_id = candidates[0]["id"]
                resolved_hcp_name = candidates[0]["name"]
            else:
                candidate_hcps = candidates

    resolved_product_ids = []
    for prod_name in extracted.get("products", []):
        p = resolve_product_entity(prod_name, db)
        if p:
            resolved_product_ids.append(p.id)

    resolved_samples = []
    for s in extracted.get("samples", []):
        p = resolve_product_entity(s.get("product_name"), db)
        if p:
            resolved_samples.append({
                "product_id": p.id,
                "product_name": p.name,
                "quantity": int(s.get("quantity", 0))
            })

    extracted["hcp_id"] = resolved_hcp_id
    extracted["hcp_name"] = resolved_hcp_name
    extracted["product_ids"] = resolved_product_ids
    extracted["samples"] = resolved_samples

    return {"extracted_fields": extracted, "candidate_hcps": candidate_hcps}

async def preview_confirm_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    intent = state["intent"]
    extracted = state["extracted_fields"] or {}
    candidate_hcps = state["candidate_hcps"]
    db = config["configurable"]["db"]

    if candidate_hcps:
        return {
            "response": f"I found multiple doctors matching '{extracted.get('hcp_name')}'. Please select the correct doctor:",
            "pending_confirmation": False,
            "preview_card": None
        }

    if intent == "query":
        hcp_id = extracted.get("hcp_id")
        if hcp_id:
            summary = summarize_history_tool(hcp_id, db)
            return {
                "response": summary,
                "pending_confirmation": False,
                "preview_card": None
            }
        else:
            return {
                "response": f"Which doctor's history would you like to review? (e.g. 'summarize history for Dr. Ananya Sharma')",
                "pending_confirmation": False,
                "preview_card": None
            }

    if intent == "followup" and not extracted.get("hcp_id"):
        return {
            "response": "Sure, which doctor is this follow-up for? (e.g. 'schedule follow up next week for Dr. Ananya Sharma')",
            "pending_confirmation": False,
            "preview_card": None
        }

    target_id = extracted.get("target_interaction_id")
    is_edit = extracted.get("is_edit_operation", False) or (intent == "edit_request")

    if is_edit and not target_id:
        hcp_id = extracted.get("hcp_id")
        if hcp_id:
            last_inter = db.query(Interaction).filter_by(hcp_id=hcp_id).order_by(Interaction.id.desc()).first()
            if last_inter:
                target_id = last_inter.id
                extracted["target_interaction_id"] = target_id

    confidence = 0.90 if (GROQ_API_KEY or GEMINI_API_KEY) else 0.80

    metadata = InteractionMetadata(
        hcp_id=FieldMetadata(source="ai" if extracted.get("hcp_id") else "manual", confidence=confidence),
        type=FieldMetadata(source="ai", confidence=confidence),
        datetime=FieldMetadata(source="ai", confidence=confidence),
        discussion_notes=FieldMetadata(source="ai", confidence=confidence),
        sentiment=FieldMetadata(source="ai", confidence=confidence),
        follow_up_required=FieldMetadata(source="ai", confidence=confidence),
        follow_up_date=FieldMetadata(source="ai" if extracted.get("follow_up_date") else "manual", confidence=confidence),
        follow_up_notes=FieldMetadata(source="ai" if extracted.get("follow_up_notes") else "manual", confidence=confidence),
        product_ids=FieldMetadata(source="ai" if extracted.get("product_ids") else "manual", confidence=confidence),
        samples=FieldMetadata(source="ai" if extracted.get("samples") else "manual", confidence=confidence)
    )

    preview_card = PreviewCard(
        hcp_id=extracted.get("hcp_id"),
        hcp_name=extracted.get("hcp_name"),
        type=extracted.get("type", "Visit"),
        datetime=extracted.get("datetime"),
        discussion_notes=extracted.get("discussion_notes"),
        sentiment=extracted.get("sentiment", "Neutral"),
        products=[db.query(Product).filter_by(id=pid).first().name for pid in extracted.get("product_ids", [])],
        samples=extracted.get("samples", []),
        follow_up_required=extracted.get("follow_up_required", False),
        follow_up_date=extracted.get("follow_up_date"),
        follow_up_notes=extracted.get("follow_up_notes"),
        metadata_fields=metadata,
        is_edit_operation=is_edit,
        target_interaction_id=target_id
    )

    if is_edit:
        msg = f"I've drafted changes for the interaction with {extracted.get('hcp_name') or 'the doctor'}. Please check details below."
    else:
        msg = f"I've drafted a new interaction log for {extracted.get('hcp_name') or 'the doctor'}. Check preview below."

    return {
        "response": msg,
        "preview_card": preview_card,
        "pending_confirmation": True
    }

# =====================================================================
# Build and Compile LangGraph
# =====================================================================

def route_by_intent(state: AgentState) -> str:
    return state.get("intent") or "new_log"

workflow = StateGraph(AgentState)

workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("extract_entities", extract_entities_node)
workflow.add_node("resolve_entities", resolve_entities_node)
workflow.add_node("preview_confirm", preview_confirm_node)

workflow.set_entry_point("classify_intent")

workflow.add_conditional_edges(
    "classify_intent",
    route_by_intent,
    {
        "new_log": "extract_entities",
        "edit_request": "extract_entities",
        "followup": "extract_entities",
        "query": "extract_entities",
        "unclear": "preview_confirm"
    }
)

workflow.add_edge("extract_entities", "resolve_entities")
workflow.add_edge("resolve_entities", "preview_confirm")
workflow.add_edge("preview_confirm", END)

memory = MemorySaver()
compiled_graph = workflow.compile(checkpointer=memory)

# =====================================================================
# Chat orchestration function
# =====================================================================

async def parse_and_process_chat(message: str, db: Session, session_id: str = "default") -> ChatResponse:
    state_input = {
        "message": message,
        "session_id": session_id,
        "intent": None,
        "extracted_fields": {},
        "candidate_hcps": [],
        "active_interaction_id": None,
        "pending_confirmation": False,
        "response": None,
        "preview_card": None
    }
    
    config = {
        "configurable": {
            "thread_id": session_id,
            "db": db
        }
    }

    final_state = await compiled_graph.ainvoke(state_input, config)

    candidate_hcps = final_state.get("candidate_hcps")
    if candidate_hcps:
        return ChatResponse(
            response=final_state.get("response") or "Multiple HCPs matched. Please disambiguate:",
            preview_card=None,
            needs_disambiguation=True,
            disambiguation_options=[{
                "id": c["id"],
                "name": c["name"],
                "specialty": c["specialty"]
            } for c in candidate_hcps]
        )

    return ChatResponse(
        response=final_state.get("response") or "Draft generated successfully.",
        preview_card=final_state.get("preview_card"),
        needs_disambiguation=False,
        disambiguation_options=[]
    )
