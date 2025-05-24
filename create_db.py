from app import app, db

# Ensure the instance folder exists, as SQLAlchemy might not create it by default
# for SQLite when the path is relative like 'sqlite:///foodies.db'
# However, app.instance_path should handle this if configured.
# For safety, especially if instance_path is not explicitly used for URI:
import os
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)
    print(f"Created instance folder: {instance_path}")

with app.app_context():
    db.create_all()
print("Database tables created successfully (if they didn't exist).")
