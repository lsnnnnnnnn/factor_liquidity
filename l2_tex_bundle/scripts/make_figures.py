#!/usr/bin/env python3
"""Redraw the continuous-account report from public derived tables only."""
from __future__ import annotations

import argparse
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
MODELS = ["reference", "unlimited", "p0.05", "p0.1", "p0.2"]
LABELS = {"reference": "按参考价全成", "unlimited": "L2 不限参与率", "p0.05": "参与率 5%", "p0.1": "参与率 10%", "p0.2": "参与率 20%"}
COLORS = {"reference": "#8A9196", "unlimited": NAVY, "p0.05": AMBER, "p0.1": TEAL, "p0.2": "#7E659A"}


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
                         "legend.frameon": False, "legend.fontsize": 7.1,
                         "axes.unicode_minus": False,
                         "pdf.fonttype": 3 if font.suffix.lower() in {".otf", ".ttc"} else 42,
                         "savefig.dpi": 240})


def panels(height=2.8):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, height))
    fig.subplots_adjust(left=.09, right=.985, bottom=.25, top=.78, wspace=.4)
    for ax in axes:
        ax.set_axisbelow(True)
        ax.grid(axis="y")
        ax.tick_params(length=0, pad=4)
    return fig, axes


def save(fig, output, name, note):
    fig.text(.09, .035, note, color=MUTED, fontsize=7)
    for suffix in ["pdf", "png"]:
        fig.savefig(output / f"{name}.{suffix}")
    plt.close(fig)


def tex(value):
    replacements = {"\\": r"\textbackslash{}", "_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#", "{": r"\{", "}": r"\}"}
    return "".join(replacements.get(char, char) for char in str(value))


def select(frame, capital, model="p0.1"):
    return frame.loc[frame.capital.eq(capital) & frame.model.eq(model)]


def date_axis(ax, dates, every=1):
    indexes = list(range(0, len(dates), every))
    if indexes[-1] != len(dates)-1:
        indexes.append(len(dates)-1)
    ax.set_xticks(indexes, [dates[i][5:] for i in indexes], rotation=30, ha="right")
    ax.set_xlabel("日期", labelpad=5)


def legend(fig, ax, columns=3):
    fig.legend(*ax.get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(.53, 1.01), ncol=columns)


def nav_path(summary, daily, output):
    capital = summary.capital.max()
    fig, (left, right) = panels(2.9)
    for model in MODELS:
        rows = select(daily, capital, model).sort_values("trade_date")
        dates = rows.trade_date.tolist()
        left.plot(range(len(rows)), rows.normalized_nav, label=LABELS[model], color=COLORS[model], ls="--" if model=="reference" else "-")
        right.plot(range(len(rows)), rows.drawdown*100, color=COLORS[model], ls="--" if model=="reference" else "-")
    left.set(title="A  净资产从 1 开始", ylabel="净值（初始资金 = 1）")
    right.set(title="B  比此前最高净值低多少", ylabel="回撤（%）")
    for ax in [left, right]:
        date_axis(ax, dates, 5)
    left.axhline(1, color=MUTED, lw=.6)
    right.axhline(0, color=MUTED, lw=.6)
    legend(fig, left)
    save(fig, output, "01_nav_drawdown", "1 亿元；7/31 全现金开始，8/3 首次买入；全部交易日连续估值，期间不重置账户。")


def completion(summary, batches, output):
    rows = select(batches, summary.capital.max()).sort_values("rebalance_date")
    dates = rows.rebalance_date.tolist()
    fig, (left, right) = panels()
    for field, label, color in [("completion_30", "30 分钟", AMBER), ("completion_60", "60 分钟", TEAL), ("completion_day", "当日", NAVY)]:
        left.plot(range(len(rows)), rows[field]*100, marker="o", color=color, label=label)
    for side, label, color in [("buy", "买入", TEAL), ("sell", "卖出", AMBER)]:
        right.plot(range(len(rows)), rows[f"{side}_completion_day"]*100, marker="o", color=color, label=label)
    left.set_title("A  每次调仓进行到哪里", loc="left", pad=10)
    right.set_title("B  当天买入和卖出完成多少", loc="left", pad=10)
    for ax in [left, right]:
        date_axis(ax, dates)
        ax.set_ylim(-3, 105)
        ax.set_ylabel("完成率（按本次计划金额，%）")
        ax.legend(fontsize=7, loc="lower left")
    save(fig, output, "02_rebalance_completion", "1 亿元、10% 参与率；每次按当天实际需要买卖的全部金额计算，首次没有卖出需求。")


def position_gap(summary, batches, output):
    capital = summary.capital.max()
    rows = select(batches, capital).sort_values("rebalance_date")
    dates = rows.rebalance_date.tolist()
    fig, (left, right) = panels()
    x = np.arange(len(rows))
    buy = rows.buy_shortfall_reference_notional/rows.sizing_nav*100
    sell = rows.unsold_reference_notional/rows.sizing_nav*100
    left.bar(x, buy, color=TEAL, label="还没买到")
    left.bar(x, sell, bottom=buy, color=AMBER, label="还没卖掉")
    left.set_title("A  收盘持仓与本次目标的差距", loc="left", pad=10)
    left.set_ylabel("差额 / 调仓时净资产（%）")
    left.legend(fontsize=7)
    for model in ["p0.05", "p0.1", "p0.2"]:
        group = select(batches, capital, model).sort_values("rebalance_date")
        right.plot(range(len(group)), group.demand_reference_notional/group.sizing_nav*100,
                   marker="o", color=COLORS[model], label=LABELS[model])
    right.set_title("B  这次实际需要买卖多少", loc="left", pad=10)
    right.set_ylabel("买卖计划金额 / 净资产（%）")
    right.legend(fontsize=7)
    for ax in [left, right]:
        date_axis(ax, dates)
    save(fig, output, "03_position_gap", "1 亿元；左图为 10% 参与率，按同一参考价换算；右图买卖相加，不相互抵消。")


def capital_results(summary, output):
    capitals = sorted(summary.capital.unique())
    fig, (left, right) = panels()
    for model in MODELS:
        rows = summary.loc[summary.model.eq(model)].sort_values("capital")
        style = "--" if model=="reference" else "-"
        left.plot(range(len(rows)), rows.total_return_pct, marker="o", color=COLORS[model], ls=style, label=LABELS[model])
        right.plot(range(len(rows)), rows.max_drawdown_pct, marker="o", color=COLORS[model], ls=style)
    left.set(title="A  全期收益（不计费用）", ylabel="累计收益（%）")
    right.set(title="B  全期最大回撤", ylabel="从此前高点下跌（%）")
    for ax in [left, right]:
        ax.set_xticks(range(len(capitals)), [f"{c/1e4:,.0f}" for c in capitals])
        ax.set_xlabel("初始资金（万元）", labelpad=7)
    legend(fig, left)
    save(fig, output, "04_capital_results", "7/31 至 9/4 的连续账户；每组按自己的净资产调仓，资金档位在图上等距排列。")


def validate(summary, daily, orders, targets, batches, signals, metadata):
    assert (metadata["start"], metadata["end"], metadata["trading_days"])==("2026-07-31", "2026-09-04", 26)
    assert metadata["rebalance_dates"]==[f"2026-08-{day}" for day in ["03", "10", "17", "24", "31"]]
    assert metadata["stock_count"]==30
    assert not summary.scenario.duplicated().any(), "每个连续场景只能有一行汇总"
    assert set(summary.model)==set(MODELS), "必须保留全部五种比较方法"
    assert len(summary)==summary.capital.nunique()*len(MODELS)
    assert summary.audit_passed.astype(str).str.lower().isin(["true", "1"]).all()
    assert summary.total_fees.eq(0).all() and orders.fee.eq(0).all(), "本版报告只接受所有费用严格为零的新结果"
    assert all(metadata["fees"][name]==0 for name in ["buy_rate", "sell_rate", "minimum"])
    assert metadata["financing_rate"]==0 and metadata["cash_buffer"]==0 and metadata["funding_mode"]=="sufficient"
    assert not daily.duplicated(["scenario", "trade_date"]).any()
    assert not batches.duplicated(["scenario", "rebalance_date"]).any()
    expected_dates = sorted(daily.trade_date.unique())
    assert expected_dates[0]==metadata["start"] and expected_dates[-1]==metadata["end"]
    assert len(expected_dates)==metadata["trading_days"]
    for row in summary.itertuples():
        path = daily.loc[daily.scenario.eq(row.scenario)].sort_values("trade_date")
        assert path.trade_date.tolist()==expected_dates, "不能删掉中间交易日"
        values = path.nav.to_numpy(float)
        assert np.isclose(values[0], row.capital), "7/31 应保留全现金、无交易的起点"
        assert np.allclose(path.normalized_nav, values/row.capital)
        assert np.allclose(path.cumulative_return, values/row.capital-1)
        assert np.allclose(path.daily_return, values/np.r_[row.capital, values[:-1]]-1)
        drawdown = values/np.maximum.accumulate(np.r_[row.capital, values])[1:]-1
        assert np.allclose(path.drawdown, drawdown)
        assert np.isclose(row.total_return_pct, (values[-1]/row.capital-1)*100)
        assert np.isclose(row.max_drawdown_pct, max(0, -drawdown.min()*100))
        parents = orders.loc[orders.scenario.eq(row.scenario)]
        amounts = parents.quantity*parents.reference_price
        assert np.isclose(row.demand_reference_notional, amounts.sum())
        for source, target in [("completion_30m", "completion_30"), ("completion_60m", "completion_60"), ("completion_eod", "completion_day")]:
            assert np.isclose(getattr(row, target), (parents[source]*amounts).sum()/amounts.sum())
        reference = summary.loc[summary.capital.eq(row.capital) & summary.model.eq("reference")].iloc[0]
        assert np.isclose(row.return_diff_pp, row.total_return_pct-reference.total_return_pct)
    assert np.allclose(orders.quantity, orders.filled_quantity+orders.remaining_quantity)
    for frame in [summary, batches]:
        assert frame.completion_30.le(frame.completion_60+1e-10).all()
        assert frame.completion_60.le(frame.completion_day+1e-10).all()
        assert frame.completion_day.between(0, 1+1e-10).all()
    assert np.allclose(targets.economic_position, targets.actual_position+targets.receivable_quantity)
    assert np.allclose(targets.net_quantity, targets.target_quantity-targets.economic_position)
    # Same weights, not the same future order quantities: each account has its own NAV and holdings.
    weights = targets.groupby(["submitted_at", "instrument"]).target_weight.nunique()
    assert weights.eq(1).all()
    assert targets.groupby(["scenario", "submitted_at"]).instrument.nunique().eq(30).all()
    assert targets.groupby("scenario").submitted_at.nunique().eq(5).all()
    assert batches.groupby("scenario").rebalance_date.nunique().eq(5).all()
    assert signals.groupby("rebalance_date").target_weight.sum().sub(1).abs().lt(1e-10).all()
    assert signals.signal_date.lt(signals.rebalance_date).all()
    for _, row in batches.iterrows():
        parents = orders.loc[orders.scenario.eq(row.scenario) & orders.submitted_at.eq(row.submitted_at)]
        amount = parents.quantity*parents.reference_price
        assert np.isclose(row.demand_reference_notional, amount.sum())
        assert np.isclose(row.position_gap_reference_notional, row.buy_shortfall_reference_notional+row.unsold_reference_notional)
        assert np.isclose(row.position_gap_pct_nav, row.position_gap_reference_notional/row.sizing_nav*100)


def write_results(summary, daily, orders, batches, actions, metadata, root):
    capital = summary.capital.max()
    large = select(summary, capital).iloc[0]
    small = select(summary, summary.capital.min()).iloc[0]
    reference = select(summary, capital, "reference").iloc[0]
    selected_batches = select(batches, capital).sort_values("rebalance_date")
    def percent(value, digits=2):
        return f"{value:.{digits}f}\\%"
    def signed(value, digits=2):
        return f"{value:+.{digits}f}"
    commands = {}
    commands["StudyConclusion"] = (
        f"结果显示：在 1 亿元资金、10\\% 参与率下，账户最终{('亏损' if large.total_return_pct<0 else '盈利')} {percent(abs(large.total_return_pct))}，"
        f"比假设所有股票都能按参考价格顺利成交的情况{('多亏了' if large.return_diff_pp<0 and reference.total_return_pct<0 else '少赚了' if large.return_diff_pp<0 else '多赚了')} "
        f"{abs(large.return_diff_pp):.2f} 个百分点，期间最大回撤为 {percent(large.max_drawdown_pct)}。每次调仓的成交进度及收盘持仓差距见后文。")
    commands["TradingDays"] = str(metadata["trading_days"])
    commands["ScenarioCount"] = str(len(summary))
    commands["OrderCount"] = f"{len(orders):,}"
    commands["RebalanceCount"] = str(len(metadata["rebalance_dates"]))
    commands["NavNarrative"] = (
        f"图中每条线都是从 7 月 31 日开始、初始资金 1 亿元的一个账户。"
        f"10\\% 参与率账户最后的净值为 {large.final_nav/capital:.4f}，"
        f"参考账户为 {reference.final_nav/capital:.4f}。右图的最大回撤分别为 {percent(large.max_drawdown_pct)} 和 {percent(reference.max_drawdown_pct)}。"
        "没有调仓的日期也照常估值，因此曲线包含持仓价格变化，而不是把五次当天收益接起来。")
    commands["CompletionNarrative"] = (
        f"1 亿元、10\\% 参与率的五次买卖计划合计后，30 分钟、60 分钟和当日完成率分别为 "
        f"{percent(large.completion_30*100)}、{percent(large.completion_60*100)}、{percent(large.completion_day*100)}。"
        f"100 万元账户的当日完成率为 {percent(small.completion_day*100)}。"
        "这是各组自己的实际需求完成率；前次少买、少卖会改变下次的需求，不能称为同一份固定订单的对照。")
    commands["ModelRows"] = "\n".join(
        f"{tex(LABELS[model])} & {row.completion_30*100:.2f} & {row.completion_60*100:.2f} & {row.completion_day*100:.2f} & {int(row.incomplete_eod_orders)} \\\\"
        for model in MODELS for row in select(summary, capital, model).itertuples())
    commands["GapNarrative"] = (
        f"1 亿元、10\\% 参与率下，五次调仓收盘后的持仓差距占当次净资产的比例，"
        f"最低为 {percent(selected_batches.position_gap_pct_nav.min())}，最高为 {percent(selected_batches.position_gap_pct_nav.max())}。"
        "左图把差距分成还没有买到的股票和还没有卖掉的股票；两者相加，不用多买一只股票去抵消另一只少买的股票。")
    commands["LifecycleNarrative"] = (
        f"这组共有 {int(large.incomplete_eod_orders)} 笔订单在提出的当天没有全部做完，"
        f"其中 {int(large.ever_carried_orders)} 笔曾因特殊状态延续到后面的交易日；"
        f"研究结束时仍在等待执行的有 {int(large.open_at_end_orders)} 笔。"
        "前一个数字统计每笔任务提出当天，后一个数字只数期末仍有效的任务。普通订单到期后，已经成交的持仓仍留在账户里。")
    source = select(orders, capital)
    filled = source.loc[source.filled_quantity.gt(0)]
    weights = filled.filled_quantity*filled.reference_price
    assert filled.slippage_bps.notna().all() and weights.sum()>0
    slippage = float((filled.slippage_bps*weights).sum()/weights.sum())
    completed = source.loc[source.remaining_quantity.le(1e-9) & source.filled_quantity.gt(0)]
    assert len(completed)>0 and completed.completion_minutes.notna().all()
    commands["ExecutionNarrative"] = (
        f"1 亿元、10\\% 参与率下，有成交部分相对各次参考价的滑点为 {signed(slippage)} bp，"
        "按实际成交股数乘参考价加权，未成交部分不虚构成交价格。正数表示买得更贵或卖得更便宜，1 bp 等于 0.01\\%。"
        f"到本窗口结束，共 {len(completed)} 笔订单已全部做完，完成用时的中位数为 {completed.completion_minutes.median():.1f} 个交易分钟；"
        f"另有 {int(source.remaining_quantity.gt(1e-9).sum())} 笔历史订单仍有未完成数量，不放进耗时中位数。"
        "用时不计午休和隔夜；这些价差还含等待期间的市场价格变化，不能都称为自身下单造成的冲击。")
    commands["CapitalRows"] = "\n".join(
        f"{row.capital/1e4:,.0f} & {signed(row.total_return_pct)} & {signed(row.return_diff_pp)} & {row.max_drawdown_pct:.2f} \\\\"
        for row in summary.loc[summary.model.eq("p0.1")].sort_values("capital").itertuples())
    commands["ReturnNarrative"] = (
        f"图中比较同一选股方法在不同初始资金下的全期结果。1 亿元、10\\% 参与率的收益差为 "
        f"{signed(large.return_diff_pp)} 个百分点。本轮交易费、税费、最低费和借款利息都为零，不主动预留现金。"
        "收益差包含成交价、成交时间、未买到或未卖掉造成的持仓变化，以及后续按各自净资产重新调仓的影响；不能全部归结为价格冲击。")
    first_action = actions.loc[actions.instrument.str.startswith("000681")]
    second_action = select(actions, capital).loc[lambda rows: rows.instrument.str.startswith("000166")]
    assert len(first_action)==len(summary) and len(second_action)==1
    assert first_action.recorded_quantity.eq(0).all() and first_action.cash_received.eq(0).all()
    action = second_action.iloc[0]
    if actions.recorded_quantity.eq(0).all():
        assert actions.cash_recognized.eq(0).all() and actions.cash_received.eq(0).all()
        commands["ActionNarrative"] = (
            "本窗口有两条已知现金分红：000681 在 7 月 31 日登记、8 月 3 日付款，000166 在 8 月 18 日登记、19 日付款。"
            "25 个账户在两次登记时的持股都为零，实际应收和实收分红也都为零。"
            "因此，真实样本只核对了零持股路径；非零持股的分红入账由合成手算测试验证，不能说这次真实样本已验证实际领取分红。")
    else:
        commands["ActionNarrative"] = (
            "本窗口有两条已知现金分红事件。000681 在 7 月 31 日登记时，全部账户都只有现金，没有持股，因此没有领取这次分红。"
            f"000166 在 8 月 18 日登记、19 日付款；1 亿元、10\\% 参与率账户登记了 {action.recorded_quantity:,.0f} 股，"
            f"实际收到税前现金 {action.cash_received:,.2f} 元。领取金额按各自登记时的真实持股计算，不是所有账户都分到同样金额。")
    additional = metadata["additional_continuation_stockdays"]
    commands["QualityNarrative"] = (
        f"本窗口保存并读取 {metadata['raw_stockdays']:,} 个股票日、{metadata['raw_snapshot_rows']:,} 条原始快照，"
        f"其中额外补充了 {len(additional)} 个非调仓股票日的续单行情。"
        f"日线估值中，有 {metadata['stale_valuation_stockdays']} 个股票日凭明确停牌证据沿用此前收盘价。"
        "这些数量只描述实际需要并核对过的输入，不表示 30 只股票每个交易日的 L2 都已完整取得。")
    commands["ValidationNarrative"] = (
        f"{len(summary)} 组连续账户、{len(orders):,} 笔订单全部通过引擎账户核对。"
        f"本次代码版本为 \\texttt{{{tex(metadata['engine_commit'][:7])}}}，{int(metadata['test_suite'].split()[0])} 项引擎测试通过。"
        "重画脚本另外检查每天净资产能否算回累计收益和回撤、是否保留全部交易日、成交与剩余股数是否守恒，以及各次调仓合计是否与完成率一致。"
        "同一时点各组必须使用相同的目标权重，但不会要求它们未来的订单股数相同。")
    (root/"results.tex").write_text("% Generated from current continuous-study CSV files; do not edit numbers here.\n"+"\n".join(
        f"\\newcommand{{\\{name}}}{{{value}}}" for name, value in commands.items())+"\n")


def main():
    parser = argparse.ArgumentParser(description="从连续账户的派生数据重画中文报告；不连接数据库。")
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--data", type=Path, default=root/"data")
    parser.add_argument("--output", type=Path, default=root/"figures")
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    tables = {name: pd.read_csv(args.data/f"{name}.csv") for name in ["summary", "daily_nav", "order_metrics", "target_history", "rebalance_metrics", "signals", "corporate_action_summary"]}
    metadata = json.loads((args.data/"study_metadata.json").read_text())
    validate(tables["summary"], tables["daily_nav"], tables["order_metrics"], tables["target_history"], tables["rebalance_metrics"], tables["signals"], metadata)
    args.output.mkdir(parents=True, exist_ok=True)
    setup(args.font)
    nav_path(tables["summary"], tables["daily_nav"], args.output)
    completion(tables["summary"], tables["rebalance_metrics"], args.output)
    position_gap(tables["summary"], tables["rebalance_metrics"], args.output)
    capital_results(tables["summary"], args.output)
    write_results(tables["summary"], tables["daily_nav"], tables["order_metrics"], tables["rebalance_metrics"], tables["corporate_action_summary"], metadata, root)
    print(f"实际 {metadata['trading_days']} 个连续交易日、{len(tables['summary'])} 组账户：4 张 PDF/PNG，正文数字与 CSV 同源。")


if __name__ == "__main__":
    main()
