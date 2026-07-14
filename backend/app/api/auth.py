import hmac
import hashlib
import base64
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from backend.app.config import JWT_SECRET, JWT_ALGORITHM

router = APIRouter()

# =====================================================================
# JWT Token Generation & Verification
# =====================================================================

def create_access_token(data: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    signature = hmac.new(
        JWT_SECRET.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_access_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        expected_sig = hmac.new(
            JWT_SECRET.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        rem = len(sig_b64) % 4
        if rem > 0:
            sig_b64 += "=" * (4 - rem)
        actual_sig = base64.urlsafe_b64decode(sig_b64.encode())
        if not hmac.compare_digest(actual_sig, expected_sig):
            return None
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        return json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
    except Exception:
        return None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login", auto_error=False)

def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        # Graceful fallback for local development and direct testing
        return {"username": "demo_rep", "role": "sales_rep"}
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

@router.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "rep" and form_data.password == "crm123":
        token = create_access_token({"sub": form_data.username, "role": "sales_rep"})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password"
    )
