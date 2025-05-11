import pandas as pd
from sqlalchemy import text
from db.connection import get_engine

engine = get_engine()

def insert_categories():
    df = pd.read_excel("data/categories.xlsx")
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("INSERT IGNORE INTO categories (name) VALUES (:name)"),
                {"name": row["name"].strip()}
            )

def insert_subcategories():
    df = pd.read_excel("data/subcategories.xlsx")
    with engine.begin() as conn:
        for _, row in df.iterrows():
            result = conn.execute(
                text("SELECT id FROM categories WHERE name = :name"),
                {"name": row["category_name"].strip()}
            ).fetchone()
            if result:
                conn.execute(
                    text("INSERT IGNORE INTO subcategories (category_id, name) VALUES (:cat_id, :subname)"),
                    {"cat_id": result.id, "subname": row["sub_category_name"].strip()}
                )

def insert_payment_methods():
    df = pd.read_excel("data/payment_methods.xlsx")
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("INSERT IGNORE INTO payment_methods (name) VALUES (:name)"),
                {"name": row["payment_methods"].strip()}
            )

def insert_credit_cards():
    df = pd.read_excel("data/credit_cards.xlsx")
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT IGNORE INTO credit_cards (name, total_limit, used_limit)
                    VALUES (:name, :total_limit, :used_limit)
                """),
                {
                    "name": row["name"].strip(),
                    "total_limit": row["total_limit"],
                    "used_limit": row["used_limit"]
                }
            )

def insert_checking_accounts():
    df = pd.read_excel("data/checking_accounts.xlsx")
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT IGNORE INTO checking_accounts (name, current_balance)
                    VALUES (:name, :current_balance)
                """),
                {
                    "name": row["name"].strip(),
                    "current_balance": row["current_balance"]
                }
            )

def insert_splitwise_people():
    df = pd.read_excel("data/splitwise_people.xlsx")
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT IGNORE INTO splitwise_people (name, net_balance)
                    VALUES (:name, :net_balance)
                """),
                {
                    "name": row["name"].strip(),
                    "net_balance": row["net_balance"]
                }
            )

if __name__ == "__main__":
    insert_categories()
    insert_subcategories()
    insert_payment_methods()
    insert_credit_cards()
    insert_checking_accounts()
    insert_splitwise_people()
    print(" All master data loaded successfully.")
