"""Source fixed-flow performance and restored plan counts; no L2 performance."""
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import dates as mdates

from make_figures import AMBER, NAVY, panels, plt, setup


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root/"data/sample3_targets"
    path = pd.read_csv(folder/"source_fixed_path_2024.csv", parse_dates=["date"])
    plans = pd.read_csv(folder/"daily_plan_summary_2024.csv", parse_dates=["execution_date"])
    if (len(path) != 163 or len(plans) != 162 or path.date.duplicated().any()
            or plans.execution_date.duplicated().any()
            or not path.date.is_monotonic_increasing or not plans.execution_date.is_monotonic_increasing):
        raise ValueError("retain the common 2023-12-29 boundary and all 162 observation dates")
    if not np.isfinite(path[["source_nav_rebased", "zero_fee_fixed_actual_path_rebased"]]).all().all():
        raise ValueError("source path cannot contain missing performance values")
    setup(None)
    fig, (left, right) = panels(2.9)
    fig.subplots_adjust(bottom=.23, top=.79, wspace=.38)
    left.plot(path.date, path.source_nav_rebased, label="原含费路径", color=NAVY)
    left.plot(path.date, path.zero_fee_fixed_actual_path_rebased, label="仅返还窗内费用", color=AMBER,
              linestyle="--", linewidth=1.1)
    left.axhline(1, color="#A2ABB0", linewidth=.6)
    left.set_title("A  来源固定实际路径", loc="left", pad=11)
    left.set_ylabel("共同边界净值 = 1")
    left.legend(fontsize=7, frameon=False, loc="lower right")
    right.plot(plans.execution_date, plans.held_count_before, label="源正持仓（含浮点尾数）", color=NAVY)
    right.plot(plans.execution_date, plans.target_count, label="正目标权重", color=AMBER)
    right.set_title("B  已恢复的日级目标", loc="left", pad=11)
    right.set_ylabel("证券数量（原模型）")
    right.set_ylim(bottom=0)
    right.legend(fontsize=7, frameon=False, loc="lower left")
    for ax in (left, right):
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
        ax.tick_params(axis="x", rotation=30)
        ax.set_xlabel("日期")
    fig.text(.09, .035, "复权模型：不重新定量目标；没有L2成交结果；沿用估值尚未验证为可变现价值。", fontsize=7)
    for suffix in ("pdf", "png"):
        fig.savefig(root/"figures"/f"08_sample3_targets.{suffix}")
    plt.close(fig)


if __name__ == "__main__":
    main()
