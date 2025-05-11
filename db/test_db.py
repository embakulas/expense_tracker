from sqlalchemy import create_engine, text

# Replace this with your actual connection string
engine_url = "mysql+pymysql://root:ZlgxuQZzIcKuOtVvpKURGRvCFvxqIqLj@maglev.proxy.rlwy.net:45257/railway"

def test_connection():
    try:
        engine = create_engine(engine_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Connected successfully. Result:", result.scalar())
    except Exception as e:
        print("❌ Failed to connect:", e)

if __name__ == "__main__":
    test_connection()
