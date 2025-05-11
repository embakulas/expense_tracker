# auth.py
import bcrypt
from sqlalchemy import text
from db.connection import get_engine

engine = get_engine()

def get_user_by_username(username):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT id, username, name, email, password_hash FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()

def register_user(name, username, email, password):
    # Check if username already exists
    if get_user_by_username(username):
        return False, "Username already exists."

    # Hash password using bcrypt
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Insert into DB
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO users (username, name, email, password_hash)
                    VALUES (:u, :n, :e, :h)
                """),
                {"u": username, "n": name, "e": email, "h": hashed_pw}
            )
        return True, "User registered successfully."
    except Exception as e:
        return False, f"Registration error: {e}"

def verify_login(username, password):
    user = get_user_by_username(username)
    if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return True, user
    return False, None
