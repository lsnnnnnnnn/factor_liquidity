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



def tex(value):
    replacements = {"\\": r"\textbackslash{}", "_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#", "{": r"\{", "}": r"\}"}
    return "".join(replacements.get(char, char) for char in str(value))


def demand(rows):
    return rows.target_qty * rows.reference_price


def weighted(rows, field, weights):
    total = weights.sum()
    return float((rows[field] * weights).sum() / total) if total else np.nan


def selected(frame, capital=None, rate=None):
    rows = frame.loc[frame.is_base.eq(1)]
    if capital is not None:
        rows = rows.loc[rows.capital.eq(capital)]
    if rate is not None:
        rows = rows.loc[rows.participation.eq(rate)]
    return rows


def date_axis(ax, dates):
    step = 2 if len(dates) > 8 else 1
    indexes = list(range(0, len(dates), step))
    if indexes[-1] != len(dates)-1:
        indexes.append(len(dates)-1)
    ax.set_xticks(indexes, [date[5:] for date in np.asarray(dates)[indexes]], rotation=35, ha="right")
    ax.set_xlabel("独立执行事件日", labelpad=5)


def completion(summary, output):
    rows = selected(summary)
    capitals = sorted(rows.capital.unique())
    fig, axes = panels(3, 2.7)
    fig.subplots_adjust(left=.065, wspace=.27)
    for ax, field, title in zip(axes, ["completion_30", "completion_60", "completion_day"], ["A  30 个交易分钟", "B  60 个交易分钟", "C  当日结束"]):
        for rate, color in COLORS.items():
            values = [weighted(selected(rows, capital, rate), field, selected(rows, capital, rate).target_reference_notional) * 100 for capital in capitals]
            ax.plot(range(len(capitals)), values, marker="o", color=color, label=f"额度参与率 {rate:.0%}")
        ax.set_title(title, loc="left", pad=10)
        ax.set_xticks(range(len(capitals)), [f"{capital/1e4:,.0f}" for capital in capitals])
        ax.set_xlabel("资金（万元；类别等距）", labelpad=7)
        ax.set_ylim(-3, 104)
        ax.set_yticks([0,25,50,75,100])
    axes[0].set_ylabel("目标参考金额加权完成率（%）")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(.53,1.015), ncol=3)
    save(fig, output, "01_completion", "先加总已成交参考金额与全部需求；跨事件汇总不删除未成交，不计算复合收益。")


def event_stability(summary, orders, output):
    capital = summary.capital.max()
    rows = selected(summary, capital, .1).sort_values("event_date")
    dates = rows.event_date.tolist()
    fig, (left, right) = panels(height=2.75)
    left.set_title("A  1 亿元、10%：逐事件完成率", loc="left", pad=10)
    for field, label, color in zip(["completion_30", "completion_60", "completion_day"], ["30 分钟", "60 分钟", "当日"], [AMBER, TEAL, NAVY]):
        left.plot(range(len(rows)), rows[field]*100, marker="o", color=color, label=label)
    right.set_title("B  当日完成率：买卖分别计算", loc="left", pad=10)
    source = selected(orders, capital, .1)
    for side, label, color in [("buy", "买入", TEAL), ("sell", "卖出", AMBER)]:
        values = []
        for date in dates:
            group = source.loc[source.event_date.eq(date) & source.side.eq(side)]
            values.append(weighted(group, "completion_eod", demand(group))*100)
        right.plot(range(len(dates)), values, marker="o", color=color, label=label)
    for ax in [left,right]:
        date_axis(ax, dates)
        ax.set_ylim(-3,104)
        ax.set_ylabel("金额完成率（%）")
        ax.legend(fontsize=7, loc="best")
    save(fig, output, "02_event_stability", "各点从共同基线独立初始化；日期相近、股票重复，因此不声称事件或订单彼此独立。")


def side_stratum(summary, orders, output):
    rows = selected(orders, summary.capital.max(), .1)
    strata = sorted(rows.stratum.unique(), key=lambda value: {"low": 0, "middle": 1, "mid": 1, "medium": 1, "high": 2}.get(str(value), 3))
    names = {"low": "低", "middle": "中", "mid": "中", "medium": "中", "high": "高"}
    fig, (left,right) = panels(height=2.7)
    left.set_title("A  预热流动性层 × 买卖：当日完成",loc="left",pad=10)
    right.set_title("B  全池买卖：三个观察时点",loc="left",pad=10)
    for side, label, color, shift in [("buy", "买入", TEAL, -.18),("sell", "卖出", AMBER, .18)]:
        values=[]
        for stratum in strata:
            group=rows.loc[rows.side.eq(side) & rows.stratum.eq(stratum)]
            values.append(weighted(group, "completion_eod", demand(group))*100)
        left.bar(np.arange(len(strata))+shift,values,width=.32,color=color,label=label)
        group=rows.loc[rows.side.eq(side)]
        values=[weighted(group,field,demand(group))*100 for field in ["completion_30m","completion_60m","completion_eod"]]
        right.bar(np.arange(3)+shift,values,width=.32,color=color,label=label)
    left.set_xticks(range(len(strata)),[names.get(str(value),str(value)) for value in strata])
    left.set_xlabel("3 月预热成交额层（研究前冻结）",labelpad=7)
    right.set_xticks(range(3),["30 分钟","60 分钟","当日"])
    for ax in [left,right]:
        ax.set_ylim(0,105)
        ax.set_ylabel("金额完成率（%）")
        ax.legend(fontsize=7,loc="best")
    save(fig,output,"03_side_stratum","1 亿元、10% 额度；各层与各方向使用自身完整需求分母，未成交量均保留。")


def duration_slippage(summary, orders, output):
    rows=selected(orders,summary.capital.max())
    fig,(left,right)=panels(height=2.7)
    left.set_title("A  已完成母单：用时经验分布",loc="left",pad=10)
    right.set_title("B  有实际成交的母单：滑点分布",loc="left",pad=10)
    ticks=[]
    for index,(rate,color) in enumerate(COLORS.items()):
        group=rows.loc[rows.participation.eq(rate)]
        done=group.loc[group.remaining_qty.eq(0),"completion_trading_minutes"].dropna().sort_values()
        if len(done):
            left.step(done,np.arange(1,len(done)+1)/len(done)*100,where="post",color=color,label=f"{rate:.0%}：完成 {len(done)}/{len(group)}")
        else:
            left.plot([],[],color=color,label=f"{rate:.0%}：完成 0/{len(group)}")
        slip=group.loc[group.filled_qty.gt(0),"slippage_bps"].dropna()
        if len(slip):
            artists=right.boxplot([slip],positions=[index],widths=.45,patch_artist=True,manage_ticks=False,
                flierprops={"marker":".","markersize":2,"markeredgecolor":color,"alpha":.45},medianprops={"color":INK,"linewidth":1.2})
            artists["boxes"][0].set(facecolor=color,alpha=.45)
        ticks.append(f"{rate:.0%}\n成交 {len(slip)} 单")
    left.set_xlabel("完成用时（交易分钟）",labelpad=7)
    left.set_ylabel("在已完成母单中的累计占比（%）")
    left.set_xlim(0,240)
    left.set_ylim(0,104)
    left.legend(fontsize=6.6,loc="lower right")
    right.set_xticks(range(len(COLORS)),ticks)
    right.set_ylabel("滑点（bp；正值不利）")
    right.axhline(0,color=MUTED,lw=.7)
    save(fig,output,"04_duration_slippage","用时未完成留空；箱体为四分位数、中线为中位数、点为尾部，未成交需求不虚设价格。")


def returns_constraints(summary, orders, output):
    rows=selected(summary,summary.capital.max())
    fig,(left,right)=panels(height=2.9)
    fig.subplots_adjust(wspace=.8)
    left.set_title("A  各事件相对原参考的收益差",loc="left",pad=10)
    for index,(rate,color) in enumerate(COLORS.items()):
        values=rows.loc[rows.participation.eq(rate)].sort_values("event_date").return_diff_pp.to_numpy()
        left.scatter(index+np.linspace(-.1,.1,len(values)),values,color=color,s=14,alpha=.8)
        left.plot([index-.15,index+.15],[np.median(values)]*2,color=INK,lw=1.5)
    left.set_xticks(range(len(COLORS)),[f"{rate:.0%}" for rate in COLORS])
    left.set_xlabel("前一区间额度参与率",labelpad=7)
    left.set_ylabel("当日收益差（百分点）")
    left.axhline(0,color=MUTED,lw=.7)
    right.set_title("B  未完成母单：累计约束记录",loc="left",pad=10)
    counts=Counter()
    groups={"participation_budget_bound":"额度上限", "rounded_participation_budget_zero":"额度取整为零",
        "source_unexplained_gap":"未知长间隔/跨界", "arrival_gap_or_session_boundary":"未知长间隔/跨界",
        "partial_visible_depth":"可见深度", "no_opposing_depth":"可见深度", "demo_lot_residual":"数量单位余量",
        "max_child_quantity_bound":"子单上限", "sellable_constraint":"可卖量", "suspended":"停牌证据",
        "retrospective_market_suspension":"停牌环境", "evidenced_suspension":"停牌证据",
        "source_volume_acc_mismatch":"区间量额核对", "source_turnover_acc_mismatch":"区间量额核对",
        "source_invalid_interval_volume":"区间量无效", "source_budget_reserved_by_other_order":"额度已预占",
        "evidenced_locked_no_opposing_depth":"封板无对手盘", "opposing_order_deferred":"反向单等待"}
    skipped={"source_outside_continuous","source_session_boundary","source_day_reset","source_no_preceding_snapshot"}
    source=selected(orders,summary.capital.max(),.1)
    source=source.loc[source.remaining_qty.gt(0)]
    for raw in source.constraint_counts_json.dropna():
        for reason,count in json.loads(raw).items():
            if reason not in skipped:
                counts[groups.get(reason,reason)]+=count
    ordered=sorted(counts.items(),key=lambda item:item[1])
    if ordered:
        right.barh([key for key,_ in ordered],[value for _,value in ordered],color=AMBER,height=.6)
        right.tick_params(axis="y",labelsize=6.2)
        right.set_xlim(0,max(value for _,value in ordered)*1.18)
        right.ticklabel_format(axis="x",style="sci",scilimits=(4,4))
    else:
        right.text(.5,.5,"无未完成约束记录",transform=right.transAxes,ha="center")
    right.set_xlabel("1 亿元、10%：记录次数（非互斥）",labelpad=7)
    right.grid(False)
    right.grid(axis="x")
    save(fig,output,"05_returns_constraints","左图每点为一个独立事件，黑线为中位数；右图同一步可多因，记录次数不分摊全部余股。")


def write_results(summary, orders, quality, coverage, metadata, root):
    base=selected(summary)
    capital=base.capital.max()
    small=selected(summary,base.capital.min(),.1)
    big=selected(summary,capital,.1)
    source=selected(orders,capital,.1)
    percent=lambda rows,field: weighted(rows,field,rows.target_reference_notional)*100
    done=source.loc[source.remaining_qty.eq(0),"completion_trading_minutes"].dropna()
    incomplete=int(source.remaining_qty.gt(0).sum())
    side_rates={side: weighted(source.loc[source.side.eq(side)],"completion_eod",demand(source.loc[source.side.eq(side)]))*100 for side in ["buy","sell"]}
    event_count=base.event_date.nunique()
    values={"EpisodeCount":str(event_count),"PrimaryScenarioCount":str(len(base)),"DefaultDelay":f"{big.delay_ms.iloc[0]:g}","DefaultRefresh":"保守扣减"}
    values["StudyConclusion"]=(f"实际完成 {event_count} 个可用事件、30 股的固定券单回放。10\\% 额度参与率下，100 万元组当日金额完成率为 {percent(small,'completion_day'):.2f}\\%；1 亿元组 30/60 分钟及当日分别为 {percent(big,'completion_30'):.2f}\\%、{percent(big,'completion_60'):.2f}\\%、{percent(big,'completion_day'):.2f}\\%。1 亿元组买单与卖单当日分别完成 {side_rates['buy']:.2f}\\% 和 {side_rates['sell']:.2f}\\%，仍有 {incomplete:,} 笔母单未完成。相对同事件原参考执行，独立当日收益差中位数为 {big.return_diff_pp.median():+.4f} 个百分点；这不是三个月累计收益。")
    actual_rows=int(quality.rows.sum())
    missing=coverage.loc[coverage.rows.eq(0)]
    excluded=sorted(set(coverage.date)-set(base.event_date))
    values["QualityNarrative"]=(f"计划 14 个执行日、420 个股票日；实际研究保留 {event_count} 个执行日。样本共 {actual_rows:,} 条真实十档快照，其中连续竞价 {int(quality.continuous_rows.sum()):,} 条、有效额度来源 {int(quality.valid_source_rows.sum()):,} 条。覆盖表保留 {len(missing)} 个零行股票日；排除事件为 {tex('、'.join(excluded))}，没有把未知数据空缺记成零流动性。区间量额有 {int(quality.volume_mismatches.sum()):,} 条差异，原行保留且不补量；连续竞价内超过 10 秒的间隔共 {int(quality.continuous_gaps_gt10s.sum()):,} 次，最长 {quality.continuous_max_gap_seconds.max():g} 秒。")
    official=quality.loc[quality.rows.gt(0)&quality.daily_volume.notna()]
    amount_micro=official.loc[official.daily_amount_delta.abs().gt(.02)]
    assert official.daily_volume_delta.abs().le(1e-6).all(), "日终数量差异需要明确披露"
    daily_text=f"{len(official)} 个有官方日线的非空股票日日终累计量与日线在浮点误差内一致；其中 {len(amount_micro)} 个股票日存在金额微差，最大绝对差 {official.daily_amount_delta.abs().max():.2f} 元，不能表述为金额逐分精确相等。"
    for row in quality.loc[quality.rows.gt(0)&quality.daily_volume.isna()].itertuples():
        assert str(row.historical_suspension_evidence).lower() in {"true","1"}
        daily_text+=f"{tex(row.symbol)} 在 {row.date[5:]} 有 {int(row.rows):,} 条 L2、无官方日线且有历史停牌证据；该事件估值采用初始参考价并保留标记。"
    assert quality.invalid_book_rows.fillna(0).eq(0).all()
    assert quality.continuous_crossed_book_rows.fillna(0).eq(0).all()
    assert quality[["ask_saturated_rows","bid_saturated_rows"]].fillna(0).eq(0).all().all()
    values["DailyQualityNarrative"]=daily_text+"盘口逆序、连续竞价交叉盘和饱和值均未发现。"
    reference=base.loc[base.capital.eq(capital)&base.model.eq("reference")]
    unlimited=base.loc[base.capital.eq(capital)&base.model.eq("unlimited")]
    triple=lambda group: "/".join(f"{percent(group,field):.2f}\\%" for field in ["completion_30","completion_60","completion_day"])
    values["CompletionNarrative"]=(f"1 亿元组的 30/60 分钟及当日金额完成率：原参考反事实为 {triple(reference)}，L2 不限参与率为 {triple(unlimited)}，L2 10\\% 为 {triple(big)}。参考对照假定全部需求按参考价成交，不能作为停牌股的可实现保证。10\\% 的逐事件当日完成率范围为 {big.completion_day.min()*100:.2f}\\% 至 {big.completion_day.max()*100:.2f}\\%，中位数 {big.completion_day.median()*100:.2f}\\%；金额加权总体与事件中位数采用不同统计单位。")
    strata=[]
    for name,group in source.groupby("stratum"):
        label={"low":"低","medium":"中","middle":"中","mid":"中","high":"高"}.get(str(name),tex(name))
        strata.append(f"{label}层 {weighted(group,'completion_eod',demand(group))*100:.2f}\\%")
    values["StratumNarrative"]="1 亿元、10\\% 的各预热层当日金额完成率为："+"，".join(strata)+"。这是一组事先固定股票的描述性比较，不能推出全市场低流动性股票的一般概率。"
    median=f"{done.median():.2f}" if len(done) else "无可计算样本"
    values["DurationNarrative"]=(f"1 亿元、10\\% 共 {len(source):,} 笔母单，全部完成 {len(done):,} 笔、未完成 {incomplete:,} 笔；已完成用时中位数为 {median} 个交易分钟。完成用时分布以已完成单为条件，不能单独替代需求完成率。")
    values["ReturnNarrative"]=(f"1 亿元、10\\% 的各事件净收益中位数为 {big.return_pct.median():+.4f}\\%，相对原参考的收益差范围为 {big.return_diff_pp.min():+.4f} 至 {big.return_diff_pp.max():+.4f} 个百分点。收益差包含成交价格、成交时点、残留持仓与费用；不串联成期间收益。收益差为正也可能来自少买或残留持仓的行情暴露，须结合完成率看，不能据此挑参与率或认定容量更大。")
    true=lambda column: column.astype(str).str.lower().isin(["true","1"])
    closing=source.loc[source.remaining_qty.gt(0)&true(source.closing_directional_limit_no_depth)&true(source.closing_quote_fresh)]
    buy_count=int(closing.side.eq("buy").sum())
    sell_count=int(closing.side.eq("sell").sum())
    values["ClosingNarrative"]=(f"1 亿元、10\\% 的未完成母单中，事后方向限价且无对手盘标记涉及买单 {buy_count} 笔、卖单 {sell_count} 笔。标记要求官方方向限价，且 14:57 前最后连续盘口距收盘观察边界不超过 10 秒、原始对手盘为空；不证明全天封板，不改写已运行的订单生命周期，也未模拟跨事件余单延续。")
    sensitivity=summary.loc[summary.capital.eq(capital)&summary.participation.eq(.1)&summary.is_base.eq(0)]
    labels=[]
    for (refresh,delay),group in sensitivity.groupby(["refresh","delay_ms"],sort=False):
        name="逐快照刷新" if refresh=="snapshot" else "保守扣减"
        labels.append(f"{name}/{delay:g} 毫秒为 {percent(group,'completion_day'):.2f}\\%")
    values["SensitivityNarrative"]="1 亿元、10\\% 的工程敏感性中，当日金额完成率："+"，".join(labels)+"。其余输入冻结；延迟参数未经真实测量。"
    three_seconds=sensitivity.loc[sensitivity.refresh.eq("conservative")&sensitivity.delay_ms.eq(3000)]
    if len(three_seconds)==len(big):
        paired=big.set_index("event_date").completion_day.to_frame("base").join(
            three_seconds.set_index("event_date").completion_day.rename("three_seconds"),validate="one_to_one")
        if paired.notna().all().all() and (paired.base-paired.three_seconds).abs().max()<=1e-4:
            values["SensitivityNarrative"]+="1 毫秒与 3 秒的完成率接近；粗快照采样下子单可能落在同一后续盘口，不能据此推断真实交易对 3 秒延迟不敏感。"
    test_count=int(metadata["test_suite"].split()[0])
    values["ValidationNarrative"]=(f"本轮引擎 {test_count} 项测试通过，含市场环境禁成交核验；桌面 5 模型复跑的 41 张账户/执行表与基线逐项相等。{len(summary):,} 个实际事件情景均通过账户核对，公开表保留 {len(orders):,} 行母单指标。重画时复核数量守恒、时点单调、完整需求、未完成时间空值及场景/母单金额一致；日期和资金重复不增加独立样本。")
    lines=[f"\\newcommand{{\\{key}}}{{{value}}}" for key,value in values.items()]
    lines.append(r"\newcommand{\CapitalRows}{%")
    for value in sorted(base.capital.unique()):
        group=selected(summary,value,.1)
        lines.append(f"{value/1e4:,.0f} & {percent(group,'completion_30'):.2f} & {percent(group,'completion_60'):.2f} & {percent(group,'completion_day'):.2f} & {int(group.incomplete_orders.sum()):,} & {group.return_diff_pp.median():+.4f}\\\\")
    lines.append("}")
    lines.append(r"\newcommand{\QualityRows}{%")
    for date,group in coverage.groupby("date",sort=True):
        actual=quality.loc[quality.date.eq(date)&quality.rows.gt(0)]
        count=int(group.rows.gt(0).sum())
        if len(actual):
            lines.append(f"{date[5:]} & {count}/30 & {int(actual.rows.sum()):,} & {int(actual.volume_mismatches.sum()):,} & {int(actual.turnover_mismatches.sum()):,} & {int(actual.continuous_gaps_gt10s.sum()):,}\\\\")
        else:
            lines.append(f"{date[5:]} & {count}/30 & 0 & -- & -- & --\\\\")
    lines.append("}")
    (root/"results.tex").write_text("\n".join(lines)+"\n",encoding="utf-8")


def validate(summary,orders):
    keys=["event_date","scenario"]
    assert not summary.duplicated(keys).any(), "每事件/情景必须唯一"
    for field in ["completion_30","completion_60","completion_day"]:
        assert summary[field].between(0,1).all(), f"{field} 必须在 0..1"
    assert summary.completion_30.le(summary.completion_60+1e-10).all()
    assert summary.completion_60.le(summary.completion_day+1e-10).all()
    assert np.allclose(orders.filled_qty+orders.remaining_qty,orders.target_qty)
    assert orders.loc[orders.remaining_qty.gt(0),"completion_trading_minutes"].isna().all()
    assert summary.audit_passed.astype(str).str.lower().isin(["true","1"]).all()
    frozen=orders.groupby(["event_date","capital","order_id"])[["target_qty","reference_price"]].nunique()
    assert frozen.le(1).all().all(), "同一事件/资金的母单数量和参考价必须跨模型冻结"
    actual=orders.assign(target=demand(orders),filled=orders.filled_qty*orders.reference_price).groupby(keys)[["target","filled"]].sum()
    assert summary.set_index(keys).index.sort_values().equals(actual.index.sort_values()), "母单与汇总的事件/情景集合必须一致"
    merged=summary.set_index(keys).join(actual,validate="one_to_one")
    assert np.allclose(merged.target_reference_notional,merged.target)
    assert np.allclose(merged.filled_reference_notional,merged.filled)
    assert np.allclose(merged.completion_day,merged.filled/merged.target)
    for source,target in [("completion_30m","completion_30"),("completion_60m","completion_60")]:
        totals=(orders[source]*demand(orders)).groupby([orders[key] for key in keys]).sum()
        assert np.allclose(merged[target],totals.reindex(merged.index)/merged.target), "时点金额完成率必须与全部母单一致"
    assert len(selected(summary))==summary.event_date.nunique()*25, "主实验应是实际事件×25，不可遗漏情景"


def main():
    parser=argparse.ArgumentParser(description="从实际独立事件派生表重画中文报告，不连接数据库、不复利事件收益。")
    root=Path(__file__).resolve().parents[1]
    parser.add_argument("--data",type=Path,default=root/"data")
    parser.add_argument("--output",type=Path,default=root/"figures")
    parser.add_argument("--font",type=Path)
    args=parser.parse_args()
    summary=pd.read_csv(args.data/"summary.csv")
    orders=pd.read_csv(args.data/"order_metrics.csv")
    quality=pd.read_csv(args.data/"data_quality.csv")
    metadata=json.loads((args.data/"study_metadata.json").read_text())
    coverage=quality[["symbol","date","rows"]]
    validate(summary,orders)
    args.output.mkdir(parents=True,exist_ok=True)
    setup(args.font)
    completion(summary,args.output)
    event_stability(summary,orders,args.output)
    side_stratum(summary,orders,args.output)
    duration_slippage(summary,orders,args.output)
    returns_constraints(summary,orders,args.output)
    write_results(summary,orders,quality,coverage,metadata,root)
    print(f"实际 {summary.event_date.nunique()} 个事件、{len(summary)} 个情景：5 张 PDF/PNG，results.tex 与 CSV 同源。")


if __name__=="__main__":
    main()
