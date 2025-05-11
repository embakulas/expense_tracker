import pandas as pd
from sqlalchemy import text
from db.connection import get_engine

# Load Excel file
df = pd.read_excel('data/expenses.xlsx')

# Normalize column names
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

# Convert 'yes'/'no' in 'is_splitwise' to boolean
df["is_splitwise"] = df["is_splitwise"].apply(lambda x: str(x).strip().lower() == "yes")

# Preview loaded data
print("Loaded data:")
print(df.head())

# Connect to MySQL
engine = get_engine()

# Insert rows into 'expenses' table
with engine.begin() as conn:
    for _, row in df.iterrows():
        query = text("""
            INSERT INTO expenses (
                date, amount, type, payment_method_id,
                category_id, subcategory_id,
                is_splitwise, description
            ) VALUES (
                :date, :amount, :type, :payment_method_id,
                :category_id, :subcategory_id,
                :is_splitwise, :description
            )
        """)

        # TEMP: using placeholder IDs until lookup is implemented
        conn.execute(query, {
            "date": row["date"],
            "amount": row["amount"],
            "type": row["type"],
            "payment_method_id": 1,
            "category_id": 1,
            "subcategory_id": 1,
            "is_splitwise": row["is_splitwise"],
            "description": row.get("description", "")
        })

print("✅ Excel data uploaded to MySQL successfully.")
