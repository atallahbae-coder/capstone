from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import os

from ai_service import (
    safe_llm_call, parse_json_response,
    VALID_GOALS, VALID_LEVELS, build_workout_prompt,
    VALID_DIET_GOALS, VALID_DIETS, build_diet_prompt,
    detect_intent_hint, chat_model
)

app = FastAPI()

# ─────────────────────────────────────────────
# HOME — serve index_combined.html (CSS & JS sudah di-embed)
# ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home():
    base_dir  = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "index_combined.html")
    if not os.path.exists(html_path):
        return HTMLResponse(
            f"<h1>File tidak ditemukan: {html_path}</h1>"
            "<p>Pastikan <b>index_combined.html</b> ada di folder yang sama dengan main_api.py</p>",
            status_code=404
        )
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

# ─────────────────────────────────────────────
# BMI
# ─────────────────────────────────────────────
@app.get("/bmi")
def calculate_bmi(
    weight: float = Query(..., gt=0, lt=500),
    height: float = Query(..., gt=0.3, lt=3.0),
    age: int      = Query(..., gt=0, lt=120),
):
    bmi = weight / (height ** 2)
    bmi_rounded = round(bmi, 2)
    if bmi < 18.5:       category = "Underweight"
    elif bmi < 25:       category = "Normal"
    elif bmi < 30:       category = "Overweight"
    else:                category = "Obese"

    prompt = (
        f"A {age}-year-old has a BMI of {bmi_rounded} ({category}). "
        "Give brief, practical health advice in 2-3 sentences. Be encouraging."
    )
    ai_advice = "AI advice unavailable right now."
    try:
        ai_advice = safe_llm_call(prompt)
    except HTTPException as e:
        ai_advice = f"AI error: {e.detail}"

    return {"bmi": bmi_rounded, "category": category, "age": age, "advice": ai_advice}

# ─────────────────────────────────────────────
# WORKOUT PLAN
# ─────────────────────────────────────────────
@app.get("/workout-plan")
def generate_workout_plan(
    goal: str,
    fitness_level: str = "beginner",
    days_per_week: int = Query(4, ge=1, le=7),
):
    if goal.lower() not in VALID_GOALS:
        raise HTTPException(400, f"Invalid goal '{goal}'. Choose: {VALID_GOALS}")
    if fitness_level.lower() not in VALID_LEVELS:
        raise HTTPException(400, f"Invalid fitness_level. Choose: {VALID_LEVELS}")
    raw = safe_llm_call(build_workout_prompt(goal, fitness_level, days_per_week))
    return parse_json_response(raw)

# ─────────────────────────────────────────────
# DIET PLAN  (target_weight added as optional param)
# ─────────────────────────────────────────────
@app.get("/diet-plan")
def generate_diet_plan(
    goal: str,
    dietary_preference: str = "none",
    allergies: str = "",
    daily_calories: int = Query(2000, ge=800, le=5000),
    meals_per_day: int = Query(3, ge=2, le=6),
    target_weight: Optional[float] = Query(None, gt=0, lt=500),
):
    if goal.lower() not in VALID_DIET_GOALS:
        raise HTTPException(400, f"Invalid goal '{goal}'. Choose: {VALID_DIET_GOALS}")
    if dietary_preference.lower() not in VALID_DIETS:
        raise HTTPException(400, f"Invalid dietary_preference. Choose: {VALID_DIETS}")
    raw = safe_llm_call(build_diet_prompt(
        goal.lower(), dietary_preference.lower(), allergies,
        daily_calories, meals_per_day, target_weight
    ))
    return parse_json_response(raw)

# ─────────────────────────────────────────────
# FITNESS CHATBOT
# ─────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str      # "user" or "model"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

MAX_HISTORY_TURNS = 20

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(400, "Message cannot be empty.")
    if len(message) > 1000:
        raise HTTPException(400, "Message too long — keep it under 1000 characters.")

    history = request.history[-(MAX_HISTORY_TURNS * 2):]

    for msg in history:
        if msg.role not in ("user", "model"):
            raise HTTPException(400, f"Invalid role '{msg.role}'. Must be 'user' or 'model'.")

    gemini_history = [
        {"role": msg.role, "parts": [msg.content]}
        for msg in history
    ]

    hint = detect_intent_hint(message)
    send_text = message + hint if hint else message

    try:
        session = chat_model.start_chat(history=gemini_history)
        response = session.send_message(send_text)
        reply = response.text
    except Exception as e:
        raise HTTPException(500, f"Chat error: {str(e)}")

    updated_history = [
        *[{"role": m.role, "content": m.content} for m in history],
        {"role": "user",  "content": message},
        {"role": "model", "content": reply},
    ]

    return {"reply": reply, "history": updated_history}

# ─────────────────────────────────────────────
# ASK AI
# ─────────────────────────────────────────────
@app.get("/ask-ai")
def ask_ai(question: str = Query(..., min_length=3, max_length=500)):
    return {"question": question, "answer": safe_llm_call(question)}
