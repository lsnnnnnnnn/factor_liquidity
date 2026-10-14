#!/usr/bin/env python3
"""Extract publishable aggregates from existing, locally held backtest outputs.

No raw market bars, account ledgers, credentials or machine paths are exported.
Trading minutes count observed, model-eligible one-minute bars for an instrument
with activated_at < bar_end <= last_fill_at. Opening auction is already absent
from replay bars; auction_excluded closing bars are removed here as well.
This clock includes eligible bars with no fill; it is not an exchange queue model.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SUMMARY_COLUMNS = [
    "initial_capital", "participation_rate", "group", "max_execution_sessions",
    "sample_sessions", "sample_start", "sample_end", "cumulative_return",
    "max_drawdown", "fees", "total_orders", "filled_orders", "uncompleted_orders",
    "order_reference_amount", "filled_reference_amount", "fill_ratio_amount",
    "uncompleted_ratio", "mean_completion_delay_hours", "max_completion_delay_hours",
    "average_cash_ratio", "return_gap_vs_reference_net",
]


def scenario_dir(row: pd.Series, root: Path) -> Path:
    rate = "off" if pd.isna(row.participation_rate) else f"{row.participation_rate:g}"
    return root / f"{row.group}_capital{row.initial_capital:g}_p{rate}"


def timestamps(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, utc=True).dt.tz_convert("Asia/Shanghai")


def extract(synthetic: Path, real: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for label, source in [("synthetic", synthetic), ("real", real)]:
        pd.read_csv(source / "summary.csv")[SUMMARY_COLUMNS].to_csv(
            destination / f"{label}_summary.csv", index=False
        )
    summary = pd.read_csv(real / "summary.csv")
    bars = pd.read_parquet(real / "company_replay_bars.parquet", columns=[
        "instrument", "bar_end", "execution_block_reason",
    ])
    bars = bars[bars.execution_block_reason.ne("auction_excluded")]
    grids = {code: frame.bar_end.sort_values() for code, frame in bars.groupby("instrument")}
    clocks, order_clocks, navs, timeline = [], [], [], []
    for _, row in summary.iterrows():
        folder = scenario_dir(row, real)
        orders = pd.read_csv(folder / "orders.csv")
        daily = pd.read_csv(folder / "daily_nav.csv")
        intraday = pd.read_csv(folder / "nav.csv", usecols=["trade_date", "cash_ratio"])
        last_session = int(row.sample_sessions) - 1
        mature = orders.first_session.notna() & orders.deadline_session.le(last_session)
        censored = ~mature
        complete = mature & orders.completion_ratio.ge(1.0 - 1e-12)
        durations = []
        for _, order in orders[complete].iterrows():
            grid = grids[order.instrument]
            activation = pd.Timestamp(order.activated_at)
            last_fill = pd.Timestamp(order.last_fill_at)
            minutes = int(((grid > activation) & (grid <= last_fill)).sum())
            durations.append(minutes)
            order_clocks.append({
                "initial_capital": row.initial_capital,
                "participation_rate": row.participation_rate,
                "group": row.group,
                "eligible_minutes": minutes,
                "elapsed_hours": order.completion_delay_hours,
            })
        references = orders.quantity * orders.reference_price
        filled_references = orders.filled_quantity * orders.reference_price
        active_daily = daily[daily.trade_date.ge("2026-08-03")]
        clocks.append({
            "initial_capital": row.initial_capital,
            "participation_rate": row.participation_rate,
            "group": row.group,
            "all_order_count": len(orders), "mature_order_count": int(mature.sum()),
            "mature_completed_count": int(complete.sum()),
            "censored_order_count": int(censored.sum()),
            "all_amount_completion": filled_references.sum() / references.sum(),
            "mature_amount_completion": filled_references[mature].sum() / references[mature].sum(),
            "censored_amount_share": references[censored].sum() / references.sum(),
            "eligible_minutes_mean": np.mean(durations),
            "eligible_minutes_median": np.median(durations),
            "eligible_minutes_p90": np.quantile(durations, .9),
            "eligible_minutes_p95": np.quantile(durations, .95),
            "eligible_minutes_max": max(durations),
            "elapsed_hours_mean": orders.loc[complete, "completion_delay_hours"].mean(),
            "active_daily_cash_ratio_mean": active_daily.cash_ratio.mean(),
            "all_daily_cash_ratio_mean": daily.cash_ratio.mean(),
            "active_bar_cash_ratio_mean": intraday.loc[intraday.trade_date.ge("2026-08-03"), "cash_ratio"].mean(),
            "all_bar_cash_ratio_mean": intraday.cash_ratio.mean(),
        })
        # Verify the specific boundary issue, rather than labeling all residuals capacity failures.
        assert orders.loc[censored, "reason"].eq("sample_end").all()
        assert orders.loc[censored, "first_session"].isna().all()
        assert timestamps(orders.loc[censored, "submitted_at"]).dt.strftime("%Y-%m-%d %H:%M").eq("2026-09-04 15:00").all()
        assert orders.loc[mature, "completion_ratio"].eq(1.0).all()
        if row.initial_capital == 100_000_000 and row.group != "reference_gross":
            nav = daily[["trade_date", "nav", "cash_ratio"]].copy()
            nav["normalized_nav"] = nav.nav / row.initial_capital
            nav = nav.drop(columns="nav")
            nav["participation_rate"] = row.participation_rate
            nav["group"] = row.group
            navs.append(nav)
        if row.initial_capital == 100_000_000 and row.group == "constrained_net":
            order = orders[orders.order_id.eq("O000004")].iloc[0]
            fills = pd.read_csv(folder / "fills.csv")
            fills = fills[fills.order_id.eq("O000004")].copy()
            fills["bar_end"] = timestamps(fills.bar_end)
            fills = fills.sort_values("bar_end")
            grid = grids[order.instrument]
            grid = grid[grid > pd.Timestamp(order.activated_at)]
            cumulative = fills.quantity.cumsum()
            timeline.append({
                "participation_rate": row.participation_rate, "eligible_minute": 0,
                "date": "2026-08-03", "completion": 0,
                "quantity": order.quantity, "reference_price": order.reference_price,
            })
            for (_, fill), quantity in zip(fills.iterrows(), cumulative):
                timeline.append({
                    "participation_rate": row.participation_rate,
                    "eligible_minute": int((grid <= fill.bar_end).sum()),
                    "date": fill.bar_end.strftime("%Y-%m-%d"),
                    "completion": quantity / order.quantity,
                    "quantity": order.quantity, "reference_price": order.reference_price,
                })
    pd.DataFrame(clocks).to_csv(destination / "real_diagnostics.csv", index=False)
    pd.DataFrame(order_clocks).to_csv(destination / "real_completed_order_clocks.csv", index=False)
    pd.concat(navs, ignore_index=True).to_csv(destination / "real_nav_100m.csv", index=False)
    pd.DataFrame(timeline).to_csv(destination / "order_example_cumulative.csv", index=False)
    diagnostics = pd.DataFrame(clocks)
    for rate, expected_mean, expected_max in [(.05, 19.9811320754717, 492), (.1, 9.73584905660377, 226), (.2, 4.0566037735849, 52)]:
        actual = diagnostics[(diagnostics.group == "constrained_net") & (diagnostics.initial_capital == 1e8) & (diagnostics.participation_rate == rate)].iloc[0]
        assert np.isclose(actual.eligible_minutes_mean, expected_mean)
        assert actual.eligible_minutes_max == expected_max
    print(f"Saved 6 aggregate CSV files to {destination}; 25 real scenarios and execution clocks verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", type=Path, required=True, help="Existing synthetic output directory")
    parser.add_argument("--real", type=Path, required=True, help="Existing real output directory")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()
    extract(args.synthetic, args.real, args.output)
