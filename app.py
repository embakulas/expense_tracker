import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import calendar
import bcrypt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import matplotlib.ticker as mtick
from sqlalchemy import text

from db.connection import get_engine
from auth import verify_login, register_user, get_user_by_username
from process_expenses import update_balances_from_expenses
from reset_password import reset_password_form
from views.input_form import show_expense_form,show_expense_form
from views.login import show_login,show_registration,show_recovery
from views.reports import show_reports
from views.dashboard import show_dashboard
from views.password_change import show_password_change



engine = get_engine()
st.set_page_config(page_title="Expense Tracker Dashboard", layout="wide")

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None

# --- Login / Register Block ---
if not st.session_state.authenticated:
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

    st.markdown("---")
    st.subheader("🆕 Register")

    reg_name = st.text_input("Full Name", key="reg_name")
    reg_username = st.text_input("Choose a Username", key="reg_user")
    reg_email = st.text_input("Email", key="reg_email")
    reg_password = st.text_input("Choose a Password", type="password", key="reg_pass")
    reg_button = st.button("Register")

    if reg_button and reg_username and reg_password and reg_name and reg_email:
        ok, msg = register_user(reg_name, reg_username, reg_email, reg_password)
        if ok:
            st.success("✅ " + msg)
        else:
            st.error("❌ " + msg)

    # Forgot Credentials
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
            st.info("For password reset, please contact the administrator to generate a new temporary password.")
        else:
            st.warning("⚠️ No account associated with this email.")

    st.stop()

# --- Main App View ---
st.title("💵 Expense Tracker Dashboard")
st.sidebar.header("Navigation")
view = st.sidebar.radio("", ["Dashboard", "Reports 📊", "Input Form", "Change Password"])

if view == "Dashboard":
    show_dashboard(engine, st.session_state.user_id)
elif view == "Reports 📊":
    show_reports(engine)
elif view == "Input Form":
    show_expense_form(engine, st.session_state.user_id)
elif view == "Change Password":
    show_password_change(engine)
