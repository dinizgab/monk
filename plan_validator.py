import json
import re
from pathlib import Path
from collections import defaultdict, Counter

AS_ALIAS_RE = re.compile(r"\bAS\s+([A-Za-z_]\w*)", re.IGNORECASE)

def extract_aliases_from_query(sql: str) -> set[str]:
    """Fallback: extract aliases appearing as 'AS alias' in SQL."""
    if not isinstance(sql, str):
        return set()
    return set(AS_ALIAS_RE.findall(sql))

def parse_plans_from_directory(root_dir: str) -> list[tuple[str, dict]]:
    """
    Read all .json under root_dir recursively.
    Returns list of (relative_path, plan_dict).
    """
    root = Path(root_dir)
    plans = []
    for fp in root.rglob("*.json"):
        try:
            plan = json.loads(fp.read_text(encoding="utf-8"))
            plans.append((str(fp.relative_to(root)), plan))
        except Exception as e:
            plans.append((str(fp.relative_to(root)), {"__parse_error__": str(e)}))
    return plans

TOP_REQUIRED = ["execution_plan", "final_output_columns", "final_aggregation"]

STEP_REQUIRED = ["id", "description", "database", "query", "depends_on", "join_info", "output_columns"]

def validate_plan(plan: dict) -> list[str]:
    """
    Returns list of reasons (empty => valid).
    Criteria based on what you defined:
    - required fields for parsing/execution
    - explicit output contracts per step (output_columns)
    - alias consistency between declared aliases and dependencies
    - acyclic depends_on graph
    - final columns and aggregation compatible with produced data
    """
    reasons = []

    # parse errors
    if "__parse_error__" in plan:
        return [f"parse_error: {plan['__parse_error__']}"]

    # top-level required fields
    for k in TOP_REQUIRED:
        if k not in plan:
            reasons.append(f"missing_top_field:{k}")

    if reasons:
        return reasons

    execution_plan = plan.get("execution_plan")
    final_cols = plan.get("final_output_columns")
    final_aggr = plan.get("final_aggregation")

    if not isinstance(execution_plan, list) or len(execution_plan) == 0:
        reasons.append("execution_plan_not_list_or_empty")
        return reasons

    if not isinstance(final_cols, list):
        reasons.append("final_output_columns_not_list")

    if not isinstance(final_aggr, dict) or "type" not in final_aggr:
        reasons.append("final_aggregation_invalid_or_missing_type")

    # validate steps + build maps
    step_ids = []
    steps_by_id = {}
    produced_aliases = set()   # from output_columns, with SQL alias fallback

    for idx, step in enumerate(execution_plan):
        if not isinstance(step, dict):
            reasons.append(f"step_{idx}_not_object")
            continue

        for k in STEP_REQUIRED:
            if k not in step:
                reasons.append(f"missing_step_field:step{idx+1}:{k}")

        # If missing output_columns, no need to continue deep checks for that step
        sid = step.get("id")
        if not isinstance(sid, int):
            reasons.append(f"step_invalid_id:step{idx+1}")
            continue

        if sid in steps_by_id:
            reasons.append(f"duplicate_step_id:{sid}")
        steps_by_id[sid] = step
        step_ids.append(sid)

        # output_columns contract
        oc = step.get("output_columns")
        if not isinstance(oc, list) or len(oc) == 0:
            reasons.append(f"missing_or_empty_output_columns:step{sid}")
        else:
            for j, col in enumerate(oc):
                if not isinstance(col, dict):
                    reasons.append(f"output_columns_item_not_object:step{sid}:{j}")
                    continue
                alias = col.get("alias")
                source = col.get("source")
                if not isinstance(alias, str) or not alias:
                    reasons.append(f"output_columns_missing_alias:step{sid}:{j}")
                if not isinstance(source, str) or not source:
                    reasons.append(f"output_columns_missing_source:step{sid}:{j}")

                # alias prefix consistency: s<id>__...
                if isinstance(alias, str) and not alias.startswith(f"s{sid}__"):
                    reasons.append(f"alias_prefix_mismatch:step{sid}:{alias}")

                if isinstance(alias, str) and alias:
                    produced_aliases.add(alias)

        # fallback: also consider SQL AS aliases (useful if output_columns are present but incomplete)
        produced_aliases |= extract_aliases_from_query(step.get("query", ""))

    # validate dependency references + cycle check
    # edges: sid -> dep
    graph = defaultdict(list)
    for sid, step in steps_by_id.items():
        deps = step.get("depends_on")
        if not isinstance(deps, list):
            reasons.append(f"depends_on_not_list:step{sid}")
            continue

        for d in deps:
            if not isinstance(d, int):
                reasons.append(f"dependency_not_int:step{sid}")
                continue
            if d not in steps_by_id:
                reasons.append(f"dependency_missing_step:step{sid}->step{d}")
            graph[sid].append(d)

        # join_info sanity: if there are deps, join_info should exist and reference valid aliases
        join_info = step.get("join_info")
        if deps and join_info is None:
            # not always wrong (you may join at app-level without join_info), but by your criteria,
            # "maintains consistency between aliases declared and used in dependencies" usually implies join_info.
            reasons.append(f"depends_on_without_join_info:step{sid}")

        if isinstance(join_info, dict):
            on = join_info.get("on")
            if isinstance(on, dict):
                cur = on.get("current_step_column")
                dep = on.get("dependency_step_column")
                if isinstance(cur, str) and cur not in produced_aliases:
                    reasons.append(f"join_info_current_alias_not_produced:step{sid}:{cur}")
                if isinstance(dep, str) and dep not in produced_aliases:
                    reasons.append(f"join_info_dependency_alias_not_produced:step{sid}:{dep}")

    # cycle detection (DFS)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {sid: WHITE for sid in steps_by_id}

    def dfs(u: int) -> bool:
        color[u] = GRAY
        for v in graph.get(u, []):
            if v not in color:
                continue
            if color[v] == GRAY:
                return True  # cycle
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    has_cycle = any(dfs(sid) for sid in steps_by_id if color[sid] == WHITE)
    if has_cycle:
        reasons.append("cycle_detected_in_depends_on")

    # final_output_columns must be produced somewhere
    if isinstance(final_cols, list):
        for c in final_cols:
            if not isinstance(c, str) or not c:
                reasons.append("final_output_columns_has_non_string")
                continue
            if c not in produced_aliases:
                reasons.append(f"final_output_column_not_produced:{c}")

    # final_aggregation compatibility
    if isinstance(final_aggr, dict) and "type" in final_aggr:
        aggr_type = final_aggr.get("type")
        if aggr_type != "NONE":
            col = final_aggr.get("column")
            if not isinstance(col, str) or not col:
                reasons.append("aggregation_missing_column")
            elif col not in produced_aliases:
                reasons.append(f"aggregation_column_not_produced:{col}")

            group_by = final_aggr.get("group_by", [])
            if group_by is None:
                group_by = []
            if not isinstance(group_by, list):
                reasons.append("aggregation_group_by_not_list")
            else:
                for g in group_by:
                    if not isinstance(g, str) or not g:
                        reasons.append("aggregation_group_by_has_non_string")
                        continue
                    if g not in produced_aliases:
                        reasons.append(f"aggregation_group_by_not_produced:{g}")

    return reasons

# -----------------------------
# Reporting
# -----------------------------

def suite_from_path(path_str: str) -> str:
    parts = Path(path_str).parts
    if "plans_v2" in parts:
        i = parts.index("plans_v2")
        if i + 1 < len(parts):
            return parts[i + 1]
    return parts[0] if len(parts) > 1 else "unknown"

def run_validation(plans: list[tuple[str, dict]]):
    by_suite = defaultdict(list)
    for pth, plan in plans:
        by_suite[suite_from_path(pth)].append((pth, plan))

    summary = {}
    reasons_global = Counter()

    for suite, items in by_suite.items():
        total = len(items)
        valid = 0
        invalid = 0
        reasons_counter = Counter()

        for pth, plan in items:
            reasons = validate_plan(plan)
            if len(reasons) == 0:
                valid += 1
            else:
                invalid += 1
                reasons_counter.update(reasons)
                reasons_global.update(reasons)

        summary[suite] = {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "top_reasons": reasons_counter.most_common(10)
        }

    return summary, reasons_global.most_common(20)

if __name__ == "__main__":
    plans = parse_plans_from_directory("plans_v2")

    summary, top_reasons = run_validation(plans)

    print("=== SUMMARY BY SUITE ===")
    for suite in sorted(summary.keys()):
        s = summary[suite]
        tpv = (s["valid"] / s["total"] * 100) if s["total"] else 0.0
        print(f"{suite}: total={s['total']} valid={s['valid']} invalid={s['invalid']} TPV={tpv:.1f}%")

    print("\n=== TOP GLOBAL INVALIDATION REASONS ===")
    for r, n in top_reasons:
        print(f"{n:>4}  {r}")
