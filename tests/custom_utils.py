from http import HTTPStatus
from sqlalchemy import Connection, text


def dummy_response(*args, **kwargs):
    return "Hello World!", HTTPStatus.OK


def custom_return_value(value=None):
    def blank_func(*args, **kwargs):
        return value

    return blank_func


def setup_pg_db(conn: Connection):
    """
    Resets database by dropping all schemas except the system ones and restoring the public schema
    """
    # Get all schema names that are not from the system
    results = conn.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema'"
        )
    ).all()
    schema_names = [res[0] for res in results]

    # Drop all schemas
    for schema_name in schema_names:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))

    # Restore default public schema
    conn.execute(text("CREATE SCHEMA public"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
