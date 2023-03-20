from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import openai
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import vision
from sqlalchemy.orm import relationship

app = Flask(__name__)
app.secret_key = os.urandom(24)
openai.api_key = os.getenv("MY_GPT3_API_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///foodies.db'
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
    submitted_meal = db.Column(db.Boolean, nullable=False)

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
        new_user = User(name=name, email=email, age=age, gender=gender, goal=goal, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))
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

def gpt3_matching_algorithm(user_data):
    prompt = f"Find a suitable partner for a user with the following information:\n\n"
    for key, value in user_data.items():
        prompt += f"{key.capitalize()}: {value}\n"
    prompt += "\nRecommendations:\n"

    gpt3_response = generate_gpt3_response(prompt)

    recommendations = gpt3_response.split("\n")[1:]
    partner_recommendations = []
    for recommendation in recommendations:
        partner_recommendations.append({"name": recommendation})

    return partner_recommendations

@app.route('/submit_photo', methods=['POST'])
@login_required
def submit_photo():
    if 'image' not in request.files:
        return jsonify({"error": "No image file found in request"}), 400

    image = request.files['image']
    image_content = io.BytesIO(image.read()).getvalue()

    labels = get_image_labels(image_content)
    food_items = filter_food_labels(labels)

    # Save the food items for the user
    # Add your code to save the food items for the user

    return jsonify({"success": True, "food_items": food_items})

@app.route('/home')
@login_required
def home():
    # Fetch the winning meals from the user's friends' games here
    # For now, let's assume you have a function named `get_winning_meals()`
    winning_meals = get_winning_meals(current_user)
    return render_template('home.html', winning_meals=winning_meals)

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

def check_and_compare_meals(user1, user2):
    if user1.submitted_meal and user2.submitted_meal:
        winner = compare_meals(user1.food_items.split(', '), user2.food_items.split(', '))
        # Do something with the winner information, e.g., update the game status or send a notification

def get_winning_meals(user):
    # Fetch the winning meals from the user's friends' games
    # Replace the implementation with the actual data fetching logic
    winning_meals = [
        # Example meal data
        {"title": "Meal 1", "image_url": "path/to/image1.jpg"},
        {"title": "Meal 2", "image_url": "path/to/image2.jpg"},
    ]
    return winning_meals

@app.route('/fetch_more_meals')
@login_required
def fetch_more_meals():
    # Fetch more winning meals from the user's friends' games
    # You can implement pagination or other logic to fetch the next set of meals
    more_meals = get_winning_meals(current_user)

    # Render the meals as an HTML string to be appended to the meal container

if __name__ == '__main__':
    app.run(debug=True)
