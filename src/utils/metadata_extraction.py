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
            pk_constraint = insp.get_pk_constraint(table) or {}
            pk_columns = pk_constraint.get("constrained_columns") or []

            fk_constraints = insp.get_foreign_keys(table)
            fk_map = {}
            for fk in fk_constraints:
                constrained_columns = fk.get("constrained_columns") or []
                referred_table = fk.get("referred_table")
                referred_schema = fk.get("referred_schema")
                referred_columns = fk.get("referred_columns") or []

                for idx, col_name in enumerate(constrained_columns):
                    reference = {
                        "table": referred_table,
                        "column": referred_columns[idx]
                        if idx < len(referred_columns)
                        else None,
                    }

                    if referred_schema:
                        reference["schema"] = referred_schema

                    fk_map.setdefault(col_name, []).append(reference)

            cols = [
                serialize_column(col, dialect, pk_columns=pk_columns, fk_map=fk_map)
                for col in insp.get_columns(table)
            ]

            payload["tables"][table] = cols

        infos.append(payload)

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
