# 因子流动性实验

[中文报告](l2_tex_bundle/report.pdf) · [可编辑正文](l2_tex_bundle/main.tex) · [完整 LaTeX bundle](dist/factor_liquidity_l2_tex_bundle.zip) · [编译与重画](l2_tex_bundle/README.md) · [图表数据说明](l2_tex_bundle/data/README.md)

本仓库只展示 **2026 年 10 月 22 日的最新状态**。已解决的数据缺项不再作为附录重复叙述；整理前的报告、图表和记录保存在[旧版本](https://github.com/lsnnnnnnnn/factor_liquidity/tree/report-20261022-before-consolidation)。

目前完成了两部分工作：

- **执行器的连续账户实验。** 使用 30 只股票、2026-07-31—09-04 的 26 个交易日，以调试用动量规则运行同一起点的 1 亿元账户。最新执行规则下，10% 参与率账户收益为 −2.9764%，当日成交完成率为 89.6872%；按参考价全部成交的假设账户收益为 −1.3017%，两者相差 −1.6746 个百分点。不限参与率的 L2 账户收益为 −4.2798%，完成率为 99.9759%。这说明完成率与收益需要一起看；参考假设也不代表真实市场一定能成交。
- **正式因子的恢复与接入准备。** 默认 N20、sample3、H20_equal_G1 的共享价格、成交、持仓、日账、目标及待执行状态已经恢复核对。2024-01-02—08-30 的新现金账户协议已经实现：保留原 H20 调仓相位，1 月 11 日首次开仓，每天 09:35 决策，使用真实股／份和未复权价格记账。这里没有换因子或重新选参数，也不称为样本外检验。

正式 2024 实验目前完成的是取数、数据准备和预检，**尚未模拟订单或账户，也没有前两三期、全窗口或资金阶梯收益**。首日 956 个目标已全部检查，954 个证券日有 L2；一个有明确停牌记录，另一个 689009.SH 有日线成交但缺 L2。公司行动的账户生命周期覆盖也未齐备。最新保存的引擎测试记录为 **379 项通过**，不等于真实组合回放已经完成。

报告区分调试策略的真实执行结果、正式策略的原账本核对，以及尚未完成的新账户实验，不提供资金容量上限。公开仓库只含正文、图、派生统计与重画脚本；原始 L2、完整证券账本、服务器配置及凭据保留在授权环境。

## 查看、编译和重画

已有 LuaLaTeX、latexmk、ctex 和 Fandol 字体时：

```bash
git clone https://github.com/lsnnnnnnnn/factor_liquidity.git
cd factor_liquidity/l2_tex_bundle
make pdf
```

`make pdf` 使用随包正文、生成的数字文件和矢量图，不需要数据库或 Python。Overleaf 上传 bundle 中 `l2_tex_bundle` 的内容，主文件选 `main.tex`，编译器选 **LuaLaTeX**。

重画使用已有 pandas、NumPy、Matplotlib 环境：

```bash
make figures PYTHON=/path/to/existing/python
make pdf
make bundle PYTHON=/path/to/existing/python
```

这些命令只读取公开派生数据，重画两组当前图、更新报告数字并打包，**不是重新运行私有回测**。更多说明见 [bundle README](l2_tex_bundle/README.md)。
