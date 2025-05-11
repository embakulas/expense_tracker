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
from process_expenses import update_balances_from_expenses
from auth import verify_login, register_user,get_user_by_username    # <-- Import our reusable auth functions

# Set up Streamlit UI and database engine
engine = get_engine()
st.set_page_config(page_title="Expense Tracker Dashboard", layout="wide")

# Session state for login
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None

# --- LOGIN / REGISTER ---
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


    # --- Forgot Credentials ---
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


    st.stop()  # Prevent access until logged in

# If authenticated, show dashboard content
st.title("💵 Expense Tracker Dashboard")



# Track form state
if "just_submitted" not in st.session_state:
    st.session_state.just_submitted = False

# View selection
st.sidebar.header("Select View")
view = st.sidebar.radio("", ["Input Form", "Reports 📊", "Dashboard", "Change Password"])

# Helper function
def fetch_column_values(query, params=None):
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=params)
    return df.iloc[:, 0].tolist()

# --- Dashboard ---
if view == "Dashboard":
    st.subheader("📊 Dashboard")

    try:
        with engine.connect() as conn:
            recent_df = pd.read_sql(text("SELECT * FROM expenses ORDER BY id DESC LIMIT 5"), conn)
        st.success("✅ Fetched recent data")
        st.dataframe(recent_df)
    except Exception as e:
        st.error(f"❌ Recent data error: {e}")

    try:
        with engine.connect() as conn:
            checking_df = pd.read_sql(text("SELECT name, current_balance FROM checking_accounts"), conn)
        st.success("✅ Fetched checking account balances")
        st.dataframe(checking_df)
    except Exception as e:
        st.error(f"❌ Checking accounts error: {e}")

    try:
        with engine.connect() as conn:
            credit_df = pd.read_sql(text("SELECT name, total_limit, used_limit, available_limit FROM credit_cards"), conn)
        st.success("✅ Fetched credit card data")
        st.dataframe(credit_df)
    except Exception as e:
        st.error(f"❌ Credit cards error: {e}")

    try:
        with engine.connect() as conn:
            splitwise_df = pd.read_sql(text("SELECT name, net_balance, last_updated FROM splitwise_people"), conn)
        st.success("✅ Fetched Splitwise data")
        st.dataframe(splitwise_df)
    except Exception as e:
        st.error(f"❌ Splitwise error: {e}")


elif view == "Reports 📊":
    st.subheader("📈 Expense Reports and Insights")

    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT * FROM expenses WHERE type = 'expense'"), conn)

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

        # This and last month filters
        today = datetime.today()
        this_month_start = datetime(today.year, today.month, 1)
        last_month_start = this_month_start - relativedelta(months=1)
        last_month_end = this_month_start - timedelta(days=1)

        this_month_df = df[(df['date'] >= this_month_start) & (df['date'] < this_month_start + relativedelta(months=1))]
        last_month_df = df[(df['date'] >= last_month_start) & (df['date'] <= last_month_end)]

        # Week 1 to 4 totals
        def get_week_totals(data):
            return [data[data['week_of_month'] == i]['amount'].sum() for i in range(1, 5)]

        compare_df = pd.DataFrame({
            'Week': [f"Week {i}" for i in range(1, 5)],
            'This Month': get_week_totals(this_month_df),
            'Last Month': get_week_totals(last_month_df)
        })

        # --- Plot ---
        st.markdown("### 📅 Weekly Spend Breakdown")
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        bar_width = 0.35
        index = range(len(compare_df))

        bars1 = ax2.bar([i - bar_width/2 for i in index], compare_df['Last Month'], bar_width, label='Last Month', color='skyblue')
        bars2 = ax2.bar([i + bar_width/2 for i in index], compare_df['This Month'], bar_width, label='This Month', color='orange')

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
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50, f"${value:,.0f}", ha='center', va='bottom')
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
                ax_sub.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"${value:,.0f}", ha='center', va='bottom')
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
                text("SELECT SUM(amount) as total FROM expenses WHERE type='income' AND subcategory='Salary'"),
                conn4
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
            debt_df = pd.read_sql(text("SELECT * FROM expenses WHERE type = 'debt_payment'"), conn2)

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
            credit_df = pd.read_sql(text("SELECT name, used_limit FROM credit_cards"), conn)
            splitwise_df = pd.read_sql(text("SELECT name, net_balance FROM splitwise_people"), conn)

        credit_out = credit_df["used_limit"].sum()
        splitwise_owe = splitwise_df[splitwise_df["net_balance"] > 0]["net_balance"].sum()

        col4, col5 = st.columns(2)
        col4.metric("💳 Credit Cards Outstanding", f"${credit_out:,.2f}")
        col5.metric("👥 Splitwise Outstanding", f"${splitwise_owe:,.2f}")

elif view == "Input Form":
    st.subheader("📝 Input New Expense")

    type_ = st.selectbox("Type", ["expense", "income", "transfer", "debt_payment"])

    # --- Category ---
    categories = fetch_column_values(
        text("SELECT name FROM categories WHERE type = :t"),
        {"t": type_}
    )
    category_options = categories + ["➕ Add New"]
    category = st.selectbox("Category", category_options)

    if category == "➕ Add New":
        new_cat = st.text_input("Enter new category name:")
        if new_cat and st.button("Add Category"):
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO categories (name, type) VALUES (:name, :type)"),
                    {"name": new_cat.strip(), "type": type_}
                )
            st.success("✅ Category added!")
            st.session_state.just_submitted = True
            st.rerun()

    subcategory = ""
    if category != "➕ Add New":
        subcategories = fetch_column_values(
            text("SELECT sub_category_name FROM subcategories WHERE category_name = :cat"),
            {"cat": category}
        )
        subcat_options = subcategories + ["➕ Add New"]
        subcategory = st.selectbox("Subcategory", subcat_options)

        if subcategory == "➕ Add New":
            new_subcat = st.text_input("Enter new subcategory name:")
            if new_subcat and st.button("Add Subcategory"):
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO subcategories (category_name, sub_category_name) VALUES (:cat, :sub)"),
                        {"cat": category, "sub": new_subcat.strip()}
                    )
                st.success("✅ Subcategory added!")
                st.session_state.just_submitted = True
                st.rerun()

    # --- Splitwise ---
    is_splitwise = st.checkbox("Splitwise?")
    splitwise_person = None
    if is_splitwise:
        people = fetch_column_values(text("SELECT name FROM splitwise_people"))
        person_options = people + ["➕ Add New"]
        splitwise_person = st.selectbox("Who Paid?", person_options)

        if splitwise_person == "➕ Add New":
            new_person = st.text_input("Enter new person's name:")
            if new_person and st.button("Add Person"):
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO splitwise_people (name, net_balance) VALUES (:name, 0.00)"),
                        {"name": new_person.strip()}
                    )
                st.success("✅ Person added!")
                st.session_state.just_submitted = True
                st.rerun()

    # --- Payment Method ---
    methods = fetch_column_values(text("SELECT name FROM payment_methods"))
    method_options = methods + ["➕ Add New"]
    payment_method = st.selectbox("Payment Method", method_options)

    if payment_method == "➕ Add New":
        new_method = st.text_input("Enter new payment method:")
        if new_method and st.button("Add Payment Method"):
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO payment_methods (name) VALUES (:name)"),
                    {"name": new_method.strip()}
                )
            st.success("✅ Payment method added!")
            st.session_state.just_submitted = True
            st.rerun()

    # --- Credit Card ---
    credit_cards = fetch_column_values(text("SELECT name FROM credit_cards"))
    cc_options = [""] + credit_cards + ["➕ Add New"]
    used_credit_card = st.selectbox("Used Credit Card (if applicable)", cc_options)

    if used_credit_card == "➕ Add New":
        new_card = st.text_input("Enter new credit card name:")
        new_limit = st.number_input("Credit Limit", min_value=0.0, step=100.0)
        if new_card and st.button("Add Credit Card"):
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO credit_cards (name, total_limit, used_limit) VALUES (:name, :limit, 0.0)"),
                    {"name": new_card.strip(), "limit": new_limit}
                )
            st.success("✅ Credit card added!")
            st.session_state.just_submitted = True
            st.rerun()

    st.info(
                "To add a new **checking account** or **credit card**, select **➕ Add New** from the "
                "**Paid To / Received From** dropdown. Then fill in the name and either the initial balance or credit limit."
            )

    # --- Paid To / Received From ---
    checking = fetch_column_values(text("SELECT name FROM checking_accounts"))
    payees = checking + credit_cards
    paid_to_options = [""] + payees + ["➕ Add New"]
    paid_to = st.selectbox("Paid To / Received From", paid_to_options)

    if paid_to == "➕ Add New":
        new_payee = st.text_input("Enter new Card/Checking/Saving Account name:")
        is_card = st.checkbox("Is this a credit card?")
        if is_card:
            card_limit = st.number_input("Credit Limit", min_value=0.0, step=100.0, key="limit3")
            if new_payee and st.button("Add New Credit Card"):
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO credit_cards (name, total_limit, used_limit) VALUES (:name, :limit, 0.0)"),
                        {"name": new_payee.strip(), "limit": card_limit}
                    )
                st.success("✅ Credit card added!")
                st.session_state.just_submitted = True
                st.rerun()
        else:
            balance = st.number_input("Initial Balance", min_value=0.0, step=100.0, key="bal3")
            if new_payee and st.button("Add New Checking Account"):
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO checking_accounts (name, current_balance) VALUES (:name, :bal)"),
                        {"name": new_payee.strip(), "bal": balance}
                    )
                st.success("✅ Checking account added!")
                st.session_state.just_submitted = True
                st.rerun()

    # --- Main Form for Expense Entry ---
    with st.form("expense_form"):
        date = st.date_input("Date")
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        description = st.text_area("Description")
        submitted = st.form_submit_button("Submit")

    if submitted:
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO expenses (
                            date, type, amount, payment_method,
                            used_credit_card, paid_to,
                            category, subcategory,
                            is_splitwise, splitwise_person, description
                        )
                        VALUES (
                            :date, :type, :amount, :method,
                            :credit, :paid_to, :cat, :subcat,
                            :splitwise, :person, :desc
                        )
                    """),
                    {
                        "date": date,
                        "type": type_,
                        "amount": amount,
                        "method": payment_method if payment_method != "➕ Add New" else new_method,
                        "credit": used_credit_card if used_credit_card != "➕ Add New" else new_card,
                        "paid_to": paid_to if paid_to != "➕ Add New" else new_payee,
                        "cat": category,
                        "subcat": subcategory,
                        "splitwise": "Yes" if is_splitwise else "No",
                        "person": splitwise_person if splitwise_person != "➕ Add New" else new_person,
                        "desc": description
                    }
                )
                last_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

            update_balances_from_expenses(engine, last_id)
            st.session_state.just_submitted = True
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to record expense: {e}")

    if st.session_state.just_submitted:
        st.success("✅ Expense recorded and balances updated!")
        st.info("ℹ️ You can switch to the Dashboard to verify the update.")
        st.session_state.just_submitted = False

elif view == "Change Password":
    st.subheader("🔒 Change Password")

    old_pw = st.text_input("Current Password", type="password")
    new_pw = st.text_input("New Password", type="password")
    confirm_pw = st.text_input("Confirm New Password", type="password")
    update_btn = st.button("Update Password")

    if update_btn:
        user = get_user_by_username(st.session_state.username)
        if not user:
            st.error("⚠️ User not found.")
        elif not bcrypt.checkpw(old_pw.encode(), user.password_hash.encode()):
            st.error("❌ Current password is incorrect.")
        elif new_pw != confirm_pw:
            st.warning("⚠️ New passwords do not match.")
        else:
            new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE users SET password_hash = :h WHERE username = :u"),
                    {"h": new_hash, "u": st.session_state.username}
                )
            st.success("✅ Password updated successfully.")




