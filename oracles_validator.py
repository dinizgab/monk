import json
import re
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd

PROJECT_ROOT = Path(".")

PLANS_DIR = PROJECT_ROOT / "plans_v2"
SUITES_DIR = PROJECT_ROOT / "test" / "suites" / "schemas"
EXEC_LOGS_DIR = PROJECT_ROOT / "test" / "execution_logs"

SUITES = ["bakery_1", "ecommerce", "chat", "sales", "store"]

EXEC_JSONL_BY_SUITE = {
    "bakery_1": EXEC_LOGS_DIR / "bakery_1.jsonl",
    "ecommerce": EXEC_LOGS_DIR / "ecommerce.jsonl",
    "chat": EXEC_LOGS_DIR / "chat.jsonl",
    "sales": EXEC_LOGS_DIR / "sales.jsonl",
    "store": EXEC_LOGS_DIR / "store.jsonl",
}

FIELD_MAP = {
    "suite": ["suite"],
    "plan_num": ["plan_num", "id", "question_id"],
    "status": ["status", "execution_status"],
    "result_path": ["result_path", "pred_result_path", "output_csv_path"],
    "question": ["question", "nl_question"],
}

SUCCESS_VALUES = {"SUCCESS", "OK", "PASS", "SUCCEEDED", True}

AGG_TRIGGERS = [
    "how many", "count", "number of", "total",
    "average", "avg", "maximum", "max", "minimum", "min", "sum",
    "most", "least", "highest", "lowest", "top ", "cheapest", "most expensive",
]

LIST_TRIGGERS = [
    "list", "show", "give", "return", "find", "what are", "which", "display"
]

DISTINCT_TRIGGERS = [
    "distinct", "unique", "no duplicates"
]

EMPTY_OK_TRIGGERS = [
    "no ", "without", "never", "none", "missing", "not ",
    "zero", "não", "nunca", "sem ", "nenhum", "ausent"
]

FILTER_HINT_RE = re.compile(
    r'(".*?")|(\b20\d{2}\b)|(\b(before|after|between|during|in the last|last \d+ days)\b)|'
    r'(\bgreater than\b|\bless than\b|\bat least\b|\bat most\b|\bover\b|\bunder\b)',
    re.IGNORECASE
)

SQL_FILTER_RE = re.compile(r"\bWHERE\b|\bBETWEEN\b|\bLIKE\b|\bIN\s*\(|>=|<=|=|<|>", re.IGNORECASE)

def has_any(text: str, keys: list[str]) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keys)

def is_agg_question(q: str) -> bool:
    return has_any(q, AGG_TRIGGERS)

def is_list_question(q: str) -> bool:
    # list intent but not clearly aggregate
    return has_any(q, LIST_TRIGGERS) and not is_agg_question(q)

def has_explicit_filter_hint(q: str) -> bool:
    return bool(FILTER_HINT_RE.search(q or ""))

def wants_distinct(q: str) -> bool:
    return has_any(q, DISTINCT_TRIGGERS)

def safe_get(d: dict, candidates: list[str], default=None):
    for k in candidates:
        if k in d:
            return d[k]
    return default

def can_be_empty_list(q: str) -> bool:
    return has_any(q, EMPTY_OK_TRIGGERS)

def load_questions() -> dict[str, dict[int, str]]:
    """questions[suite][id] = question"""
    questions = {}
    for suite in SUITES:
        qpath = SUITES_DIR / suite / "questions.json"
        if not qpath.exists():
            questions[suite] = {}
            continue
        data = json.loads(qpath.read_text(encoding="utf-8"))
        questions[suite] = {int(x["id"]): x["question"] for x in data}
    return questions

def load_plan(suite: str, plan_num: int) -> dict | None:
    p = PLANS_DIR / suite / f"plan_{plan_num}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def load_jsonl(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out

def read_result_csv(result_path: str):
    if not result_path:
        return None
    p = Path(result_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    if not p.exists():
        return None
    try:
        return pd.read_csv(p)
    except Exception:
        return None

def produced_aliases(plan: dict) -> set[str]:
    out = set()
    for step in plan.get("execution_plan", []) or []:
        for col in (step.get("output_columns") or []):
            alias = col.get("alias")
            if isinstance(alias, str) and alias:
                out.add(alias)
    return out

def plan_databases(plan: dict) -> set[str]:
    dbs = set()
    for step in plan.get("execution_plan", []) or []:
        db = step.get("database")
        if isinstance(db, str) and db:
            dbs.add(db)
    return dbs

def O2_list_no_agg(plan, q):
    applicable = is_list_question(q)
    if not applicable:
        return False, True, "n/a"
    fa = plan.get("final_aggregation", {}) or {}
    ok = (fa.get("type") == "NONE")
    return True, ok, "list query should have final_aggregation.type == NONE"

def O3_filter_presence(plan, q):
    applicable = has_explicit_filter_hint(q)
    if not applicable:
        return False, True, "n/a"
    ok = any(SQL_FILTER_RE.search((step.get("query") or "")) for step in plan.get("execution_plan", []) or [])
    return True, ok, "question hints filter; expected WHERE/IN/BETWEEN/etc in some step SQL"

def O4_sales_scope(plan, q, suite):
    applicable = (suite == "sales") and any(k in (q or "").upper() for k in ["EU", "US", "BOTH"])
    if not applicable:
        return False, True, "n/a"
    qU = (q or "").upper()
    dbs = {d.lower() for d in plan_databases(plan)}
    need_eu = ("EU" in qU) or ("BOTH" in qU)
    need_us = ("US" in qU) or ("BOTH" in qU)
    ok = True
    if need_eu:
        ok = ok and any("sales_eu" in d for d in dbs)
    if need_us:
        ok = ok and any("sales_us" in d for d in dbs)
    return True, ok, f"databases used: {sorted(dbs)}"

def O5_final_cols_produced(plan):
    produced = produced_aliases(plan)
    final_cols = plan.get("final_output_columns", []) or []
    ok = all(isinstance(c, str) and c in produced for c in final_cols)
    return True, ok, "final_output_columns must appear in some output_columns.alias"

def O6_aggregation_declared_ok(plan):
    produced = produced_aliases(plan)
    fa = plan.get("final_aggregation", {}) or {}
    t = fa.get("type")
    if t == "NONE":
        col_ok = (not fa.get("column"))
        gb = fa.get("group_by", [])
        gb_ok = (gb is None) or (isinstance(gb, list) and len(gb) == 0)
        return True, (col_ok and gb_ok), "NONE aggregation should not define column/group_by"
    else:
        col = fa.get("column")
        gb = fa.get("group_by", []) or []
        ok = isinstance(col, str) and col in produced and all(isinstance(g, str) and g in produced for g in gb)
        return True, ok, "aggregation column/group_by must be produced"

def O7_result_shape_for_agg(df, plan):
    fa = plan.get("final_aggregation", {}) or {}
    applicable = (fa.get("type") != "NONE")
    if not applicable:
        return False, True, "n/a"

    if df is None:
        return True, False, "missing result CSV"
    if len(df) != 1 or df.shape[1] != 1:
        return True, False, f"expected 1x1; got shape={df.shape}, rows={len(df)}"
    s = df.iloc[:, 0]
    coerced = pd.to_numeric(s, errors="coerce")
    ok = coerced.notna().mean() >= 0.8
    return True, ok, "expected numeric scalar"

def O8_non_empty_for_list(df, q):
    applicable = is_list_question(q)
    if not applicable:
        return False, True, "n/a"
    if df is None:
        return True, False, "missing result CSV"

    if len(df) == 0 and can_be_empty_list(q):
        return True, True, "empty list acceptable given absence-style intent"
    
    ok = len(df) > 0
    return True, ok, "expected non-empty result for list queries (soft oracle)"

def O9_numeric_type_for_agg(df, plan):
    fa = plan.get("final_aggregation", {}) or {}
    applicable = (fa.get("type") != "NONE")
    if not applicable:
        return False, True, "n/a"
    if df is None or df.shape[1] == 0:
        return True, False, "missing/empty result CSV"
    best = 0.0
    for c in df.columns:
        coerced = pd.to_numeric(df[c], errors="coerce")
        best = max(best, coerced.notna().mean())
    ok = best >= 0.8
    return True, ok, "expected mostly numeric output for aggregation intent"

def O10_distinct(df, q):
    applicable = wants_distinct(q)
    if not applicable:
        return False, True, "n/a"
    if df is None:
        return True, False, "missing result CSV"
    ok = df.duplicated().sum() == 0
    return True, ok, "expected no duplicate rows for distinct/unique intent"

ORACLES = [
    ("O2_list_no_agg", lambda plan, q, suite, df: O2_list_no_agg(plan, q)),
    ("O3_filter_presence", lambda plan, q, suite, df: O3_filter_presence(plan, q)),
    ("O4_sales_scope", lambda plan, q, suite, df: O4_sales_scope(plan, q, suite)),
    ("O5_final_cols_produced", lambda plan, q, suite, df: O5_final_cols_produced(plan)),
    ("O6_aggregation_declared_ok", lambda plan, q, suite, df: O6_aggregation_declared_ok(plan)),
    ("O7_result_shape_for_agg", lambda plan, q, suite, df: O7_result_shape_for_agg(df, plan)),
    ("O8_non_empty_for_list", lambda plan, q, suite, df: O8_non_empty_for_list(df, q)),
    ("O9_numeric_type_for_agg", lambda plan, q, suite, df: O9_numeric_type_for_agg(df, plan)),
    ("O10_distinct", lambda plan, q, suite, df: O10_distinct(df, q)),
]

# =============================
# TCSP main
# =============================

def is_success(status_val) -> bool:
    if status_val in SUCCESS_VALUES:
        return True
    if isinstance(status_val, str) and status_val.upper() in SUCCESS_VALUES:
        return True
    return False

def compute_tcsp():
    questions = load_questions()

    rows = []
    suite_scores = defaultdict(list)
    oracle_fail_counter = Counter()

    for suite, log_path in EXEC_JSONL_BY_SUITE.items():
        logs = load_jsonl(log_path)
        for rec in logs:
            rec_suite = safe_get(rec, FIELD_MAP["suite"], suite) or suite
            plan_num = safe_get(rec, FIELD_MAP["plan_num"], None)
            status = safe_get(rec, FIELD_MAP["status"], None)

            if plan_num is None:
                continue
            try:
                plan_num = int(plan_num)
            except Exception:
                continue

            if status is None or not is_success(status):
                continue

            q = safe_get(rec, FIELD_MAP["question"], None)
            if not q:
                q = questions.get(rec_suite, {}).get(plan_num, "")

            plan = load_plan(rec_suite, plan_num)
            if not plan:
                continue

            df = read_result_csv(safe_get(rec, FIELD_MAP["result_path"], ""))

            applicable = 0
            passed = 0
            failed = []

            for name, fn in ORACLES:
                is_app, ok, _detail = fn(plan, q, rec_suite, df)
                if is_app:
                    applicable += 1
                    if ok:
                        passed += 1
                    else:
                        failed.append(name)
                        oracle_fail_counter[name] += 1

            score = (passed / applicable) if applicable else 1.0

            rows.append({
                "suite": rec_suite,
                "plan_num": plan_num,
                "oracle_applicable": applicable,
                "oracle_passed": passed,
                "tcsp_score": round(score, 4),
                "failed_oracles": ",".join(failed),
            })
            suite_scores[rec_suite].append(score)

    df_out = pd.DataFrame(rows)
    df_out.to_csv("tcsp_results.csv", index=False)

    summary = []
    for suite in SUITES:
        scores = suite_scores.get(suite, [])
        if not scores:
            summary.append({"suite": suite, "n": 0, "tcsp_mean": 0.0, "tcsp_pass_all_pct": 0.0})
            continue
        summary.append({
            "suite": suite,
            "n": len(scores),
            "tcsp_mean": round(sum(scores) / len(scores), 4),
            "tcsp_pass_all_pct": round(sum(1 for s in scores if s == 1.0) / len(scores) * 100, 2),
        })

    pd.DataFrame(summary).to_csv("tcsp_summary_by_suite.csv", index=False)

    with open("tcsp_top_oracle_failures.txt", "w", encoding="utf-8") as f:
        for name, cnt in oracle_fail_counter.most_common(50):
            f.write(f"{cnt}\t{name}\n")

    print("✅ Gerados:")
    print(" - tcsp_results.csv")
    print(" - tcsp_summary_by_suite.csv")
    print(" - tcsp_top_oracle_failures.txt")

if __name__ == "__main__":
    compute_tcsp()
