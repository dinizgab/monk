from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url


def extract_db_info(urls: str) -> dict:
    infos = []
    for u in urls:
        u = add_url_driver(u)

        engine = create_engine(u)
        url = make_url(u)

        driver = url.drivername.split("+")
        inspector = inspect(engine)

        tables_infos = {}
        tables = inspector.get_table_names()
        for table in tables:
            table_columns = []
            columns = inspector.get_columns(table)
            for column in columns:
                table_columns.append(column)

            tables_infos[table] = table_columns

        infos.append(
            {
                "dialect": driver[0],
                "drivername": driver[1] if len(driver) > 1 else None,
                "username": url.username,
                "password": url.password,
                "host": url.host,
                "port": url.port,
                "database": url.database,
                "tables": tables_infos,
            }
        )

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
