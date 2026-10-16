# L2 快照执行实验：中文报告与 LaTeX bundle

[`main`](https://github.com/lsnnnnnnnn/factor_liquidity/tree/main) 只维护新版 L2 快照执行报告。旧版分钟 VWAP 报告、合成实验和扩展真实样本实验完整保存在 [`v1`](https://github.com/lsnnnnnnnn/factor_liquidity/tree/v1)，需要旧版时切换分支阅读。

先读 [中文报告](l2_tex_bundle/report.pdf)，或下载 [完整 TeX bundle](dist/factor_liquidity_l2_tex_bundle.zip)。[可编辑正文](l2_tex_bundle/main.tex)、[重画与复现说明](l2_tex_bundle/README.md)、[公开派生数据与指标口径](l2_tex_bundle/data/README.md)均在 `l2_tex_bundle/`。

本轮使用两只股票、三个交易日的 22,798 条真实十档快照，比较同一批固定股数需求在参考价、可见盘口不限参与率和滞后参与率约束下的执行。每档只取可见数量，深度不足保留未成交量；普通余单当日终止，30/60 分钟是观察点。

1 亿元、10% 额度参与率下，30/60 分钟及当日参考金额完成率为 **12.11% / 19.41% / 34.06%**，期末净收益 **+0.3839%**，较原参考低 **0.1425 个百分点**。买单仅完成 **1.09%**，正收益不代表调仓完成。正式公司因子尚未接入，指定两股 2024 年压力窗口无可用记录；本轮未设置容量合格线，不给出资金容量上限。

## 使用

已有 TeX Live / MacTeX（含 ctex、Fandol、latexmk、LuaLaTeX）时：

```bash
git clone --branch main https://github.com/lsnnnnnnnn/factor_liquidity.git
cd factor_liquidity/l2_tex_bundle
make pdf
```

现成图表已随仓库提供，仅编译 PDF 不需要 Python 或数据库。修改正文后重新执行 `make pdf`。Overleaf 上传 ZIP 内 `l2_tex_bundle` 的内容，主文件选择 `main.tex`，编译器选择 **LuaLaTeX**。

图表由附带 CSV 离线重画；完整 L2 执行器与授权样本的运行命令见 [bundle 使用说明](l2_tex_bundle/README.md)。公开仓库不包含公司原始 L2、完整账户账本、连接地址或凭据。

整理后的 L2 引擎通过 58 项测试；本轮 28 组账户核对通过。PDF 已实际编译并逐页检查，数据、图表和报告数值采用同一口径。
