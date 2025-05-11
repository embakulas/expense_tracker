import streamlit as st
import pandas as pd
from sqlalchemy import text
from db.connection import get_engine
from process_expenses import update_balances_from_expenses


def fetch_column_values(query, params=None):
    with get_engine().connect() as conn:
        df = pd.read_sql(query, conn, params=params)
    return df.iloc[:, 0].tolist()


def show_expense_form(engine, user_id):
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
                            is_splitwise, splitwise_person, description,
                            user_id
                        )
                        VALUES (
                            :date, :type, :amount, :method,
                            :credit, :paid_to, :cat, :subcat,
                            :splitwise, :person, :desc,
                            :user_id
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
                        "desc": description,
                        "user_id": user_id
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
