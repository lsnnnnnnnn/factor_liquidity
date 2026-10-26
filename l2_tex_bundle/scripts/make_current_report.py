"""Redraw the complete study from public aggregates without editing report prose."""
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

PUBLIC_TABLES = ("daily_nav", "window_summary", "new_target_progress", "data_exposure_daily", "unfilled_reasons")


def model_key(model):
    if model == "reference":
        return (0, 0)
    if model in {"unlimited", "l2_unlimited", "new_unlimited"}:
        return (1, 0)
    number = float(model[1:])
    return (2, number if number < 1 else number/100)


def model_label(model):
    key = model_key(model)
    if key[0] == 0:
        return "参考价账户"
    if key[0] == 1:
        return "L2 不限参与率"
    return f"L2 {key[1]*100:g}%"


def refresh_report(output):
    """Generate five figures for all 25 complete January–August accounts."""
    bundle = Path(output)
    tables = {}
    for name in PUBLIC_TABLES:
        try:
            tables[name] = pd.read_csv(bundle/"data"/(name+".csv"))
        except pd.errors.EmptyDataError:
            tables[name] = pd.DataFrame()
    summary = tables["window_summary"]
    completed = summary.completed.map(lambda value: value is True or str(value).lower() in {"true", "1"})
    end, capital = "2024-08-30", 1e8
    capitals = [1e6, 3e6, 1e7, 3e7, 1e8]
    staircase = summary.loc[completed & summary.end.eq(end)].copy()
    models = sorted(staircase.model.unique(), key=model_key)
    if len(models) != 5 or {model_key(model) for model in models} != {
            (0, 0), (1, 0), (2, .05), (2, .1), (2, .2)}:
        raise ValueError("need reference, unlimited and 5/10/20 percent full-window models")
    if len(staircase) != 25 or set(zip(staircase.capital, staircase.model)) != {
            (value, model) for value in capitals for model in models}:
        raise ValueError("need the complete five-capital by five-model grid through 2024-08-30")
    main_model = next(model for model in models if model_key(model) == (2, .1))

    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import dates as mdates, font_manager
    from matplotlib.ticker import FixedLocator, FuncFormatter
    import matplotlib.pyplot as plt

    figures = bundle/"figures"
    figures.mkdir(exist_ok=True)
    font = subprocess.check_output(["kpsewhich", "FandolHei-Regular.otf"], text=True).strip()
    if not font:
        raise RuntimeError("existing TeX runtime must provide FandolHei")
    font_manager.fontManager.addfont(font)
    navy, teal, gray, amber, purple = "#29465C", "#167C80", "#7D8992", "#C28A40", "#775A85"
    colors = dict(zip(models, [gray, navy, amber, teal, purple]))
    plt.rcParams.update({"font.family": font_manager.FontProperties(fname=font).get_name(),
        "font.size": 8, "axes.titlesize": 9.5, "axes.labelsize": 8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.edgecolor": "#DDE4E8", "axes.labelcolor": navy, "text.color": navy,
        "xtick.color": gray, "ytick.color": gray, "grid.color": "#E6EBEE", "grid.linewidth": .6,
        "axes.unicode_minus": False, "legend.frameon": False, "lines.linewidth": 1.6,
        "savefig.dpi": 300, "pdf.fonttype": 42, "figure.constrained_layout.w_pad": .035,
        "figure.constrained_layout.h_pad": .035})

    def line(ax, x, y, model, marker=None):
        ax.plot(x, y, color=colors[model], label=model_label(model),
            linestyle="--" if model == "reference" else "-", marker=marker, markersize=3.5,
            alpha=.95, zorder=4 if model == main_model else 3)

    def finish(fig, axes, filename, legend=False):
        flat_axes = np.asarray(axes, dtype=object).ravel()
        for ax in flat_axes:
            ax.set_axisbelow(True)
            ax.grid(axis="y")
            ax.tick_params(length=0, pad=4)
        if legend:
            handles, labels = flat_axes[0].get_legend_handles_labels()
            fig.legend(handles, labels, loc="outside upper center", ncol=5,
                fontsize=7, handlelength=2.2, columnspacing=1.3)
        for suffix in ("pdf", "png"):
            fig.savefig(figures/(filename+"."+suffix), bbox_inches="tight", pad_inches=.04)
        plt.close(fig)

    def date_axis(ax, days, events=False):
        values = pd.to_datetime(days)
        ax.set_xlim(values.min(), values.max())
        if events:
            ax.set_xticks(values, values.strftime("%m-%d"), rotation=30)
        else:
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))

    nav = tables["daily_nav"]
    nav = nav.loc[nav.capital.eq(capital) & nav.trade_date.le(end)]
    calendar = nav.loc[nav.model.eq("reference"), "trade_date"].sort_values()
    if (len(calendar) != 162 or calendar.duplicated().any()
            or calendar.iloc[0] != "2024-01-02" or calendar.iloc[-1] != end):
        raise ValueError("retain the full 162-day common NAV calendar")
    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.7), layout="constrained")
    for model in models:
        group = nav.loc[nav.model.eq(model)].sort_values("trade_date")
        if group.trade_date.tolist() != calendar.tolist():
            raise ValueError("each model must retain the entire common NAV calendar")
        dates = pd.to_datetime(group.trade_date)
        line(axes[0], dates, group.normalized_nav, model)
        line(axes[1], dates, group.drawdown*100, model)
    axes[0].axhline(1, color="#BEC8CE", linewidth=.7, zorder=1)
    axes[0].set(title="A  同一现金起点的连续净值", ylabel="净值（初始资金 = 1）")
    axes[1].set(title="B  持有过程中的回撤", ylabel="回撤（%）")
    for ax in axes:
        date_axis(ax, calendar)
    finish(fig, axes, "01_research_nav", legend=True)

    progress = tables["new_target_progress"]
    progress = progress.loc[progress.capital.eq(capital) & progress.date.le(end)]
    event_days = sorted(progress.date.unique())
    if len(event_days) != 8:
        raise ValueError("retain all eight original new-target dates")
    fig, axes = plt.subplots(2, 2, figsize=(6.75, 3.75), layout="constrained")
    for model in models:
        group = progress.loc[progress.model.eq(model)].sort_values("date")
        if group.date.tolist() != event_days:
            raise ValueError("models must preserve the same new-target dates")
        for ax, field, title in zip(axes.ravel(),
            ["completion_30m", "completion_60m", "completion_eod", "eod_quantified_position_gap_nav_fraction"],
            ["A  30个交易分钟", "B  60个交易分钟", "C  当日执行结束", "D  日末已定量持仓差距"]):
            line(ax, pd.to_datetime(group.date), group[field]*100, model, marker="o")
            ax.set_title(title, loc="left")
            ax.set_ylabel("占冻结净资产（%）" if field.endswith("fraction") else "固定计划完成率（%）")
            date_axis(ax, event_days, events=True)
    finish(fig, axes, "02_new_target_progress", legend=True)

    exposure = tables["data_exposure_daily"]
    exposure = exposure.loc[exposure.capital.eq(capital) & exposure.date.le(end)]
    fig, axes = plt.subplots(1, 3, figsize=(6.75, 2.65), layout="constrained")
    for model in models:
        group = exposure.loc[exposure.model.eq(model) & exposure.date.ge(min(event_days))].sort_values("date")
        dates = pd.to_datetime(group.date)
        line(axes[0], dates, group.cash_nav_fraction*100, model)
        if model == main_model:
            for field, text, color in [("missing_reference_weight", "缺参考目标", teal),
                    ("minimum_quantity_weight", "数量单位限制", navy),
                    ("critical_event_excluded_weight", "共同权益清单", amber)]:
                axes[1].plot(dates, group[field]*100, color=color, label=text)
            axes[2].plot(dates, group.stale_valuation_nav_fraction*100, color=teal, label="沿用估值")
            eod_nav = nav.loc[nav.model.eq(model)].set_index("trade_date").nav
            axes[2].plot(dates, (group.cash_receivable+group.share_receivable_value)/group.date.map(eod_nav)*100,
                         color=navy, label="尚未到账权益")
    for ax, title, ylabel in zip(axes, ["A  建仓后现金占比", "B  原目标中的限制", "C  估值与权益"],
                               ["占净资产（%）", "原目标权重（%）", "占净资产（%）"]):
        ax.set(title=title, ylabel=ylabel)
        date_axis(ax, group.date)
        if ax is not axes[0]:
            ax.legend(fontsize=6, loc="upper left", handlelength=1.8)
    finish(fig, axes, "03_data_cash_rights", legend=True)

    reasons = tables["unfilled_reasons"]
    selected_reasons = reasons.loc[reasons.capital.eq(capital) & reasons.model.eq(main_model)
        & reasons.scope.eq("daily_parent_attempt_unfilled") & reasons.date.isin(event_days)]

    def reason_label(reason):
        for terms, title in [(["suspension"], "停牌"), (["participation", "budget"], "参与率额度"),
            (["depth", "opposing"], "盘口数量"), (["source_", "quality_", "reference_", "missing_l2"], "行情或量源"),
            (["quantity", "lot", "board_", "minimum"], "数量单位"), (["sellable"], "可卖或权益"),
            (["cash"], "现金不足"), (["critical_event"], "共同权益清单"), (["daily_limit"], "交易状态资料")]:
            if any(term in str(reason) for term in terms):
                return title
        return "其他已记录限制"
    grouped = selected_reasons.assign(reason_group=selected_reasons.primary_block_reason.map(reason_label))
    grouped = grouped.groupby("reason_group").reference_amount.sum().sort_values()
    fig, ax = plt.subplots(figsize=(6.75, 1.55), layout="constrained")
    bars = ax.barh(grouped.index, grouped/1e4, color=teal, height=.58)
    ax.bar_label(bars, fmt="%.2f", padding=4, fontsize=7)
    if len(grouped) and grouped.max() > 0:
        ax.set_xlim(0, grouped.max()/1e4*1.18)
    ax.set(xlabel="未完成计划金额（万元，按各父单参考价）",
           title="1亿元、10%参与率：新目标日未完成计划的主原因")
    finish(fig, [ax], "04_unfilled_reasons")

    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.8), layout="constrained")
    for model in models:
        group = staircase.loc[staircase.model.eq(model)].sort_values("capital")
        line(axes[0], group.capital/1e4, group.return_pct, model, marker="o")
        line(axes[1], group.capital/1e4, group.completion_eod*100, model, marker="o")
    for ax in axes:
        ax.set_xscale("log")
        ax.xaxis.set_major_locator(FixedLocator(np.asarray(capitals)/1e4))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, position: f"{value:,.0f}"))
        ax.xaxis.set_minor_locator(FixedLocator([]))
        ax.set_xlabel("初始资金（万元，对数轴）")
    axes[0].set(title="A  连续账户全期收益", ylabel="收益（%）")
    axes[1].set(title="B  新目标日固定计划完成率", ylabel="当日完成率（%）")
    finish(fig, axes, "05_capital_staircase", legend=True)
    return dict(bundle=str(bundle), completed_accounts=25, latest_completed_window=end,
        trading_days=162, new_targets=8, figures=["01_research_nav", "02_new_target_progress",
        "03_data_cash_rights", "04_unfilled_reasons", "05_capital_staircase"])


if __name__ == "__main__":
    print(refresh_report(Path(__file__).resolve().parents[1]))
