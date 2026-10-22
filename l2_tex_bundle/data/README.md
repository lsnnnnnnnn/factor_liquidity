# 当前报告的公开派生数据

这里只保留新版正文直接使用或用于核对当前状态的数据。旧报告的图源和过程记录保留在 Git 标签 `report-20261022-before-consolidation`，不与当前包混排。

|文件|用途|
|---|---|
|execution_summary.csv|最新规则下三个已实际运行的2026年、1亿元连续账户；不含旧规则行|
|execution_nav.csv|最新10%参与率及参考账户的完整26日净值；不含旧规则曲线|
|targets_2024.csv|正式N20/G1八次新目标的日期、筛选和数量汇总|
|source_reconstruction.json|当前完整原账、目标及pending恢复核对结果|
|research_protocol.json|新现金、09:35、真实股/份研究约定|
|research_status.json|当前2024正式组合运行状态及尚未验收项|
|first_day_preparation.json|首日956目标的实际原始行情准备与质量诊断；0订单、0账户模拟|
|corporate_action_review.json|前三期账户范围9项事件及生命周期覆盖缺项|
|test_results.json|已有379项测试通过记录；不代表真实策略收益已运行|

`make figures` 检查收益与初末资产等式、26日净值终点和八次目标汇总，然后重画两张当前图并生成 `current_results.tex`。不连接数据库、不重跑回测、不执行哈希或校验和流程。

2026年调试动量与2024年正式因子不是同一套策略。原复权账本的固定路径退费收益不是新现金账户基线。完整原始L2、证券级目标与持仓、私有凭据不在此包中。
