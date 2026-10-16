# 30 股周频独立券单的 L2 执行实验

`main` 维护本次扩样研究。此前两股 L2 小样完整保存在 [`v2`](https://github.com/lsnnnnnnnn/factor_liquidity/tree/v2)，旧分钟 VWAP 报告与实验完整保存在 [`v1`](https://github.com/lsnnnnnnnn/factor_liquidity/tree/v1)。各版源码、数据、图和 PDF 随对应分支保存。

[中文报告](l2_tex_bundle/report.pdf) · [可编辑正文](l2_tex_bundle/main.tex) · [完整 TeX bundle](dist/factor_liquidity_l2_tex_bundle.zip) · [编译与复现](l2_tex_bundle/README.md) · [公开图源口径](l2_tex_bundle/data/README.md)

股票池在研究前按 2026 年 3 月预热成交额分为高、中、低各 10 股，仅覆盖深圳 000 代码子集。计划窗口为 2026-07-01 至 09-30，每周首交易日共 14 次事件；计划覆盖与实际可评估日期分别保留。每次事件独立重置初始持仓和现金，同一事件、同一资金的券单在原参考执行、L2 不限参与率、L2 5%/10%/20% 间冻结。研究比较 30/60 分钟及当日完成率、买卖与流动性层差异、完成用时、成交滑点和当日账户收益差，不将独立事件复利成三个月策略收益。

实际取得 **1,678,487 条快照、13 个事件、390 个非空股票日**；7 月 1 日整池缺 L2，保留覆盖记录并排除该事件。364 个场景（325 主对照、39 敏感性）及 10,920 行母单指标全部通过账户核对，72 项引擎测试通过。

10% 额度参与率下，100 万元组当日金额完成率 **99.14%**；1 亿元组 30/60 分钟及当日分别为 **65.14% / 72.70% / 86.19%**，买入与卖出当日分别为 **80.55% / 97.47%**。1 亿元组相对原参考的独立事件收益差中位数为 **-0.6769 个百分点**，未完成 107 笔母单；这是独立当日比较，不能解释为季度累计收益。报告 PDF 已实际编译并逐页检查，共 5 页。

## 使用

已有 TeX Live / MacTeX（ctex、Fandol、latexmk、LuaLaTeX）时：

```bash
git clone --branch main https://github.com/lsnnnnnnnn/factor_liquidity.git
cd factor_liquidity/l2_tex_bundle
make pdf
```

现成图表随仓库提供，仅编译 PDF 不需要 Python 或数据库。Overleaf 上传 ZIP 中 `l2_tex_bundle` 的内容，主文件选择 `main.tex`，编译器选择 **LuaLaTeX**。图表可用附带派生 CSV 离线重画。

调试动量采用未复权官方日收盘，正式公司因子接口尚未接入。原始 L2、完整账户、私有配置与凭据不进入公开仓库。30/60 分钟为观察点，容量合格线保持未设置，不给出资金容量上限。
