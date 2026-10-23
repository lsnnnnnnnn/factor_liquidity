# 本轮公开派生统计

daily_nav.csv：每日现金、实际股份市值、权益应收、净值及含初始现金起点的回撤。

window_summary.csv、account_comparison.csv：实际完成窗口的收益、回撤、同资金新参考差值、新目标日固定计划完成率、实际成交滑点、明确完成任务的交易分钟及未完成数量，以及各资金首次原正目标数、取整后正数量、实际建仓数和现金比例。completed=false不代表完整窗口结果。

new_target_progress.csv：各新目标日09:35固定父计划的30/60分钟、当日进度。每天重试不重复累加为独立目标；无计划分母时完成率留空。股与份的未成数量分列，不混加。

data_exposure_daily.csv：原权重中缺参考、停牌、共同关键权益清单、数量限制，以及日终才知道的整日缺L2、状态未知、陈旧估值和未到账权益。日报暴露不可跨日相加冒充新增需求。

unfilled_reasons.csv：固定顺序下的互斥主原因。daily_parent_attempt_unfilled以剩余数量乘本父参考价计；daily_unquantified_target_exposure是数量未定时的理论权重金额，两者分开，不能拼作同一个完成率分母。

上述数据均为汇总，不包含原始L2、逐证券目标、完整流水或连接配置。
