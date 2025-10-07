from pathlib import Path
import re
import json
import argparse
import pandas as pd
from typing import Dict, List, Tuple

ID_RE_CROSS = re.compile(r"^result_(\d+)\.csv$", re.IGNORECASE)
ID_RE_PLAN = re.compile(r"^result_plan_(\d+)\.csv$", re.IGNORECASE)


def find_subdirs(base: Path) -> List[Path]:
    if not base.exists():
        return []
    return sorted([p for p in base.iterdir() if p.is_dir()])


def list_ids_in_cross(cross_subdir: Path) -> Dict[str, Path]:
    out = {}
    for p in cross_subdir.glob("*.csv"):
        m = ID_RE_CROSS.match(p.name)
        if m:
            out[m.group(1)] = p
    return out


def list_plan_files(results_subdir: Path) -> Dict[str, Path]:
    out = {}
    for p in results_subdir.glob("*.csv"):
        m = ID_RE_PLAN.match(p.name)
        if m:
            out[m.group(1)] = p
    return out


def read_csv_normalized(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns=lambda c: str(c).strip().lower())
    df = df.sort_index(axis=1)
    try:
        df = df.sort_values(by=list(df.columns)).reset_index(drop=True)
    except Exception:
        df = df.reset_index(drop=True)
    return df


def equals_csv(a: Path, b: Path, strict: bool = False) -> bool:
    if strict:
        return a.read_bytes() == b.read_bytes()
    try:
        da = read_csv_normalized(a)
        db = read_csv_normalized(b)
    except Exception:
        return a.read_bytes() == b.read_bytes()
    if da.shape != db.shape or list(da.columns) != list(db.columns):
        return False
    return da.equals(db)


def is_csv_empty(path: Path) -> bool:
    try:
        df = pd.read_csv(path)
        return df.empty
    except Exception:
        return path.stat().st_size == 0


def compare_subdir(
    cross_subdir: Path, results_subdir: Path, strict: bool = False
) -> Dict:
    cross_ids = list_ids_in_cross(cross_subdir)
    plan_ids = list_plan_files(results_subdir)
    missing = []
    equals = []
    diffs = []

    for id_, cross_path in cross_ids.items():
        plan_path = plan_ids.get(id_)
        if plan_path is None:
            missing.append(id_)
            continue
        if equals_csv(cross_path, plan_path, strict=strict):
            equals.append(id_)
        else:
            diffs.append(id_)

    empty_plan_ids = sorted(
        [pid for pid, ppath in plan_ids.items() if is_csv_empty(ppath)],
        key=lambda x: int(x),
    )

    return {
        "subdir": cross_subdir.name,
        "total_cross_files": len(cross_ids),
        "missing_in_results_count": len(missing),
        "missing_in_results_ids": sorted(missing, key=lambda x: int(x)),
        "equal_count": len(equals),
        "equal_ids": sorted(equals, key=lambda x: int(x)),
        "different_count": len(diffs),
        "different_ids": sorted(diffs, key=lambda x: int(x)),
        "empty_in_results_count": len(empty_plan_ids),
        "empty_in_results_ids": empty_plan_ids,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Compare CSVs between crossing_data and results."
    )
    ap.add_argument(
        "--base",
        type=str,
        default=".",
        help="Base directory containing crossing_data/ and results/",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Use byte-for-byte comparison instead of CSV-normalized",
    )
    ap.add_argument("--outdir", type=str, default=".", help="Where to write reports")
    args = ap.parse_args()

    base = Path(args.base).resolve()
    cross_base = base / "crossing_data"
    results_base = base / "results"

    cross_subdirs = {p.name: p for p in find_subdirs(cross_base)}
    results_subdirs = {p.name: p for p in find_subdirs(results_base)}

    # Intersect subdir names that exist in both; still process ones that exist only in crossing_data (to count missing)
    subdir_names = sorted(set(cross_subdirs.keys()) | set(results_subdirs.keys()))

    all_reports = []
    for name in subdir_names:
        cross_sub = cross_subdirs.get(name, None)
        results_sub = results_subdirs.get(name, None)

        # If crossing subdir doesn't exist, nothing to compare for that subdir
        if cross_sub is None:
            continue

        if results_sub is None:
            # Count all files as "missing in results"
            cross_ids = list_ids_in_cross(cross_sub)
            rep = {
                "subdir": name,
                "total_cross_files": len(cross_ids),
                "missing_in_results_count": len(cross_ids),
                "missing_in_results_ids": sorted(
                    list(cross_ids.keys()), key=lambda x: int(x)
                ),
                "equal_count": 0,
                "equal_ids": [],
                "different_count": 0,
                "different_ids": [],
            }
        else:
            rep = compare_subdir(cross_sub, results_sub, strict=args.strict)

        all_reports.append(rep)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Write per-subdir CSV and combined JSON
    for rep in all_reports:
        sub = rep["subdir"]
        rows = []
        for id_ in rep["missing_in_results_ids"]:
            rows.append({"id": int(id_), "status": "missing_in_results"})
        for id_ in rep["equal_ids"]:
            rows.append({"id": int(id_), "status": "equal"})
        for id_ in rep["different_ids"]:
            rows.append({"id": int(id_), "status": "different"})
        df = (
            pd.DataFrame(rows).sort_values(by="id")
            if rows
            else pd.DataFrame(columns=["id", "status"])
        )
        df.to_csv(outdir / f"comparison_report_{sub}.csv", index=False)

    (outdir / "comparison_summary.json").write_text(
        json.dumps(all_reports, indent=2, ensure_ascii=False)
    )

    # Print concise summary
    print("=== Comparison Summary ===")
    for rep in all_reports:
        print(
            f"[{rep['subdir']}] total_cross={rep['total_cross_files']} missing={rep['missing_in_results_count']} equal={rep['equal_count']} different={rep['different_count']}"
        )
    print(f"\nReports saved to: {outdir.resolve()}")
    print("- Per-subdir CSV: comparison_report_<subdir>.csv")
    print("- Combined JSON: comparison_summary.json")


if __name__ == "__main__":
    main()
