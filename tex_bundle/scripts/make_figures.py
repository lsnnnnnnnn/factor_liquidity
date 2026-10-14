#!/usr/bin/env python3
"""Render the five report figures offline from the included aggregate CSV files."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter, MultipleLocator
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


NAVY, TEAL, AMBER = "#274158", "#167C86", "#B97A2B"
INK, MUTED, GRID, PAPER = "#263D4D", "#637784", "#DFE5E7", "#FAFBF9"
COLORS = {.05: AMBER, .1: TEAL, .2: NAVY}
CAPITALS = [1e6, 3e6, 1e7, 3e7, 1e8]
CAPITAL_LABELS = ["100", "300", "1,000", "3,000", "10,000"]


def setup(font: Path | None) -> None:
    if font is None and shutil.which("kpsewhich"):
        found = subprocess.run(["kpsewhich", "FandolHei-Regular.otf"], capture_output=True, text=True, check=True).stdout.strip()
        if found:
            font = Path(found)
    if font is not None:
        font_manager.fontManager.addfont(str(font))
        family = font_manager.FontProperties(fname=str(font)).get_name()
    else:
        available = {item.name for item in font_manager.fontManager.ttflist}
        family = next((name for name in ["Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", "PingFang SC", "Heiti SC", "Arial Unicode MS"] if name in available), None)
        if family is None:
            raise RuntimeError("No Chinese font found. Install Fandol/Noto Sans CJK or pass --font /path/to/font.")
    resolved_font = font or Path(font_manager.findfont(font_manager.FontProperties(family=family)))
    vector_fonttype = 3 if resolved_font.suffix.lower() in {".otf", ".ttc"} else 42
    plt.rcParams.update({
        "font.family": family, "font.size": 9, "axes.titlesize": 10,
        "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.labelcolor": INK, "text.color": INK, "xtick.color": MUTED,
        "ytick.color": MUTED, "axes.edgecolor": GRID,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.linewidth": .6,
        "axes.facecolor": PAPER, "figure.facecolor": PAPER,
        "grid.color": GRID, "grid.linewidth": .6,
        "lines.linewidth": 1.7, "lines.markersize": 4,
        "legend.fontsize": 8, "legend.frameon": False,
        # Fandol OTF uses CFF outlines. Type 3 stores its glyphs as vector paths;
        # advertising those bytes as a TrueType FontFile2 breaks some PDF readers.
        "pdf.fonttype": vector_fonttype, "ps.fonttype": vector_fonttype,
        "axes.unicode_minus": False, "savefig.dpi": 220,
    })


def panels(widths=(1, 1)):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.72), gridspec_kw={"width_ratios": widths})
    fig.subplots_adjust(left=.105, right=.985, bottom=.255, top=.83, wspace=.37)
    for ax in axes:
        ax.set_axisbelow(True)
        ax.grid(axis="y")
        ax.tick_params(axis="both", length=0, pad=4)
    return fig, axes


def capital_axis(ax):
    ax.set_xticks(range(5), CAPITAL_LABELS)
    ax.set_xlabel("初始资金（万元）", labelpad=8)
    ax.set_xlim(-.2, 4.2)


def subtitle(ax, label):
    ax.set_title(label, loc="left", pad=11, fontweight="normal")


def save(fig, output: Path, name: str) -> None:
    # Fixed dimensions allow report text to use a stable, readable layout.
    for suffix in ["pdf", "png"]:
        fig.savefig(output / f"{name}.{suffix}")
    plt.close(fig)


def synthetic_figure(data, output):
    frame = pd.read_csv(data / "synthetic_summary.csv")
    constrained = frame[(frame.group == "constrained_net") & frame.participation_rate.eq(.1)].sort_values("initial_capital")
    reference = frame[frame.group.eq("reference_net")].sort_values("initial_capital")
    fig, (left, right) = panels()
    subtitle(left, "A  资金增大后，净收益下降")
    left.plot(range(5), reference.cumulative_return * 100, color=MUTED, ls="--", label="无参与率上限，含费用")
    left.plot(range(5), constrained.cumulative_return * 100, color=TEAL, marker="o", label="参与率 10%，含费用")
    left.set_ylabel("区间净收益率（%）")
    left.set_ylim(5.5, 10)
    left.yaxis.set_major_locator(MultipleLocator(1))
    first_return, last_return = constrained.cumulative_return.iloc[[0, -1]] * 100
    left.annotate(f"{first_return:.2f}%", (0, first_return), xytext=(0, 8), textcoords="offset points", ha="center", color=TEAL, fontsize=8)
    left.annotate(f"{last_return:.2f}%", (4, last_return), xytext=(-3, -13), textcoords="offset points", ha="right", color=TEAL, fontsize=8)
    capital_axis(left)
    subtitle(right, "B  资金增大后，成交比例下降")
    right.fill_between(range(5), constrained.fill_ratio_amount * 100, 100, color="#E9CFA7", alpha=.5)
    right.plot(range(5), constrained.fill_ratio_amount * 100, color=AMBER, marker="o")
    right.axhline(100, color=MUTED, ls="--", lw=1)
    right.set_ylabel("订单金额完成比例（%）")
    right.set_ylim(58, 104)
    right.yaxis.set_major_locator(MultipleLocator(10))
    for x, y in zip(range(5), constrained.fill_ratio_amount * 100):
        right.annotate(f"{y:.1f}", (x, y), xytext=(0, -13), textcoords="offset points", ha="center", color=AMBER, fontsize=8)
    capital_axis(right)
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.10, 1.01), ncol=2, columnspacing=1.7)
    fig.text(.105, .035, "固定种子 42 · 30 只模拟股票 · 80 个模拟交易日 · 最长执行 3 个交易日", color=MUTED, fontsize=8)
    save(fig, output, "01_synthetic")


def nav_figure(data, output):
    frame = pd.read_csv(data / "real_nav_100m.csv")
    diagnostics = pd.read_csv(data / "real_diagnostics.csv")
    fig, (left, right) = panels((2.5, 1))
    fig.subplots_adjust(left=.08, wspace=.3)
    subtitle(left, "A  1 亿元：持仓阶段净值下跌")
    left.axvspan(pd.Timestamp("2026-07-03"), pd.Timestamp("2026-08-03"), color=GRID, alpha=.65, lw=0)
    left.text(pd.Timestamp("2026-07-15"), 1.012, "21 个交易日预热", fontsize=8, color=MUTED, ha="center")
    for rate in [.05, .1, .2]:
        selected = frame[frame.group.eq("constrained_net") & frame.participation_rate.eq(rate)]
        left.plot(pd.to_datetime(selected.trade_date), selected.normalized_nav, color=COLORS[rate], label=f"参与率 {rate:.0%}")
    reference = frame[frame.group.eq("reference_net")]
    left.plot(pd.to_datetime(reference.trade_date), reference.normalized_nav, color=MUTED, ls="--", lw=1.15, label="无参与率上限，计费")
    left.axhline(1, color=GRID, lw=.8)
    left.set_ylabel("净值（初始值 = 1）")
    left.set_ylim(.945, 1.018)
    left.yaxis.set_major_locator(MultipleLocator(.02))
    left.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[3, 17]))
    left.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    left.set_xlim(pd.Timestamp("2026-07-03"), pd.Timestamp("2026-09-08"))
    left.annotate("期末均为负收益", (pd.Timestamp("2026-09-04"), .976), xytext=(-80, 15), textcoords="offset points", fontsize=8, color=MUTED, arrowprops={"arrowstyle": "-", "color": MUTED, "lw": .6})
    subtitle(right, "B  持仓阶段现金占比")
    chosen = diagnostics[diagnostics.initial_capital.eq(1e8) & diagnostics.group.eq("constrained_net")].sort_values("participation_rate")
    right.bar(range(3), chosen.active_bar_cash_ratio_mean * 100, color=[COLORS[rate] for rate in [.05, .1, .2]], width=.5)
    for i, value in enumerate(chosen.active_bar_cash_ratio_mean * 100):
        right.text(i, value + .05, f"{value:.2f}%", ha="center", fontsize=8)
    right.set_xticks(range(3), ["5%", "10%", "20%"])
    right.set_xlabel("参与率", labelpad=8)
    right.set_ylabel("每分钟现金占净资产的平均比例（%）")
    right.set_ylim(0, 1.5)
    right.yaxis.set_major_locator(MultipleLocator(.5))
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.075, 1.01), ncol=4, columnspacing=1.0, handlelength=1.7)
    fig.text(.08, .035, "08/03 起开始持仓；此前 21 个交易日用于计算因子，账户全部持有现金。", color=MUTED, fontsize=8)
    save(fig, output, "02_real_nav")


def returns_figure(data, output):
    frame = pd.read_csv(data / "real_summary.csv")
    fig, (left, right) = panels()
    subtitle(left, "A  全部场景的净收益为负")
    subtitle(right, "B  部分受限账户的亏损略少")
    reference = frame[frame.group.eq("reference_net")].sort_values("initial_capital")
    for rate in [.05, .1, .2]:
        selected = frame[frame.group.eq("constrained_net") & frame.participation_rate.eq(rate)].sort_values("initial_capital")
        left.plot(range(5), selected.cumulative_return * 100, marker="o", color=COLORS[rate], label=f"参与率 {rate:.0%}")
        right.plot(range(5), selected.return_gap_vs_reference_net * 1e4, marker="o", color=COLORS[rate])
    left.plot(range(5), reference.cumulative_return * 100, color=MUTED, ls="--", lw=1.15, label="无参与率上限，计费")
    left.set_ylabel("区间净收益率（%）")
    left.set_ylim(-2.52, -2.32)
    left.yaxis.set_major_locator(MultipleLocator(.05))
    right.set_ylabel("相比无上限计费场景的收益差（bp）")
    right.set_ylim(-.9, 12.9)
    right.yaxis.set_major_locator(MultipleLocator(4))
    right.axhline(0, color=MUTED, lw=.8, ls="--")
    right.text(.03, .91, "正值 = 限制成交后亏损较少", transform=right.transAxes, color=MUTED, fontsize=8)
    for ax in [left, right]:
        capital_axis(ax)
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.10, 1.01), ncol=4, columnspacing=1, handlelength=1.7)
    fig.text(.105, .035, "每组对比使用相同初始资金；1 bp = 0.01 个百分点。", color=MUTED, fontsize=8)
    save(fig, output, "03_real_returns")


def clock_figure(data, output):
    diagnostics = pd.read_csv(data / "real_diagnostics.csv")
    fig, (left, right) = panels()
    subtitle(left, "A  资金越大，平均成交用时越长")
    subtitle(right, "B  1 亿元：少数订单耗时更长")
    for rate in [.05, .1, .2]:
        selected = diagnostics[diagnostics.group.eq("constrained_net") & diagnostics.participation_rate.eq(rate)].sort_values("initial_capital")
        left.plot(range(5), selected.eligible_minutes_mean, color=COLORS[rate], marker="o", label=f"参与率 {rate:.0%}")
    left.set_ylim(0, 23)
    left.yaxis.set_major_locator(MultipleLocator(5))
    left.set_ylabel("平均成交用时（交易分钟）")
    capital_axis(left)
    selected = diagnostics[diagnostics.group.eq("constrained_net") & diagnostics.initial_capital.eq(1e8)].sort_values("participation_rate")
    for i, (_, row) in enumerate(selected.iterrows()):
        color = COLORS[row.participation_rate]
        values = [row.eligible_minutes_median, row.eligible_minutes_p90, row.eligible_minutes_max]
        right.plot([i, i, i], values, color=color, lw=1, alpha=.55)
        right.scatter(i, values[0], color=color, marker="o", s=24, zorder=3)
        right.scatter(i, values[1], color=color, marker="s", s=26, zorder=3)
        right.scatter(i, values[2], color=color, marker="^", s=35, zorder=3)
        for value, label in zip(values, [f"{values[0]:.0f}", f"{values[1]:.1f}", f"{values[2]:.0f}"]):
            right.annotate(label, (i, value), xytext=(7, 0), textcoords="offset points", va="center", fontsize=8, color=color)
    right.set_yscale("log")
    right.set_ylim(1, 2000)
    right.set_yticks([2, 10, 50, 200, 500], ["2", "10", "50", "200", "500"])
    right.set_xticks([0, 1, 2], ["5%", "10%", "20%"])
    right.set_xlim(-.35, 2.55)
    right.set_xlabel("参与率", labelpad=8)
    right.set_ylabel("成交用时（交易分钟，对数刻度）")
    right.text(.03, .98, "圆点 中位数 · 方点90% · 三角 最长", transform=right.transAxes, fontsize=6.8, color=MUTED, va="top")
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.10, 1.01), ncol=3, columnspacing=2)
    fig.text(.105, .055, "交易分钟不计周末、夜间、午休和不可执行的收盘竞价。", color=MUTED, fontsize=7.6)
    fig.text(.105, .018, "90%分位表示：90%的已完成订单不超过该用时。", color=MUTED, fontsize=7.6)
    save(fig, output, "05_real_clock")


def timeline_figure(data, output):
    frame = pd.read_csv(data / "order_example_cumulative.csv")
    fig, ax = plt.subplots(figsize=(6.5, 2.72))
    fig.subplots_adjust(left=.10, right=.98, bottom=.28, top=.83)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, lw=.6)
    ax.tick_params(length=0, pad=5)
    ax.axvspan(0, 237, color=GRID, alpha=.3, lw=0)
    ax.axvspan(474, 711, color=GRID, alpha=.3, lw=0)
    for rate in [.05, .1, .2]:
        selected = frame[frame.participation_rate.eq(rate)].sort_values("eligible_minute")
        final = selected.iloc[-1]
        ax.step(selected.eligible_minute, selected.completion * 100, where="post", color=COLORS[rate], label=f"参与率 {rate:.0%}")
        ax.plot([final.eligible_minute, 520], [100, 100], color=COLORS[rate], ls=":" if rate != .05 else "-", lw=1, alpha=.65)
        ax.scatter(final.eligible_minute, 100, color=COLORS[rate], s=20, zorder=5)
        ax.annotate(f"{int(final.eligible_minute)} 分钟", (final.eligible_minute, 100), xytext=(0, 8 if rate != .1 else -15), textcoords="offset points", ha="center", color=COLORS[rate], fontsize=8)
    for boundary in [237, 474]:
        ax.axvline(boundary, color=MUTED, lw=.7, ls="--")
    ax.text(118.5, 8, "08/03 周一", ha="center", fontsize=8, color=MUTED)
    ax.text(355.5, 8, "08/04 周二", ha="center", fontsize=8, color=MUTED)
    ax.text(496, 8, "08/05", ha="center", fontsize=8, color=MUTED)
    ax.set_xlim(0, 525)
    ax.set_ylim(0, 115)
    ax.set_xticks([0, 100, 200, 300, 400, 500])
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel("从开始执行起累计的交易分钟", labelpad=8)
    ax.set_ylabel("累计完成数量 / 下单数量（%）")
    ax.set_title("同一笔买单：5% 分 3 天完成，10% 和 20% 当天完成", loc="left", pad=12, fontsize=10)
    fig.legend(*ax.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.10, 1.01), ncol=3, columnspacing=2)
    fig.text(.10, .03, "O000004 · 000069.SZ · 买入 5,653,400 股（约 995 万元）· 07/31 下单 · 08/03 开始执行", fontsize=7.6, color=MUTED)
    save(fig, output, "06_order_timeline")


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=root / "data")
    parser.add_argument("--output", type=Path, default=root / "figures")
    parser.add_argument("--font", type=Path, help="Optional Chinese font file, e.g. FandolHei-Regular.otf")
    args = parser.parse_args()
    setup(args.font)
    args.output.mkdir(parents=True, exist_ok=True)
    for function in [synthetic_figure, nav_figure, returns_figure, clock_figure, timeline_figure]:
        function(args.data, args.output)
    print("Rendered 5 figures as vector PDF and 220 dpi PNG.")


if __name__ == "__main__":
    main()
