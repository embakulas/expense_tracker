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

            # ========== INCOME ==========
            if tx_type == "income":
                if method:
                    conn.execute(text("""
                        UPDATE checking_accounts
                        SET current_balance = current_balance + :amt
                        WHERE name = :name
                    """), {"amt": amount, "name": method})
                if is_splitwise and person:
                    # they paid me → reduce what they owe me
                    conn.execute(text("""
                        UPDATE splitwise_people
                        SET net_balance = net_balance + :amt
                        WHERE name = :name
                    """), {"amt": amount, "name": person})

            # ========== EXPENSE ==========
            elif tx_type == "expense":
                if is_splitwise and person:
                    if amount > 0:
                        # I paid → they owe me more
                        conn.execute(text("""
                            UPDATE splitwise_people
                            SET net_balance = net_balance - :amt
                            WHERE name = :name
                        """), {"amt": amount, "name": person})
                    else:
                        # They paid → I owe them more
                        conn.execute(text("""
                            UPDATE splitwise_people
                            SET net_balance = net_balance + :amt
                            WHERE name = :name
                        """), {"amt": abs(amount), "name": person})
                else:
                    if credit_card:
                        conn.execute(text("""
                            UPDATE credit_cards
                            SET used_limit = used_limit + :amt
                            WHERE name = :name
                        """), {"amt": abs(amount), "name": credit_card})
                    elif method:
                        conn.execute(text("""
                            UPDATE checking_accounts
                            SET current_balance = current_balance - :amt
                            WHERE name = :name
                        """), {"amt": abs(amount), "name": method})

            # ========== TRANSFER ==========
            elif tx_type == "transfer":
                if is_splitwise:
                    continue  # skip invalid
                if method:
                    conn.execute(text("""
                        UPDATE checking_accounts
                        SET current_balance = current_balance - :amt
                        WHERE name = :name
                    """), {"amt": abs(amount), "name": method})
                if paid_to:
                    conn.execute(text("""
                        UPDATE checking_accounts
                        SET current_balance = current_balance + :amt
                        WHERE name = :name
                    """), {"amt": abs(amount), "name": paid_to})

            # ========== DEBT PAYMENT ==========
            elif tx_type == "debt_payment":
                if method:
                    conn.execute(text("""
                        UPDATE checking_accounts
                        SET current_balance = current_balance - :amt
                        WHERE name = :name
                    """), {"amt": abs(amount), "name": method})

                if paid_to:
                    result = conn.execute(text("SELECT COUNT(*) FROM credit_cards WHERE name = :name"), {"name": paid_to})
                    if result.scalar() > 0:
                        conn.execute(text("""
                            UPDATE credit_cards
                            SET used_limit = used_limit - :amt
                            WHERE name = :name
                        """), {"amt": abs(amount), "name": paid_to})

                if is_splitwise and person:
                    # I repaid them → I owe them less
                    conn.execute(text("""
                        UPDATE splitwise_people
                        SET net_balance = net_balance - :amt
                        WHERE name = :name
                    """), {"amt": abs(amount), "name": person})

    print("✅ All balances updated.")
