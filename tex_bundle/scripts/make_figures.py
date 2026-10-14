#!/usr/bin/env python3
"""Render the six report figures offline from the included aggregate CSV files."""
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
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.12), gridspec_kw={"width_ratios": widths})
    fig.subplots_adjust(left=.105, right=.985, bottom=.21, top=.83, wspace=.37)
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
    subtitle(left, "A  同一策略，资金越大执行越困难")
    left.plot(range(5), reference.cumulative_return * 100, color=MUTED, ls="--", label="无参与率上限，含费用")
    left.plot(range(5), constrained.cumulative_return * 100, color=TEAL, marker="o", label="参与率 10%，含费用")
    left.set_ylabel("区间净收益率（%）")
    left.set_ylim(5.5, 10)
    left.yaxis.set_major_locator(MultipleLocator(1))
    first_return, last_return = constrained.cumulative_return.iloc[[0, -1]] * 100
    left.annotate(f"{first_return:.2f}%", (0, first_return), xytext=(0, 8), textcoords="offset points", ha="center", color=TEAL, fontsize=8)
    left.annotate(f"{last_return:.2f}%", (4, last_return), xytext=(-3, -13), textcoords="offset points", ha="right", color=TEAL, fontsize=8)
    capital_axis(left)
    subtitle(right, "B  执行约束改变需求完成程度")
    right.fill_between(range(5), constrained.fill_ratio_amount * 100, 100, color="#E9CFA7", alpha=.5)
    right.plot(range(5), constrained.fill_ratio_amount * 100, color=AMBER, marker="o")
    right.axhline(100, color=MUTED, ls="--", lw=1)
    right.set_ylabel("金额完成率（%）")
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
    subtitle(left, "A  一亿元场景：预热之后，净值经历回撤")
    left.axvspan(pd.Timestamp("2026-07-03"), pd.Timestamp("2026-08-03"), color=GRID, alpha=.65, lw=0)
    left.text(pd.Timestamp("2026-07-15"), 1.012, "21 个交易日预热", fontsize=8, color=MUTED, ha="center")
    for rate in [.05, .1, .2]:
        selected = frame[frame.group.eq("constrained_net") & frame.participation_rate.eq(rate)]
        left.plot(pd.to_datetime(selected.trade_date), selected.normalized_nav, color=COLORS[rate], label=f"参与率 {rate:.0%}")
    reference = frame[frame.group.eq("reference_net")]
    left.plot(pd.to_datetime(reference.trade_date), reference.normalized_nav, color=MUTED, ls="--", lw=1.15, label="无参与率上限")
    left.axhline(1, color=GRID, lw=.8)
    left.set_ylabel("净值（初始值 = 1）")
    left.set_ylim(.945, 1.018)
    left.yaxis.set_major_locator(MultipleLocator(.02))
    left.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[3, 17]))
    left.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    left.set_xlim(pd.Timestamp("2026-07-03"), pd.Timestamp("2026-09-08"))
    left.annotate("期末均为负收益", (pd.Timestamp("2026-09-04"), .976), xytext=(-80, 15), textcoords="offset points", fontsize=8, color=MUTED, arrowprops={"arrowstyle": "-", "color": MUTED, "lw": .6})
    subtitle(right, "B  持仓阶段的现金")
    chosen = diagnostics[diagnostics.initial_capital.eq(1e8) & diagnostics.group.eq("constrained_net")].sort_values("participation_rate")
    right.bar(range(3), chosen.active_bar_cash_ratio_mean * 100, color=[COLORS[rate] for rate in [.05, .1, .2]], width=.5)
    for i, value in enumerate(chosen.active_bar_cash_ratio_mean * 100):
        right.text(i, value + .05, f"{value:.2f}%", ha="center", fontsize=8)
    right.set_xticks(range(3), ["5%", "10%", "20%"])
    right.set_xlabel("参与率", labelpad=8)
    right.set_ylabel("每根 bar 后现金比例均值（%）")
    right.set_ylim(0, 1.5)
    right.yaxis.set_major_locator(MultipleLocator(.5))
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.075, 1.01), ncol=4, columnspacing=1.0, handlelength=1.7)
    fig.text(.08, .035, "持仓阶段从 08/03 起；全样本约 46% 的平均现金主要来自前段全现金预热。", color=MUTED, fontsize=8)
    save(fig, output, "02_real_nav")


def returns_figure(data, output):
    frame = pd.read_csv(data / "real_summary.csv")
    fig, (left, right) = panels()
    subtitle(left, "A  绝对收益：全部场景均亏损")
    subtitle(right, "B  收益差：执行路径会改变盈亏")
    reference = frame[frame.group.eq("reference_net")].sort_values("initial_capital")
    for rate in [.05, .1, .2]:
        selected = frame[frame.group.eq("constrained_net") & frame.participation_rate.eq(rate)].sort_values("initial_capital")
        left.plot(range(5), selected.cumulative_return * 100, marker="o", color=COLORS[rate], label=f"参与率 {rate:.0%}")
        right.plot(range(5), selected.return_gap_vs_reference_net * 1e4, marker="o", color=COLORS[rate])
    left.plot(range(5), reference.cumulative_return * 100, color=MUTED, ls="--", lw=1.15, label="无参与率上限")
    left.set_ylabel("区间净收益率（%）")
    left.set_ylim(-2.52, -2.32)
    left.yaxis.set_major_locator(MultipleLocator(.05))
    right.set_ylabel("相对同资金净参考的收益差（bp）")
    right.set_ylim(-.9, 12.9)
    right.yaxis.set_major_locator(MultipleLocator(4))
    right.axhline(0, color=MUTED, lw=.8, ls="--")
    right.text(.03, .91, "正值 = 本路径亏损较少", transform=right.transAxes, color=MUTED, fontsize=8)
    for ax in [left, right]:
        capital_axis(ax)
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.10, 1.01), ncol=4, columnspacing=1, handlelength=1.7)
    fig.text(.105, .035, "1 bp = 0.01 个百分点；本样本没有足够证据确定最优参与率。", color=MUTED, fontsize=8)
    save(fig, output, "03_real_returns")


def completion_figure(data, output):
    diagnostics = pd.read_csv(data / "real_diagnostics.csv")
    chosen = diagnostics[diagnostics.group.eq("constrained_net") & diagnostics.participation_rate.eq(.1)].sort_values("initial_capital")
    fig, (left, right) = panels((1.4, 1))
    subtitle(left, "A  两种完成率回答不同的问题")
    x = np.arange(5)
    left.bar(x - .16, chosen.all_amount_completion * 100, width=.29, color=AMBER, label="全部订单")
    left.bar(x + .16, chosen.mature_amount_completion * 100, width=.29, color=TEAL, label="执行窗口已完整观察")
    for position, value in zip(x, chosen.all_amount_completion * 100):
        left.text(position - .16, value + 1.4, f"{value:.1f}", ha="center", fontsize=7.5, color=AMBER)
    left.set_ylim(0, 111)
    left.yaxis.set_major_locator(MultipleLocator(25))
    left.set_ylabel("金额完成率（%）")
    capital_axis(left)
    subtitle(right, "B  一亿元：末日截断需求")
    completed_share = chosen.iloc[-1].all_amount_completion * 100
    censored_share = chosen.iloc[-1].censored_amount_share * 100
    right.barh([0], [completed_share], color=TEAL, height=.27)
    right.barh([0], [censored_share], left=[completed_share], color=AMBER, height=.27)
    right.text(45, .0, f"已成交 {completed_share:.2f}%", ha="center", va="center", color="white", fontsize=8)
    right.annotate(f"期末截断 {censored_share:.2f}%", (94, .13), xytext=(.45, .8), textcoords="axes fraction", ha="center", fontsize=8, color=AMBER, arrowprops={"arrowstyle": "-", "color": AMBER, "lw": .7})
    right.text(.05, .34, "09/04 收盘才产生\n没有后续可执行 bar\n11 笔订单尚未激活", transform=right.transAxes, fontsize=8, color=MUTED, linespacing=1.6, va="top")
    right.set_xlim(0, 100)
    right.set_ylim(-.65, .6)
    right.set_yticks([])
    right.set_xticks([0, 50, 100])
    right.set_xlabel("下单参考金额占比（%）", labelpad=8)
    right.grid(False)
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.10, 1.01), ncol=2, columnspacing=2)
    fig.text(.105, .035, "参与率 10%；完整观察订单均完成，不能把样本末端截断的需求解释为容量失败。", color=MUTED, fontsize=8)
    save(fig, output, "04_real_completion")


def clock_figure(data, output):
    diagnostics = pd.read_csv(data / "real_diagnostics.csv")
    fig, (left, right) = panels()
    subtitle(left, "A  平均执行时间随资金增加")
    subtitle(right, "B  一亿元：少数订单形成长尾")
    for rate in [.05, .1, .2]:
        selected = diagnostics[diagnostics.group.eq("constrained_net") & diagnostics.participation_rate.eq(rate)].sort_values("initial_capital")
        left.plot(range(5), selected.eligible_minutes_mean, color=COLORS[rate], marker="o", label=f"参与率 {rate:.0%}")
    left.set_ylim(0, 23)
    left.yaxis.set_major_locator(MultipleLocator(5))
    left.set_ylabel("已完成订单的平均可执行分钟")
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
    right.set_ylabel("可执行分钟（对数刻度）")
    right.text(.03, .98, "圆点 中位数 · 方点 P90 · 三角 最大", transform=right.transAxes, fontsize=7, color=MUTED, va="top")
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.10, 1.01), ncol=3, columnspacing=2)
    fig.text(.105, .035, "周五 15:00 提交至周一 09:30 等待 66.5 小时；可执行分钟不累计周末、午休和夜间。", color=MUTED, fontsize=7.6)
    save(fig, output, "05_real_clock")


def timeline_figure(data, output):
    frame = pd.read_csv(data / "order_example_cumulative.csv")
    fig, ax = plt.subplots(figsize=(6.5, 3.12))
    fig.subplots_adjust(left=.10, right=.98, bottom=.24, top=.83)
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
    ax.set_xlabel("从首次激活起累计的模型可执行分钟", labelpad=8)
    ax.set_ylabel("累计完成数量 / 下单数量（%）")
    ax.set_title("一笔约 995 万元买单：同一目标，不同参与率下的跨日成交路径", loc="left", pad=12, fontsize=10)
    fig.legend(*ax.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.10, 1.01), ncol=3, columnspacing=2)
    fig.text(.10, .03, "O000004 · 000069.SZ · 买入 5,653,400 股 · 07/31 收盘提交 · 08/03 09:30 激活", fontsize=8, color=MUTED)
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
    for function in [synthetic_figure, nav_figure, returns_figure, completion_figure, clock_figure, timeline_figure]:
        function(args.data, args.output)
    print("Rendered 6 figures as vector PDF and 220 dpi PNG.")


if __name__ == "__main__":
    main()
