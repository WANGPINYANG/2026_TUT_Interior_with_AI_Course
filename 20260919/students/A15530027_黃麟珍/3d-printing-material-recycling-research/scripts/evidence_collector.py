#!/usr/bin/env python3
"""3D Printing Material Recycling Evidence Collector & Analysis CLI tool.

Processes structured data on recycled AM materials, computes property retention
rates, validates evidence levels against standards, identifies data gaps, and
exports evidence matrices into Markdown or CSV.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

VALID_PROCESS_TYPES = {"FDM/FFF", "SLA/DLP", "SLS", "SLM/DMLS", "COMPOSITE"}
VALID_EVIDENCE_LEVELS = {"EMPIRICAL", "MODELLED", "CLAIMED"}


def load_dataset(file_path: str) -> Dict[str, Any]:
    """Load JSON dataset from file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "records" not in data:
        raise ValueError("JSON must contain an object with a 'records' array.")
    return data


def save_dataset(file_path: str, data: Dict[str, Any]) -> None:
    """Save JSON dataset to file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def validate_record(record: Dict[str, Any], index: int) -> List[str]:
    """Validate a single record against schema rules."""
    errors = []
    rid = record.get("record_id", f"Row-{index}")

    if not record.get("record_id"):
        errors.append(f"[{rid}] Missing required field: 'record_id'")

    proc = record.get("process_type")
    if proc not in VALID_PROCESS_TYPES:
        errors.append(f"[{rid}] Invalid 'process_type': '{proc}'. Expected one of {sorted(VALID_PROCESS_TYPES)}")

    if not record.get("material_name"):
        errors.append(f"[{rid}] Missing required field: 'material_name'")

    rec_pct = record.get("recycled_content_pct")
    if rec_pct is None or not (0.0 <= float(rec_pct) <= 100.0):
        errors.append(f"[{rid}] 'recycled_content_pct' must be a float between 0.0 and 100.0")

    ev_level = record.get("evidence_level")
    if ev_level not in VALID_EVIDENCE_LEVELS:
        errors.append(f"[{rid}] Invalid 'evidence_level': '{ev_level}'. Expected one of {sorted(VALID_EVIDENCE_LEVELS)}")

    if not record.get("testing_standard"):
        errors.append(f"[{rid}] Missing required field: 'testing_standard'")

    if not record.get("source_reference"):
        errors.append(f"[{rid}] Missing required field: 'source_reference'")

    return errors


def compute_retention_rates(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Calculate tensile and elongation retention rates based on baseline values."""
    baseline = data.get("baseline", {})
    base_tensile = baseline.get("tensile_strength_mpa")
    base_elongation = baseline.get("elongation_at_break_pct")

    updated_count = 0
    for r in data["records"]:
        # Tensile retention
        if r.get("tensile_strength_mpa") is not None and base_tensile:
            computed_ts = round((float(r["tensile_strength_mpa"]) / float(base_tensile)) * 100.0, 1)
            if r.get("tensile_retention_pct") != computed_ts:
                r["tensile_retention_pct"] = computed_ts
                updated_count += 1

        # Elongation retention
        if r.get("elongation_at_break_pct") is not None and base_elongation:
            computed_el = round((float(r["elongation_at_break_pct"]) / float(base_elongation)) * 100.0, 1)
            if r.get("elongation_retention_pct") != computed_el:
                r["elongation_retention_pct"] = computed_el
                updated_count += 1

    return data, updated_count


def generate_markdown_table(data: Dict[str, Any]) -> str:
    """Render records into a clean Markdown table."""
    headers = [
        "ID", "製程", "材料規格", "再生比例", "世代",
        "拉伸強度 (保留率)", "伸長率 (保留率)", "MFI", "證據等級", "測試標準", "來源"
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |"
    ]

    for r in data.get("records", []):
        ts_str = f"{r.get('tensile_strength_mpa', '-')} MPa"
        if r.get("tensile_retention_pct") is not None:
            ts_str += f" ({r['tensile_retention_pct']}%)"

        el_str = f"{r.get('elongation_at_break_pct', '-')} %"
        if r.get("elongation_retention_pct") is not None:
            el_str += f" ({r['elongation_retention_pct']}%)"

        mfi_str = str(r.get("melt_flow_index", "-"))
        rec_pct_str = f"{r.get('recycled_content_pct', 0)}%"

        cols = [
            str(r.get("record_id", "-")),
            str(r.get("process_type", "-")),
            str(r.get("material_name", "-")),
            rec_pct_str,
            str(r.get("cycle_generation", "-")),
            ts_str,
            el_str,
            mfi_str,
            f"`{r.get('evidence_level', '-')}`",
            str(r.get("testing_standard", "-")),
            str(r.get("source_reference", "-"))
        ]
        lines.append("| " + " | ".join(cols) + " |")

    return "\n".join(lines)


def generate_csv(data: Dict[str, Any]) -> str:
    """Render records into a CSV string."""
    output = io.StringIO()
    fields = [
        "record_id", "process_type", "material_name", "recycled_content_pct",
        "cycle_generation", "additive_or_compatibilizer", "tensile_strength_mpa",
        "tensile_retention_pct", "elongation_at_break_pct", "elongation_retention_pct",
        "melt_flow_index", "evidence_level", "testing_standard",
        "environmental_lca_impact", "safety_ehs_notes", "source_reference"
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for r in data.get("records", []):
        row = {k: r.get(k, "") for k in fields}
        writer.writerow(row)
    return output.getvalue()


def run_gap_and_feasibility_assessment(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze data gaps, count evidence tiers, and estimate TRL."""
    records = data.get("records", [])
    total_records = len(records)
    counts = {"EMPIRICAL": 0, "MODELLED": 0, "CLAIMED": 0}
    gaps = []

    has_baseline = bool(data.get("baseline"))
    if not has_baseline:
        gaps.append("缺少 G0 原生基準對照組 (Baseline data missing)")

    has_elongation = False
    has_lca = False
    has_ehs = False
    generations = set()

    for r in records:
        ev = r.get("evidence_level")
        if ev in counts:
            counts[ev] += 1

        if r.get("elongation_at_break_pct") is not None:
            has_elongation = True
        if r.get("environmental_lca_impact"):
            has_lca = True
        if r.get("safety_ehs_notes"):
            has_ehs = True
        gen = r.get("cycle_generation")
        if gen:
            generations.add(gen)

    if not has_elongation:
        gaps.append("缺乏延性/斷裂伸長率測試 (Ductility/Elongation data missing - critical for embrittlement analysis)")
    if len(generations) <= 1:
        gaps.append("僅有單一世代紀錄，缺乏多重循環 (Multi-generation aging curve missing)")
    if not has_lca:
        gaps.append("缺乏生命週期評估 (LCA) 或碳足跡數據")
    if not has_ehs:
        gaps.append("未評估熱加工空氣逸散微粒或環安衛風險 (EHS evaluation missing)")

    # Feasibility Rating calculation
    empirical_ratio = counts["EMPIRICAL"] / total_records if total_records > 0 else 0
    if total_records >= 3 and empirical_ratio >= 0.7 and len(generations) >= 2:
        trl = 5
        trl_label = "TRL 5 (小型試驗 / 原型拉絲驗證完成 - Pilot scale demonstrated)"
    elif total_records >= 2 and counts["EMPIRICAL"] >= 1:
        trl = 3
        trl_label = "TRL 3 (實驗室概念驗證階段 - Lab-scale proof of concept)"
    else:
        trl = 2
        trl_label = "TRL 2 (初步文獻與技術概念形成 - Conceptual/Claimed)"

    return {
        "total_records": total_records,
        "evidence_counts": counts,
        "empirical_ratio_pct": round(empirical_ratio * 100, 1),
        "evaluated_trl": trl,
        "trl_description": trl_label,
        "identified_gaps": gaps
    }


def main():
    parser = argparse.ArgumentParser(
        description="3D Printing Material Recycling Evidence Collector & CLI Tool"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: validate
    v_parser = subparsers.add_parser("validate", help="Validate dataset against schema")
    v_parser.add_argument("--input", "-i", required=True, help="Path to input JSON dataset")

    # Subcommand: calculate
    c_parser = subparsers.add_parser("calculate", help="Compute retention rates using baseline")
    c_parser.add_argument("--input", "-i", required=True, help="Path to input JSON dataset")
    c_parser.add_argument("--output", "-o", help="Path to save updated JSON (defaults to overwriting input)")

    # Subcommand: export
    e_parser = subparsers.add_parser("export", help="Export evidence matrix into Markdown or CSV")
    e_parser.add_argument("--input", "-i", required=True, help="Path to input JSON dataset")
    e_parser.add_argument("--format", "-f", choices=["markdown", "csv"], default="markdown")
    e_parser.add_argument("--output", "-o", help="Optional output file path")

    # Subcommand: assess
    a_parser = subparsers.add_parser("assess", help="Perform feasibility assessment and data gap checklist")
    a_parser.add_argument("--input", "-i", required=True, help="Path to input JSON dataset")

    args = parser.parse_args()

    try:
        data = load_dataset(args.input)

        if args.command == "validate":
            all_errors = []
            for idx, rec in enumerate(data.get("records", [])):
                errs = validate_record(rec, idx + 1)
                all_errors.extend(errs)

            if all_errors:
                print(f"[FAILED] Found {len(all_errors)} validation error(s):")
                for err in all_errors:
                    print(f"  - {err}")
                sys.exit(1)
            else:
                print(f"[PASSED] Dataset is valid. ({len(data.get('records', []))} records checked)")

        elif args.command == "calculate":
            updated_data, count = compute_retention_rates(data)
            out_file = args.output if args.output else args.input
            save_dataset(out_file, updated_data)
            print(f"[SUCCESS] Calculated retention rates for {len(updated_data.get('records', []))} records ({count} fields updated).")
            print(f"Saved to: {out_file}")

        elif args.command == "export":
            if args.format == "markdown":
                res = generate_markdown_table(data)
            else:
                res = generate_csv(data)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(res)
                print(f"[SUCCESS] Exported {args.format} to: {args.output}")
            else:
                print(res)

        elif args.command == "assess":
            report = run_gap_and_feasibility_assessment(data)
            print("=" * 60)
            print("3D 列印材料回收可行性與資料缺口評估報告")
            print("=" * 60)
            print(f"總紀錄筆數: {report['total_records']}")
            print(f"證據等級分佈: 實測 (EMPIRICAL): {report['evidence_counts']['EMPIRICAL']} | "
                  f"推估 (MODELLED): {report['evidence_counts']['MODELLED']} | "
                  f"宣稱 (CLAIMED): {report['evidence_counts']['CLAIMED']}")
            print(f"實測證據佔比: {report['empirical_ratio_pct']}%")
            print(f"評定成熟度: {report['trl_description']}")
            print("\n識別之資料缺口 (Data Gaps):")
            if report['identified_gaps']:
                for gap in report['identified_gaps']:
                    print(f"  [!] {gap}")
            else:
                print("  [✓] 資料完整，未發現重大缺口。")
            print("=" * 60)

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
