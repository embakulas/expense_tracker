import streamlit as st
import pandas as pd
from sqlalchemy import text

def show_dashboard(engine, user_id):
    st.subheader("📊 Dashboard")

    try:
        with engine.connect() as conn:
            recent_df = pd.read_sql(
                text("SELECT * FROM expenses WHERE user_id = :uid ORDER BY id DESC LIMIT 5"),
                conn, params={"uid": user_id}
            )
        st.success("✅ Fetched recent data")
        st.dataframe(recent_df)
    except Exception as e:
        st.error(f"❌ Recent data error: {e}")

    try:
        with engine.connect() as conn:
            checking_df = pd.read_sql(
                text("SELECT name, current_balance FROM checking_accounts WHERE user_id = :uid"),
                conn, params={"uid": user_id}
            )
        st.success("✅ Fetched checking account balances")
        st.dataframe(checking_df)
    except Exception as e:
        st.error(f"❌ Checking accounts error: {e}")

    try:
        with engine.connect() as conn:
            credit_df = pd.read_sql(
                text("SELECT name, total_limit, used_limit, available_limit FROM credit_cards WHERE user_id = :uid"),
                conn, params={"uid": user_id}
            )
        st.success("✅ Fetched credit card data")
        st.dataframe(credit_df)
    except Exception as e:
        st.error(f"❌ Credit cards error: {e}")

    try:
        with engine.connect() as conn:
            splitwise_df = pd.read_sql(
                text("SELECT name, net_balance, last_updated FROM splitwise_people WHERE user_id = :uid"),
                conn, params={"uid": user_id}
            )
        st.success("✅ Fetched Splitwise data")
        st.dataframe(splitwise_df)
    except Exception as e:
        st.error(f"❌ Splitwise error: {e}")
