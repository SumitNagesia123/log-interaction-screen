import os
from typing import List, Dict
from backend.app.config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    GROQ_MODEL_PRIMARY,
    GROQ_MODEL_FALLBACK
)

async def call_llm(messages: List[Dict[str, str]], json_mode: bool = False) -> str:
    """Invokes LLM (Groq primary with fallback, or Gemini fallback)."""
    if GROQ_API_KEY:
        for model in [GROQ_MODEL_PRIMARY, GROQ_MODEL_FALLBACK]:
            try:
                import groq
                client = groq.Groq(api_key=GROQ_API_KEY)
                kwargs = {
                    "messages": messages,
                    "model": model,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                completion = client.chat.completions.create(**kwargs)
                return completion.choices[0].message.content
            except Exception as e:
                print(f"Groq API Error on model {model}: {e}")
                continue

    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
            if json_mode:
                try:
                    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                except Exception as e_config:
                    # Fallback for older versions of google-generativeai that do not support response_mime_type
                    response = model.generate_content(prompt)
            else:
                response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API Error: {e}")

    raise ValueError("No LLM key configured or all LLM API requests failed.")
