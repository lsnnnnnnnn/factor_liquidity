"""Regenerate the update tables from the bundled public derived CSV files."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/execution_update'
VARIANTS = ['baseline', 'cumulative_only', 'snapshot_only', 'persistent_only', 'szse_000_only', 'main']
LABELS = ['旧规则', '仅累计额度', '仅刷新盘口', '仅保留子单余量', '仅改卖出余股规则', '新比较情景']


def main():
    fixed = pd.read_csv(DATA/'fixed_rule_groups.csv')
    reasons = pd.read_csv(DATA/'residual_reason_summary.csv')
    examples = pd.read_csv(DATA/'hand_examples.csv')
    continuous = pd.read_csv(DATA/'continuous_summary.csv').set_index('path')
    if len(fixed) != 18 or fixed.duplicated(['variant', 'classification']).any():
        raise ValueError('fixed groups must retain 6 rules x 3 original classifications')
    indexed = fixed.set_index(['variant', 'classification'])
    lines = [r'\clearpage', r'\lead{固定同一批母单后，究竟减少了什么}',
        '本次固定旧 22 笔母单、原日初持仓、行情和当日终点，六种规则共实际运行 132 次；另外将同日股票同时推进，44 个订单检查与单独运行的数量、金额一致。旧 22 笔的基线数量和金额全部精确重现。诊断统一使用 1 亿元起始现金和原持仓，使资金充足，不把这一现金假设冒充原账户边界。每次另由成交、借入归还和原始末价重建现金、负债、可卖量、持仓与 NAV，最大独立 NAV 差小于 0.000001 元。',
        r'\begin{table}[H]\centering\small', r'\begin{tabular}{lrrr}',
        r'\toprule 规则 &14 大单余量（万股）&7 尾差余量（股）&22 单余额（万元）\\\midrule']
    for variant, label in zip(VARIANTS, LABELS):
        material = indexed.loc[(variant, 'ordinary_material_residual')]
        tails = indexed.loc[(variant, 'demo_lot_residual')]
        total = fixed.loc[fixed.variant.eq(variant), 'remaining_reference_notional'].sum()
        lines.append(f'{label} &{material.remaining_quantity/1e4:,.2f}&{tails.remaining_quantity:,.0f}&{total/1e4:,.2f}'+r'\\')
    lines += [r'\bottomrule\end{tabular}', r'\caption{全部仍使用 10\% 参与率。余额是历史需求剩余的参考金额合计，不是收益损失或期末挂单。}\end{table}',
        '新比较情景下，14 笔较大订单仍全部未精确完成，剩余 6,305,000 股、参考金额 32,432,858 元。7 笔尾差中 5 笔精确完成，余下 104 股、2,314 元，是 000048 在 8 月 24、31 日的两笔原母单各自带入 52 股；固定券单不能凭修改数量规则虚构这两笔买入。明确停牌的 10,300 股不变。',
        r'\begin{table}[H]\centering\small\begin{tabular}{lrrr}',
        r'\toprule 新比较情景的结果 &笔数&余量（股）&余额（元）\\\midrule']
    reason_labels = {'configured_participation_limit':'已设限额不足', 'normal_market_obstacle':'正常市场障碍：明确停牌',
                     'model_quantity_residual':'数量规则与历史尾差', 'completed':'精确完成', 'needs_investigation':'原因待查'}
    for row in reasons.loc[reasons.variant.eq('main')].itertuples():
        lines.append(f'{reason_labels[row.residual_category]} &{int(row.orders)}&{row.remaining_quantity:,.0f}&{row.remaining_reference_notional:,.2f}'+r'\\')
    lines += [r'\bottomrule\end{tabular}', r'\caption{数据质量与数量原因并列保留，不能因归入额度不足就抹去区间缺量。}\end{table}',
        r'\lead{三个可手算例子：绝对几百万元，不等于额度足够}',
        r'\begin{table}[H]\centering\small\begin{tabular}{lrrrrr}',
        r'\toprule 股票与日期 &需求&全日市场量&旧取整额度&旧成交&新成交\\\midrule']
    selected = examples.loc[examples.variant.eq('main')]
    for symbol, day in [('000529.SZ','2026-08-03'),('000550.SZ','2026-08-03'),('000530.SZ','2026-08-24')]:
        row = selected.loc[selected.instrument.eq(symbol)&selected.start_day.eq(day)].iloc[0]
        values = [row.quantity, row.eod_acc_volume, row.participation_capacity_with_rounding, row.eod_filled_quantity, row.new_filled_quantity]
        lines.append(f'{symbol[:6]} {day[5:]} &'+'&'.join(f'{value/1e4:,.2f}' for value in values)+r'\\')
    lines += [r'\bottomrule\end{tabular}', r'\caption{数量单位均为万股。新规则还受边界、预占和盘口约束，不等于有效窗口总额度全能成交。}\end{table}',
        '000529 的需求为 1,418,400 股，而全日成交量的 10\% 仅 571,560 股；有效窗口未取整额度更少，为 545,211.6 股。000550 的有效额度为 318,200.1 股，旧逐张整手取整仅 227,000 股，旧模型实际成交 203,400 股；新情景成交 316,700 股，仍少于 391,900 股需求。000530 的全日 10\% 为 1,305,849.8 股，看似超过需求，但有效窗口未取整仅 1,261,339.8 股；旧取整后 1,203,100 股，新成交 1,258,600 股，仍剩 15,600 股。',
        '上述有效未取整额度沿用旧口径：该来源之后还须有同一时段、无未知间隔的可执行快照。新增累计模式的已观察额度还可能包含随后遇到边界而必须丢弃的部分，不能全当可成交。三例累计记入分别为 552,541.6、318,760.1、1,262,949.8 股，实际成交后分别丢弃 11,941.6、2,060.1、4,349.8 股；各额度段最终预占均为零。两种来源口径在 CSV 中分列，不混作同一个上限。',
        '复用此前 150 个股票日的量额检查：149 组日末累计与日线一致、1 组明确停牌；45 组区间求和不足，合计少 404,200 股、9,342,869 元。没有重扫同一套检查，也没有用事后累计差分覆盖原字段。L2 价格除以 10,000 为元/股，成交量与盘口量为股，成交额直接为元；逐笔金额按数量乘价格核对。日线与 L2 同源，日末对齐不构成盘中完整性的独立证明。',
        r'\clearpage', r'\lead{连续账户重新运行后的收益与完成率}',
        '从 7 月 31 日同样的 1 亿元现金开始，新增三条完整 26 日路径：参考假设、L2 不限参与率、L2 的 10\% 参与率。现金、持仓、可卖量和债务逐日保留；以后需求按各账户实际状态重算。旧 25 路径结果保留，以下旧 10\% 行为原已运行结果，新设置均重新执行全期，未在旧收益上手工加减。',
        r'\begin{table}[H]\centering\small\begin{tabular}{lrrr}',
        r'\toprule 连续账户 &全期收益（\%）&当日完成（\%）&对参考收益差（百分点）\\\midrule']
    path_labels = [('reference','按参考价全成假设'),('old_p0.1','旧规则 10\%'),('new_p0.1','新比较情景 10\%'),('new_unlimited','新比较情景不限参与率')]
    for key, label in path_labels:
        row = continuous.loc[key]
        lines.append(f'{label} &{row.total_return_pct:.4f}&{100*row.completion_day:.4f}&{row.return_diff_pp:+.4f}'+r'\\')
    newer, older, reference = continuous.loc['new_p0.1'], continuous.loc['old_p0.1'], continuous.loc['reference']
    difference = newer.total_return_pct-older.total_return_pct
    lines += [r'\bottomrule\end{tabular}', r'\caption{本表是调试动量的连续策略对照；参考价全成不是原回测实际执行，也没有同期 100001 指数超额。}\end{table}',
        f'新 10\% 情景比旧规则的全期收益变化 {difference:+.4f} 个百分点，期末净资产变化 {newer.final_nav-older.final_nav:+,.2f} 元；相对参考假设的净资产差为 {newer.final_nav-reference.final_nav:+,.2f} 元。这里的差额属于规则与后续持仓路径的比较，不能冒称正式因子相对原回测执行的流动性差。完成率较高也不保证收益较高。',
        '新 10\% 路径共 91 笔需求，当日精确完成 76 笔；14 笔普通余量由已设限额不足解释，余 6,227,600 股、参考金额 32,054,032 元；另 1 笔明确停牌，9,900 股、64,944 元，次日续成。没有不足 100 股尾差。其全部需求金额为 311,446,782 元，未成需求保留在分母。新路径的停牌数量与旧固定单的 10,300 股不同，正是连续账户重算后续需求的结果。期末现金为零、借款 1,008,314.50 元计负债，应收和费用均为零；无仍有效挂单，历史已到期余量并未消失为假成交。',
        r'\panel{05_execution_update}{左图固定同一批 14 笔较大需求，右图为各账户重算后续需求的连续净值；两类对照的含义不同。}',
        '代码全套 180 项测试通过。固定对照与新连续路径均通过账户核对，并另用成交、借贷和日线收盘价重建每日现金、负债、持仓与 NAV。真实样本中两笔公司行动仍为登记时零持股，非零分红和送转依靠合成测试；没有把零持股样本扩大解释为已完成真实非零权益验证。1 毫秒延迟仅为正延迟的工程设置，不代表原始行情具有 1 毫秒精度。']
    (ROOT/'execution_results_20261021.tex').write_text('\n\n'.join(lines)+'\n')
    print('已从公开 CSV 更新执行规则表与连续收益表。')


if __name__ == '__main__':
    main()
