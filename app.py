from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import io
import openai
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import vision
from sqlalchemy.orm import relationship

OPPONENT_MEAL_DATA = {
    "food_items": ["grilled chicken salad", "avocado", "mixed greens", "cherry tomatoes"],
    "image_url": "static/Images/logo.png" # Placeholder, can be updated later
}

app = Flask(__name__)
app.secret_key = "my_super_secret_testing_key_123"
openai.api_key = os.getenv("MY_GPT3_API_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/foodies.db' # Corrected path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

user_game_association = db.Table(
    'user_game',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    goal = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    food_items = db.Column(db.String(255), nullable=True)
    submitted_meal = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f'<User {self.name}>'

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'))

    user = db.relationship('User', backref='games')
    meal = db.relationship('Meal', backref='games')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

migrate = Migrate(app, db)

# Placeholder functions for Google Vision API and GPT-3
def get_image_labels(image_content):
    """Placeholder for Google Vision API call."""
    print("Mock get_image_labels called")
    # Simulate some labels for testing
    return ["apple", "banana", "fruit salad"]

def filter_food_labels(labels):
    """Placeholder for filtering labels to food items."""
    print("Mock filter_food_labels called")
    return [label for label in labels if label in ["apple", "banana", "orange"]] # Example filter

def generate_gpt3_response(prompt):
    """Placeholder for OpenAI GPT-3 call."""
    print(f"Mock generate_gpt3_response called with prompt: {prompt}")
    # Simulate a response for testing
    if "User 1 meal: apple, banana" in prompt and "User 2 meal: grilled chicken salad, avocado, mixed greens, cherry tomatoes" in prompt:
        return "User 2" # Simulate opponent's meal as healthier
    return "Tie" # Default response

def compare_meals(user1_food_items, user2_food_items):
    prompt = f"Compare the following meals and determine which one is healthier:\n\nUser 1 meal: {', '.join(user1_food_items)}\nUser 2 meal: {', '.join(user2_food_items)}\n\nHealthier meal:"

    gpt3_response = generate_gpt3_response(prompt)
    healthier_meal = gpt3_response.strip()

    if "User 1" in healthier_meal:
        return "User 1"
    elif "User 2" in healthier_meal:
        return "User 2"
    else:
        return "Tie"

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        age = request.form['age']
        gender = request.form['gender']
        goal = request.form['goal']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            error_msg = 'Passwords do not match. Please try again.'
            return render_template('signup.html', error=error_msg)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error_msg = 'A user with this email already exists. Please use a different email.'
            return render_template('signup.html', error=error_msg)

        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, age=age, gender=gender, goal=goal, password=hashed_password, submitted_meal=False) # Ensure submitted_meal is initialized
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'] # Added password field
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password): # Added password check
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.') # Added error message
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user_id=current_user.id)

@app.route('/camera')
@login_required
def camera():
    return render_template('camera.html')

@app.route('/match', methods=['POST'])
@login_required
def match():
    user = User.query.get(current_user.id)
    user_data = request.form.to_dict()
    partner_recommendations = gpt3_matching_algorithm(user_data)
    return render_template('partners.html', recommendations=partner_recommendations)

@app.route('/submit_photo', methods=['POST'])
@login_required
def submit_photo():
    if 'image' not in request.files:
        return jsonify({"error": "No image file found in request"}), 400

    image = request.files['image']
    image_content = io.BytesIO(image.read()).getvalue() # Read image content

    # Simulate image processing
    labels = get_image_labels(image_content) # This will now call our placeholder
    food_items = filter_food_labels(labels) # This will now call our placeholder

    # Convert the food_items list to a comma-separated string for DB storage
    food_items_str = ", ".join(food_items)

    # Save to database
    current_user.food_items = food_items_str
    current_user.submitted_meal = True
    db.session.commit()

    # Call compare_meals with the list of food items
    winner = compare_meals(food_items, OPPONENT_MEAL_DATA["food_items"])

    # Store results in the session
    session['user_food_items'] = food_items
    session['opponent_food_items'] = OPPONENT_MEAL_DATA["food_items"]
    session['winner'] = winner
    session['opponent_image_url'] = OPPONENT_MEAL_DATA["image_url"]
    # session['user_image_filename'] = image.filename # Store filename if needed later

    return redirect(url_for('comparison_result'))

@app.route('/comparison_result')
@login_required
def comparison_result():
    user_food_items = session.get('user_food_items', [])
    opponent_food_items = session.get('opponent_food_items', [])
    winner = session.get('winner', 'Unknown')
    opponent_image_url = session.get('opponent_image_url', '')
    user_image_filename = session.get('user_image_filename', None) 

    return render_template('comparison_result.html',
                           user_food_items=user_food_items,
                           opponent_food_items=opponent_food_items,
                           winner=winner,
                           opponent_image_url=opponent_image_url,
                           user_image_filename=user_image_filename)

@app.route('/home')
@login_required
def home():
    winning_meals = get_winning_meals(current_user)
    return render_template('home.html', winning_meals=winning_meals)

def get_winning_meals(user):
    # Placeholder: Fetch winning meals (not relevant for this test)
    return []

if __name__ == '__main__':
    # Create the instance directory if it doesn't exist
    instance_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    app.run(debug=True)
