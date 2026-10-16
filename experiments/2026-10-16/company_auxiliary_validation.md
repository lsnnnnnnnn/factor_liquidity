# 真实数据辅助口径与接入状态

检查日期：2026-10-16。本记录区分“字典说明”“接口可读”和“样本已验收”，不把其中一项代替另外两项。

10 月 15 日最初未取得 MySQL 入口；10 月 16 日指定配置因权限受阻。用户创建 `sc` 可读的私有副本后，已实际连接 MySQL 并完成下面的逐表探查和两批样本导出。最初受阻的记录仅保留作访问历史，不代表当前状态。

## 本轮实际检查

本轮已通过现有授权连接读取 TDengine 日线表的结构；`stock_kdata.bar_daily` 可读，包含 OHLC、`vol`、`amount`、`pre_close`、`pct_chg`、`adj_factor`、`vwap` 和证券标签。逐股逐日的收盘价、量额及覆盖核对，应以本轮实验的核对输出为准，接口可读本身不代表全部记录已验收。

已重新读取公司数据字典的固定版本 `ac555e58a6dca1531c2c10dab5eae684b4307715`：

- `root/public-dbschema-docs/l2marketdata/db_schema.md`：§1.1、§1.2、§2.1。
- `root/public-dbschema-docs/tushare-stockinfo-limit-y10-calender/db_schema.md`：连接契约、§3、§5.3、§5.4、§6。
- `root/public-dbschema-docs/corporate-actions-equity/db_schema.md`：开头的当前生产契约、严格事件/动作视图、覆盖检查及后部的市场 PIT 说明。

已通过用户授权的 SSH 会话使用服务器现成的 PyMySQL 驱动，凭据仅在服务器读取和使用，没有尝试其他账号或配置。以下 8 个明确授权对象均实际通过 `DESCRIBE`、`SELECT ... LIMIT 0` 和 `SELECT ... LIMIT 1`：

- `stock_fundamentals.trade_cal`
- `stock_fundamentals.tushare_stk_limit`
- `stock_fundamentals.v_stock_st_daily_market_pit`
- `stock_fundamentals.tushare_suspend_daily`
- `stock_fundamentals.v_suspend_state_daily_market_pit`
- `corporate_actions_v2_v5.v_corporate_action_event_versions_pit_strict`
- `corporate_actions_v2_v5.v_corporate_action_action_legs_pit_strict`
- `corporate_actions_v2_v5.corporate_action_coverage`

逐表结构和探查状态保存在本地忽略目录 `data/auxiliary_probe_20261016/`。样本导出只执行只读事务，单次最多 200 行，按明确键排序分页；每张导出表的前后 `COUNT(*)` 都与实际文件行数一致。各页属于独立只读事务，这种核对不等于认证了历史修订版本或整个导出期间的同一数据库快照。

| 数据 | 本轮状态 | 尚需的验证 |
|---|---|---|
| `stock_kdata.bar_daily` | 两批实际导出588、4,465行；可比较的588、4,406个股票日收盘与成交量均对齐；正式收盘已用于信号与日终估值 | 扩大样本仍缺5个日线股票日，不能由日线对齐证明分钟覆盖完整 |
| `stock_fundamentals.trade_cal` | 两个窗口自然日完整，分别69、222行；已映射`SZSE`并按真实开市日推动执行期限 | 不用股票行情缺行推算休市日 |
| 每日涨跌停价 | 原12股588行、扩大30股4,470行；键齐全且唯一，实际均为有效正值；已应用整根bar锁板约束 | 本轮未遇无涨跌幅限制哨兵；未知哨兵仍拒绝当作普通限价 |
| 历史停复牌、ST | 原窗口三类状态/事件查询均成功返回 0 行；扩大窗口 ST 247、停牌状态 5、停复牌事件 9 行 | 正状态记录不能证明缺行日期正常；逐日覆盖与盘中生效时间仍需判断 |
| 公司行动 | 原窗口5个严格版本/5条动作腿，1条登记日在样本前、初始空仓，余4条进入可用动作；扩大窗口18个版本/19条动作腿；现金和整数送转已入账并审计 | 覆盖表666、775行仍有阶段区间空洞；个人后续股息税、金额尾数和其他事件族未全面认证 |
| 历史交易规则 | 未提供完整证据 | 按日期生效的数量单位、零股、费用和可卖规则 |

原实验的演示交易规则和未验收标志不能因为本轮取得日线而自动改为真实制度已验证。

## 日线的使用口径

字典规定 `bar_daily.ts` 为**裸北京时间的日期键**。例如 REST 返回 `2026-07-10T00:00:00.000Z`，交易日就是 7 月 10 日；不做 UTC 到北京时间的加八小时转换。

价格单位为元/股，`vol` 为股，`amount` 为人民币元，均为当日总量。`close` 在字典中定义为交易所正式收盘价；它不是直接对所有证券承诺等于最后一根分钟快照价。应保留并报告两者的实际差异，不改动分钟价格来制造一致。

全天量额核对要包含独立的 09:30 开盘竞价和 15:00 收盘记录。执行回放排除开盘竞价后剩余分钟的量额，不能直接当作全天总量对账。`pre_close` 为交易所发布的当日前收盘基准，除权除息日可能不同于上一交易日的裸收盘价；出现差异可作为进一步核查提示，不能据此直接推算账户应收现金或新增股份。

`adj_factor` 是预留列，字典明确当前日更写入 NULL，**不能用作复权因子**。另一个 MySQL 自算因子表也不能替代公司行动的现金、股份和可交易日期账本。

日线在生产系统中最早于 D+1 06:10 的相应任务成功后可靠可用，同键可覆盖，没有完整历史修订版本。当前实验若按市场事件时间回放，必须保留这一说明；不得称为严格还原当时数据库可见版本。日线若用于模拟该生产系统的决策，则还需遵守其可得时间。

## 可接受的最小文件输入

本轮已取得下面涉及的公司日线、日历、限价、状态和公司行动文件；历史制度的完整证明仍未取得。以下字段作为接入契约。CSV 或 Parquet 均可，证券代码保留前导零；未知值保持空，不填成“正常”或“无事件”。每份导出附来源对象、日期区间、查询时间、预期与实际行数、缺口及成功空查询说明。

| 文件 | 最小内容 |
|---|---|
| `daily.csv` | `code, exchange, ts, open, high, low, close, vol, amount, pre_close, pct_chg, vwap`；`ts` 解释后得到交易日期，主键为代码和日期 |
| `calendar.csv` | `exchange, cal_date, is_open, pretrade_date`；包含整个区间的自然日。行情 `SH/SZ` 映射日历 `SSE/SZSE` |
| `limits.csv` | `ts_code, trade_date, up_limit, down_limit`；另附哨兵值解释及可用时点。生产基础表没有 `pre_close`，不要假定该列存在 |
| `suspend.csv` | `ts_code, trade_date, suspend_type, suspend_timing, source`；保留停牌与复牌记录和逐日覆盖说明 |
| `st.csv` | 本轮实际视图字段为 `ts_code, trade_date, is_st, source, market_known_at, pit_at, pit_source, pit_quality, pit_timestamp_safe, pit_usage`；另附覆盖说明 |
| 覆盖记录 | 本轮已取得 `corporate_action_coverage`；其他数据集逐日就绪覆盖尚未取得，不能由公司行动覆盖替代 |

停复牌使用实际可读的 `tushare_suspend_daily` / `v_suspend_state_daily_market_pit`；ST 使用 `v_stock_st_daily_market_pit`。停牌视图有 `is_suspended`、`suspend_timing` 和上述 PIT 字段。扩大窗口的 247 条 ST 记录全部为 `is_st=1`；5 条停牌状态全部为 `is_suspended=1`，其 `pit_usage=execution_constraint_only`，不是普通交易日的完整状态面板。9 条原始事件为 5 条停牌和 4 条复牌。字典将开盘状态保守放到当日 09:30，有明确盘中时刻时按该时刻生效；不可提前变成选股信号，也不可由缺行自动推断可以交易。

## 公司行动的必要证据

本轮已经取得 `corporate_actions_v2_v5` 的以下读取层：

- `v_corporate_action_event_versions_pit_strict`：事件、阶段、版本、`market_known_at` 和版本有效区间。
- `v_corporate_action_action_legs_pit_strict`：证券、动作类型、精确金额或比例、条件及选择权、登记/经济生效/结算/到账/可交易日期。
- `corporate_action_coverage`：事件族、阶段、覆盖起止、候选数、解决数、`review_count`、`unresolved_count`、`status`。

回放需同时判断“该版本在决策时已经可知”和“该账户动作在当前账本日期应发生”，不能只按公告日或除权日过滤。精确比例保留整数分子分母或十进制文本，不从浮点数反推；到账日和股份可交易日分别处理。

**零事件不等于没有公司行动。** 只有相关事件族、阶段和整个窗口均有连续完整覆盖，`status=complete`，且 `review_count=0`、`unresolved_count=0`，才可将空结果解释为已证明的无事件窗口。若覆盖读取有截断、缺段或状态不完整，仍应标为未验收。

该生产库当前正式覆盖分红送转、配股和股权分置改革。拆并股、合并、重整等其他事件族，还需要另外的排除或处理依据，不能因为当前库无记录就认定不存在。

## 本轮公司行动与覆盖区间的实际结果

原 12 股窗口为 2026-07-03—2026-09-09，查到 5 条现金动作，涉及 `000063.SZ`、`000157.SZ`、`000338.SZ`、`000425.SZ` 和 `000651.SZ`。它们来自严格动作视图，不能再把该样本写成“期间没有公司行动”。是否改变账户收益，要进一步按登记日实际持仓、到账日和税口径判断。

扩大 30 股窗口为 2026-03-02—2026-10-09，查到 18 条现金动作和 1 条股份动作。`000034.SZ` 在 5 月 19 日的股份动作比例为 0.4/1，登记日为 5 月 18 日，到账和可交易日均为 5 月 19 日；源字段注明 `largest_remainder` 和需要全局分配，不能未经核对就自行规定零股到账。现金规则注明公告含税金额，不能据此自动确定具体账户后续股息税。

覆盖表的每行均标为 `complete`，复核和未解决计数均为 0；但按事件族、精确阶段、来源和覆盖维度合并起止日期后，仍能看到自然日空洞：

| 核心阶段 | 原 12 股窗口 | 扩大 30 股窗口 |
|---|---|---|
| 分红 `accepted_window` | 连续覆盖全窗 | 缺 10 月 1 日、10 月 3—4 日 |
| 分红 `account_action_lifecycle_v2` | 缺 7 月 3—30 日、9 月 5—6 日 | 缺 7 月 1—30 日及部分 9—10 月日期，详见逐阶段文件 |
| 配股、股改 `monthly_notice_lifecycle` | 连续覆盖全窗 | 缺 10 月 1—9 日 |
| 配股、股改 `daily_notice_lifecycle` | 存在空洞 | 存在空洞 |

公告可能发生在休市日，不能自动删除这些自然日空洞后声称已覆盖。覆盖记录的层级是 `announcement_window`；该阶段的区间完整，也不能替代其他事件族或所有经济生效日的覆盖证明。完整区间与缺口保存在 `coverage_by_family_stage.csv`，核心阶段汇总保存在 `coverage_summary.json`。

## 复跑辅助导出

使用已有两份选股和日期配置，凭据仍只读取服务器私有副本：

```bash
PYTHONPATH=src .venv/bin/python -m factor_liquidity.company_auxiliary_export \
  --config configs/company-tail-export.yaml \
  --output data/company_auxiliary_tail_20261016

PYTHONPATH=src .venv/bin/python -m factor_liquidity.company_auxiliary_export \
  --config configs/company-expanded-export.yaml \
  --output data/company_auxiliary_expanded_20261016
```

输出目录必须为空。`--mysql-env` 仅用于原授权文件与已授权私有副本之间切换；传入含 `~` 的远端路径时应加单引号，留给服务器展开。不会从 TDengine 配置猜测 MySQL 账号。`export_receipt.json` 保存日期、证券、筛选、排序、行数和读取时间；导出数据保持在 Git 忽略目录，不推公共仓库。
