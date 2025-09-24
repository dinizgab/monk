from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

from src.utils.column_serialization import serialize_column


def extract_db_info(urls: str) -> dict:
    infos = []
    for url in urls:
        url = add_url_driver(url)

        engine = create_engine(url)

        db = make_url(url)
        dialect = engine.dialect
        insp = inspect(engine)

        payload = {
            "dialect": db.get_backend_name(),
            "drivername": (
                db.drivername.split("+")[1] if "+" in db.drivername else db.drivername
            ),
            "username": db.username,
            "password": db.password,
            "host": db.host,
            "port": db.port,
            "database": db.database,
            "tables": {},
        }

        for table in insp.get_table_names():
            cols = [serialize_column(col) for col in insp.get_columns(table)]

            payload["tables"][table] = cols

    return infos


def add_url_driver(url: str) -> str:
    drivers = {
        "oracle": "cx_oracle",
        "postgresql": "psycopg",
        "mysql": "pymysql",
        "mssql": "pyodbc",
    }
    dialect = url.split("://")[0]

    if "+" in dialect:
        return url

    if dialect in drivers:
        return url.replace(dialect, f"{dialect}+{drivers[dialect]}")
