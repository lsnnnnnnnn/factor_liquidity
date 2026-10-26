# 2024年真实因子执行研究

[中文报告](report.pdf) · [正文源码](main.tex) · [完整bundle](../dist/factor_liquidity_l2_tex_bundle.zip) · [数据口径](data/README.md)

本版为2026年10月26日完成的完整实验：2024-01-02—08-30，共162个交易日、8次新目标；100万、300万、1000万、3000万、1亿元，各运行参考、L2不限参与率、5%、10%、20%参与率，共25组，均通过账户审计。账户从现金、零持仓开始，沿用原 N20、sample3、H20_equal_G1 目标与H20相位，费用、税费为零，不融资。

215只关键权益分配资料不足的证券采用共同交易限制，原权重保留。源库原清单581个整日零L2证券日现已出现记录，本批次仍使用已保存缓存。测试记录为462项通过。研究不称为独立样本外，也不设定资金容量上限。

## 编译与重画

在本目录运行：

```bash
make pdf       # 使用随包正文及矢量图编译report.pdf
make figures   # 仅从data/重画5组PDF和PNG
make all       # 先重画，再编译
make bundle    # 生成../dist/factor_liquidity_l2_tex_bundle.zip
```

`make pdf`使用现有LuaLaTeX、latexmk、ctex和Fandol，不需要Python或数据库。Overleaf选择`main.tex`为主文件，编译器为 **LuaLaTeX**。

重画使用已有pandas、NumPy、Matplotlib环境，可以指定Python：

```bash
make figures PYTHON=/path/to/existing/python
make bundle PYTHON=/path/to/existing/python
```

`make figures`调用`scripts/make_current_report.py`，**不改写手工正文、README或CSV**。修改文字后只需`make pdf`。本地缓存和编译文件保存在`build/`，不进入交付ZIP。

## 图表与文件

| 文件 | 内容 |
|---|---|
| `main.tex`、`report.pdf` | 当前中文正文及编译结果 |
| `figures/01_research_nav.pdf`、`.png` | 1亿元五情景的连续净值与回撤 |
| `figures/02_new_target_progress.pdf`、`.png` | 8次新目标的完成进度及持仓差距 |
| `figures/03_data_cash_rights.pdf`、`.png` | 现金比例、数据限制、估值与权益 |
| `figures/04_unfilled_reasons.pdf`、`.png` | 1亿元10%路径的新目标日未完成计划主原因 |
| `figures/05_capital_staircase.pdf`、`.png` | 五档资金、五情景的全期收益与计划完成率 |
| `data/` | 公开派生统计及研究设置 |
| `scripts/build_bundle.py` | 打包报告与公开材料 |

图采用完整25账户、162日数据；脚本在缺组时拒绝绘制，不回退为较短窗口。PDF为矢量图，PNG为300dpi。图中金额、完成率和暴露的口径见[data说明](data/README.md)。

本包可重画和编译，不包含重跑真实执行所需的原始L2、逐证券目标、完整流水及私有输入。重画公开图表不是重新运行私有回测。
