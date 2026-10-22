# 三矩阵接入后的目标路径与固定原成交窗口

2026-10-22。这里的更新取代此前“缺实际group/membership/prior及逐证券权重”的状态。全部为派生统计，不含证券级目标/持仓、私人五价宽表、完整账户或配置。

- `input_review.json`：三表均1376日期×5166证券；`group==1`，执行日直接读取已滞后的`liquid_prior`；全部68次新目标和96186条原买入满足来源约束。
- `target_reconstruction.json`：全1355日权重、退出及origin路径重建；139409条实际成交的origin与独立递推units全部相等。后补open_observed后恢复全部pending买卖方向及金额，1339次源尝试的计数均一致；原浮点units不是股数。
- `new_targets_2024.csv`：8次新目标的聚合计数；不在2024起点重启H20相位。
- `daily_plan_summary_2024.csv`：全部162日目标与源正持仓数量、权重和、退出计数。源正持仓包含浮点尾数，不是合法股级账户或母单。
- `source_fixed_path_2024.csv`、`source_window_metrics.csv`：从相同观察边界源资产开始，保留原实际成交金额，只返还窗口内费用。2024曲线首值为2023-12-29边界，随后保留162日。不是重新运行零费目标策略、L2收益或指数超额。
- `first_three_coverage_summary.json`、`first_three_role_summary.json`：前三次新目标及其执行前持仓共6007个证券日期，5248复用旧证据、759新查；5961个有L2，46个零行/未返回，日线5963个单行、44个零行。仅3个执行日期的整日核查，不能覆盖全部持有日或证明盘中完整。
- `new_target_state_review.json`：两个无L2正目标之一有当日停牌记录；原始日内停牌时段缺失，视图09:30是状态代理，不能当原策略指令时点。另一项是此前已记录的CDR缺L2。
- `test_results.json`、`validation_status.json`：此目录原316项阶段测试保留，最终新增研究入口测试见 ../research_0935/。完整源pending已恢复；源buy/sell尚缺，但不是新09:35实验前置。新现金、真实数量和日内时点已按研究约定实现，正式真实L2、100001和资金阶梯仍未完成。

普通ZIP读取/打包以外不运行额外摘要或完整性校验流程。图8可用 `python scripts/make_sample3_targets.py` 从本目录重画。

- `open_observed_review.json`：两张后补开盘观测表的实际尺寸、类型、交集及原成交标志核对。

最新实验起点为新现金账户，见 `../research_0935/`。本目录全部旧账曲线仅核对来源，不是新现金参考账户基线；6007覆盖范围含旧原持仓，也不是新现金账户实际动态需求。
