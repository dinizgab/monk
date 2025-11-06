def type_to_string(coltype, dialect):
    try:
        return dialect.type_compiler.process(coltype)
    except Exception:
        return coltype.__class__.__name__.upper()


def to_scalar(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


def serialize_column(col, dialect, pk_columns=None, fk_map=None) -> dict:
    pk_columns = set(pk_columns or [])
    fk_map = fk_map or {}

    t = col.get("type")
    out = {
        "name": col.get("name"),
        "type": type_to_string(t, dialect) if t is not None else None,
        "nullable": bool(col.get("nullable", True)),
        "default": to_scalar(col.get("default")),
        "comment": to_scalar(col.get("comment")),
    }

    out["autoincrement"] = bool(col.get("autoincrement", False))

    column_name = out["name"]

    out["is_primary_key"] = column_name in pk_columns or bool(
        col.get("primary_key", False)
    )

    references = fk_map.get(column_name, [])
    out["is_foreign_key"] = bool(references)
    out["foreign_key_references"] = references

    return out
