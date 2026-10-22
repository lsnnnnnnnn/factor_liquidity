"""Draw only the current report from its public aggregate inputs."""
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, FIGURES = ROOT / "data", ROOT / "figures"
NAVY, TEAL, GRAY = "#29465C", "#167C80", "#7D8992"


def main():
    font = subprocess.check_output(["kpsewhich", "FandolHei-Regular.otf"], text=True).strip()
    if not font:
        raise RuntimeError("需要现有 TeX 环境中的 Fandol 中文字体")
    font_manager.fontManager.addfont(font)
    plt.rcParams.update({
        "font.family": font_manager.FontProperties(fname=font).get_name(),
        "font.size": 8, "axes.titlesize": 10, "axes.labelsize": 8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.edgecolor": "#DDE4E8",
        "axes.labelcolor": NAVY, "text.color": NAVY,
        "xtick.color": GRAY, "ytick.color": GRAY,
        "grid.color": "#E6EBEE", "grid.linewidth": .6,
        "axes.unicode_minus": False, "legend.frameon": False,
        "lines.linewidth": 1.8, "savefig.dpi": 240,
    })
    summary = pd.read_csv(DATA / "execution_summary.csv").set_index("path")
    nav = pd.read_csv(DATA / "execution_nav.csv")
    targets = pd.read_csv(DATA / "targets_2024.csv")
    expected = {"reference", "new_unlimited", "new_p0.1"}
    if set(summary.index) != expected or summary.index.has_duplicates:
        raise ValueError("当前版本只允许三个已实际完成的最新规则账户")
    if not np.isfinite(summary.select_dtypes("number")).all().all():
        raise ValueError("结果表含非有限数")
    if not np.allclose(summary.final_nav / summary.initial_nav - 1,
                       summary.total_return_pct / 100, atol=1e-12):
        raise ValueError("末资产不能核回收益")
    if (len(nav) != 26 or nav.trade_date.duplicated().any()
            or not nav.trade_date.is_monotonic_increasing
            or nav.trade_date.iloc[0] != "2026-07-31"
            or nav.trade_date.iloc[-1] != "2026-09-04"):
        raise ValueError("净值必须保留全部26个交易日")
    for col, key in [("reference", "reference"), ("new_p0.1", "new_p0.1")]:
        if not np.isfinite(nav[col]).all() or not np.isclose(nav[col].iloc[0], 1):
            raise ValueError("净值起点或数据无效")
        if not np.isclose(nav[col].iloc[-1], summary.loc[key, "final_nav"] / 1e8):
            raise ValueError("净值图终点与结果表不一致")
    if len(targets) != 8 or targets.target_count.sum() != 7642:
        raise ValueError("正式策略必须保留8次、7642条新正目标")

    FIGURES.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.75))
    fig.subplots_adjust(left=.08, right=.985, bottom=.23, top=.84, wspace=.4)
    left, right = axes
    x = np.arange(len(nav))
    left.plot(x, nav.reference, color=GRAY, ls="--", label="参考价成交假设")
    left.plot(x, nav["new_p0.1"], color=TEAL, label="L2 · 10%参与率")
    ticks = [0, 5, 10, 15, 20, 25]
    left.set_xticks(ticks, [nav.trade_date.iloc[i][5:] for i in ticks], rotation=25)
    left.set(title="A  同一资金起点的连续净值", ylabel="净值（起点 = 1）", xlabel="2026年日期")
    left.legend(fontsize=7, loc="lower left")
    positions = np.arange(3)
    right.bar(positions - .17, summary.loc["new_p0.1", ["completion_30", "completion_60", "completion_day"]].astype(float) * 100,
              width=.31, color=TEAL, label="10%参与率")
    right.bar(positions + .17, summary.loc["new_unlimited", ["completion_30", "completion_60", "completion_day"]].astype(float) * 100,
              width=.31, color=NAVY, label="不限参与率")
    values = summary.loc["new_p0.1", ["completion_30", "completion_60", "completion_day"]].astype(float) * 100
    for i, value in enumerate(values):
        right.text(i - .17, value + 2, f"{value:.1f}", ha="center", fontsize=7)
    right.set_xticks(positions, ["30分钟", "60分钟", "当日"])
    right.set(title="B  各自计划金额的完成比例", ylabel="完成率（%）", ylim=(0, 114))
    right.legend(fontsize=7, loc="upper center", bbox_to_anchor=(.5, -.17), ncol=2)
    for ax in axes:
        ax.set_axisbelow(True)
        ax.grid(axis="y")
        ax.tick_params(length=0)
    for suffix in ("pdf", "png"):
        fig.savefig(FIGURES / f"01_current_execution.{suffix}")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.75, 1.95))
    fig.subplots_adjust(left=.08, right=.985, bottom=.25, top=.88)
    x = np.arange(len(targets))
    bars = ax.bar(x, targets.target_count, color=TEAL, width=.55)
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set_xticks(x, targets.execution_date.str[5:])
    ax.set(ylabel="正目标证券数", xlabel="2024年原定执行日期", ylim=(0, 1080))
    ax.set_axisbelow(True)
    ax.grid(axis="y")
    ax.tick_params(length=0)
    for suffix in ("pdf", "png"):
        fig.savefig(FIGURES / f"02_current_targets.{suffix}")
    plt.close(fig)

    labels = {"reference": "参考价成交假设", "new_unlimited": "L2 不限参与率", "new_p0.1": "L2 10\\%参与率"}
    rows = []
    for key in ("reference", "new_unlimited", "new_p0.1"):
        r = summary.loc[key]
        rows.append(f"{labels[key]} & {r.total_return_pct:.4f} & {r.return_diff_pp:+.4f} & {100*r.completion_day:.4f} & {r.max_drawdown_pct:.4f} \\\\")
    r = summary.loc["new_p0.1"]
    macros = [f"\\newcommand{{\\CurrentReturn}}{{{r.total_return_pct:.4f}}}",
              f"\\newcommand{{\\CurrentDifference}}{{{abs(r.return_diff_pp):.4f}}}",
              f"\\newcommand{{\\CurrentCompletion}}{{{100*r.completion_day:.4f}}}",
              "\\newcommand{\\CurrentResultRows}{%\n" + "\n".join(rows) + "\n}"]
    (ROOT / "current_results.tex").write_text("\n".join(macros) + "\n", encoding="utf-8")
    print("当前图表已生成；收益等式、26日净值与8次目标核对通过。")


if __name__ == "__main__":
    main()
