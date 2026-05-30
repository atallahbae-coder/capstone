# AI Fitness Assistant

## Overview

AI Fitness Assistant is a web-based fitness application powered by Google's Gemini AI. The application helps users manage their fitness journey by generating personalized workout plans, diet recommendations, BMI analysis, and AI-powered fitness guidance.

The system uses FastAPI as the backend service and an interactive HTML frontend for user interaction.

---

## Features

### BMI Calculator

* Calculates Body Mass Index (BMI)
* Classifies BMI category
* Generates AI-powered health recommendations

### Workout Plan Generator

* Personalized workout routines
* Supports different fitness goals
* Supports multiple fitness levels
* Adjustable training frequency

### Diet Plan Generator

* Personalized meal planning
* Dietary preference support
* Allergy considerations
* Daily calorie customization

### AI Fitness Chatbot

* Interactive fitness assistant
* Answers fitness-related questions
* Provides guidance and recommendations

### Ask AI

* General-purpose AI question answering
* Powered by Google Gemini

---

## Technology Stack

### Backend

* Python
* FastAPI
* Pydantic
* Google Gemini API

### Frontend

* HTML
* CSS
* JavaScript

---

## Project Structure

```text
project-revisii/
│
├── main_api.py          # FastAPI application
├── ai_service.py        # Gemini AI integration
├── index_combined.html  # Frontend interface
├── .env.example         # Environment variable template
├── .gitignore
└── README.md
```

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/atallahbae-coder/capstone.git
cd capstone
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

### 4. Run Application

```bash
uvicorn main_api:app --reload
```

### 5. Open Browser

```text
http://127.0.0.1:8000
```

---

## API Endpoints

| Endpoint        | Method | Description           |
| --------------- | ------ | --------------------- |
| `/`             | GET    | Home page             |
| `/bmi`          | GET    | Calculate BMI         |
| `/workout-plan` | GET    | Generate workout plan |
| `/diet-plan`    | GET    | Generate diet plan    |
| `/chat`         | POST   | Fitness chatbot       |
| `/ask-ai`       | GET    | General AI questions  |

---

## Example Usage

### BMI Calculation

```http
GET /bmi?weight=70&height=1.75&age=22
```

### Workout Plan

```http
GET /workout-plan?goal=muscle_gain&fitness_level=beginner&days_per_week=4
```

### Diet Plan

```http
GET /diet-plan?goal=weight_loss&daily_calories=2000
```

---

## Security

This project uses environment variables to store API credentials.

The `.env` file is excluded from Git tracking through `.gitignore` to prevent accidental exposure of API keys.

---

## Future Improvements

* User authentication
* Progress tracking
* Workout history
* Nutrition analytics dashboard
* Mobile-responsive interface
* Deployment to cloud platform

---

## Author

Capstone Project Submission

Developed using FastAPI and Google Gemini AI.
