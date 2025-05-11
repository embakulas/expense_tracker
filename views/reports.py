import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import calendar
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import text


def show_reports(engine):
    st.subheader("📈 Expense Reports and Insights")

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("User not authenticated.")
        return

    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT * FROM expenses WHERE type = 'expense' AND user_id = :uid"),
            conn,
            params={"uid": user_id}
        )

        df['date'] = pd.to_datetime(df['date'])

        # =========================
        # Monthly Expense Trend
        # =========================
        df['month'] = df['date'].dt.to_period('M')
        monthly = df.groupby('month')['amount'].sum().reset_index()
        monthly['month'] = monthly['month'].dt.strftime('%b %Y')
        monthly = monthly.tail(4)

        st.markdown("### 📅 Monthly Expense Trend")
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        bars = ax1.bar(monthly['month'], monthly['amount'], color='royalblue')
        for bar in bars:
            yval = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, yval + 50, f"${yval:,.0f}", ha='center')
        ax1.set_ylabel("Amount ($)")
        st.pyplot(fig1)

        # =========================
        # Weekly Spend Breakdown
        # =========================
        def get_week_of_month(dt):
            first_day = dt.replace(day=1)
            dom = dt.day
            adjusted_dom = dom + first_day.weekday()
            return int((adjusted_dom - 1) / 7) + 1

        df['week_of_month'] = df['date'].apply(get_week_of_month)

        today = datetime.today()
        this_month_start = datetime(today.year, today.month, 1)
        last_month_start = this_month_start - relativedelta(months=1)
        last_month_end = this_month_start - timedelta(days=1)

        this_month_df = df[(df['date'] >= this_month_start) & (df['date'] < this_month_start + relativedelta(months=1))]
        last_month_df = df[(df['date'] >= last_month_start) & (df['date'] <= last_month_end)]

        def get_week_totals(data):
            return [data[data['week_of_month'] == i]['amount'].sum() for i in range(1, 5)]

        compare_df = pd.DataFrame({
            'Week': [f"Week {i}" for i in range(1, 5)],
            'This Month': get_week_totals(this_month_df),
            'Last Month': get_week_totals(last_month_df)
        })

        st.markdown("### 📅 Weekly Spend Breakdown")
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        bar_width = 0.35
        index = range(len(compare_df))

        bars1 = ax2.bar([i - bar_width / 2 for i in index], compare_df['Last Month'], bar_width, label='Last Month', color='skyblue')
        bars2 = ax2.bar([i + bar_width / 2 for i in index], compare_df['This Month'], bar_width, label='This Month', color='orange')

        for bars in [bars1, bars2]:
            for bar in bars:
                yval = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width() / 2, yval + 10, f"${yval:,.0f}", ha='center', va='bottom')

        ax2.set_xticks(index)
        ax2.set_xticklabels(compare_df['Week'])
        ax2.set_ylabel("Amount ($)")
        ax2.legend()
        st.pyplot(fig2)

        # =========================
        # Category-wise Expense
        # =========================
        cat_df = df[df['category'].notnull() & (df['category'].str.strip() != '') & (df['category'] != 'Income')]
        cat_summary = cat_df.groupby('category')['amount'].sum().sort_values(ascending=False)

        st.markdown("### 📊 Category-wise Expense")
        fig3, ax3 = plt.subplots(figsize=(10, 4))
        bars = ax3.bar(cat_summary.index, cat_summary.values, color='dodgerblue')
        for bar, value in zip(bars, cat_summary.values):
            ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50, f"${value:,.0f}", ha='center', va='bottom')
        ax3.set_ylabel("Amount ($)")
        ax3.set_xlabel("Category")
        plt.xticks(rotation=30)
        st.pyplot(fig3)

        # =========================
        # Category Drill-Down
        # =========================
        st.markdown("### 🔍 Category Drill-down")
        selected_category = st.selectbox("Select a Category to view subcategory-wise spend:", options=cat_summary.index.tolist())

        if selected_category:
            drill_df = cat_df[cat_df['category'] == selected_category]
            sub_summary = drill_df.groupby('subcategory')['amount'].sum().sort_values(ascending=False)

            fig_sub, ax_sub = plt.subplots(figsize=(8, 4))
            bars = ax_sub.bar(sub_summary.index, sub_summary.values, color='mediumseagreen')
            for bar, value in zip(bars, sub_summary.values):
                ax_sub.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 10, f"${value:,.0f}", ha='center', va='bottom')
            ax_sub.set_ylabel("Amount ($)")
            ax_sub.set_xlabel("Subcategory")
            ax_sub.set_title(f"Subcategory-wise Spend: {selected_category}")
            plt.xticks(rotation=30)
            st.pyplot(fig_sub)

        # =========================
        # Income Summary
        # =========================
        with engine.connect() as conn4:
            income_total = pd.read_sql(
                text("SELECT SUM(amount) as total FROM expenses WHERE type='income' AND subcategory='Salary' AND user_id = :uid"),
                conn4,
                params={"uid": user_id}
            )['total'][0] or 0

        st.markdown("### 💰 Income Summary")
        st.metric("👨‍💼 Total Salary Income", f"${income_total:,.2f}")

        # =========================
        # Projected Spend
        # =========================
        today_day = today.day
        total_days = calendar.monthrange(today.year, today.month)[1]
        current_spend = this_month_df['amount'].sum()
        projected_spend = (current_spend / today_day) * total_days if today_day else 0

        st.markdown("### 📉 Projected Spend")
        st.metric("📈 Projected End-of-Month Spend", f"${projected_spend:,.2f}")

        # =========================
        # Debt Payment Summary
        # =========================
        with engine.connect() as conn2:
            debt_df = pd.read_sql(
                text("SELECT * FROM expenses WHERE type = 'debt_payment' AND user_id = :uid"),
                conn2,
                params={"uid": user_id}
            )

        credit_card_total = debt_df[debt_df['subcategory'].str.contains("Credit Card", na=False)]['amount'].sum()
        splitwise_total = debt_df[debt_df['subcategory'].str.contains("Splitwise", na=False)]['amount'].sum()
        india_transfer_total = debt_df[
            debt_df['subcategory'].fillna('').str.contains("India Transfer", case=False) |
            debt_df['paid_to'].fillna('').str.contains("India Transfer", case=False)
        ]['amount'].sum()

        st.markdown("### 💳 Debt Payments Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("💳 Credit Card Payments", f"${credit_card_total:,.2f}")
        col2.metric("👥 Splitwise Payments", f"${splitwise_total:,.2f}")
        col3.metric("🌐 India Transfers", f"${india_transfer_total:,.2f}")

        # =========================
        # Outstanding Balances
        # =========================
        st.markdown("### 🧾 Outstanding Balances")
        with engine.connect() as conn:
            credit_df = pd.read_sql(text("SELECT name, used_limit FROM credit_cards WHERE user_id = :uid"), conn, params={"uid": user_id})
            splitwise_df = pd.read_sql(text("SELECT name, net_balance FROM splitwise_people WHERE user_id = :uid"), conn, params={"uid": user_id})

        credit_out = credit_df["used_limit"].sum()
        splitwise_owe = splitwise_df[splitwise_df["net_balance"] > 0]["net_balance"].sum()

        col4, col5 = st.columns(2)
        col4.metric("💳 Credit Cards Outstanding", f"${credit_out:,.2f}")
        col5.metric("👥 Splitwise Outstanding", f"${splitwise_owe:,.2f}")
