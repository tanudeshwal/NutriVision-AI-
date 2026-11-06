
import os
import uuid
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING

from analyzer import predict_food
from nutrition import get_nutrition, health_analysis, NUTRITION


# ================= CONFIGURATION =================

load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

IST = timezone(timedelta(hours=5, minutes=30))


# ================= MONGODB CONNECTION =================

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "NutriVisionAI")

mongo_client = None
db = None


def get_db():
    global mongo_client, db

    if db is not None:
        return db

    if not MONGO_URI:
        raise RuntimeError(
            "MongoDB URI is missing. Check MONGO_URI in your .env file."
        )

    mongo_client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    mongo_client.admin.command("ping")
    db = mongo_client[DB_NAME]

    return db


def users_collection():
    return get_db()["users"]


def food_logs_collection():
    return get_db()["food_logs"]


# ================= LOGIN REQUIRED =================

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")

        return function(*args, **kwargs)

    return wrapper


def api_login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Please login first."}), 401

        return function(*args, **kwargs)

    return wrapper


# ================= HELPER FUNCTIONS =================

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def current_date():
    return datetime.now(IST).strftime("%Y-%m-%d")


# ================= HOME PAGE =================

@app.route("/")
def home():
    return render_template("index.html")


# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():

    if session.get("user_id"):
        return redirect("/dashboard")

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.", "warning")
            return redirect("/register")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "warning")
            return redirect("/register")

        try:
            collection = users_collection()

            if collection.find_one({"email": email}):
                flash("This email is already registered.", "warning")
                return redirect("/register")

            user = {
                "user_id": str(uuid.uuid4()),
                "name": name,
                "email": email,
                "password": generate_password_hash(password),
                "created_at": datetime.now(timezone.utc)
            }

            collection.insert_one(user)

            flash("Account created successfully. Please login.", "success")
            return redirect("/login")

        except Exception as error:
            app.logger.exception("Registration error")
            flash("Registration failed. Check your database connection.", "danger")

    return render_template("register.html")


# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("user_id"):
        return redirect("/dashboard")

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        try:
            user = users_collection().find_one({"email": email})

            if user and check_password_hash(user["password"], password):

                session.clear()
                session["user_id"] = user["user_id"]
                session["name"] = user["name"]
                session["email"] = user["email"]

                return redirect("/dashboard")

            flash("Invalid email or password.", "warning")

        except Exception:
            app.logger.exception("Login error")
            flash("Login failed. Check your database connection.", "danger")

    return render_template("login.html")


# ================= LOGOUT =================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================= DASHBOARD =================

@app.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html",
        name=session.get("name", "User")
    )


# ================= FOOD IMAGE ANALYSIS =================

@app.route("/api/analyze", methods=["POST"])
@api_login_required
def analyze_food():

    if "food_image" not in request.files:
        return jsonify({"error": "Please select a food image."}), 400

    image = request.files["food_image"]

    if not image.filename:
        return jsonify({"error": "No image selected."}), 400

    if not allowed_file(image.filename):
        return jsonify({
            "error": "Only JPG, JPEG, PNG and WEBP images are allowed."
        }), 400

    filename = secure_filename(image.filename)

    if not filename:
        return jsonify({"error": "Invalid image filename."}), 400

    saved_path = os.path.join(
        UPLOAD_FOLDER,
        str(uuid.uuid4()) + "_" + filename
    )

    try:
        image.save(saved_path)

        prediction = predict_food(saved_path)

        food_name = prediction.get("food", "Unknown food")

        nutrition = get_nutrition(food_name)

        if not nutrition or not nutrition.get("matched_food"):
            return jsonify({
                "food": food_name,
                "confidence": prediction.get("confidence", 0),
                "alternatives": prediction.get("alternatives", []),
                "nutrition": nutrition,
                "health": None,
                "note": (
                    "The food was predicted, but no matching nutrition "
                    "entry was found. Nutrition values are unavailable."
                )
            })

        health = health_analysis(nutrition)

        log = {
            "user_id": session["user_id"],
            "food": nutrition["matched_food"],
            "calories": nutrition["calories"],
            "protein": nutrition["protein"],
            "carbs": nutrition["carbs"],
            "fat": nutrition["fat"],
            "fiber": nutrition["fiber"],
            "sugar": nutrition["sugar"],
            "serving": nutrition["serving"],
            "confidence": prediction.get("confidence", 0),
            "date": current_date(),
            "created_at": datetime.now(timezone.utc)
        }

        food_logs_collection().insert_one(log)

        return jsonify({
            "food": food_name,
            "confidence": prediction.get("confidence", 0),
            "alternatives": prediction.get("alternatives", []),
            "nutrition": nutrition,
            "health": health,
            "note": prediction.get("note", "")
        })

    except Exception:
        app.logger.exception("Food analysis error")
        return jsonify({
            "error": "Food analysis failed. Please check the image and server."
        }), 500

    finally:
        if os.path.exists(saved_path):
            os.remove(saved_path)


# ================= DAILY NUTRITION SUMMARY =================

@app.route("/api/daily-summary")
@api_login_required
def daily_summary():

    selected_date = request.args.get("date", current_date())

    try:
        datetime.strptime(selected_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format."}), 400

    logs = list(
        food_logs_collection().find({
            "user_id": session["user_id"],
            "date": selected_date
        })
    )

    fields = ["calories", "protein", "carbs", "fat", "fiber", "sugar"]

    totals = {
        field: round(
            sum(float(log.get(field, 0) or 0) for log in logs), 2
        )
        for field in fields
    }

    return jsonify({
        "date": selected_date,
        "total_foods": len(logs),
        "totals": totals
    })


# ================= FOOD HISTORY =================

@app.route("/api/history")
@api_login_required
def food_history():

    logs = list(
        food_logs_collection().find(
            {"user_id": session["user_id"]}
        ).sort("created_at", DESCENDING).limit(100)
    )

    history = []

    for log in logs:
        history.append({
            "food": log.get("food", "Unknown"),
            "calories": log.get("calories", 0),
            "protein": log.get("protein", 0),
            "carbs": log.get("carbs", 0),
            "fat": log.get("fat", 0),
            "fiber": log.get("fiber", 0),
            "sugar": log.get("sugar", 0),
            "serving": log.get("serving", ""),
            "date": log.get("date", "")
        })

    return jsonify({"logs": history})


# ================= MEAL SUGGESTIONS =================

@app.route("/api/meal-suggestions")
def meal_suggestions():

    meal_options = {
        "breakfast": [
            "poha", "vegetable sandwich", "bread and milk",
            "aloo paratha", "besan chilla", "vegetable upma",
            "paneer sandwich", "plain paratha", "paratha with curd",
            "dosa", "plain dosa", "masala dosa", "cheese dosa",
            "paneer dosa", "onion dosa", "rava dosa",
            "mysore masala dosa", "paper dosa", "butter dosa",
            "idli", "omelette", "banana"
        ],

        "lunch": [
            "mix vegetable sabzi", "bhindi masala", "lauki sabzi",
            "palak paneer", "aloo gobhi", "seasonal vegetable sabzi",
            "chapati", "plain rice", "dal rice", "rajma chawal",
            "chole with puri", "chole bhature", "naan", "biryani",
            "butter chicken", "pav bhaji", "vada pav", "chana dal",
            "paneer bhurji", "kadhi chawal", "vegetable khichdi",
            "bajra khichdi"
        ],

        "snacks": [
            "bhelpuri", "pani puri", "golgappa", "samosa",
            "momos", "steamed veg momos", "fried momos",
            "dumpling", "dhokla", "masala sweet corn",
            "sprouts chaat", "roasted makhana",
            "spring roll", "vegetable spring roll",
            "paneer spring roll", "cheese spring roll",
            "chicken spring roll", "corn spring roll",
            "fried spring roll", "pizza", "bread pizza",
            "cheese pizza", "margherita pizza", "paneer pizza",
            "farmhouse pizza", "pepperoni pizza", "burger",
            "hamburger", "cheeseburger", "chicken burger",
            "french fries", "chicken wings", "sandwich",
            "cheese sandwich", "hot dog", "pasta",
            "white sauce pasta", "red sauce pasta",
            "mix sauce pasta", "pink sauce pasta", "cheese pasta",
            "maggi", "schezwan maggi", "cheese maggi",
            "vegetable maggi", "chow mein", "hakka noodles",
            "schezwan noodles", "apple"
        ],

        "dinner": [
            "bajra roti", "makki roti", "sarson ka saag",
            "makki roti with sarson ka saag", "missi roti",
            "kadhi chawal", "vegetable khichdi", "bajra khichdi",
            "paneer bhurji", "chana dal", "chapati", "plain rice",
            "dal rice", "mix vegetable sabzi", "bhindi masala",
            "lauki sabzi", "aloo gobhi", "palak paneer",
            "idli", "plain dosa", "biryani", "butter chicken",
            "naan", "rajma chawal", "seasonal vegetable sabzi"
        ]
    }

    assigned_foods = {
        food.lower()
        for foods in meal_options.values()
        for food in foods
    }

    extra_foods = sorted(
        food for food in NUTRITION
        if food.lower() not in assigned_foods
    )

    meal_options["snacks"].extend(extra_foods)

    suggestions = {}

    for meal, foods in meal_options.items():

        suggestions[meal] = []
        added_foods = set()

        for name in foods:

            nutrition = get_nutrition(name)

            if not nutrition or not nutrition.get("matched_food"):
                continue

            matched_name = nutrition["matched_food"]

            if matched_name.lower() in added_foods:
                continue

            added_foods.add(matched_name.lower())

            suggestions[meal].append({
                "food": matched_name,
                "calories": nutrition["calories"],
                "protein": nutrition["protein"],
                "carbs": nutrition["carbs"],
                "fat": nutrition["fat"],
                "fiber": nutrition["fiber"],
                "sugar": nutrition["sugar"],
                "serving": nutrition["serving"]
            })

    return jsonify({
        "suggestions": suggestions,
        "note": (
            "Indian and international food suggestions with approximate "
            "nutrition values per reference serving."
        )
    })


# ================= FOOD LIST =================

@app.route("/api/food-list")
def food_list():
    return jsonify({
        "foods": sorted(NUTRITION.keys())
    })


# ================= ERROR HANDLERS =================

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "Image is too large. Maximum file size is 8 MB."
    }), 413


# ================= RUN APPLICATION =================

if __name__ == "__main__":
    app.run(debug=True)
