from sqlalchemy import text
from db.connection import get_engine

def update_balances_from_expenses(engine, last_id=None):
    query = "SELECT * FROM expenses"
    params = {}

    if last_id:
        query += " WHERE id = :last_id"
        params = {"last_id": last_id}
    else:
        query += " ORDER BY id"

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = result.fetchall()

    with engine.begin() as conn:
        for row in rows:
            r = row._mapping
            amount = float(r["amount"])
            tx_type = r["type"]
            method = r["payment_method"]
            credit_card = r["used_credit_card"]
            paid_to = r["paid_to"]
            is_splitwise = str(r["is_splitwise"]).lower() == "yes"
            person = r["splitwise_person"]
            user_id = r["user_id"]

            # ========== INCOME ==========
            if tx_type == "income":
                if method:
                    conn.execute(text("""
                        UPDATE checking_accounts
                        SET current_balance = current_balance + :amt
                        WHERE name = :name AND user_id = :user_id
                    """), {"amt": amount, "name": method, "user_id": user_id})
                if is_splitwise and person:
                    # they paid me → reduce what they owe me
                    conn.execute(text("""
                        UPDATE splitwise_people
                        SET net_balance = net_balance + :amt
                        WHERE name = :name AND user_id = :user_id
                    """), {"amt": amount, "name": person, "user_id": user_id})

            # ========== EXPENSE ==========
            elif tx_type == "expense":
                if is_splitwise and person:
                    delta = -amount if amount > 0 else abs(amount)
                    sign = -1 if amount > 0 else 1
                    conn.execute(text("""
                        UPDATE splitwise_people
                        SET net_balance = net_balance + :delta
                        WHERE name = :name AND user_id = :user_id
                    """), {"delta": sign * abs(amount), "name": person, "user_id": user_id})
                else:
                    if credit_card:
                        conn.execute(text("""
                            UPDATE credit_cards
                            SET used_limit = used_limit + :amt
                            WHERE name = :name AND user_id = :user_id
                        """), {"amt": abs(amount), "name": credit_card, "user_id": user_id})
                    elif method:
                        conn.execute(text("""
                            UPDATE checking_accounts
                            SET current_balance = current_balance - :amt
                            WHERE name = :name AND user_id = :user_id
                        """), {"amt": abs(amount), "name": method, "user_id": user_id})

            # ========== TRANSFER ==========
            elif tx_type == "transfer":
                if is_splitwise:
                    continue
                if method:
                    conn.execute(text("""
                        UPDATE checking_accounts
                        SET current_balance = current_balance - :amt
                        WHERE name = :name AND user_id = :user_id
                    """), {"amt": abs(amount), "name": method, "user_id": user_id})
                if paid_to:
                    conn.execute(text("""
                        UPDATE checking_accounts
                        SET current_balance = current_balance + :amt
                        WHERE name = :name AND user_id = :user_id
                    """), {"amt": abs(amount), "name": paid_to, "user_id": user_id})

            # ========== DEBT PAYMENT ==========
            elif tx_type == "debt_payment":
                if method:
                    conn.execute(text("""
                        UPDATE checking_accounts
                        SET current_balance = current_balance - :amt
                        WHERE name = :name AND user_id = :user_id
                    """), {"amt": abs(amount), "name": method, "user_id": user_id})

                if paid_to:
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM credit_cards
                        WHERE name = :name AND user_id = :user_id
                    """), {"name": paid_to, "user_id": user_id})
                    if result.scalar() > 0:
                        conn.execute(text("""
                            UPDATE credit_cards
                            SET used_limit = used_limit - :amt
                            WHERE name = :name AND user_id = :user_id
                        """), {"amt": abs(amount), "name": paid_to, "user_id": user_id})

                if is_splitwise and person:
                    conn.execute(text("""
                        UPDATE splitwise_people
                        SET net_balance = net_balance - :amt
                        WHERE name = :name AND user_id = :user_id
                    """), {"amt": abs(amount), "name": person, "user_id": user_id})

    print("✅ All balances updated.")
