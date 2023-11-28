import os
from sqlalchemy import create_engine, text
from autosubmit_api.config.basicConfig import APIBasicConfig


def create_main_db_conn():
    APIBasicConfig.read()
    autosubmit_db_path = os.path.abspath(APIBasicConfig.DB_PATH)
    as_times_db_path = os.path.join(APIBasicConfig.DB_DIR, APIBasicConfig.AS_TIMES_DB)
    engine = create_engine("sqlite://")
    conn = engine.connect()
    conn.execute(text(f"attach database '{autosubmit_db_path}' as autosubmit;"))
    conn.execute(text(f"attach database '{as_times_db_path}' as as_times;"))
    return conn


def create_autosubmit_db_engine():
    APIBasicConfig.read()
    return create_engine(f"sqlite:///{ os.path.abspath(APIBasicConfig.DB_PATH)}")


def create_as_times_db_engine():
    APIBasicConfig.read()
    db_path = os.path.join(APIBasicConfig.DB_DIR, APIBasicConfig.AS_TIMES_DB)
    return create_engine(f"sqlite:///{ os.path.abspath(db_path)}")
