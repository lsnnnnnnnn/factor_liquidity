# 连续账户实验：报告、源码和图表

`report.pdf` 是中文报告，`main.tex` 是正文，`results.tex` 的数字由附带 CSV 生成。账户在 2026-07-31 全现金开始，到 09-04 共 26 个交易日，每天估值；8 月 3、10、17、24、31 日调仓，共 5 次。没有调仓也不重置账户。

## 编译、重画与打包

```bash
make pdf                     # 用已有正文和矢量图编译 PDF
make figures                 # 用 data/ 重画 PDF/240 dpi PNG，更新 results.tex
make all                     # 重画并编译
make bundle                  # 生成 ../dist/factor_liquidity_l2_tex_bundle.zip
```

使用 Python、Matplotlib、Fandol、LuaLaTeX 和 latexmk，不连接数据库。例如已有引擎环境时可运行 `make all PYTHON=/path/to/engine/.venv/bin/python`。`latexmk`、`lualatex`、`kpsewhich` 需要在 PATH 中，macOS 现有 TeX 位于 `/Library/TeX/texbin`。也可指定画图字体：

```bash
python scripts/make_figures.py --font /path/to/chinese-font.otf
```

临时文件在 `build/`，ZIP 不包含缓存、日志和页面预览。Overleaf 的主文件选 `main.tex`，编译器选 **LuaLaTeX**。修改 CSV 后，要一起更新图、`results.tex` 和报告 PDF，避免数字不一致。

## 这次怎样连续运行

股票沿用研究开始前按 2026 年 3 月成交额选出的 30 只深圳 000 代码股票，成交额高、中、低各 10 只。暂用前 21 个官方交易日收盘价计算 20 日未复权动量，前 15 只目标权重各为 1/15，其余为零。每次只读取此前的价格，不用当天或未来收盘价选股。

每档资金的五个账户从同样现金开始，收到相同排名、目标权重和盘前参考价，但按自己的净资产和实际持仓计算买卖股数。前次未成交会影响后续持仓和需求，所以各组之后的订单不相同。这是在比较同一选股规则连续运行的结果，不能再套用上一版固定股数的比较方式。

净资产为现金加股票市值及应收权益，再减借款。本轮完全不考虑费用：买卖交易费、税费、最低费和借款利息全部为零，不主动预留现金；借入本金不算收益。分红、送转股按登记日真实持股计应收，生效、到账和可卖时间分开，不重复计入收益，现金分红全额计入。

普通订单当天没完成就结束，但已成交持仓留下。只有正面停牌证据，或新鲜收盘盘口触及官方方向限价且没有原始对手盘，剩余任务才可跨日；下次调仓先撤旧单，再按实际持股重算。若有跨日活跃订单，当天缺 L2 且没有停牌证据，程序停止，不能把未知缺失当作零成交。没有活跃订单的日子使用官方日线估值即可。

四张图分别看：全期净值和回撤、五次调仓完成多少、收盘持仓距目标多远以及后续需求、不同资金下的全期收益和回撤。所有收益从同一笔初始资金计算，不能用旧版独立单日收益拼接。

## 使用授权本地数据重新运行

完整引擎和原始数据保存在授权本地；公开包只包含重画所需的派生结果。以下命令在授权引擎目录运行，先检查输入，输出使用新的空目录：

```bash
PYTHONPATH=src MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m factor_liquidity.l2_continuous \
  --data data/company_l2_continuous_stage_20261019 --output outputs/my-continuous-check \
  --start 2026-07-31 --end 2026-09-04 \
  --rebalance-date 2026-08-03 --rebalance-date 2026-08-10 \
  --rebalance-date 2026-08-17 --rebalance-date 2026-08-24 \
  --rebalance-date 2026-08-31 --check-data
PYTHONPATH=src .venv/bin/python -m factor_liquidity.l2_continuous \
  --data data/company_l2_continuous_stage_20261019 --output outputs/my-continuous-zero-fee-study \
  --start 2026-07-31 --end 2026-09-04 \
  --rebalance-date 2026-08-03 --rebalance-date 2026-08-10 \
  --rebalance-date 2026-08-17 --rebalance-date 2026-08-24 \
  --rebalance-date 2026-08-31 --cache-prepared
```

`--check-data` 核对日期、日线、官方限价和公司行动输入；实际逐日执行时，还要核对跨日任务是否有行情，预检通过不代表未来所有续单需求都已知道。缺少任何必要资料时先补资料，不跳过中间日期继续算收益。

`--cache-prepared` 把本窗口已核对的盘口准备结果暂存内存，供不同资金和成交方法复用，减少重复读取；它不缓存账户状态，也不改变每个账户从头连续运行的过程。

本阶段只覆盖连续五周。原季度窗口因 7/1、7/2 的全池 L2 空缺及 7 月权益证据不足，仍标记未完成。公司行动源声明为公告窗口；所列版本已核对，不把它扩大成所有经济事件都完整无遗漏的证明。归档数据可覆盖的历史限制仍然存在，尚未认证生产数据库在每个历史时点的实际可用性。

上一版单日研究在 Git 历史 `51a539f`，两股小样在 `v2`，旧分钟实验在 `v1`。正式公司因子和指定的 2024 年压力数据尚未接入。原始 L2、逐日价格序列、完整账户、服务器和连接配置、凭据不公开，也不生成哈希或校验和。

## 已完成的核对

本轮在零费用设置下重新运行 25 个连续账户，共 650 条日终估值、3,750 条调仓目标、2,255 笔母单，全部通过账户核对。执行代码为 `8e8ffe5`，158 项引擎测试通过。重画前还检查了每个账户的费用合计和每笔订单费用严格为零，以及元数据中的买卖费率、最低费、融资利率和现金预留均为零，拒绝把旧计费结果带入报告。

独立按逐笔记录重建了全部 25 个账户的现金、债务、持仓、权益和净资产；各账户的目标权重合计为 1，没有主动预留现金。桌面交付副本还在零费用下完整运行 26 个交易日、100 万元的参考、不限参与率和 10% 参与率三个账户，45 张 CSV 解压后及账户核对 JSON 都与正式结果逐字一致。新输出在桌面交付目录的 `outputs/desktop-zero-fee-smoke-20261019`，核对记录为 `review/desktop_reproduction.json`；此前计费的桌面连续实验路径已归档到 `history_with_fees_20261019`。

报告共 6 页，四组图均附 PDF 和 240 dpi PNG，最终页面全部渲染检查。此前计费结果及其核对记录保留在 Git 历史 `563beed`。
