from sqlalchemy import create_engine

def get_engine():
    user = "root"
    password = "ZlgxuQZzIcKuOtVvpKURGRvCFvxqIqLj"
    host = "maglev.proxy.rlwy.net"
    database = "railway"
    port = 45257

    engine_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(engine_url)
    return engine
