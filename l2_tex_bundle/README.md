# 中文因子流动性报告

[报告 PDF](report.pdf) · [正文源码](main.tex) · [完整 bundle](../dist/factor_liquidity_l2_tex_bundle.zip) · [数据说明](data/README.md)

本包仅保留 2026 年 10 月 22 日的最新实验状态。整理前的正文、附录和历史图表见[旧版本](https://github.com/lsnnnnnnnn/factor_liquidity/tree/report-20261022-before-consolidation)。

## 本版包含什么

2026 年执行器实验只展示最新规则下的三个 1 亿元连续账户：参考价全部成交假设、L2 不限参与率、L2 的 10% 参与率。它们采用调试用动量策略，观察窗口为 2026-07-31—09-04，共 26 个交易日。10% 路径收益为 −2.9764%，当日完成率为 89.6872%，较参考假设收益低 1.6746 个百分点。旧规则的 25 场景结果不作为本版结果。

正式 N20、sample3、H20_equal_G1 已完成共享价格、原成交、持仓、现金净值、目标及完整待执行状态的恢复核对。新的 2024 年实验从现金、零持仓开始，保留原调仓相位，每天 09:35 决策，按真实股／份和未复权价格记账，不融资，费用为零。它不接续原账户旧持仓，也不把原账本固定成交路径的收益当作新账户基线。

2024 年正式回放尚未开始模拟订单或账户。当前仅完成首日真实数据准备及各窗口预检；689009.SH 缺 L2、公司行动账户生命周期覆盖不完整，仍阻止发布完整收益。保存的最新测试记录为 379 项通过。报告不提供 2024 年完成率、资金阶梯或容量结论。

## 编译、重画与打包

在本目录执行：

```bash
make pdf       # 用随包正文、数字文件和图编译 report.pdf
make figures   # 从公开派生数据重画两组图并更新 current_results.tex
make all       # 先重画，再编译
make bundle    # 重画、编译并生成 ../dist/factor_liquidity_l2_tex_bundle.zip
```

PDF 编译使用现有 **LuaLaTeX、latexmk、ctex、Fandol**。`make pdf` 不调用 Python 或数据库。macOS 若已安装 TeX，可将 `/Library/TeX/texbin` 加入 PATH。

重画使用现有 **pandas、NumPy、Matplotlib**，不需要新增依赖。可以指定已有引擎环境：

```bash
make figures PYTHON=/path/to/engine/.venv/bin/python
make pdf
make bundle PYTHON=/path/to/engine/.venv/bin/python
```

Overleaf 上传 ZIP 中 `l2_tex_bundle` 文件夹内的内容，选择 `main.tex` 为主文件，编译器为 **LuaLaTeX**。`build/` 保存本地编译和绘图缓存，不进入交付 ZIP。

## 文件与结果的对应关系

| 文件 | 内容 |
|---|---|
| `main.tex` | 当前中文正文 |
| `current_results.tex` | 从派生数据生成的报告数字 |
| `figures/01_current_execution.pdf`、`.png` | 最新 2026 年执行账户的图表 |
| `figures/02_current_targets.pdf`、`.png` | 正式策略的 2024 年目标记录 |
| `data/execution_summary.csv` | 最新三个 1 亿元账户的汇总 |
| `data/execution_nav.csv` | 10% 路径和参考账户的 26 日净值 |
| `data/targets_2024.csv` | 2024 年正式策略目标统计 |
| `data/source_reconstruction.json` | 原账本与目标恢复核对 |
| `data/research_protocol.json` | 新现金账户及 09:35 研究规则 |
| `data/research_status.json` | 真实实验当前状态和未完成项 |
| `data/first_day_preparation.json` | 首日 L2 数据准备诊断 |
| `data/corporate_action_review.json` | 公司行动输入及覆盖检查 |
| `data/test_results.json` | 已运行的引擎测试记录 |
| `scripts/make_current_report.py` | 读取上述数据，重画当前图并更新数字 |
| `scripts/build_bundle.py` | 打包报告及公开派生材料 |

重画脚本不访问数据库，不生成订单，也不重算私有回测。修改派生数据后，应重新生成图、数字和 PDF，保持口径一致。原始行情、逐证券完整账本、账户流水和私有配置不在本包；缺少授权输入时，不能将公开图表重画称为真实策略复现。
