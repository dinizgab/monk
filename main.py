import argparse

from src.utils.metadata_extraction import extract_db_info

# oracle://user:password@host:1521/dbname
# postgresql://user:password@host:5432/dbname
# mysql://user:password@host:3306/dbname
# mssql://user:password@host:1433/dbname

p = argparse.ArgumentParser()
p.add_argument("db_urls", nargs="+", type=str, help="Database URL")
args = p.parse_args().db_urls

info = extract_db_info(args)
print(info)
