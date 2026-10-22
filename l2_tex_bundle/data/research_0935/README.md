# 新现金、09:35执行研究的真实状态

2026-10-22。正式default N20、sample3、H20_equal_G1、低G1等权和原H20相位均保留。2024是参与过选参的样本，只能称既有策略的执行压力回放。用户明确采用新账户约定，旧账户仅核账，旧固定成交路径收益不是新基线。

379项测试通过（9.58秒）。这些包含真实源字段/行数核对，以及合成账户的时点、现金、权益和低内存集成回归；合成测试不代表正式回测已经运行。

|实际步骤|已运行范围与状态|
|---|---|
|源目标与pending|68次源新目标、1355日、139409成交origin/余额及完整pending核对；见../sample3_targets/。|
|新账户输入|Jan2—Aug30共162日、八次新目标7642行；前7日现金，Jan11首次开仓；不导入旧账户。|
|首日L2导出|956请求全部留证，3754065行，954非空；300765.SZ有明确停牌，689009.SH日线有成交但无L2且用户确认无其他来源。目标全部保留。|
|首日实际准备|954文件全部逐股读入、保留原60字段后准备Parquet；952只具备10秒内合格参考，另两只最新参考距09:35为12/13秒。0订单、0账户模拟。|
|公司行动|前三期2515证券发现10事件；1项首次可能持有前已登记、已知零权益，账户范围9事件/9版本/9legs。公告覆盖完整，但账户生命周期覆盖缺失，严格准备拒绝。|
|三个窗口预检|Jan2—Mar14为47日，Jan2—Apr15为67日，完整窗口162日；三个CLI均退出2，未生成summary.csv。25情景仅配置，未运行。|
|正式结果|新账户前两三期/全窗口收益、完成率、收益差、指数超额及资金阶梯均未完成，没有容量上限结论。|

`first_day_export.json`为导出前/实际/导出后行数等式，不证明数据库原子快照或同等行数下源值没有变化。`first_day_source_diagnostic.json`和原因CSV描述现行10秒间隔、时段及量额政策；source_invalid含预期首行、午休/交易时段边界，不是一概“坏数据”。原因可重叠，不能将gap次数当丢失成交量。price_bounds实际检查2212773行，未发生交易的其他行不是独立量额认证。

两项非空但参考太旧属于本次显式10秒新鲜度设置下不可用：不能用09:35后新快照倒补。引擎API可显式配置该阈值，本次CLI使用10s，未为通过验收改参数。硬缺项仍包括CDR原目标的零L2和公司行动阶段覆盖；完整日线估值、全日期显式交易环境及后续动态L2仍未验收。单条停牌正面记录不能认证其他行正常，稀疏缺行不能填正常。

目录仅含聚合派生资料：

- `research_protocol.json`：新现金、原目标、T日membership、09:35及股/份声明。
- `actual_preflights.json`：三次真实预检的退出、缺项、未检查阶段、未生成收益状态。
- `first_day_export.json`、`first_day_source_diagnostic.json`、`first_day_source_reason_counts.csv`：真实导出与准备统计，不含完整私人目标清单或逐股参考价格。
- `corporate_action_review.json`：账户范围完整版本导出及覆盖拒绝证据；没有将9个已列事件冒充全部经济事件已验收。
- `test_results.json`、`validation_status.json`：最终测试与正式数据状态。
- `pdf_qa.json`：编译、渲染与用户前11页保护检查。

## 在授权引擎重现

以下相对路径在`factor-liquidity`仓库使用；新输出目录不得已存在。原始矩阵、raw L2、完整账户和服务器配置不随公开bundle发布，无这些本地输入不能重跑真实预检。

```bash
PYTHONPATH=src .venv/bin/python scripts/build_sample3_research_inputs.py \
  --matrices outputs/sample3-targets-20261022/input \
  --official-calendar outputs/sample3-execution-20261022/auxiliary/official_calendar.csv \
  --start 2024-01-02 --end 2024-08-30 --output outputs/my-0935-inputs
PYTHONPATH=src .venv/bin/python scripts/run_sample3_research.py \
  --inputs outputs/sample3-research-0935-20261022/inputs-v2 \
  --raw-l2 outputs/sample3-research-0935-20261022/raw-l2 \
  --auxiliary outputs/sample3-research-0935-20261022/actions-first-three/account-scope \
  --daily outputs/sample3-research-0935-20261022/daily_cdr.csv \
  --states outputs/sample3-research-0935-20261022/positive_suspension_states.csv \
  --end 2024-04-15 --quantity-order-type market --output outputs/my-0935-preflight
PYTHONPATH=src .venv/bin/python -m pytest -q
```

第二条预期退出2；daily_cdr和positive_suspension_states仅是早期缺项证据，不是全组合可执行输入。用end=2024-03-14或2024-08-30和不同输出路径重现另两次预检。真正就绪后需要完整canonical daily和states，以及动态需求所需raw文件与公司行动覆盖，入口才会继续逐日运行。官方日线收盘不能补成09:35可知价格；普通全完成持有日只用官方日线估值，不重新下单。CA当日晚到新股需按本账户登记权益加载当日行情并处理退出。

五档资金/参与率均可重复参数配置；默认25情景。`--capital 1000000 --rate 0.1`默认只选L2单情景；参考另用`--model reference`。双方零费用、不融资、先卖后买，订单数量由各自实际账户决定，后续股数可以不同；共同的是原计划目标协议。数量类型market仅选择合法申报数量上限，不表示重建完整交易所市价委托、保护价或队列。

新增图8仍只显示旧账固定成交路径和目标计数，可在bundle内执行`python scripts/make_sample3_targets.py`重画；`make pdf`用LuaLaTeX编译，`python scripts/build_bundle.py`打包。没有制作不存在的新账户收益图。未运行额外哈希、校验和或指纹验证流程。
