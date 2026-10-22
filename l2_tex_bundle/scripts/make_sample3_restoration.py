"""Draw account reconciliation and carried-mark diagnostics, not L2 performance."""
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import dates as mdates

from make_figures import AMBER, NAVY, panels, plt, setup


def main():
    root = Path(__file__).resolve().parents[1]
    data = pd.read_csv(root/"data/sample3_restoration/daily_validation.csv", parse_dates=["date"])
    if len(data) != 1355 or data.date.duplicated().any() or not data.date.is_monotonic_increasing:
        raise ValueError("retain all 1355 source account dates")
    if not np.isfinite(data[["nav_difference", "carried_value_share_of_source_nav"]]).all().all():
        raise ValueError("missing account diagnostic values")
    setup(None)
    fig, (left, right) = panels(2.9)
    fig.subplots_adjust(bottom=.23, top=.79, wspace=.43)
    left.plot(data.date, data.nav_difference*1e14, color=NAVY, linewidth=1.)
    left.axhline(0, color="#A2ABB0", linewidth=.6)
    left.set_title("A  重建NAV减原日账", loc="left", pad=11)
    left.set_ylabel(r"归一化差额（$\times10^{-14}$）")
    left.xaxis.set_major_locator(mdates.YearLocator(2))
    left.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    current = data[data.date.between("2024-01-02", "2024-08-30")]
    if len(current) != 162:
        raise ValueError("retain every 2024 account date")
    right.plot(current.date, current.carried_value_share_of_source_nav*100, color=AMBER)
    right.set_title("B  2024年沿用价持仓", loc="left", pad=11)
    right.set_ylabel("账面金额占源NAV（%）")
    right.set_ylim(bottom=0)
    right.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    right.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
    for ax in (left, right):
        ax.tick_params(axis="x", rotation=30)
        ax.set_xlabel("日期")
    fig.text(.09, .035, "仅核对原复权账户与沿用估值；图中没有L2收益、可变现价值或容量结论。", fontsize=7)
    for suffix in ("pdf", "png"):
        fig.savefig(root/"figures"/f"07_sample3_restoration.{suffix}")
    plt.close(fig)


if __name__ == "__main__":
    main()
