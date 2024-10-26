from app import app
from extensions import db


def init_database():
    with app.app_context():
        try:
            db.create_all()
            print("Tables created successfully.")
        except Exception as e:
            print(f"Error creating tables: {e}")

if __name__ == "__main__":
    init_database()
