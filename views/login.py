import streamlit as st
from sqlalchemy import text
from db.connection import get_engine
from auth import verify_login, register_user

engine = get_engine()

def show_login():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn and username and password:
        success, user = verify_login(username, password)
        if success:
            st.session_state.authenticated = True
            st.session_state.user_id = user.id
            st.session_state.username = user.username
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

def show_registration():
    st.markdown("---")
    st.subheader("🆕 Register")

    reg_name = st.text_input("Full Name", key="reg_name")
    reg_username = st.text_input("Choose a Username", key="reg_user")
    reg_email = st.text_input("Email", key="reg_email")
    reg_password = st.text_input("Choose a Password", type="password", key="reg_pass")
    reg_button = st.button("Register")

    if reg_button and reg_username and reg_password and reg_name and reg_email:
        ok, msg = register_user(reg_name, reg_username, reg_email, reg_password)
        st.success("✅ " + msg) if ok else st.error("❌ " + msg)

def show_recovery():
    st.markdown("---")
    st.subheader("🔑 Forgot Username or Password?")

    forgot_email = st.text_input("Enter your registered email", key="forgot_email")
    recover_btn = st.button("Recover Account")

    if recover_btn and forgot_email:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT username FROM users WHERE email = :email"),
                {"email": forgot_email}
            ).fetchone()
        if result:
            st.success(f"✅ Username found: **{result.username}**")
            st.info("For password reset, please contact the administrator.")
        else:
            st.warning("⚠️ No account associated with this email.")
