"""Plot public aggregate data checks, never execution performance."""
from pathlib import Path

import numpy as np
import pandas as pd

from make_figures import AMBER, MUTED, NAVY, TEAL, plt, setup


def main():
    root = Path(__file__).resolve().parents[1]
    setup(None)
    frame = pd.read_csv(root/"data/sample3_update/monthly_market_checks.csv")
    if (frame.month.duplicated().any() or len(frame) != 8
            or int(frame.actual_trade_stockdays.sum()) != 20414
            or not (frame.l2_present+frame.l2_missing).equals(frame.actual_trade_stockdays)):
        raise ValueError("public aggregate scope/denominator differs from the saved source audit")
    fig, (left, right) = plt.subplots(1, 2, figsize=(6.5, 3.0))
    fig.subplots_adjust(left=.075, right=.985, bottom=.21, top=.78, wspace=.36)
    months = frame.month.str[5:7]+"月"
    x = np.arange(len(frame))
    left.bar(x, frame.actual_trade_stockdays, color=NAVY, width=.64)
    left.set_xticks(x, months, rotation=45)
    left.set_ylim(0, 3700)
    left.set_ylabel("实际成交涉及的证券日期数")
    left.set_title("A  本次读取范围", loc="left", pad=12)
    left.grid(axis="y", alpha=.3)
    left.set_axisbelow(True)
    for i, row in frame.iterrows():
        left.text(i, row.actual_trade_stockdays+55, f"{row.actual_trade_stockdays:,}", ha="center", fontsize=6.3)
        if row.l2_missing:
            left.text(i, 135, f"缺{row.l2_missing}", color="white", ha="center", fontsize=7)
    right.bar(x-.18, frame.amount_difference_over_one_yuan, .36, color=AMBER, label="L2与日线金额差 > 1元")
    right.bar(x+.18, frame.negative_turnover_increment, .36, color=TEAL, label="含负成交额增量")
    right.set_xticks(x, months, rotation=45)
    right.set_ylabel("需进一步核查的证券日期数")
    right.set_ylim(0, max(frame.amount_difference_over_one_yuan)*1.22)
    right.set_title("B  原字段差异，分类可重叠", loc="left", pad=12)
    right.grid(axis="y", alpha=.3)
    right.set_axisbelow(True)
    for i, row in frame.iterrows():
        for delta, column in [(-.18, "amount_difference_over_one_yuan"), (.18, "negative_turnover_increment")]:
            if row[column]:
                right.text(i+delta, row[column]+16, str(row[column]), ha="center", fontsize=7)
    handles, labels = right.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(.55, 1.01),
               frameon=False, fontsize=6.5, labelspacing=.6)
    fig.savefig(root/"figures/06_sample3_data_checks.pdf")
    fig.savefig(root/"figures/06_sample3_data_checks.png", dpi=240)
    plt.close(fig)


if __name__ == "__main__":
    main()
