#!/usr/bin/env python3
"""Draw the execution update using public derived CSV files only."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from make_figures import AMBER, MUTED, NAVY, TEAL, date_axis, plt, setup


VARIANTS = ["baseline", "cumulative_only", "snapshot_only", "persistent_only", "szse_000_only", "main"]
LABELS = ["旧规则", "仅累计", "仅刷新", "仅余单保留", "仅卖余股", "新比较情景"]


def draw(data, output):
    groups = pd.read_csv(data/"fixed_rule_groups.csv")
    nav = pd.read_csv(data/"daily_nav_comparison.csv", dtype={"trade_date": str})
    required = {"variant", "classification", "remaining_reference_notional"}
    if not required.issubset(groups):
        raise ValueError("固定对照缺少 variant/classification/remaining_reference_notional")
    material = groups.loc[groups.classification.eq("ordinary_material_residual")].copy()
    if material.variant.duplicated().any() or set(material.variant) != set(VARIANTS):
        raise ValueError("14 笔较大余量固定母单必须保留全部六种规则，且每种只能有一行")
    material = material.set_index("variant").loc[VARIANTS]
    if "orders" in material and not material.orders.eq(14).all():
        raise ValueError("左图必须固定同一批 14 笔较大余量母单")
    amounts = material.remaining_reference_notional.to_numpy(dtype=float)/10_000
    if not np.isfinite(amounts).all() or (amounts < 0).any():
        raise ValueError("剩余参考金额必须有限且非负，源数据单位为元")
    columns = ["old_p0.1", "new_p0.1", "reference"]
    if not {"trade_date", *columns}.issubset(nav):
        raise ValueError("连续净值缺少旧、新 10% 参与率或参考假设账户")
    if (len(nav) != 26 or nav.trade_date.duplicated().any() or not nav.trade_date.is_monotonic_increasing
            or nav.trade_date.iloc[0] != "2026-07-31" or nav.trade_date.iloc[-1] != "2026-09-04"):
        raise ValueError("右图必须完整保留 2026-07-31 至 09-04 的 26 个连续观察交易日")
    values = nav[columns].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any() or not np.allclose(values[0], 1):
        raise ValueError("连续净值必须有限、正值，且双方与参考账户均从 1 开始")

    fig, (left, right) = plt.subplots(1, 2, figsize=(6.5, 3.35))
    fig.subplots_adjust(left=.13, right=.985, bottom=.28, top=.82, wspace=.48)
    for ax in [left, right]:
        ax.set_axisbelow(True)
        ax.tick_params(length=0, pad=4)
    positions = np.arange(len(VARIANTS))
    left.grid(axis="x")
    left.barh(positions, amounts, height=.61, color=[NAVY, MUTED, MUTED, MUTED, MUTED, TEAL])
    left.set_yticks(positions, LABELS)
    left.invert_yaxis()
    left.set_xlim(0, max(float(amounts.max())*1.24, 1.))
    left.set_xlabel("剩余参考金额（万元）", labelpad=7)
    left.set_title("A  固定 14 笔较大余量母单", loc="left", pad=11)
    for position, amount in zip(positions, amounts):
        left.annotate(f"{amount:,.1f}", (amount, position), xytext=(4, 0),
                      textcoords="offset points", va="center", fontsize=7)

    right.grid(axis="y")
    for column, label, color, style in [
        ("old_p0.1", "旧规则 · 10%", AMBER, "-"),
        ("new_p0.1", "新比较情景 · 10%", TEAL, "-"),
        ("reference", "按参考价全成假设", MUTED, "--"),
    ]:
        right.plot(np.arange(len(nav)), nav[column], label=label, color=color, ls=style)
    right.axhline(1, color=MUTED, lw=.6)
    right.set_title("B  连续 26 个交易日", loc="left", pad=11)
    right.set_ylabel("净值（初始资金 = 1）")
    date_axis(right, nav.trade_date.tolist(), every=5)
    right.legend(loc="lower left", fontsize=6.5)
    fig.text(.13, .11, "左：固定券单只改规则；右：按各账户净资产与持仓重算后续券单。", color=MUTED, fontsize=6.8)
    fig.text(.13, .055, "快照刷新仅为比较假设；参考价全成账户是假设，并非原回测执行。", color=MUTED, fontsize=6.8)
    output.mkdir(parents=True, exist_ok=True)
    for suffix in ["pdf", "png"]:
        fig.savefig(output/f"05_execution_update.{suffix}")
    plt.close(fig)


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=root/"data/execution_update")
    parser.add_argument("--output", type=Path, default=root/"figures")
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    setup(args.font)
    draw(args.data, args.output)
    print("已从公开派生 CSV 生成 05_execution_update.pdf/png；固定券单与连续账户分图说明。")


if __name__ == "__main__":
    main()
