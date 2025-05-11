import streamlit as st
from auth import change_user_password

def show_password_change():
    st.subheader("🔒 Change Password")

    old_pw = st.text_input("Current Password", type="password")
    new_pw = st.text_input("New Password", type="password")
    confirm_pw = st.text_input("Confirm New Password", type="password")
    update_btn = st.button("Update Password")

    if update_btn:
        if new_pw != confirm_pw:
            st.warning("⚠️ New passwords do not match.")
        else:
            success, message = change_user_password(st.session_state.username, old_pw, new_pw)
            st.success("✅ " + message) if success else st.error("❌ " + message)
