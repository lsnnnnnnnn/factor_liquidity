"""Render matched-account charts from an existing comparison output directory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

import matplotlib
matplotlib.use("Agg")
from matplotlib import dates as mdates, font_manager, pyplot as plt
import numpy as np
import pandas as pd


NAVY, TEAL, AMBER = "#274158", "#167C86", "#B97A2B"
INK, MUTED, GRID, PAPER = "#263D4D", "#637784", "#DFE5E7", "#FAFBF9"


def setup(font: Path | None = None) -> None:
    if font is None and shutil.which("kpsewhich"):
        found = subprocess.run(["kpsewhich", "FandolHei-Regular.otf"], capture_output=True,
                               text=True, check=True).stdout.strip()
        font = Path(found) if found else None
    if font is not None:
        font_manager.fontManager.addfont(str(font))
        family = font_manager.FontProperties(fname=str(font)).get_name()
    else:
        available = {item.name for item in font_manager.fontManager.ttflist}
        family = next((name for name in ["Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei",
                                        "PingFang SC", "Heiti SC", "Arial Unicode MS"] if name in available), None)
        if family is None:
            raise ValueError("需要中文字体；安装 Fandol/Noto Sans CJK 或用 --font 指定字体文件")
        font = Path(font_manager.findfont(font_manager.FontProperties(family=family)))
    # CFF outlines must remain vector paths; they are not TrueType FontFile2 data.
    fonttype = 3 if font.suffix.lower() in {".otf", ".ttc"} else 42
    plt.rcParams.update({"font.family": family, "font.size": 8, "axes.titlesize": 9.5,
                         "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
                         "text.color": INK, "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.edgecolor": GRID, "axes.linewidth": .6,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.spines.left": False, "axes.facecolor": PAPER,
                         "figure.facecolor": PAPER, "grid.color": GRID, "grid.linewidth": .6,
                         "lines.linewidth": 1.7, "lines.markersize": 4,
                         "legend.frameon": False, "legend.fontsize": 7.5,
                         "axes.unicode_minus": False, "pdf.fonttype": fonttype,
                         "ps.fonttype": fonttype, "savefig.dpi": 220})


def panels(widths=(1, 1)):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.2), gridspec_kw={"width_ratios": widths})
    fig.subplots_adjust(left=.095, right=.985, bottom=.28, top=.78, wspace=.40)
    for ax in axes:
        ax.set_axisbelow(True)
        ax.grid(axis="y")
        ax.tick_params(length=0, pad=4)
    return fig, axes


def capital_axis(ax, capitals):
    labels = [f"{capital / 1e4:,.3f}".rstrip("0").rstrip(".") for capital in capitals]
    ax.set_xticks(range(len(capitals)), labels)
    ax.set_xlim(-.25, len(capitals) - .75)
    ax.set_xlabel("初始资金（万元）", labelpad=7)


def save(fig, output, name, source, note):
    fig.text(.095, .105, note, fontsize=7.2, color=MUTED)
    fig.text(.095, .045, source, fontsize=7, color=MUTED)
    for suffix in ["pdf", "png"]:
        fig.savefig(output / f"{name}.{suffix}")
    plt.close(fig)
    return [f"{name}.pdf", f"{name}.png"]


def _read(output, name, columns):
    frame = pd.read_csv(output / name)
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{name} 缺少字段：{', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError(f"{name} 没有可画记录")
    return frame


def _rate(frame, rate):
    return frame.loc[np.isclose(frame.participation_rate, rate, equal_nan=False)]


def nav_chart(frame, output, capital, sample_label):
    selected = frame.loc[frame.initial_capital.eq(capital)]
    benchmark = selected.loc[selected.strategy.eq("equal_weight")].sort_values("trade_date")
    reference = selected.loc[selected.strategy.eq("momentum") & selected.group.eq("reference_net")].sort_values("trade_date")
    constrained = _rate(selected.loc[selected.group.eq("constrained_net")], .1).sort_values("trade_date")
    if benchmark.empty or reference.empty or constrained.empty:
        raise ValueError("最大资金净值图需要等权基准、动量净参考及 10% 参与率场景")
    fig, (left, right) = panels((1.6, 1))
    lines = [(benchmark, "股票池等权", NAVY, "--"), (reference, "动量净参考", AMBER, "-"),
             (constrained, "动量参与率 10%", TEAL, "-")]
    for data, label, color, style in lines:
        left.plot(pd.to_datetime(data.trade_date), data.normalized_nav, label=label, color=color, ls=style)
        if label != "股票池等权":
            right.plot(pd.to_datetime(data.trade_date), data.return_gap_vs_benchmark_pp, color=color, ls=style)
    left.set_title(f"A  最大资金：{capital / 1e4:,.0f} 万元", loc="left", pad=12)
    right.set_title("B  相对等权基准", loc="left", pad=12)
    left.set_ylabel("账户净值（初始值 = 1）")
    right.set_ylabel("累计收益差（百分点）")
    right.axhline(0, color=MUTED, ls="--", lw=.9)
    for ax in [left, right]:
        locator = mdates.AutoDateLocator(minticks=3, maxticks=4)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.set_xlabel("交易日期（月/日）", labelpad=7)
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.09, .99), ncol=3,
               columnspacing=1.7, handlelength=2)
    return save(fig, output, "comparison_01_nav",
                "来源：nav_comparison.csv；样本说明：study_manifest.json",
                f"{sample_label}；全部组合计费，动量净参考和等权基准不设参与率上限。")


def return_chart(frame, output, capitals, rates, colors, sample_label):
    fig, (left, right) = panels()
    for rate in rates:
        selected = _rate(frame.loc[frame.group.eq("constrained_net")], rate).set_index("initial_capital").reindex(capitals)
        left.plot(range(len(capitals)), selected.cumulative_return * 100, marker="o", color=colors[rate], label=f"参与率 {rate:.0%}")
        right.plot(range(len(capitals)), selected.return_gap_vs_momentum_reference_net_pp, marker="o", color=colors[rate])
    for group, label, color, style in [("equal_weight_net", "股票池等权", MUTED, "--"),
                                        ("reference_net", "动量净参考", INK, ":")]:
        selected = frame.loc[frame.group.eq(group)].set_index("initial_capital").reindex(capitals)
        left.plot(range(len(capitals)), selected.cumulative_return * 100, color=color, ls=style, lw=1.3, label=label)
    left.set_title("A  期末净收益", loc="left", pad=12)
    right.set_title("B  相对动量净参考", loc="left", pad=12)
    left.set_ylabel("累计净收益率（%）")
    right.set_ylabel("累计收益差（百分点）")
    right.axhline(0, color=MUTED, ls="--", lw=.9)
    for ax in [left, right]:
        capital_axis(ax, capitals)
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.09, 1), ncol=3,
               columnspacing=1.8, handlelength=2)
    return save(fig, output, "comparison_02_returns",
                "来源：comparison_summary.csv；样本说明：study_manifest.json",
                f"{sample_label}；相对收益使用相同资金的计费组合比较，正值表示收益更高。")


def execution_chart(summary, orders, output, capitals, rates, colors, sample_label):
    fig, (left, right) = panels()
    fig.subplots_adjust(bottom=.33)
    for rate in rates:
        selected = _rate(summary.loc[summary.group.eq("constrained_net")], rate).set_index("initial_capital").reindex(capitals)
        left.plot(range(len(capitals)), selected.complete_window_fill_ratio_amount * 100,
                  marker="o", color=colors[rate], label=f"参与率 {rate:.0%}")
    left.axhline(100, color=MUTED, ls="--", lw=.9)
    left.set_ylim(0, 106)
    left.set_ylabel("订单参考金额完成比例（%）")
    left.set_title("A  完整观察订单的成交比例", loc="left", pad=12)
    capital_axis(left, capitals)

    full = orders.full_execution_window_observed.astype(str).str.lower().map({"true": True, "false": False})
    if full.isna().any():
        raise ValueError("full_execution_window_observed 只能是 True 或 False")
    selected = orders.loc[orders.group.eq("constrained_net") & orders.initial_capital.eq(max(capitals)) & full]
    labels, observed_counts, completed_counts, values = [], [], [], []
    for x, rate in enumerate(rates):
        rows = _rate(selected, rate)
        completed = rows.loc[rows.remaining_quantity.le(1e-9)]
        minutes = completed.completion_trading_minutes
        if minutes.isna().any() or (minutes < 0).any():
            raise ValueError("已完成订单需要有效、非负的 completion_trading_minutes")
        observed_counts.append(len(rows))
        completed_counts.append(len(completed))
        labels.append(f"{rate:.0%}\n已成 {len(completed)}/{len(rows)}")
        if minutes.empty:
            right.text(x, .05, "无已完成订单", transform=right.get_xaxis_transform(), ha="center", fontsize=7)
            continue
        stats = [minutes.median(), minutes.quantile(.9), minutes.max()]
        values.extend(stats)
        right.plot([x] * 3, stats, color=colors[rate], lw=1, alpha=.6)
        for value, marker, offset in zip(stats, ["o", "s", "^"], [-.07, 0, .07]):
            right.scatter(x + offset, value, color=colors[rate], marker=marker, s=25, zorder=3)
    if values and min(values) > 0 and max(values) / min(values) > 20:
        right.set_yscale("log")
        lower, upper = min(values) / 1.6, max(values) * 3
        right.set_ylim(lower, upper)
        ticks = [value for value in [1, 2, 10, 50, 200, 1000, 5000, 20000] if lower <= value <= upper]
        if ticks:
            right.set_yticks(ticks, [str(value) for value in ticks])
        right.minorticks_off()
        scale_note = "右图为对数刻度；"
    else:
        right.set_ylim(0, max(values, default=1) * 1.35 or 1)
        scale_note = ""
        if not values:
            right.set_yticks([])
    right.set_xticks(range(len(rates)), labels)
    right.set_xlim(-.4, len(rates) - .6)
    right.set_xlabel("参与率；已成数 / 完整观察订单数", labelpad=6)
    right.set_ylabel("已完成订单用时（交易分钟）")
    right.set_title("B  最大资金的完成用时", loc="left", pad=12)
    right.text(.02, .98, "圆：中位数  方：90%分位  三角：最长", transform=right.transAxes,
               fontsize=6.8, va="top", color=MUTED)
    fig.legend(*left.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.09, .99), ncol=3,
               columnspacing=2)
    files = save(fig, output, "comparison_03_execution",
                 "来源：comparison_summary.csv、order_observations.csv；口径：study_manifest.json",
                 f"{sample_label}；{scale_note}未完成订单保留在左图分母，用时留空，不计作零分钟。")
    return files, {f"{rate:g}": {"complete_window_orders": count, "completed_orders": completed}
                   for rate, count, completed in zip(rates, observed_counts, completed_counts)}


def render(output: Path, font: Path | None = None) -> dict:
    summary = _read(output, "comparison_summary.csv", ["strategy", "group", "initial_capital", "participation_rate",
                    "cumulative_return", "return_gap_vs_momentum_reference_net_pp", "complete_window_fill_ratio_amount"])
    nav = _read(output, "nav_comparison.csv", ["strategy", "group", "initial_capital", "participation_rate",
                "trade_date", "normalized_nav", "return_gap_vs_benchmark_pp"])
    orders = _read(output, "order_observations.csv", ["group", "initial_capital", "participation_rate",
                   "full_execution_window_observed", "remaining_quantity", "completion_trading_minutes"])
    manifest = json.loads((output / "study_manifest.json").read_text(encoding="utf-8"))
    constrained = summary.loc[summary.strategy.eq("momentum") & summary.group.eq("constrained_net")]
    capitals = sorted(constrained.initial_capital.unique())
    rates = sorted(constrained.participation_rate.dropna().unique())
    if not capitals or not rates:
        raise ValueError("没有动量参与率约束场景")
    if len(rates) > 3:
        raise ValueError("该紧凑图表最多支持三种参与率")
    keys = ["strategy", "group", "initial_capital", "participation_rate"]
    if summary.duplicated(keys).any():
        raise ValueError("汇总场景主键重复")
    expected = len(capitals) * len(rates)
    if len(constrained) != expected:
        raise ValueError("每一档资金都需要相同的参与率场景")
    setup(font)
    colors = dict(zip(rates, [AMBER, TEAL, NAVY] if len(rates) == 3 else [TEAL, AMBER]))
    label = "合成演示，非真实实证" if manifest.get("source_type") == "synthetic_company_fixture" else "历史分钟样本回放"
    artifacts = nav_chart(nav, output, max(capitals), label)
    artifacts += return_chart(summary, output, capitals, rates, colors, label)
    execution_files, counts = execution_chart(summary, orders, output, capitals, rates, colors, label)
    artifacts += execution_files
    provenance = {"source_files": ["comparison_summary.csv", "nav_comparison.csv", "order_observations.csv", "study_manifest.json"],
                  "source_type": manifest.get("source_type"), "signal_cutoff_date": manifest.get("signal_cutoff_date"),
                  "evaluation_end": manifest.get("evaluation_end"), "maximum_capital": float(max(capitals)),
                  "nav_participation_rate": .1, "completion_clock_counts_at_maximum_capital": counts,
                  "completion_clock_population": "complete execution window observed and remaining_quantity <= 1e-9; incomplete orders excluded from time statistics, not assigned zero",
                  "artifacts": artifacts}
    (output / "comparison_plot_manifest.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    return provenance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="已有 comparison 实验输出目录")
    parser.add_argument("--font", type=Path, help="可选中文字体文件")
    args = parser.parse_args()
    try:
        render(args.output, args.font)
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))
    print(f"已生成三组中文 PDF / PNG：{args.output.resolve()}")


if __name__ == "__main__":
    main()
