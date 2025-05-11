from streamlit_authenticator import Hasher
from sqlalchemy import text
from db.connection import get_engine

def reset_user_password(username, new_password):
    hashed_pw = Hasher([new_password]).generate()[0]
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE users SET password_hash = :pw WHERE username = :u"),
            {"pw": hashed_pw, "u": username}
        )
    print(f"✅ Password for '{username}' has been reset.")

# --- Example Usage ---
if __name__ == "__main__":
    # Replace with target username and new password
    username = input("Enter the username to reset: ")
    new_password = input("Enter the new password: ")
    reset_user_password(username, new_password)
