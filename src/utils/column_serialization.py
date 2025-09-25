def type_to_string(coltype, dialect):
    try:
        return dialect.type_compiler.process(coltype)
    except Exception:
        return coltype.__class__.__name__.upper()


def to_scalar(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


def serialize_column(col, dialect) -> dict:
    t = col.get("type")
    out = {
        "name": col.get("name"),
        "type": type_to_string(t, dialect) if t is not None else None,
        "nullable": bool(col.get("nullable", True)),
        "default": to_scalar(col.get("default")),
        "comment": to_scalar(col.get("comment")),
    }

    out["autoincrement"] = bool(col.get("autoincrement", False))

    return out
