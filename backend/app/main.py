from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.db.session import engine, Base
from backend.seed import seed_db
from backend.app.api import auth, hcps, interactions, chat

app = FastAPI(title="Log Interaction CRM API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database and seed on startup
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    seed_db()

# Include routers
app.include_router(auth.router)
app.include_router(hcps.router)
app.include_router(interactions.router)
app.include_router(chat.router)
