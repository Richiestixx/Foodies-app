from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import openai # You'll replace this with Gemini later
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import vision # For later implementation
from sqlalchemy.orm import relationship
import io # For file handling

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key') # Use environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///foodies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# OpenAI API Key - will be replaced with Gemini later
# openai.api_key = os.getenv("MY_GPT3_API_KEY") # Comment out or remove if not using OpenAI

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)  # Stores the hash
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    goal = db.Column(db.String(50), nullable=True)
    
    # New fields to match signup.html and potential future use
    weight_kg = db.Column(db.Float, nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    activity_level = db.Column(db.String(50), nullable=True)
    dietary_preferences = db.Column(db.String(100), nullable=True)
    
    submitted_meal = db.Column(db.Boolean, default=False, nullable=False)
    food_items = db.Column(db.Text, nullable=True)  # For storing comma-separated food items or JSON

    # Relationships (if any, e.g., meals, friendships)
    # meals = db.relationship('Meal', backref='user', lazy=True) # Example

    def __repr__(self):
        return f'<User {self.name}>'

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    protein = db.Column(db.Integer, nullable=True)
    carbs = db.Column(db.Integer, nullable=True)
    fats = db.Column(db.Integer, nullable=True)
    photo_url = db.Column(db.String(200), nullable=True) # URL or path to the image

    user = db.relationship('User', backref=db.backref('meals', lazy=True))

    def __repr__(self):
        return f'<Meal {self.description}>'

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending') # e.g., pending, accepted, declined

    # Ensures user1_id < user2_id to avoid duplicate pairs in different orders, or handle via logic
    __table_args__ = (db.UniqueConstraint('user1_id', 'user2_id', name='_user_friendship_uc'),)


class Game(db.Model): # Assuming Game model is for meal comparison games
    id = db.Column(db.Integer, primary_key=True)
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # If a game is owned by one user
    # meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'), nullable=False) # If a game is about one meal
    status = db.Column(db.String(50), nullable=False, default='active') # e.g., active, completed
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # If multiple users participate in a game, a many-to-many might be needed
    # participants = db.relationship('User', secondary=user_game_association, backref='games')
    # If multiple meals are in a game
    # meals_in_game = db.relationship('Meal', secondary=meal_game_association, backref='games')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/home')
@login_required
def home():
    # Placeholder for fetching meals for the home feed
    meals_to_display = Meal.query.order_by(Meal.id.desc()).limit(10).all() # Example
    return render_template('home.html', meals=meals_to_display)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        age_str = request.form.get('age')
        gender = request.form.get('gender')
        goal = request.form.get('goal')
        weight_kg_str = request.form.get('weight')
        height_cm_str = request.form.get('height')
        activity_level = request.form.get('activity_level')
        dietary_preferences = request.form.get('dietary_preferences')

        if not name or not email or not password or not confirm_password:
            flash('All fields marked with * are required.', 'danger')
            return render_template('signup.html', error='Required fields are missing.', **request.form)

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return render_template('signup.html', error='Passwords do not match.', name=name, email=email)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('A user with this email already exists.', 'danger')
            return render_template('signup.html', error='Email already exists.', name=name)

        hashed_password = generate_password_hash(password)
        
        age = int(age_str) if age_str and age_str.isdigit() else None
        weight_kg = float(weight_kg_str) if weight_kg_str and weight_kg_str.replace('.', '', 1).isdigit() else None
        height_cm = float(height_cm_str) if height_cm_str and height_cm_str.replace('.', '', 1).isdigit() else None

        new_user = User(
            name=name, 
            email=email, 
            password=hashed_password,
            age=age, 
            gender=gender, 
            goal=goal,
            weight_kg=weight_kg,
            height_cm=height_cm,
            activity_level=activity_level,
            dietary_preferences=dietary_preferences
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user) # Log in the user after successful signup
        flash('Account created successfully! You are now logged in.', 'success')
        return redirect(url_for('dashboard')) # Or 'home' or an onboarding page

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password_candidate = request.form.get('password')

        if not email or not password_candidate:
            flash('Email and password are required.', 'danger')
            return render_template('login.html', error='Email and password are required.', email=email)

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password_candidate):
            login_user(user)
            flash('Logged in successfully!', 'success')
            # next_page = request.args.get('next') # For redirecting after login
            # return redirect(next_page or url_for('dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('login.html', error='Invalid email or password.', email=email)
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/camera')
@login_required
def camera():
    return render_template('camera.html')

# --- Helper Functions for Vision API (Placeholders) ---
def get_image_labels(image_content_bytes):
    """
    Placeholder for Google Cloud Vision API label detection.
    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable to be set
    to the path of your service account key file.
    """
    # try:
    #     client = vision.ImageAnnotatorClient()
    #     image = vision.Image(content=image_content_bytes)
    #     response = client.label_detection(image=image)
        
    #     if response.error.message:
    #         raise Exception(f"Vision API Error: {response.error.message}")
            
    #     labels = [label.description for label in response.label_annotations]
    #     return labels
    # except Exception as e:
    #     print(f"Error calling Vision API: {e}")
    #     return ["Error processing image"] # Or raise the exception
    
    print("Placeholder: get_image_labels called. Returning dummy data.")
    return ["Example Label 1", "Food", "Delicious Meal", "Fruit Salad"] # Dummy data for testing

def filter_food_labels(labels):
    """
    Placeholder for filtering food-related labels from Vision API results.
    """
    print(f"Placeholder: filter_food_labels called with: {labels}")
    # More comprehensive food keyword list might be needed
    food_keywords = [
        "food", "fruit", "vegetable", "meal", "dish", "cuisine", "salad", "dessert",
        "breakfast", "lunch", "dinner", "snack", "bakery", "pastry", "beverage",
        "ingredient", "recipe", "cooking", "eat", "plate", "bowl", "sandwich", "soup"
    ] 
    filtered = [label for label in labels if any(keyword in label.lower() for keyword in food_keywords)]
    return list(set(filtered)) # Return unique labels


@app.route('/submit_photo', methods=['POST'])
@login_required
def submit_photo():
    if 'image' not in request.files:
        flash('No image part in the request.', 'danger')
        return jsonify({"error": "No image file found in request", "success": False}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        flash('No image selected for uploading.', 'danger')
        return jsonify({"error": "No selected file", "success": False}), 400

    if image_file: # Basic check if file exists
        try:
            image_content_bytes = image_file.read() # Read directly as bytes
            
            # Call Vision API helper (using placeholder for now)
            labels = get_image_labels(image_content_bytes)
            food_items_list = filter_food_labels(labels)
            
            # Save the food items for the user
            if food_items_list:
                current_user.food_items = ", ".join(food_items_list)
            else:
                current_user.food_items = "No specific food items identified" # Or None
            current_user.submitted_meal = True
            db.session.commit()

            flash('Meal photo submitted and analyzed!', 'success')
            return jsonify({"success": True, "food_items": food_items_list, "message": "Meal submitted successfully!"})
        except Exception as e:
            app.logger.error(f"Error in submit_photo: {e}") # Log the full error server-side
            flash(f'An error occurred processing the image.', 'danger')
            return jsonify({"error": f"An error occurred: {str(e)}", "success": False}), 500
    
    flash('Image file is not valid.', 'danger')
    return jsonify({"error": "Invalid image file", "success": False}), 400


# --- Placeholder/Example AI and Game Logic ---
def generate_gemini_response(prompt):
    """
    Placeholder for generating response from Gemini API.
    You will need to install the google-generativeai SDK (pip install google-generativeai)
    and configure your API KEY.
    """
    # import google.generativeai as genai
    # genai.configure(api_key="YOUR_GEMINI_API_KEY") # Use os.getenv("YOUR_GEMINI_API_KEY")
    # model = genai.GenerativeModel('gemini-pro') # Or other appropriate model
    # try:
    #     response = model.generate_content(prompt)
    #     return response.text
    # except Exception as e:
    #     print(f"Error calling Gemini API: {e}")
    #     return "Error generating AI response."
    print(f"Placeholder: generate_gemini_response called with prompt: {prompt[:100]}...")
    return f"This is a placeholder AI response for the prompt about: {prompt[:50]}..."

def gpt3_matching_algorithm(user1, user2): # Will be gemini_matching_algorithm
    # This logic needs to be defined based on your matching criteria
    prompt = f"User 1 ({user1.name}) has goal: {user1.goal}, dietary preferences: {user1.dietary_preferences}. User 2 ({user2.name}) has goal: {user2.goal}, dietary preferences: {user2.dietary_preferences}. Are they a good match? Explain briefly."
    match_analysis = generate_gemini_response(prompt) # Changed from gpt3
    # Simple logic based on response (you'll need more sophisticated parsing)
    compatibility_score = 0.75 # Placeholder
    return {"analysis": match_analysis, "score": compatibility_score}

def compare_meals(meal1_desc, meal2_desc):
    prompt = f"Compare two meals. Meal 1: {meal1_desc}. Meal 2: {meal2_desc}. Which is healthier and why?"
    comparison = generate_gemini_response(prompt) # Changed from gpt3
    return comparison

def check_and_compare_meals(user1, user2):
    # This function needs to be integrated into a route or triggered by an event
    # It also assumes food_items is a string that can be split.
    if user1.food_items and user2.food_items:
        food_items1 = user1.food_items.split(', ')
        food_items2 = user2.food_items.split(', ')
        
        # Example: compare the first food item if they exist
        if food_items1 and food_items2:
            comparison_result = compare_meals(food_items1[0], food_items2[0])
            print(f"Meal comparison for {user1.name} and {user2.name}: {comparison_result}")
            return comparison_result
    return "Not enough data to compare meals."

@app.route('/partners')
@login_required
def partners():
    # Example: Find other users (excluding current user)
    potential_partners = User.query.filter(User.id != current_user.id).limit(5).all() # Limit for demo
    matches = []
    if potential_partners:
        for partner in potential_partners:
            match_info = gpt3_matching_algorithm(current_user, partner) # Will be gemini
            matches.append({"partner": partner, "match_info": match_info})
    return render_template('partners.html', matches=matches)


# --- Example functions that were in your original file ---
def get_winning_meals(user):
    # Placeholder logic
    print(f"get_winning_meals called for user {user.name}")
    # In a real app, this would query the database for meals associated with wins in games for this user
    # Example static data:
    return [
        {"description": "Super Healthy Salad", "calories": 300, "protein": 20},
        {"description": "Lean Chicken Breast with Veggies", "calories": 450, "protein": 40}
    ]

@app.route('/fetch_more_meals', methods=['GET'])
@login_required
def fetch_more_meals():
    # Placeholder for pagination or infinite scroll
    # page = request.args.get('page', 1, type=int)
    # per_page = 5 # Or some other number
    # meals_pagination = Meal.query.order_by(Meal.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    # meals_data = [{"description": meal.description, "calories": meal.calories, "photo_url": meal.photo_url} for meal in meals_pagination.items]
    # return jsonify(meals=meals_data, has_next=meals_pagination.has_next)
    print("fetch_more_meals route called (placeholder)")
    # Example static data for now
    example_more_meals = [
        {"description": "Fetched Meal A", "calories": 320, "photo_url": "http://placekitten.com/300/200"},
        {"description": "Fetched Meal B", "calories": 480, "photo_url": "http://placekitten.com/301/200"}
    ]
    return jsonify(meals=example_more_meals, has_next=False) # Assume no more for this placeholder

if __name__ == '__main__':
    # Ensure the app context is available for db operations if any are done at startup
    # with app.app_context():
    #     db.create_all() # Be cautious with this in production if using migrations
    app.run(debug=True)
