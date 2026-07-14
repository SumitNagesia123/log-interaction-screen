import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-12345")
JWT_ALGORITHM = "HS256"

# Database url
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hcp_crm.db")

# Groq models
GROQ_MODEL_PRIMARY = os.getenv("GROQ_MODEL_PRIMARY", "gemma2-9b-it")
GROQ_MODEL_FALLBACK = os.getenv("GROQ_MODEL_FALLBACK", "llama-3.3-70b-versatile")
