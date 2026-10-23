from pathlib import Path
import json
import numpy as np
import pandas as pd

PUBLIC_TABLES = ('daily_nav', 'window_summary', 'new_target_progress', 'data_exposure_daily', 'unfilled_reasons')

PUBLIC_METADATA_KEYS = ('rule_version', 'factor', 'cash_once', 'fees', 'financing', 'reference_max_age_seconds', 'max_source_gap_seconds', 'execution_windows', 'timezone', 'initial_date', 'full_calendar_end', 'fixed_critical_event_excluded_security_count')

def _truth(series):
    return series.map(lambda value: value is True or str(value).lower() in {"true", "1"})


def compare_accounts(summaries):
    """Join each capital/window to its own newly run reference account."""
    combined = pd.concat(summaries, ignore_index=True)
    baseline = combined.loc[combined.model.eq("reference"), ["capital", "end", "return_pct", "final_nav"]]
    if baseline.duplicated(["capital", "end"]).any():
        raise ValueError("more than one reference account for a capital/window")
    baseline = baseline.rename(columns={"return_pct": "reference_return_pct", "final_nav": "reference_final_nav"})
    result = combined.merge(baseline, on=["capital", "end"], how="left", validate="many_to_one")
    result["return_difference_pp"] = result.return_pct-result.reference_return_pct
    result["asset_difference_cny"] = result.final_nav-result.reference_final_nav
    return result


def export_public_aggregates(stats, directory):
    """Export only these explicitly aggregated tables; never arbitrary run files."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for name in PUBLIC_TABLES:
        table = stats[name]
        if any(any(token in column.lower() for token in ("instrument", "stock_code", "action_id", "order_id", "source_file")) for column in table.columns):
            raise ValueError("private identity field in public aggregate")
        path = directory/(name+".csv")
        table.to_csv(path, index=False)
        outputs.append(str(path))
    return outputs


def collect_report_data(output):
    """Export the public report inputs without importing plotting or TeX tools."""
    output = Path(output)
    public_source = (output/"data/window_summary.csv").exists()
    sources = [output/"data"] if public_source else sorted(path.parent for path in output.rglob("statistics/window_summary.csv"))
    if not sources:
        raise ValueError("no actual account statistics are available")
    tables = {}
    for name in PUBLIC_TABLES:
        frames = []
        for directory in sources:
            try:
                frames.append(pd.read_csv(directory/(name+".csv")))
            except pd.errors.EmptyDataError:
                continue
        tables[name] = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    summary = compare_accounts([tables["window_summary"]])
    completed = summary.loc[_truth(summary.completed)].copy()
    bundle = output if public_source else output/"report_bundle"
    export_public_aggregates(tables, bundle/"data")
    summary.to_csv(bundle/"data/account_comparison.csv", index=False)
    metadata_file = bundle/"data/research_metadata.json"
    if not public_source and (output/"run_config.json").exists():
        private_config = json.loads((output/"run_config.json").read_text())
        metadata = {key: private_config[key] for key in PUBLIC_METADATA_KEYS if key in private_config}
        metadata["fixed_critical_event_excluded_security_count"] = len(private_config.get("critical_event_exclusions", []))
    else:
        existing_metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}
        metadata = {key: existing_metadata[key] for key in PUBLIC_METADATA_KEYS if key in existing_metadata}
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n")
    return dict(bundle=bundle, sources=sources, tables=tables, summary=summary,
        completed=completed, metadata=metadata)


def refresh_report(output):
    """Refresh the shareable Chinese bundle from actual account aggregates."""
    collected = collect_report_data(output)
    bundle, sources, tables, summary, completed, metadata = (collected[key] for key in
        ("bundle", "sources", "tables", "summary", "completed", "metadata"))
    if completed.empty:
        raise ValueError("no requested real-account window is complete yet")
    import subprocess
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager
    import matplotlib.pyplot as plt

    figures = bundle/"figures"
    figures.mkdir(exist_ok=True)
    font = subprocess.check_output(["kpsewhich", "FandolHei-Regular.otf"], text=True).strip()
    if not font:
        raise RuntimeError("existing report TeX runtime must provide FandolHei")
    font_manager.fontManager.addfont(font)
    navy, teal, gray = "#29465C", "#167C80", "#7D8992"
    plt.rcParams.update({"font.family": font_manager.FontProperties(fname=font).get_name(),
        "font.size": 8, "axes.titlesize": 10, "axes.labelsize": 8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.edgecolor": "#DDE4E8", "axes.labelcolor": navy, "text.color": navy,
        "xtick.color": gray, "ytick.color": gray, "grid.color": "#E6EBEE", "grid.linewidth": .6,
        "axes.unicode_minus": False, "legend.frameon": False, "lines.linewidth": 1.7, "savefig.dpi": 240})
    models = sorted(completed.model.unique(), key=lambda name: (name != "reference", name))
    palette = [gray, teal, navy, "#C28A40", "#775A85"]
    colors = {model: palette[i % len(palette)] for i, model in enumerate(models)}

    def label(model):
        if model == "reference":
            return "参考价账户"
        if model in {"unlimited", "l2_unlimited", "new_unlimited"}:
            return "L2 不限参与率"
        if model.startswith("p") and model[1:].isdigit():
            return "L2 "+str(int(model[1:]))+"%"
        if model.startswith("p"):
            try:
                return "L2 "+f"{float(model[1:])*100:g}"+"%"
            except ValueError:
                pass
        return model

    def finish(fig, axes, filename):
        for ax in np.asarray(axes, dtype=object).ravel():
            ax.set_axisbelow(True)
            ax.grid(axis="y")
            ax.tick_params(length=0)
        for suffix in ("pdf", "png"):
            fig.savefig(figures/(filename+"."+suffix), bbox_inches="tight")
        plt.close(fig)

    capital = 1e8 if completed.capital.eq(1e8).any() else float(completed.capital.max())
    focus = completed.loc[completed.capital.eq(capital)]
    main_model = next((m for m in ("p0.1", "p10") if m in set(focus.model)),
                      next((m for m in models if m != "reference"), "reference"))
    reference_ends = set(focus.loc[focus.model.eq("reference"), "end"])
    model_ends = set(focus.loc[focus.model.eq(main_model), "end"])
    end = str(max(reference_ends & model_ends if reference_ends & model_ends else model_ends))
    focus = focus.loc[focus.end.le(end)]
    nav = tables["daily_nav"].loc[tables["daily_nav"].capital.eq(capital)]
    nav = nav.loc[nav.trade_date.le(end)]
    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.65), layout="constrained")
    for model, group in nav.groupby("model", sort=False):
        group = group.sort_values("trade_date")
        x = np.arange(len(group))
        axes[0].plot(x, group.normalized_nav, label=label(model), color=colors.get(model, navy))
        axes[1].plot(x, group.drawdown*100, label=label(model), color=colors.get(model, navy))
        ticks = np.unique(np.linspace(0, len(group)-1, min(6, len(group)), dtype=int))
        for ax in axes:
            ax.set_xticks(ticks, group.trade_date.iloc[ticks].str[5:], rotation=25)
    axes[0].set(title="A  同一现金起点的连续净值", ylabel="净值（初始资金 = 1）")
    axes[1].set(title="B  从历史最高净值计算回撤", ylabel="回撤（%）")
    axes[0].legend(fontsize=7)
    finish(fig, axes, "01_research_nav")

    progress = tables["new_target_progress"]
    progress = progress.loc[progress.capital.eq(capital) & progress.date.le(end)]
    fig, axes = plt.subplots(2, 2, figsize=(6.75, 3.8), layout="constrained")
    for model, group in progress.groupby("model", sort=False):
        group = group.sort_values("date")
        x = np.arange(len(group))
        for ax, field, title in zip(axes.ravel(),
            ["completion_30m", "completion_60m", "completion_eod", "eod_quantified_position_gap_nav_fraction"],
            ["A  30个交易分钟", "B  60个交易分钟", "C  当日执行结束", "D  日末已定量持仓差距"]):
            ax.plot(x, group[field]*100, marker="o", markersize=3, label=label(model), color=colors.get(model, navy))
            ax.set_xticks(x, group.date.str[5:], rotation=25)
            ax.set_title(title)
            ax.set_ylabel("占冻结净资产（%）" if field.endswith("fraction") else "固定计划完成率（%）")
    axes[0, 0].legend(fontsize=7)
    finish(fig, axes, "02_new_target_progress")

    exposure = tables["data_exposure_daily"]
    exposure = exposure.loc[exposure.capital.eq(capital) & exposure.date.le(end)]
    fig, axes = plt.subplots(1, 3, figsize=(6.75, 2.5), layout="constrained")
    for model, group in exposure.groupby("model", sort=False):
        # The full-cash opening days remain in NAV and the exported daily data.
        # Show deployed-account variation here instead of compressing it under 100%.
        group = group.loc[group.date.ge(progress.date.min())].sort_values("date")
        x = np.arange(len(group))
        axes[0].plot(x, group.cash_nav_fraction*100, label=label(model), color=colors.get(model, navy))
        if model == main_model:
            axes[1].plot(x, group.missing_reference_weight*100, color=teal, label="缺参考目标")
            axes[1].plot(x, group.minimum_quantity_weight*100, color=navy, label="数量单位限制")
            axes[1].plot(x, group.critical_event_excluded_weight*100, color="#C28A40", label="共同权益清单")
            axes[2].plot(x, group.stale_valuation_nav_fraction*100, color=teal, label="沿用估值")
            eod_nav = nav.loc[nav.model.eq(model)].set_index("trade_date").nav
            axes[2].plot(x, (group.cash_receivable+group.share_receivable_value)/group.date.map(eod_nav)*100,
                         color=navy, label="尚未到账权益")
        ticks = np.unique(np.linspace(0, len(group)-1, min(4, len(group)), dtype=int))
        for ax in axes:
            ax.set_xticks(ticks, group.date.iloc[ticks].str[5:], rotation=25)
    for ax, title, ylabel in zip(axes, ["A  建仓后现金占比", "B  原目标中的限制", "C  估值与权益"],
                               ["占净资产（%）", "原目标权重（%）", "占净资产（%）"]):
        ax.set(title=title, ylabel=ylabel)
        ax.legend(fontsize=6)
    finish(fig, axes, "03_data_cash_rights")

    reasons = tables["unfilled_reasons"]
    dates = set(progress.loc[progress.model.eq(main_model), "date"])
    selected_reasons = reasons.loc[reasons.capital.eq(capital) & reasons.model.eq(main_model)
        & reasons.scope.eq("daily_parent_attempt_unfilled") & reasons.date.isin(dates)]

    def reason_label(reason):
        for terms, title in [(["suspension"], "停牌"), (["source_", "quality_", "reference_", "missing_l2"], "行情或量源"),
            (["quantity", "lot", "board_", "minimum"], "数量单位"), (["sellable"], "可卖或权益"),
            (["cash"], "现金不足"), (["participation", "budget"], "参与率额度"),
            (["depth", "opposing"], "盘口数量")]:
            if any(term in str(reason) for term in terms):
                return title
        return "其他已记录限制"
    if len(selected_reasons):
        grouped = selected_reasons.assign(reason_group=selected_reasons.primary_block_reason.map(reason_label))
        grouped = grouped.groupby("reason_group").reference_amount.sum().sort_values()
        fig, ax = plt.subplots(figsize=(6.75, 2.2), layout="constrained")
        ax.barh(grouped.index, grouped/1e4, color=teal, height=.55)
        ax.set(xlabel="未完成计划金额（万元，按各父单参考价）",
               title="新目标日的未成交计划：每笔只归入一个主原因")
        finish(fig, [ax], "04_unfilled_reasons")
    staircase = completed.loc[completed.end.eq(end)]
    has_staircase = staircase.capital.nunique() > 1
    if has_staircase:
        fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.65), layout="constrained")
        for model, group in staircase.groupby("model"):
            group = group.sort_values("capital")
            axes[0].plot(group.capital/1e4, group.return_pct, marker="o", color=colors[model], label=label(model))
            axes[1].plot(group.capital/1e4, group.completion_eod*100, marker="o", color=colors[model], label=label(model))
        for ax in axes:
            ax.set_xscale("log")
            ax.set_xlabel("初始资金（万元，对数轴）")
        axes[0].set(title="A  执行后的账户收益", ylabel="收益（%）")
        axes[1].set(title="B  新目标日固定计划完成率", ylabel="当日完成率（%）")
        axes[0].legend(fontsize=7)
        finish(fig, axes, "05_capital_staircase")

    def fmt(value, digits=4):
        return f"{float(value):.{digits}f}" if pd.notna(value) else "---"
    def tex(value):
        return str(value).replace("_", r"\_").replace("%", r"\%")
    rows = []
    for row in focus.sort_values(["end", "model"]).itertuples():
        rows.append(f"{row.end[5:]} & {tex(label(row.model))} & {fmt(row.return_pct)} & {fmt(row.return_difference_pp)} & {fmt(row.completion_eod*100)} & {fmt(row.max_drawdown_pct)} "+r"\\")
    current = focus.loc[focus.end.eq(end) & focus.model.eq(main_model)].iloc[0]
    timing_rows = []
    for row in focus.loc[focus.end.eq(end)].sort_values("model").itertuples():
        timing_rows.append(f"{tex(label(row.model))} & {row.completed_new_target_parent_count:d} & "
            f"{fmt(row.completed_new_target_mean_trading_minutes, 2)} & {fmt(row.completed_new_target_p90_trading_minutes, 2)} & "
            f"{row.unfinished_new_target_parent_count:d} & {fmt(row.unfinished_new_target_reference_notional/1e4, 2)} "+r"\\")
    first_progress = progress.loc[progress.model.eq(main_model)].sort_values("date").iloc[0]
    first_exposure = exposure.loc[exposure.model.eq(main_model) & exposure.date.eq(first_progress.date)].iloc[0]
    worst_missing = float(exposure.loc[exposure.model.eq(main_model), "missing_reference_weight"].max())*100
    own_progress = progress.loc[progress.model.eq(main_model)].sort_values("date")
    latest_progress = own_progress.iloc[-1]

    def day_text(value):
        day = pd.Timestamp(value)
        return f"{day.month}月{day.day}日"

    progress_observation = (f"首次开仓的{day_text(first_progress.date)}，{tex(label(main_model))}在30分钟、60分钟和当日结束时，"
        f"分别完成 {fmt(first_progress.completion_30m*100, 2)}\\%、{fmt(first_progress.completion_60m*100, 2)}\\%和"
        f"{fmt(first_progress.completion_eod*100, 2)}\\%的当次计划金额。")
    if latest_progress.date != first_progress.date:
        progress_observation += (f"最近一次新目标日{day_text(latest_progress.date)}，三项进度分别为 "
            f"{fmt(latest_progress.completion_30m*100, 2)}\\%、{fmt(latest_progress.completion_60m*100, 2)}\\%和"
            f"{fmt(latest_progress.completion_eod*100, 2)}\\%；30分钟以后又完成了"
            f" {fmt((latest_progress.completion_eod-latest_progress.completion_30m)*100, 2)} 个百分点。")
    progress_observation += "这些进度都对应当天09:35已经固定的计划，后续重试不回写当天的完成比例。\n"
    reference_rows = focus.loc[focus.model.eq("reference") & focus.end.eq(end)]
    incomplete_observation = (f"汇总本窗口{len(own_progress)}次新目标，{tex(label(main_model))}按金额加权的当日完成率为"
        f" {fmt(current.completion_eod*100)}\\%，仍有 {int(current.unfinished_new_target_parent_count)} 笔当次任务未完全成交，"
        f"剩余参考金额合计 {fmt(current.unfinished_new_target_reference_notional/1e4, 2)} 万元。")
    if main_model != "reference" and len(reference_rows):
        reference_current = reference_rows.iloc[0]
        incomplete_observation += (f"参考账户的对应完成率为 {fmt(reference_current.completion_eod*100)}\\%，"
            f"未完 {int(reference_current.unfinished_new_target_parent_count)} 笔、"
            f"{fmt(reference_current.unfinished_new_target_reference_notional/1e4, 2)} 万元。")
    if current.unfinished_new_target_parent_count:
        incomplete_observation += (f"本路径每笔未完任务平均还剩"
            f" {fmt(current.unfinished_new_target_reference_notional/current.unfinished_new_target_parent_count/1e4, 2)} 万元，"
            "完成率按金额计，未完笔数按任务计，两项指标需要一起看。")
    incomplete_observation += "这里统计的是新目标当天的任务，窗口末还未完成的目标另计。\n"
    own_nav = nav.loc[nav.model.eq(main_model)].sort_values("trade_date")
    trough = own_nav.loc[own_nav.drawdown.idxmin()]
    nav_observation = (f"{tex(label(main_model))}在{day_text(trough.trade_date)}出现本窗口最深回撤"
        f" {fmt(-trough.drawdown*100)}\\%，当日净值为 {fmt(trough.normalized_nav)}；")
    nav_observation += ("此后回升，" if own_nav.normalized_nav.iloc[-1] > trough.normalized_nav else "")
    nav_observation += f"期末净值为 {fmt(own_nav.normalized_nav.iloc[-1])}。"
    if main_model != "reference" and len(reference_rows):
        reference_nav = nav.loc[nav.model.eq("reference")].sort_values("trade_date")
        reference_trough = reference_nav.loc[reference_nav.drawdown.idxmin()]
        nav_observation += (f"参考账户在{day_text(reference_trough.trade_date)}出现最深回撤"
            f" {fmt(-reference_trough.drawdown*100)}\\%，期末净值为 {fmt(reference_nav.normalized_nav.iloc[-1])}。")
    nav_observation += "因此，期末收益需要与持有过程中的回撤一起评估；两条连续路径之间的差异也会累积到最后的收益差中。\n"
    critical_event_explanation = ""
    if "fixed_critical_event_excluded_security_count" in metadata:
        critical_event_explanation = (f"全窗口已有事件资料中，{int(metadata['fixed_critical_event_excluded_security_count'])} 只证券的非整数股份分配"
            "需要尚未取得的账户或全体账户分配信息；本次在查看收益前固定共同限制清单，所有资金与情景都从现金起点不交易这些证券，"
            "保留原目标权重。当前路径原目标中被这项清单限制的权重最高为 "
            f"{fmt(current.max_critical_event_excluded_weight*100)}\\%。这是根据现有历史资料确定的数据范围条件，不是当时可用的选股筛选。\n\n")
    own_exposure = exposure.loc[exposure.model.eq(main_model) & exposure.date.ge(first_progress.date)].sort_values("date")
    stale_peak = own_exposure.loc[own_exposure.stale_valuation_nav_fraction.idxmax()]
    exposure_observation = (f"首次建仓日末，{tex(label(main_model))}现金占净资产的"
        f" {fmt(first_exposure.cash_nav_fraction*100, 2)}\\%，到窗口末为 {fmt(current.final_cash_nav_fraction*100, 2)}\\%。")
    if stale_peak.stale_valuation_nav_fraction > 0:
        exposure_observation += (f"沿用估值的账面金额占净资产最高为 {fmt(stale_peak.stale_valuation_nav_fraction*100)}\\%，"
            f"出现在{day_text(stale_peak.date)}；这部分持仓仍保留在账户中，使用以前已知的有效价格估值。")
    rights_fraction = ((own_exposure.cash_receivable+own_exposure.share_receivable_value)
        /own_exposure.date.map(own_nav.set_index("trade_date").nav))
    if rights_fraction.max() > 0:
        exposure_observation += f"两类未到账权益的日末余额占净资产最高为 {fmt(rights_fraction.max()*100)}\\%。\n"
    else:
        exposure_observation += "本窗口已记入账内的两类未到账权益，在日末的余额均为零。\n"
    reason_observation = ""
    if len(selected_reasons):
        largest_reasons = grouped.sort_values(ascending=False).head(2)
        parts = [f"{name} {fmt(amount/1e4, 2)} 万元" for name, amount in largest_reasons.items()]
        reason_observation = ("新目标日剩余计划按主原因分类，金额最多的为"+"、".join(parts)+"。"
            "这说明订单最后停在哪一项检查条件；同一任务此前仍可能受到其他限制。\n")
    source = r"""\documentclass[UTF8,fontset=fandol,11pt,a4paper]{ctexart}
\usepackage[top=18mm,bottom=18mm,left=20mm,right=20mm]{geometry}
\usepackage{amsmath,booktabs,tabularx,array,graphicx,caption,float,setspace,hyperref,needspace}
\hypersetup{hidelinks,pdftitle={因子流动性实验：2024年真实账户结果},pdfauthor={factor-liquidity}}
\setstretch{1.10}\setlength{\parskip}{0.22em}\setlength{\parindent}{2em}
\setlength{\textfloatsep}{8pt}\setlength{\intextsep}{7pt}
\captionsetup{font=small,labelfont=bf,labelsep=quad,skip=4pt}
\newcommand{\lead}[1]{\par\medskip\Needspace{3\baselineskip}\noindent\textbf{#1}\par\smallskip}
\newcommand{\panel}[2]{\begin{figure}[H]\centering\includegraphics[width=\linewidth]{figures/#1.pdf}\caption{#2}\end{figure}}
\clubpenalty=10000\widowpenalty=10000\raggedbottom
\begin{document}
\noindent{\large\bfseries 因子流动性实验}\hfill{\small 2026 年 10 月 23 日}
\lead{实验结论}
"""
    source += (f"本次已将公司的原 G1 目标接入从现金起步的连续账户。对于初始资金 {capital/1e4:,.0f} 万元，"
        f"从 2024 年 1 月 2 日至 {end[5:7]} 月 {int(end[8:])} 日的 {int(current.trading_days)} 个交易日，"
        f"{tex(label(main_model))}收益为 {fmt(current.return_pct)}\\%，比同资金参考账户{('高' if current.return_difference_pp >= 0 else '低')}"
        f" {fmt(abs(current.return_difference_pp))} 个百分点；新目标日可定量计划的当日完成率为 {fmt(current.completion_eod*100)}\\%，"
        f"最大回撤为 {fmt(current.max_drawdown_pct)}\\%。这些是加入实际账户约束后的模拟结果，费用和税费均为零。\n\n")
    source += (f"首次开仓保留 {int(first_progress.original_positive_target_count)} 个正权重目标，其中 "
        f"{int(first_progress.quantified_target_count)} 个取得合格参考并可定量，取整后有 "
        f"{int(first_progress.positive_integer_target_count)} 个正数量目标，日末实际持有 "
        f"{int(first_exposure.actual_positive_holding_count)} 只证券。无法取得参考的目标仍保留原权重，其他证券没有因此增权。"
        f"本路径每日缺参考目标权重最高为 {fmt(worst_missing)}\\%；下文的订单完成率只衡量已经定量的计划，不能代表全部原目标都已完成。\n")
    source += r"""
\lead{因子、数据和实验设置}
沿用原 N20、sample3、\texttt{H20\_equal\_G1}，取原处理后低因子 G1，保持原权重和 H20 相位。正式因子的原始公式是 $f_t=C_t/C_{t-20}-1$，其中 $C$ 为原批次复权收盘价。之后经过缺失处理、去极值、行业和市值中性化及标准化，才分成五组；G1 是处理后因子的低分组，不能直接理解为过去跌幅最大的股票。$N=20$ 是回看期，$H=20$ 是调仓间隔，两者含义不同。

正式组合使用信号日当时的历史100001股票池。目标生成沿用原来的流动性筛选：最近20个正成交额观测的均值严格大于500万元。这是来源策略已有的条件，不是本次新增的容量合格线。调仓直接采用上一交易日已经确定的筛选结果，不再额外延迟一个交易日。股票池退出时目标归零，退出权重不重新分配。

行情使用公司 TDengine 的 \texttt{level2.stb\_depthmarket}，价格和交易量以未复权的元／股或元／份、股或份解释；官方日历、限价、停牌和现有公司行动资料用于共同约束。日线只用于已到日终的估值和库内交叉核对，不作为早晨已知价格。此前合成案例和较新市场小样本用于检查执行程序，本报告的数字均来自这次2024年新账户。

两个账户都在1月2日一次投入同额现金，从零持仓、零历史余单开始；1月2日至10日持现金，1月11日首次开仓。每天09:35先处理已经生效的权益，再以严格早于09:35、年龄不超过30秒的合格价格估值并冻结净资产，一次生成全部证券的当日父计划。执行窗口为09:35至11:30、13:00至14:57，均左闭右开。完成目标不随每日价格变化重新平衡，未完成方向次日重新定量；新目标才重新判断买卖方向。

参考账户以事先确定的参考价作为反事实成交价，不限盘口数量和参与率，但保留现金、数量、T+1、停牌、权益、延迟和共同数据资格约束。L2账户在正延迟后的合格快照按可见对手盘成交，同证券订单共享盘口和累计有效成交量额度，不使用未来成交量。每张合格快照刷新可见深度是一项研究假设，不能据此还原真实排队或自身市场冲击。

\lead{指标怎样计算}
净资产等于真实现金、实际股份市值、现金应收及尚未记入实际股份的应收股份市值之和；本研究不融资。应收到账只是科目移动，不再次增加净资产，未到账现金不能买股。预占资金仍属于现金余额，只限制可用现金，不重复扣减净资产。净值为日末净资产除以唯一初始资金，回撤包含共同现金起点。
\[
\text{计划完成率}=\frac{\sum(\text{已成交数量}\times\text{本父单参考价})}
{\sum(\text{计划数量}\times\text{本父单参考价})}.
\]
买卖金额均按正数汇总，现金不足不缩小分母。30、60分钟按交易时间计算，不含午休；主图只统计每次新目标日固定的计划，不把次日剩余需求再次累加为新需求。缺参考的目标数量未定，单列权重和理论金额。日末持仓差距只对已定量目标计算，不能抵消缺数据暴露。

例如，计划买入60万元、卖出40万元，分别完成45万元和35万元，完成率为80\%。跨多次调仓先汇总金额再相除，不直接平均百分比。市场区间均价可用该区间成交额除以成交量计算，成交量为零时不计算。模拟订单均价则由真正模拟成交的盘口价格与数量计算：卖一10元有200股、卖二10.01元有100股，买入这300股花费3,001元，均价约10.0033元；不能因为市场区间均价为10元就全部按10元成交。

滑点只计算模拟成交部分。买入均价高于参考价、卖出均价低于参考价时记为正，按成交数量乘本次参考价加权，以基点报告。它同时包含等待期间的市场变化，不能全部称为自身冲击。耗时从当日09:35到最后一笔成交，只对明确完成的当日父任务计算交易分钟，不含午休和隔夜；另列未完成任务数量，未成交部分没有虚构成交价或完成时间。

\begin{table}[H]\centering\small
\begin{tabular}{llrrrr}\toprule
窗口截至 & 成交情景 & 收益（\%） & 收益差（百分点） & 当日完成（\%） & 最大回撤（\%）\\\midrule
"""
    source += "\n".join(rows)+r"""
\bottomrule\end{tabular}
\caption{同额初始现金账户的实际完成窗口。收益差为本账户减新参考账户，未运行完成的窗口不填结果。}
\end{table}
\panel{01_research_nav}{每个情景独立保存现金、持仓和权益；成交造成的持仓差异会影响以后的账户净值与调仓数量。}
"""
    source += nav_observation
    source += r"""
\lead{完成速度和持仓差距}
"""
    source += progress_observation
    source += incomplete_observation
    source += r"""
\begin{table}[H]\centering\small
\begin{tabular}{lrrrrr}\toprule
情景 & 当天完成数 & 平均分钟 & 90分位分钟 & 当天未完数 & 未完金额（万元）\\\midrule
"""+"\n".join(timing_rows)+r"""
\bottomrule\end{tabular}
\caption{仅统计新目标日生成的固定父任务，耗时只看其中当天完成者；未完金额按原父参考价计。随后重试不回写这些首日计划的完成率，当前目标状态另列。}
\end{table}
"""
    source += (f"截至该窗口末日，{tex(label(main_model))}仍有 "
        f"{int(current.final_unfinished_current_positive_target_direction_count)} 个正权重目标的执行方向尚未结束；"
        f"这包含数据或数量限制，不只包含参与率不足。全部实际模拟成交的加权滑点为 {fmt(current.filled_slippage_bps, 2)} 个基点。"
        "这些成交价格指标不为未成交部分补造价格。\n")
    source += r"""
\panel{02_new_target_progress}{新目标日固定父计划的30分钟、60分钟、当日进度，以及已定量部分的日末持仓差距。}
\lead{现金、缺数据和权益限制}
缺少合格早晨参考的证券当天不生成虚构数量，次日重试；有持仓时缺L2只暂停相关执行，不把持仓变回现金。有效日线用于日终估值，日线也缺时沿用最近已知估值并记录暴露。坏量源区间不授额度，断点后的第一张快照只建立新基准；异常造成的限制与市场本身成交容量分开解释。

现金比例既受未成交影响，也受最小申报单位和后续持仓变化影响；它不被强制调整为缺数权重对应的金额。图中的“数量单位限制”按目标证券去重，包括取整为零及正数量仍低于合法新申报要求的情况。“尚未到账权益”计入净资产，但不能当作已到账现金或已可卖股份使用。
"""
    source += exposure_observation
    source += r"\panel{03_data_cash_rights}{首次建仓后的现金比例，以及缺参考、数量限制、陈旧估值和应收权益暴露；此前全现金日已在图1和每日数据中保留。}"+"\n"
    if len(selected_reasons):
        source += reason_observation
        source += r"\panel{04_unfilled_reasons}{仅统计新目标日的未成交父计划，每笔按固定检查顺序归入一个主原因；同一金额不重复加到多个原因。其他限制仍保留在本地逐笔记录中。}"+"\n"
    if has_staircase:
        source += r"""
\lead{资金规模与执行结果}
各资金档从各自同额现金起点独立运行，沿用同一原目标、数据规则和共同事件清单。资金关系图展示本次已完成账户；低资金档受最小单位影响，高资金档则可能更受可用现金、盘口和参与率额度约束，不能把这些机制统称为流动性损失。尚未确定最低业务收益要求，因此本报告不据此宣告容量上限。
\panel{05_capital_staircase}{相同窗口内，初始资金与执行后收益、新目标日固定计划完成率的关系。}
"""
        structures = staircase.loc[staircase.model.eq(main_model)].sort_values("capital")
        if len(structures) > 1:
            structure_rows = [f"{row.capital/1e4:,.0f} & {row.first_original_positive_target_count:d} & "
                f"{row.first_positive_integer_target_count:d} & {row.first_actual_positive_holding_count:d} & "
                f"{fmt(row.first_cash_nav_fraction*100, 2)} & {fmt(row.final_cash_nav_fraction*100, 2)} "+r"\\"
                for row in structures.itertuples()]
            source += r"""
\begin{table}[H]\centering\small
\begin{tabular}{rrrrrr}\toprule
资金（万元） & 原正目标数 & 取整后正数 & 首日建仓数 & 首日现金（\%） & 期末现金（\%）\\\midrule
"""+"\n".join(structure_rows)+r"""
\bottomrule\end{tabular}
\caption{10\%路径首次开仓的数量结构与现金比例。原目标数、取整后正数量和实际建仓数分别列出；正数量仍须满足最小申报要求，数量单位限制不等于盘口不足。}
\end{table}
"""
    source += r"""
\lead{研究假设和结果适用范围}
"""
    source += critical_event_explanation
    source += r"""
公司行动按现有事件资料记账，缺全市场完整覆盖声明记为警告。日期明确而时刻未知时，登记在日末锁定资格，除息／权益生效日在09:35前确认经济权益，付款、股份到账和可卖日期均在已知日期结束后更新，下一交易日使用。付款或可卖日期未知而金额、资格和生效明确时保留应收；真正缺少关键经济事实的证券按事先固定共同清单限制交易，原权重保留。复杂权益和整数股份分配不能由程序猜测。

沿用价格跨越明确的简单权益事件时，只做一次理论除权估值调整，保留原市场价格时点；这不是成交价，也不使旧行情变新。真实除权后价格出现后直接替换。主账使用未复权价格和显式权益，不另叠加复权收益。

这些结果说明原 G1 目标在共同数据可用条件、既定现金与权益规则下怎样执行。共同规则不保证缺数据误差完全抵消。100001指数未在本轮核对的系列不填超额收益，也不以其他指数替代；2024年曾参与原策略参数选择，本轮不称为独立样本外检验。
\end{document}
"""
    (bundle/"main.tex").write_text(source, encoding="utf-8")
    import inspect
    script_directory = bundle/"scripts"
    script_directory.mkdir(exist_ok=True)
    standalone = "from pathlib import Path\nimport json\nimport numpy as np\nimport pandas as pd\n\n"
    standalone += "PUBLIC_TABLES = "+repr(PUBLIC_TABLES)+"\n\n"
    standalone += "PUBLIC_METADATA_KEYS = "+repr(PUBLIC_METADATA_KEYS)+"\n\n"
    standalone += "\n\n".join(inspect.getsource(function) for function in
        (_truth, compare_accounts, export_public_aggregates, collect_report_data, refresh_report))
    standalone += '\n\nif __name__ == "__main__":\n    print(refresh_report(Path(__file__).resolve().parents[1]))\n'
    (script_directory/"make_current_report.py").write_text(standalone, encoding="utf-8")
    (bundle/"README.md").write_text("# 2024年真实因子执行研究\n\n"
        "本目录只含本轮连续账户派生汇总、图和中文报告，不含原始L2、逐证券因子、目标及完整流水。\n\n"
        "编译：lualatex -interaction=nonstopmode -halt-on-error main.tex（运行两次）。\n"
        "重画：python scripts/make_current_report.py，仅读取本包data目录的公开派生统计。\n"
        "引擎刷新：PYTHONPATH=src .venv/bin/python scripts/research_results.py --report 本次结果目录。\n",
        encoding="utf-8")
    (bundle/"data/README.md").write_text("# 本轮公开派生统计\n\n"
        "daily_nav.csv：每日现金、实际股份市值、权益应收、净值及含初始现金起点的回撤。\n\n"
        "window_summary.csv、account_comparison.csv：实际完成窗口的收益、回撤、同资金新参考差值、"
        "新目标日固定计划完成率、实际成交滑点、明确完成任务的交易分钟及未完成数量，"
        "以及各资金首次原正目标数、取整后正数量、实际建仓数和现金比例。completed=false不代表完整窗口结果。\n\n"
        "new_target_progress.csv：各新目标日09:35固定父计划的30/60分钟、当日进度。"
        "每天重试不重复累加为独立目标；无计划分母时完成率留空。股与份的未成数量分列，不混加。\n\n"
        "data_exposure_daily.csv：原权重中缺参考、停牌、共同关键权益清单、数量限制，"
        "以及日终才知道的整日缺L2、状态未知、陈旧估值和未到账权益。日报暴露不可跨日相加冒充新增需求。\n\n"
        "unfilled_reasons.csv：固定顺序下的互斥主原因。daily_parent_attempt_unfilled以剩余数量乘本父参考价计；"
        "daily_unquantified_target_exposure是数量未定时的理论权重金额，两者分开，不能拼作同一个完成率分母。\n\n"
        "上述数据均为汇总，不包含原始L2、逐证券目标、完整流水或连接配置。\n", encoding="utf-8")
    return dict(bundle=str(bundle), source=str(bundle/"main.tex"),
        completed_accounts=int(completed[["capital", "model"]].drop_duplicates().shape[0]),
        latest_completed_window=end, public_statistics_sources=len(sources), capital_staircase=has_staircase)


if __name__ == "__main__":
    print(refresh_report(Path(__file__).resolve().parents[1]))
