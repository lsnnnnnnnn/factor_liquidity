"""Copy an explicitly public report bundle into a fresh publication directory.

Only standard-library file reads/copies and ZIP creation are used. This does
not read private account tables, inspect existing archives, or run Git commands.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from zipfile import ZIP_DEFLATED, ZipFile


PUBLIC_COLUMNS = {
    "trial_summary": "factor scenario capital verdict full_window_completed audit_passed return_pct minimum_order_completion worst_day_reference_completion planned_order_count unfinished_order_count unknown_target_count book_cost_cny sweep_price_cost_cny extra_impact_cost_cny fee_cny impact_cost_pct_initial impact_model impact_version impact_bps_at_10pct impact_parameter_source",
    "capacity_summary": "factor scenario maximum_tested_pass_cny nearest_higher_failure_cny unknown_capitals_cny tested_count ceiling_cny ceiling_passed nonmonotonic_observed",
    "special_cases_summary": "factor scenario capital category category_cn independent_plan_count unfinished_plan_count unknown_plan_count security_count security_day_count planned_reference_notional unfilled_reference_notional unknown_plan_quantity_count unknown_unfilled_notional_count evidence_scope",
    "run_progress": "factor scenario capital saved_status completed_day completed_trading_days total_trading_days observed_trials recorded_at_utc",
    "completion_time_summary": "factor scenario capital positive_original_plans unquantified_original_targets unfinished_original_plans timing_known_plans completed_within_30m completed_within_60m reference_completion_30m reference_completion_60m median_completed_minutes p90_completed_minutes",
    "turnover_case": "date market_amount_cny is_trade_date",
    "intraday_cases": "case_id kind timestamp background_price quantity cumulative_filled remaining_quantity",
    "plan_rounding_summary": "factor scenario capital plan_episode_count quantified_plan_episode_count positive_legal_plan_count unknown_plan_episode_count plan_rounding_reference_cny legal_zero_plan_count legal_zero_raw_reference_cny unestablished_positive_target_count unestablished_positive_target_reference_cny",
}
PUBLIC_FIGURES = ("capital_return", "capital_completion", "capital_impact", "turnover_case",
                  "intraday_1", "intraday_2", "intraday_3")
PRIVATE_KEYS = {"instrument", "order_id", "child_id", "account", "evaluation_output", "password",
                "credentials", "broker_socket", "shared_cache", "inputs", "private", "portable"}
ROLES = ("historical_baseline", "representative", "capacity_study")
STRICT_CRITERIA = {"all-plan-same-day-exact-quantity", "all-plan-same-day-exact-100pct-20261109-v1"}
LEGAL_PLAN_CRITERION = "legal-plan-same-day-exact-100pct-20261116-v1"


def check_metadata(value):
    if isinstance(value, dict):
        private = set(value)&PRIVATE_KEYS
        if private:
            raise ValueError("metadata contains private fields: "+", ".join(sorted(private)))
        for child in value.values():
            check_metadata(child)
    elif isinstance(value, list):
        for child in value:
            check_metadata(child)


def select_public_files(source):
    source = Path(source).resolve()
    if (source/"report/data/report_metadata.json").is_file():
        source = source/"report"
    metadata = json.loads((source/"data/report_metadata.json").read_text())
    if metadata.get("data_kind") != "company_historical_replay":
        raise ValueError("real-report publication requires company_historical_replay metadata")
    if metadata.get("pdf_status") != "compiled" or metadata.get("private_security_data_included") is not False:
        raise ValueError("report must declare a compiled PDF and public-only data")
    if metadata.get("criterion") == LEGAL_PLAN_CRITERION:
        if (metadata.get("research_plan_policy") != "legal_net_demand_floor_v1" or
                metadata.get("rule_version") != "g1-0935-legal-plan-impact-20261116-v5"):
            raise ValueError("legal-plan publication requires its explicit plan policy and v5 financial rule")
        if not (source/"data/plan_rounding_summary.csv").is_file():
            raise FileNotFoundError("legal-plan publication requires public target-deviation evidence")
    elif metadata.get("criterion") not in STRICT_CRITERIA:
        raise ValueError("publication requires an explicit same-day exact 100% quantity criterion")
    elif metadata.get("research_plan_policy") == "legal_net_demand_floor_v1":
        raise ValueError("legal plans must not be labelled as the historical original-plan criterion")
    if metadata.get("reference_price_rule") not in {"max_age", "event_state_same_am_v1"}:
        raise ValueError("save the actual reference-price rule before publication")
    if not metadata.get("rule_version"):
        raise ValueError("save the financial rule version before publication")
    check_metadata(metadata)
    required = [Path(name) for name in ("main.pdf", "main.tex", "README.md", "data/report_metadata.json",
                                      "data/trial_summary.csv", "data/capacity_summary.csv")]
    for relative in required:
        if not (source/relative).is_file():
            raise FileNotFoundError(source/relative)
    selected = set(required)
    for stem, columns in PUBLIC_COLUMNS.items():
        relative = Path("data")/(stem+".csv")
        path = source/relative
        if path.is_file():
            with path.open(newline="") as stream:
                header = next(csv.reader(stream), [])
            unexpected = set(header)-set(columns.split())
            if unexpected:
                raise ValueError(f"{relative} has non-public columns: {sorted(unexpected)}")
            selected.add(relative)
    for stem in PUBLIC_FIGURES:
        for extension in ("pdf", "png"):
            relative = Path("figures")/(stem+"."+extension)
            if (source/relative).is_file():
                selected.add(relative)
    return source, metadata, sorted(selected)


def publish(source, destination, role, *, dry_run=False):
    if role not in ROLES:
        raise ValueError("unknown publication role")
    source, metadata, selected = select_public_files(source)
    destination = Path(destination).resolve()
    archive_path = destination.with_name(destination.name+"_tex_bundle.zip")
    if destination.exists() or archive_path.exists():
        raise FileExistsError("use a new publication directory; existing reports are preserved")
    receipt = {"role": role, "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "rule_version": metadata["rule_version"], "reference_price_rule": metadata["reference_price_rule"],
        "source_results_generated_at_utc": metadata.get("source_results_generated_at_utc"),
        "report_generated_at_utc": metadata.get("generated_at_utc"),
        "observed_trials": metadata.get("observed_trials"), "financial_accounts_recomputed": False,
        "historical_results_are_new_capacity": False if role == "historical_baseline" else None,
        "files": [str(path) for path in selected]}
    if dry_run:
        return receipt
    destination.mkdir(parents=True)
    for relative in selected:
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/relative, target)
    (destination/"publication.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n")
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for relative in [*selected, Path("publication.json")]:
            archive.write(destination/relative, Path(destination.name)/relative)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=ROLES, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args.name):
        parser.error("name must contain only lowercase letters, numbers, underscores or hyphens")
    result = publish(args.source, Path(__file__).resolve().parent/args.name, args.role, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
