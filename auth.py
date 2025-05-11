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

def change_user_password(username, old_password, new_password):
    user = get_user_by_username(username)
    if not user:
        return False, "User not found."

    if not bcrypt.checkpw(old_password.encode(), user.password_hash.encode()):
        return False, "Current password is incorrect."

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET password_hash = :h WHERE username = :u"),
                {"h": new_hash, "u": username}
            )
        return True, "Password updated successfully."
    except Exception as e:
        return False, f"Error updating password: {e}"

