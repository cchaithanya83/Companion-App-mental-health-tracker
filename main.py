from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_302_FOUND
import firebase_admin
from firebase_admin import credentials, auth, firestore
import requests
import json
import openai

app = FastAPI()

# Initialize Firebase
cred = credentials.Certificate("firebase_config.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Replace with your Firebase Web API Key and OpenAI API Key
FIREBASE_WEB_API_KEY = "AIzaSyD6RHMjwdOWnvougV9-srvOuBVwWHZbp78"
OPENAI_API_KEY = "............."

openai.api_key = OPENAI_API_KEY

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if request.session.get("user"):
        return templates.TemplateResponse("home.html", {"request": request, "user": request.session["user"]})
    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)

@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
                          data=json.dumps(payload))
        r.raise_for_status()
        id_info = r.json()
        request.session["user"] = id_info["email"]
        return RedirectResponse(url="/", status_code=HTTP_302_FOUND)
    except requests.exceptions.HTTPError:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/signup", response_class=HTMLResponse)
async def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        user = auth.create_user(email=email, password=password)
        request.session["user"] = user.email
        return RedirectResponse(url="/", status_code=HTTP_302_FOUND)
    except firebase_admin.auth.EmailAlreadyExistsError:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already exists"})
    except firebase_admin.auth.AuthError:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Failed to create user"})

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)

@app.get("/save_answers", response_class=HTMLResponse)
async def save_answers_form(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse("save_answers.html", {"request": request})

@app.post("/save_answers")
async def save_answers(request: Request,
                       feeling_today: str = Form(...),
                       stress_anxiety: str = Form(...),
                       overall_mood: int = Form(...),
                       activity_level: str = Form(...),
                       physical_exercise: str = Form(...),
                       exercise_duration: int = Form(None),
                       social_interactions: str = Form(...),
                       social_satisfaction: str = Form(...),
                       sleep_hours: int = Form(...),
                       trouble_sleeping: str = Form(...),
                       sleep_quality: int = Form(...),
                       regular_meals: str = Form(...),
                       balanced_diet: str = Form(...),
                       water_intake: int = Form(...),
                       relaxation: str = Form(...),
                       relaxation_duration: int = Form(None),
                       current_relaxation: int = Form(...)):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
    
    user_email = request.session["user"]
    doc_ref = db.collection("user_answers").document(user_email)
    doc_ref.set({
        'feeling_today': feeling_today,
        'stress_anxiety': stress_anxiety,
        'overall_mood': overall_mood,
        'activity_level': activity_level,
        'physical_exercise': physical_exercise,
        'exercise_duration': exercise_duration,
        'social_interactions': social_interactions,
        'social_satisfaction': social_satisfaction,
        'sleep_hours': sleep_hours,
        'trouble_sleeping': trouble_sleeping,
        'sleep_quality': sleep_quality,
        'regular_meals': regular_meals,
        'balanced_diet': balanced_diet,
        'water_intake': water_intake,
        'relaxation': relaxation,
        'relaxation_duration': relaxation_duration,
        'current_relaxation': current_relaxation,
        'timestamp': firestore.SERVER_TIMESTAMP,
    })
    return templates.TemplateResponse("save_answers.html", {"request": request, "message": "Answers saved successfully"})

async def suggest_tasks(answers):
    tasks = []

    # Prepare data for OpenAI
    data = {
        "feeling_today": answers['feeling_today'],
        "stress_anxiety": answers['stress_anxiety'],
        "overall_mood": answers['overall_mood'],
        "activity_level": answers['activity_level'],
        "physical_exercise": answers['physical_exercise'],
        "exercise_duration": answers['exercise_duration'],
        "social_interactions": answers['social_interactions'],
        "social_satisfaction": answers['social_satisfaction'],
        "sleep_hours": answers['sleep_hours'],
        "trouble_sleeping": answers['trouble_sleeping'],
        "sleep_quality": answers['sleep_quality'],
        "regular_meals": answers['regular_meals'],
        "balanced_diet": answers['balanced_diet'],
        "water_intake": answers['water_intake'],
        "relaxation": answers['relaxation'],
        "relaxation_duration": answers['relaxation_duration'],
        "current_relaxation": answers['current_relaxation']
    }

    prompt = (
        "Based on the following user input, suggest some tasks to improve their mental and physical health:\n\n"
        f"Feeling today: {data['feeling_today']}\n"
        f"Stress/Anxiety: {data['stress_anxiety']}\n"
        f"Overall mood (1-10): {data['overall_mood']}\n"
        f"Activity level: {data['activity_level']}\n"
        f"Physical exercise: {data['physical_exercise']}\n"
        f"Exercise duration: {data['exercise_duration']}\n"
        f"Social interactions: {data['social_interactions']}\n"
        f"Social satisfaction: {data['social_satisfaction']}\n"
        f"Sleep hours: {data['sleep_hours']}\n"
        f"Trouble sleeping: {data['trouble_sleeping']}\n"
        f"Sleep quality (1-10): {data['sleep_quality']}\n"
        f"Regular meals: {data['regular_meals']}\n"
        f"Balanced diet: {data['balanced_diet']}\n"
        f"Water intake: {data['water_intake']}\n"
        f"Relaxation: {data['relaxation']}\n"
        f"Relaxation duration: {data['relaxation_duration']}\n"
        f"Current relaxation (1-10): {data['current_relaxation']}\n"
    )


    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content":prompt }
        ],
        max_tokens=150,
        temperature=0.7,
    )

    return response.choices[0]['message']['content'].strip()


@app.get("/get_tasks", response_class=HTMLResponse)
async def get_tasks(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)

    user_email = request.session["user"]
    doc_ref = db.collection("user_answers").document(user_email)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        tasks = await suggest_tasks(data)
        return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks})
    else:
        return templates.TemplateResponse("tasks.html", {"request": request, "error": "No user answers found"})
