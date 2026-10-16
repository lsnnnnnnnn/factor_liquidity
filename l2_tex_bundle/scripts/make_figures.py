#!/usr/bin/env python3
"""Redraw report panels from the small, public derived tables. No database access."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import subprocess

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

NAVY, TEAL, AMBER = "#274158", "#167C86", "#B97A2B"
INK, MUTED, GRID, PAPER = "#263D4D", "#637784", "#DFE5E7", "#FAFBF9"
COLORS = {.05: AMBER, .1: TEAL, .2: NAVY}


def setup(font):
    if font is None and shutil.which("kpsewhich"):
        found = subprocess.run(["kpsewhich", "FandolHei-Regular.otf"], capture_output=True, text=True, check=True).stdout.strip()
        font = Path(found) if found else None
    if font is not None:
        font_manager.fontManager.addfont(str(font))
        family = font_manager.FontProperties(fname=str(font)).get_name()
    else:
        families = {item.name for item in font_manager.fontManager.ttflist}
        family = next((name for name in ["Noto Sans CJK SC", "PingFang SC", "Arial Unicode MS"] if name in families), None)
        if family is None:
            raise RuntimeError("需要中文字体；请使用 --font 指定字体文件。")
        font = Path(font_manager.findfont(font_manager.FontProperties(family=family)))
    plt.rcParams.update({"font.family": family, "font.size": 8, "axes.titlesize": 9.5,
                         "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
                         "text.color": INK, "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.edgecolor": GRID, "axes.linewidth": .6,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.spines.left": False, "axes.facecolor": PAPER,
                         "figure.facecolor": PAPER, "grid.color": GRID, "grid.linewidth": .6,
                         "lines.linewidth": 1.7, "lines.markersize": 4,
                         "legend.frameon": False, "legend.fontsize": 7.3,
                         "axes.unicode_minus": False,
                         "pdf.fonttype": 3 if font.suffix.lower() in {".otf", ".ttc"} else 42,
                         "savefig.dpi": 240})


def panels(n=2, height=2.8):
    fig, axes = plt.subplots(1, n, figsize=(6.5, height), squeeze=False)
    fig.subplots_adjust(left=.09, right=.985, bottom=.24, top=.82, wspace=.38)
    for ax in axes.flat:
        ax.set_axisbelow(True)
        ax.grid(axis="y")
        ax.tick_params(length=0, pad=4)
    return fig, list(axes.flat)


def save(fig, output, name, note):
    fig.text(.09, .04, note, color=MUTED, fontsize=7)
    for suffix in ["pdf", "png"]:
        fig.savefig(output / f"{name}.{suffix}")
    plt.close(fig)


def capital_axis(ax, capitals):
    ax.set_xticks(range(len(capitals)), [f"{c/1e4:,.0f}" for c in capitals])
    ax.set_xlabel("初始资金（万元；类别等距）", labelpad=7)


def rate_label(rate):
    return f"{rate:.0%}"


def handcalc(data, output):
    frame = pd.read_csv(data / "handcalc_levels.csv")
    fig, axes = panels(height=2.65)
    for ax, side, title, color in zip(axes, ["buy", "sell"], ["A  买入：从卖一向外取量", "B  卖出：从买一向外取量"], [TEAL, AMBER]):
        rows = frame[frame.side.eq(side)].sort_values("level")
        x = np.arange(len(rows))
        ax.bar(x, rows.visible_qty, color=GRID, label="可见数量")
        ax.bar(x, rows.taken_qty, color=color, width=.55, label="本步取用")
        ax.set_xticks(x, [f"{int(r.level)}档\n{r.price:.3f}元" for r in rows.itertuples()])
        ax.set_ylabel("股")
        ax.set_ylim(0, rows.visible_qty.max()*1.45)
        ax.set_title(title, loc="left", pad=10)
        qty = rows.taken_qty.sum()
        avg = (rows.price * rows.taken_qty).sum() / qty
        ax.text(.98, .96, f"成交 {qty:,.0f} 股\n均价 {avg:.4f} 元", transform=ax.transAxes, ha="right", va="top", fontsize=8)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2, bbox_to_anchor=(.52,1.01))
    save(fig, output, "01_handcalc", "可控手算例；深度为存量，成交量为逐档实际取用量。十档不足时保留余单。")


def matrix(summary, output):
    base = summary[summary.is_base.eq(1) & summary.participation.isin(COLORS)].copy()
    capitals = sorted(base.capital.unique())
    fig, axes = panels(3, 2.85)
    fig.subplots_adjust(left=.06, wspace=.27)
    for ax, field, title in zip(axes, ["completion_30", "completion_60", "completion_day"], ["A  30 个交易分钟", "B  60 个交易分钟", "C  当日结束"]):
        for rate, color in COLORS.items():
            rows = base[base.participation.eq(rate)].sort_values("capital")
            ax.plot(range(len(rows)), rows[field] * 100, color=color, marker="o", label=f"额度参与率 {rate:.0%}")
        ax.set_title(title, loc="left", pad=10)
        ax.set_ylim(-3, 104)
        ax.set_yticks([0,25,50,75,100])
        capital_axis(ax, capitals)
        ax.set_xlabel("资金（万元）", labelpad=7)
    axes[0].set_ylabel("按参考金额加权的完成率（%）")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(.53,1.015), ncol=3)
    save(fig, output, "02_completion", "各时点来自同一执行路径；未成交需求保留在分母。普通余单当日终止。")


def duration_slippage(summary, orders, output):
    chosen = summary[summary.is_base.eq(1) & summary.capital.eq(summary.capital.max()) & summary.participation.isin(COLORS)]
    fig, (left, right) = panels(height=2.5)
    left.set_title("A  1 亿元：完成用时与未完成笔数", loc="left", pad=10)
    right.set_title("B  实际成交的滑点与盘口诊断", loc="left", pad=10)
    for x, row in enumerate(chosen.sort_values("participation").itertuples()):
        rows = orders[orders.scenario.eq(row.scenario)]
        done = rows[rows.remaining_qty.eq(0) & rows.completion_trading_minutes.notna()]
        left.scatter(np.full(len(done), x), done.completion_trading_minutes, color=COLORS[row.participation], s=23, zorder=3)
        filled = rows[rows.filled_qty.gt(0) & rows.slippage_bps.notna()]
        right.scatter(np.full(len(filled), x)-.12, filled.slippage_bps, color=COLORS[row.participation], s=21, zorder=3, label="逐单滑点" if x==0 else None)
        if hasattr(row,"cross_depth_bps"):
            right.scatter(x+.08,row.cross_depth_bps,color=INK,marker="s",s=22,zorder=4,label="跨档成本" if x==0 else None)
            right.scatter(x+.22,row.latency_best_quote_bps,color=AMBER,marker="D",s=20,zorder=4,label="源至执行最优价变化" if x==0 else None)
    labels = [rate_label(p) for p in sorted(chosen.participation.unique())]
    for ax in [left,right]:
        ax.set_xticks(range(len(labels)), labels)
        ax.set_xlim(-.5,len(labels)-.5)
        ax.set_xlabel("前一区间额度参与率", labelpad=7)
    left.set_xticks(range(len(labels)),[f"{r.participation:.0%}\n未完 {int(orders[orders.scenario.eq(r.scenario)].remaining_qty.gt(0).sum())} 笔" for r in chosen.sort_values("participation").itertuples()])
    left.set_xlabel("")
    left.set_ylabel("已完成订单用时（交易分钟）")
    left.set_ylim(0,left.get_ylim()[1]*1.12)
    right.set_ylabel("滑点（bp；正值为不利）")
    right.axhline(0,color=MUTED,lw=.7)
    right.legend(fontsize=6.2,loc="best")
    save(fig, output, "03_duration_slippage", "圆点为母单；方块/菱形为成交额加权诊断，三者不构成可相加的冲击分解。未完成时间留空。")


def nav_returns(summary, nav, output):
    base = summary[summary.is_base.eq(1)]
    big = base[base.capital.eq(base.capital.max())]
    fig, (left,right) = panels(height=2.6)
    left.set_title("A  1 亿元：同一估值终点的净值",loc="left",pad=10)
    for row in big.sort_values("participation",na_position="first").itertuples():
        points = nav[nav.scenario.eq(row.scenario)].sort_values("date")
        if row.participation in COLORS:
            color, ls, label = COLORS[row.participation], "-", f"L2 {row.participation:.0%}"
        elif "reference" in row.model:
            color,ls,label = MUTED,"--","原参考执行"
        else:
            color,ls,label = "#8B7E9E",":","L2 不限参与率"
        left.plot(range(len(points)), points.nav_normalized, color=color, ls=ls, marker="o",label=label)
        left.set_xticks(range(len(points)), [str(d)[5:10] for d in points.date])
    left.set_xlabel("估值日")
    left.set_ylabel("净资产 / 初始净资产")
    left.legend(fontsize=6.9,ncol=2,loc="best")
    right.set_title("B  相对同资金原参考执行的收益差",loc="left",pad=10)
    capitals = sorted(base.capital.unique())
    for rate,color in COLORS.items():
        rows = base[base.participation.eq(rate)].sort_values("capital")
        right.plot(range(len(rows)),rows.return_diff_pp,color=color,marker="o",label=f"{rate:.0%}")
    right.axhline(0,color=MUTED,lw=.7)
    right.set_ylabel("期末收益差（百分点）")
    capital_axis(right,capitals)
    save(fig, output, "04_nav_return", "差值包括成交价、时点、未完成持仓和费用等共同作用；不能统称自身市场冲击。")


REASONS = {"volume_limit":"区间额度", "insufficient_volume":"区间额度", "no_liquidity":"无对手盘", "no_opposite_depth":"无对手盘", "lot_rounding":"数量取整", "data_gap":"行情缺口", "ordinary_day_end":"普通当日终止", "day_end":"普通当日终止", "visible_depth":"可见深度", "participation_limit":"额度限制", "auction_excluded":"竞价排除", "max_gap":"行情缺口", "no_opposing_depth":"无可用对手深度", "demo_lot_residual":"演示单位余量", "rounded_participation_budget_zero":"额度取整为零", "partial_visible_depth":"可见深度不足", "participation_budget":"额度约束", "sellable_constraint":"可卖量约束", "arrival_gap_or_session_boundary":"延迟跨缺口或阶段", "no_valid_source":"无有效源区间"}


def reasons_sensitivity(summary, orders, output):
    base = summary[summary.is_base.eq(1) & summary.capital.eq(summary.capital.max()) & summary.participation.eq(.1)]
    scenario = base.iloc[0].scenario
    rows = orders[orders.scenario.eq(scenario) & orders.remaining_qty.gt(0)].copy()
    fig,(left,right)=panels(height=2.85)
    left.set_title("A  未完成买单：约束记录",loc="left",pad=10)
    if rows.empty:
        left.text(.5,.5,"无未完成母单",transform=left.transAxes,ha="center",va="center")
        left.set_xticks([])
    else:
        counts=Counter()
        groups={"participation_budget_bound":"参与率额度", "rounded_participation_budget_zero":"额度取整为零",
                "source_unexplained_gap":"未知长间隔/到达跨界", "arrival_gap_or_session_boundary":"未知长间隔/到达跨界",
                "partial_visible_depth":"可见深度不足", "no_opposing_depth":"可见深度不足",
                "demo_lot_residual":"数量单位余量", "max_child_quantity_bound":"子单上限", "sellable_constraint":"可卖量"}
        skipped={"source_outside_continuous","source_session_boundary","source_day_reset","source_no_preceding_snapshot"}
        if "constraint_counts_json" not in rows:
            raise ValueError("需要已记录全部约束的 verified 输出，不能把末条原因分配给全部余量")
        for value in rows.constraint_counts_json:
            for reason,count in json.loads(value).items():
                if reason not in skipped:
                    counts[groups.get(reason,REASONS.get(reason,reason))]+=count
        ordered=sorted(counts.items(),key=lambda item:item[1])
        left.set_position([.245,.25,.285,.56])
        right.set_position([.655,.25,.33,.56])
        left.barh([label for label,_ in ordered],[count for _,count in ordered],color=AMBER,height=.6)
        left.set_xlabel("约束记录次数（非互斥）",labelpad=6)
        left.grid(False)
        left.grid(axis="x")
        for y,(_,count) in enumerate(ordered):
            left.text(count,y,f" {count:,}",va="center",fontsize=6.5)
        left.set_xlim(0,max([v for _,v in ordered] or [1])*1.25)
    right.set_title("B  工程假设敏感性：当日完成率",loc="left",pad=10)
    rows=summary[summary.capital.eq(summary.capital.max()) & summary.participation.eq(.1)].copy()
    labels=[f"{'保守扣减' if r.refresh == 'conservative' else '逐帧刷新'}\n{r.delay_ms:g} ms" for r in rows.itertuples()]
    right.bar(range(len(rows)),rows.completion_day*100,color=[TEAL if r.is_base else NAVY for r in rows.itertuples()],width=.55)
    right.set_xticks(range(len(rows)),labels,fontsize=6.4)
    for x,value in enumerate(rows.completion_day*100):
        right.text(x,value+2,f"{value:.1f}%",ha="center",fontsize=7)
    right.set_ylabel("当日金额完成率（%）")
    right.set_ylim(0,105)
    save(fig,output,"05_reasons_sensitivity","左图排除非连续阶段边界，保留累计约束记录，同一步可多因；不将全部余量归于末条原因。")


def tex(text):
    for a,b in [("\\",r"\textbackslash{}"),("_",r"\_"),("%",r"\%"),("&",r"\&"),("#",r"\#")]:
        text=str(text).replace(a,b)
    return text


def write_results(summary, orders, data, root):
    base=summary[summary.is_base.eq(1)]
    small=base[base.capital.eq(base.capital.min()) & base.participation.eq(.1)].iloc[0]
    big=base[base.capital.eq(base.capital.max()) & base.participation.eq(.1)].iloc[0]
    ref=base[base.capital.eq(big.capital) & base.model.str.contains("reference")].iloc[0]
    unlimited=base[base.capital.eq(big.capital) & ~base.model.str.contains("reference") & base.participation.isna()].iloc[0]
    values={"SmallDay":f"{small.completion_day*100:.2f}","BigThirty":f"{big.completion_30*100:.2f}","BigSixty":f"{big.completion_60*100:.2f}","BigDay":f"{big.completion_day*100:.2f}","BigReturn":f"{big.return_pct:.4f}","BigDiff":f"{big.return_diff_pp:+.4f}","RefReturn":f"{ref.return_pct:.4f}","UnlimitedDay":f"{unlimited.completion_day*100:.2f}","ScenarioCount":str(len(summary)),"BigUnfinished":str(int(big.incomplete_orders)),"DefaultDelay":f"{big.delay_ms:g}","DefaultRefresh":tex(big.refresh)}
    lines=[f"\\newcommand{{\\{key}}}{{{value}}}" for key,value in values.items()]
    lines += [r"\newcommand{\CapitalRows}{%"]
    for row in base[base.participation.eq(.1)].sort_values("capital").itertuples():
        lines += [f"{row.capital/1e4:,.0f} & {row.completion_30*100:.2f} & {row.completion_60*100:.2f} & {row.completion_day*100:.2f} & {row.return_pct:.4f} & {row.return_diff_pp:+.4f}\\\\"]
    lines += ["}"]
    quality=pd.read_csv(data/"data_quality.csv")
    lines += [r"\newcommand{\QualityRows}{%"]
    # The input table has one row per symbol/day and named public diagnostics.
    for row in quality.itertuples():
        lines += [f"{tex(row.symbol)} & {row.date} & {int(row.rows):,} & {int(row.continuous_rows):,} & {int(row.volume_mismatches)} & {int(row.turnover_mismatches)} & {int(row.continuous_gaps_gt10s)}\\\\"]
    lines += ["}"]
    (root/"results.tex").write_text("\n".join(lines)+"\n",encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    root=Path(__file__).resolve().parents[1]
    parser.add_argument("--data",type=Path,default=root/"data")
    parser.add_argument("--output",type=Path,default=root/"figures")
    parser.add_argument("--font",type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    setup(args.font)
    summary=pd.read_csv(args.data/"summary.csv")
    orders=pd.read_csv(args.data/"order_metrics.csv")
    nav=pd.read_csv(args.data/"nav.csv")
    required={"scenario","capital","participation","model","refresh","delay_ms","is_base","completion_30","completion_60","completion_day","return_pct","return_diff_pp","incomplete_orders"}
    if required-set(summary):
        raise ValueError(f"summary.csv 缺列：{sorted(required-set(summary))}")
    for col in ["completion_30","completion_60","completion_day"]:
        assert summary[col].between(0,1).all(), f"{col} 必须用 0..1 表示"
    assert (summary.completion_30 <= summary.completion_60+1e-10).all()
    assert (summary.completion_60 <= summary.completion_day+1e-10).all()
    assert (orders.filled_qty+orders.remaining_qty == orders.target_qty).all()
    assert orders.loc[orders.remaining_qty.gt(0),"completion_trading_minutes"].isna().all()
    matrix(summary,args.output)
    handcalc(args.data,args.output)
    duration_slippage(summary,orders,args.output)
    nav_returns(summary,nav,args.output)
    reasons_sensitivity(summary,orders,args.output)
    write_results(summary,orders,args.data,root)
    print(f"已重画 5 张图的 PDF/PNG，并由同一 CSV 更新 results.tex；{len(summary)} 个情景。")


if __name__=="__main__":
    main()
