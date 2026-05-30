import os
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi import HTTPException
from typing import Optional

# Memuat variabel lingkungan dari file .env
load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY tidak ditemukan di .env")

genai.configure(api_key=api_key)

# Model umum (digunakan oleh endpoint BMI, workout, dan diet)
model = genai.GenerativeModel("models/gemini-3.5-flash")

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def strip_fences(text: str) -> str:
    """Membersihkan markdown code blocks (fences) dari respons LLM."""
    text = text.strip()
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def safe_llm_call(prompt: str) -> str:
    """Melakukan panggilan LLM dengan penanganan kesalahan standar."""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

def parse_json_response(raw: str) -> dict:
    """Mengonversi respons teks mentah menjadi objek JSON/dict."""
    try:
        return json.loads(strip_fences(raw))
    except json.JSONDecodeError:
        return {"raw_plan": raw, "parse_error": "LLM did not return valid JSON."}

# ─────────────────────────────────────────────
# WORKOUT PLAN
# ─────────────────────────────────────────────
VALID_GOALS  = {"weight_loss", "muscle_gain"}
VALID_LEVELS = {"beginner", "intermediate", "advanced"}

def build_workout_prompt(goal: str, fitness_level: str, days_per_week: int) -> str:
    """Menyusun instruksi prompt untuk rencana latihan mingguan."""
    goal_context = {
        "weight_loss": (
            "weight loss. Prioritise compound movements, supersets, and cardio "
            "finishers. Keep rest periods short (30-60 s) to maximise calorie burn."
        ),
        "muscle_gain": (
            "muscle gain (hypertrophy). Prioritise progressive overload, "
            "isolation exercises, and adequate rest (60-90 s) between sets."
        ),
    }[goal]

    return f"""
You are an expert personal trainer. Create a detailed {days_per_week}-day weekly workout plan
for a {fitness_level}-level person whose primary goal is {goal_context}

Rules:
- Spread the {days_per_week} workout days across the week (include rest days).
- For each workout day: day name, focus area, and 4-6 exercises.
- Each exercise: name, sets (integer), reps (string e.g. "8-10" or "30 sec"), one coaching tip.
- Use bodyweight or standard gym equipment only.
- End with a short 2-sentence motivational note.

Respond in EXACT JSON (no markdown fences):
{{
  "goal": "{goal}",
  "fitness_level": "{fitness_level}",
  "days_per_week": {days_per_week},
  "weekly_plan": [
    {{
      "day": "Monday",
      "focus": "Upper Body Push",
      "exercises": [
        {{"name": "Bench Press", "sets": 4, "reps": "8-10", "tip": "Retract shoulder blades."}}
      ]
    }}
  ],
  "motivation": "Short motivational note here."
}}
"""

# ─────────────────────────────────────────────
# DIET PLAN  (target_weight param added)
# ─────────────────────────────────────────────
VALID_DIET_GOALS = {"weight_loss", "muscle_gain", "maintenance", "clean_eating"}
VALID_DIETS      = {"none", "vegetarian", "vegan", "keto", "halal", "gluten_free"}

def build_diet_prompt(goal, dietary_preference, allergies, daily_calories, meals_per_day,
                      target_weight: Optional[float] = None):
    """Menyusun instruksi prompt untuk rencana makanan/diet harian."""
    allergy_note = (
        f"Allergies/intolerances to avoid: {allergies}."
        if allergies.strip() else "No known allergies."
    )
    goal_context = {
        "weight_loss":  f"weight loss (target {daily_calories} kcal/day, high protein, high fibre, low refined carbs).",
        "muscle_gain":  f"muscle gain (target {daily_calories} kcal/day, very high protein ≥1.8 g/kg, complex carbs).",
        "maintenance":  f"weight maintenance ({daily_calories} kcal/day, balanced macros).",
        "clean_eating": f"clean eating ({daily_calories} kcal/day, whole foods only, minimal processing).",
    }[goal]
    diet_note = "" if dietary_preference == "none" else f"Strictly follow a {dietary_preference.replace('_',' ')} diet."
    target_note = (
        f"The person's target weight is {target_weight} kg. "
        "Include a brief note on estimated timeline to reach this target based on the calorie plan."
        if target_weight else ""
    )

    return f"""
You are a registered nutritionist. Create a detailed one-day meal plan for someone whose goal is {goal_context}
{diet_note}
{allergy_note}
{target_note}
The plan must contain exactly {meals_per_day} meals/snacks.

Respond in EXACT JSON (no markdown fences):
{{
  "goal": "{goal}", "dietary_preference": "{dietary_preference}",
  "target_calories": {daily_calories}, "meals_per_day": {meals_per_day},
  {"\"target_weight\": " + str(target_weight) + ", " if target_weight else ""}
  {"\"timeline_note\": \"Estimated timeline to reach target weight.\", " if target_weight else ""}
  "meals": [
    {{
      "meal": "Breakfast", "dish": "Oatmeal with Berries",
      "ingredients": ["80g rolled oats", "150ml almond milk"],
      "calories": 320,
      "macros": {{"protein_g": 10, "carbs_g": 55, "fat_g": 6}},
      "tip": "One-line nutrition tip."
    }}
  ],
  "daily_totals": {{"total_calories": 1800, "protein_g": 140, "carbs_g": 180, "fat_g": 55}},
  "nutrition_note": "2-sentence advice."
}}
"""

# ─────────────────────────────────────────────
# FITNESS CHATBOT
# ─────────────────────────────────────────────
FITNESS_SYSTEM_PROMPT = """\
You are FitCoach AI, a friendly and knowledgeable fitness and nutrition assistant built into the FitAI app.

Your expertise covers:
- Workout programming (strength, hypertrophy, cardio, HIIT, home workouts, gym splits)
- Nutrition and diet planning (macros, meal timing, supplements, weight loss, muscle gain)
- Recovery, sleep, mobility, and injury prevention
- Motivation, habit-building, and goal setting

Behaviour rules:
1. Be concise but complete — 2-4 sentences for simple questions; bullet lists for multi-step answers.
2. Always be encouraging, positive, and science-backed.
3. If asked about injuries or medical issues, give general guidance and always recommend consulting a doctor or physiotherapist.
4. If a question is completely unrelated to fitness, health, or nutrition, politely say:
   "I'm specialised in fitness and nutrition — happy to help with anything in that area!"
5. Never invent specific medical diagnoses or prescribe medications.
6. Remember the conversation history provided and build on it naturally.
"""

INTENT_HINTS: dict = {
    "home workout":  "User wants home/bodyweight workouts with no gym equipment.",
    "gym":           "User is asking about gym-based training. Include equipment names.",
    "muscle gain":   "User wants hypertrophy. Emphasise: progressive overload, 1.6-2.2 g protein/kg, compound lifts, 48h muscle recovery.",
    "build muscle":  "User wants hypertrophy. Emphasise: progressive overload, 1.6-2.2 g protein/kg, compound lifts, 48h muscle recovery.",
    "weight loss":   "User wants fat loss. Emphasise: 300-500 kcal deficit, protein to retain muscle, cardio + strength combo.",
    "lose weight":   "User wants fat loss. Emphasise: 300-500 kcal deficit, protein to retain muscle, cardio + strength combo.",
    "diet":          "User is asking about nutrition. Cover whole foods, macro balance, hydration.",
    "protein":       "Cover daily targets (1.6-2.2 g/kg), best sources (chicken, eggs, legumes, whey), and timing.",
    "cardio":        "Cover LISS vs HIIT, zone 2 training (60-70% max HR), frequency recommendations.",
    "beginner":      "User is a beginner. Keep advice simple, safe, and progressive. Start with 2-3 days/week.",
    "supplement":    "Stick to evidence-based supplements: creatine monohydrate, protein powder, vitamin D, omega-3.",
    "stretch":       "Cover dynamic warm-up before training, static stretching post-workout, daily mobility.",
    "sleep":         "Cover 7-9 hours, consistent schedule, pre-sleep routine, and its direct impact on gains.",
    "abs":           "Explain that low body-fat reveals abs (diet is key), plus core stability work (plank, dead bug).",
    "motivation":    "Give practical habit-building advice: identity-based habits, streak tracking, environment design.",
    "injury":        "Express empathy, give general RICE advice, and clearly recommend seeing a physiotherapist.",
    "fat":           "Distinguish dietary fat (healthy fats vs trans fats) from body fat. Cover role in hormones.",
    "calorie":       "Cover TDEE calculation, caloric deficit/surplus, and why quality of calories also matters.",
    "running":       "Cover proper form, progressive mileage increase (10% rule), shoe selection, and rest days.",
    "split":         "Cover popular training splits: full body 3x, upper/lower 4x, PPL 6x — pros/cons for each.",
}

def detect_intent_hint(message: str) -> str:
    """Mendeteksi apakah pesan mengandung kata kunci tertentu untuk menyuntikkan petunjuk kontekstual."""
    msg_lower = message.lower()
    for keyword, hint in INTENT_HINTS.items():
        if keyword in msg_lower:
            return f" [Coach context: {hint}]"
    return ""

# Model obrolan dengan sistem instruksi (system instruction) menggunakan gemini-3.5-flash
chat_model = genai.GenerativeModel("models/gemini-3.5-flash",
    system_instruction=FITNESS_SYSTEM_PROMPT,
)
