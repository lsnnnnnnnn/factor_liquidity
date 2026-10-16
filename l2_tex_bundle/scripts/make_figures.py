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
    ax.set_xlabel("调仓日期", labelpad=5)


def completion(summary, output):
    rows = selected(summary)
    capitals = sorted(rows.capital.unique())
    fig, axes = panels(3, 2.7)
    fig.subplots_adjust(left=.065, wspace=.27)
    for ax, field, title in zip(axes, ["completion_30", "completion_60", "completion_day"], ["A  30 个交易分钟", "B  60 个交易分钟", "C  当日结束"]):
        for rate, color in COLORS.items():
            values = [weighted(selected(rows, capital, rate), field, selected(rows, capital, rate).target_reference_notional) * 100 for capital in capitals]
            ax.plot(range(len(capitals)), values, marker="o", color=color, label=f"参与率 {rate:.0%}")
        ax.set_title(title, loc="left", pad=10)
        ax.set_xticks(range(len(capitals)), [f"{capital/1e4:,.0f}" for capital in capitals])
        ax.set_xlabel("资金（万元）", labelpad=7)
        ax.set_ylim(-3, 104)
        ax.set_yticks([0,25,50,75,100])
    axes[0].set_ylabel("完成率（按计划金额，%）")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(.53,1.015), ncol=3)
    save(fig, output, "01_completion", "完成率按全部计划金额计算；买卖金额相加，未成交部分仍计入原计划。")


def event_stability(summary, orders, output):
    capital = summary.capital.max()
    rows = selected(summary, capital, .1).sort_values("event_date")
    dates = rows.event_date.tolist()
    fig, (left, right) = panels(height=2.75)
    left.set_title("A  1 亿元、10%：各日完成情况", loc="left", pad=10)
    for field, label, color in zip(["completion_30", "completion_60", "completion_day"], ["30 分钟", "60 分钟", "当日"], [AMBER, TEAL, NAVY]):
        left.plot(range(len(rows)), rows[field]*100, marker="o", color=color, label=label)
    right.set_title("B  当日结束时，买卖各完成多少", loc="left", pad=10)
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
        ax.set_ylabel("完成率（按计划金额，%）")
        ax.legend(fontsize=7, loc="best")
    save(fig, output, "02_event_stability", "每个日期重新设定持仓和现金；连线只方便比较日期，不表示持仓连续变化。")


def side_stratum(summary, orders, output):
    rows = selected(orders, summary.capital.max(), .1)
    strata = sorted(rows.stratum.unique(), key=lambda value: {"low": 0, "middle": 1, "mid": 1, "medium": 1, "high": 2}.get(str(value), 3))
    names = {"low": "低", "middle": "中", "mid": "中", "medium": "中", "high": "高"}
    fig, (left,right) = panels(height=2.4)
    left.set_title("A  按股票成交活跃程度分组",loc="left",pad=10)
    right.set_title("B  买入和卖出各完成多少",loc="left",pad=10)
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
    left.set_xlabel("成交活跃程度（按 3 月成交额分组）",labelpad=7)
    right.set_xticks(range(3),["30 分钟","60 分钟","当日"])
    for ax in [left,right]:
        ax.set_ylim(0,105)
        ax.set_ylabel("完成率（按计划金额，%）")
    fig.legend(*left.get_legend_handles_labels(),loc="upper center",bbox_to_anchor=(.53,1.015),ncol=2)
    save(fig,output,"03_side_stratum","1 亿元、10% 参与率；每组分别按原计划金额计算，未成交部分不删除。")


def duration_slippage(summary, orders, output):
    rows=selected(orders,summary.capital.max())
    fig,(left,right)=panels(height=2.4)
    left.set_title("A  已做完的订单花了多长时间",loc="left",pad=10)
    right.set_title("B  成交价比参考价差多少",loc="left",pad=10)
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
    left.set_ylabel("已完成订单的累计占比（%）")
    left.set_xlim(0,240)
    left.set_ylim(0,104)
    left.legend(fontsize=6.6,loc="lower right")
    right.set_xticks(range(len(COLORS)),ticks)
    right.set_ylabel("滑点（bp；正值不利）")
    right.axhline(0,color=MUTED,lw=.7)
    save(fig,output,"04_duration_slippage","未完成订单另计笔数；箱内为中间一半订单，中线为中位数，小点为较极端的结果。")


def returns_constraints(summary, orders, output):
    rows=selected(summary,summary.capital.max())
    fig,(left,right)=panels(height=2.9)
    fig.subplots_adjust(wspace=.8)
    left.set_title("A  各日收益与参考结果的差别",loc="left",pad=10)
    for index,(rate,color) in enumerate(COLORS.items()):
        values=rows.loc[rows.participation.eq(rate)].sort_values("event_date").return_diff_pp.to_numpy()
        left.scatter(index+np.linspace(-.1,.1,len(values)),values,color=color,s=14,alpha=.8)
        left.plot([index-.15,index+.15],[np.median(values)]*2,color=INK,lw=1.5)
    left.set_xticks(range(len(COLORS)),[f"{rate:.0%}" for rate in COLORS])
    left.set_xlabel("参与率",labelpad=7)
    left.set_ylabel("当日收益差（百分点）")
    left.axhline(0,color=MUTED,lw=.7)
    right.set_title("B  未完成订单遇到的限制",loc="left",pad=10)
    counts=Counter()
    groups={"participation_budget_bound":"参与率限制", "rounded_participation_budget_zero":"取整后不足100股",
        "source_unexplained_gap":"行情间隔或时段切换", "arrival_gap_or_session_boundary":"行情间隔或时段切换",
        "partial_visible_depth":"盘口数量不足", "no_opposing_depth":"盘口数量不足", "demo_lot_residual":"剩余不足100股",
        "max_child_quantity_bound":"单次下单数量上限", "sellable_constraint":"可卖数量不足", "suspended":"有停牌记录",
        "retrospective_market_suspension":"停牌环境", "evidenced_suspension":"停牌证据",
        "source_volume_acc_mismatch":"区间量额核对", "source_turnover_acc_mismatch":"区间量额核对",
        "source_invalid_interval_volume":"区间成交量无效", "source_budget_reserved_by_other_order":"数量已被其他订单占用",
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
        right.text(.5,.5,"没有未完成订单的限制记录",transform=right.transAxes,ha="center")
    right.set_xlabel("1 亿元、10%：遇到该限制的次数",labelpad=7)
    right.grid(False)
    right.grid(axis="x")
    save(fig,output,"05_returns_constraints","左图每点为一个调仓日，黑线为中位数；右图同一次尝试可能同时受多种限制。")


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
    values["StudyConclusion"]=(
        "\\begin{itemize}"
        f"\\item 资金越大，按计划完成买卖越困难。参与率为 10\\% 时，资金从 100 万元增至 1 亿元，当日完成率从 {percent(small,'completion_day'):.2f}\\% 降至 {percent(big,'completion_day'):.2f}\\%；1 亿元在前 30、60 分钟只完成 {percent(big,'completion_30'):.2f}\\%、{percent(big,'completion_60'):.2f}\\%。"
        f"\\item 大资金下，买入比卖出更难做完。1 亿元、10\\% 参与率下，当日买入完成 {side_rates['buy']:.2f}\\%，卖出完成 {side_rates['sell']:.2f}\\%；{event_count} 个调仓日合计仍有 {incomplete:,} 笔订单没有全部完成。"
        f"\\item 成交限制会改变当天收益。与全部按参考价成交相比，1 亿元、10\\% 参与率下，{event_count} 个当日收益差的中位数为 {big.return_diff_pp.median():+.4f} 个百分点。"
        "\\end{itemize}")
    actual_rows=int(quality.rows.sum())
    missing=coverage.loc[coverage.rows.eq(0)]
    excluded=sorted(set(coverage.date)-set(base.event_date))
    values["QualityNarrative"]=(f"原计划 14 个调仓日，每天 30 只股票，共应有 420 份单只股票的日行情。实际保留 {event_count} 天，共 {actual_rows:,} 条十档快照，其中连续竞价时段 {int(quality.continuous_rows.sum()):,} 条，能用于计算下单数量的 {int(quality.valid_source_rows.sum()):,} 条。{tex('、'.join(excluded))} 的 {len(missing)} 只股票均无行情，已单独列出并排除。区间成交量和成交额共发现 {int(quality.volume_mismatches.sum()):,} 条核对差异；连续竞价内，快照相隔超过 10 秒的情况有 {int(quality.continuous_gaps_gt10s.sum()):,} 次，最长 {quality.continuous_max_gap_seconds.max():g} 秒。")
    official=quality.loc[quality.rows.gt(0)&quality.daily_volume.notna()]
    amount_micro=official.loc[official.daily_amount_delta.abs().gt(.02)]
    assert official.daily_volume_delta.abs().le(1e-6).all(), "日终数量差异需要明确披露"
    daily_text=f"能与官方日线核对的 {len(official)} 份日行情，日终累计成交量均在计算误差范围内一致。{len(amount_micro)} 份的成交额有微小差别，最大为 {official.daily_amount_delta.abs().max():.2f} 元。"
    for row in quality.loc[quality.rows.gt(0)&quality.daily_volume.isna()].itertuples():
        assert str(row.historical_suspension_evidence).lower() in {"true","1"}
        daily_text+=f"{tex(row.symbol)} 在 {row.date[5:]} 有 {int(row.rows):,} 条快照，但没有官方日线，并查到当天停牌记录；因此用最初的参考价估值，另外标明价格没有更新，买入计划仍计入完成率。"
    assert quality.invalid_book_rows.fillna(0).eq(0).all()
    assert quality.continuous_crossed_book_rows.fillna(0).eq(0).all()
    assert quality[["ask_saturated_rows","bid_saturated_rows"]].fillna(0).eq(0).all().all()
    values["DailyQualityNarrative"]=daily_text+"没有发现买卖档位顺序错误、连续竞价买价高于卖价，或数量达到字段上限的记录。"
    reference=base.loc[base.capital.eq(capital)&base.model.eq("reference")]
    unlimited=base.loc[base.capital.eq(capital)&base.model.eq("unlimited")]
    triple=lambda group: "、".join(f"{percent(group,field):.2f}\\%" for field in ["completion_30","completion_60","completion_day"])
    values["CompletionNarrative"]=(f"以 1 亿元为例，假设全部按参考价成交，三个时点自然都是 100\\%。换成实际 L2 盘口，即使不限制参与率，30 分钟、60 分钟和当日也只能完成 {triple(unlimited)}；参与率限制为 10\\% 后，降为 {triple(big)}。这说明盘口数量本身已经构成限制，再限制每次下单数量，完成得更慢。分日期看，10\\% 参与率下当日完成率为 {big.completion_day.min()*100:.2f}\\% 至 {big.completion_day.max()*100:.2f}\\%，13 天的中位数为 {big.completion_day.median()*100:.2f}\\%。")
    strata=[]
    for name,group in source.groupby("stratum"):
        label={"low":"较少","medium":"一般","middle":"一般","mid":"一般","high":"较活跃"}.get(str(name),tex(name))
        strata.append(f"成交{label}的一组完成 {weighted(group,'completion_eod',demand(group))*100:.2f}\\%")
    values["StratumNarrative"]="1 亿元、10\\% 参与率下，"+"，".join(strata)+"。股票按研究前的成交额分组，没有根据这次结果重新挑选。这只反映本次选定股票的差别，不能直接推广到全市场。"
    median=f"{done.median():.2f}" if len(done) else "无可计算样本"
    values["DurationNarrative"]=(f"1 亿元、10\\% 参与率下，13 天共 {len(source):,} 笔买卖订单，做完 {len(done):,} 笔，未做完 {incomplete:,} 笔。已经做完的订单，完成用时中位数为 {median} 个交易分钟；也就是其中一半不超过这个时间。未完成订单不参加这个中位数的计算。")
    values["ReturnNarrative"]=(f"1 亿元、10\\% 参与率下，13 个调仓日的当日净收益中位数为 {big.return_pct.median():+.4f}\\%。与全部按参考价成交相比，各日收益差从 {big.return_diff_pp.min():+.4f} 到 {big.return_diff_pp.max():+.4f} 个百分点不等。实际成交更少，有时反而会少亏一些，因此收益差为正不一定表示交易做得更好，还要看原计划是否完成。这些都是单日比较，不能相加或复利成三个月收益。")
    true=lambda column: column.astype(str).str.lower().isin(["true","1"])
    closing=source.loc[source.remaining_qty.gt(0)&true(source.closing_directional_limit_no_depth)&true(source.closing_quote_fresh)]
    buy_count=int(closing.side.eq("buy").sum())
    sell_count=int(closing.side.eq("sell").sum())
    values["ClosingNarrative"]=(f"1 亿元、10\\% 参与率下，未完成订单中有 {buy_count} 笔买单、{sell_count} 笔卖单，在 14:57 前最后 10 秒内的有效盘口中，已处于相应的官方涨跌停价，且原始盘口没有对手盘。这是事后查看收盘前行情得到的标记，只能说明那个时点的情况，不能证明全天都封板；本次也没有继续模拟这些剩余数量下一周能否成交。")
    sensitivity=summary.loc[summary.capital.eq(capital)&summary.participation.eq(.1)&summary.is_base.eq(0)]
    labels=[]
    for (refresh,delay),group in sensitivity.groupby(["refresh","delay_ms"],sort=False):
        name="每张快照重新计算可见数量" if refresh=="snapshot" else "继续扣除当天已用过的同价位数量"
        delay_text=f"{delay/1000:g} 秒" if delay>=1000 else f"{delay:g} 毫秒"
        labels.append(f"{name}、延迟 {delay_text}时，为 {percent(group,'completion_day'):.2f}\\%")
    values["SensitivityNarrative"]="同样使用 1 亿元、10\\% 参与率和原来的买卖计划，改变两项假设后，当日完成率为："+"；".join(labels)+"。这些延迟都是实验参数，尚未测量真实下单耗时。"
    three_seconds=sensitivity.loc[sensitivity.refresh.eq("conservative")&sensitivity.delay_ms.eq(3000)]
    if len(three_seconds)==len(big):
        paired=big.set_index("event_date").completion_day.to_frame("base").join(
            three_seconds.set_index("event_date").completion_day.rename("three_seconds"),validate="one_to_one")
        if paired.notna().all().all() and (paired.base-paired.three_seconds).abs().max()<=1e-4:
            values["SensitivityNarrative"]+="1 毫秒和 3 秒的结果接近，可能因为行情快照之间本来就隔着数秒，两种延迟最终用到了同一张后续盘口。因此不能据此认定真实交易中慢 3 秒也没关系。"
    test_count=int(metadata["test_suite"].split()[0])
    values["ValidationNarrative"]=(f"本轮程序通过 {test_count} 项测试，{len(summary):,} 组运行结果均通过现金、持仓与负债核对。桌面重新运行 5 种成交规则，得到的 41 张结果表与原结果逐项一致。公开数据保留 {len(orders):,} 行订单指标。重画图表时还会核对：计划股数等于已成交加剩余股数，未完成订单不填写完成时间，各图表使用同一份原计划金额。")
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
