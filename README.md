# 因子流动性实验

[中文报告](l2_tex_bundle/report.pdf) · [可编辑正文](l2_tex_bundle/main.tex) · [LaTeX bundle](dist/factor_liquidity_l2_tex_bundle.zip) · [编译与重画](l2_tex_bundle/README.md) · [图表数据](l2_tex_bundle/data/README.md)

本仓库展示2026年10月23日完成的真实因子连续账户实验。本轮沿用 N20、sample3、H20_equal_G1 的原目标、权重与调仓日期，从2024年1月2日一次投入现金、零持仓起步，1月11日首次建仓。已完成至3月14日的47个官方交易日，包含7个开仓前现金日和两次新目标日。

| 初始资金1亿元 | 参考账户 | L2 10%参与率 |
|---|---:|---:|
| 账户收益 | 3.8686% | 3.4303% |
| 相对参考收益差 | — | −0.4383个百分点 |
| 新目标日可定量计划的当日完成率 | 99.8584% | 99.6650% |
| 最大回撤 | 27.8272% | 27.8875% |

两个账户均已通过独立逐笔核账。费用、税费为零；参考账户也保留现金、真实数量、T+1、权益、延迟和共同数据约束。完成率按已定量计划金额加权，缺参考和共同关键事件限制的原目标权重另列，不能把99%以上的完成率理解为全部原目标都已实现。

67日、162日和五档资金×五种情景的25组研究正在服务器继续。本仓库当前只填已完成的47日结果，不把待运行窗口写成已有收益。报告中的图、表、正文均来自本轮新账户，旧演示和旧账本核对不再混入当前实验结论。

本研究是原G1目标在共同数据可用条件、既定现金与权益规则下的历史执行对照。2024年参与过原参数选择，不称为独立样本外；不编造指数超额或容量上限。公开包只含派生汇总和重画脚本，不包含原始L2、私有逐证券目标、完整账户流水或凭据。

## 查看与编译

直接阅读[报告PDF](l2_tex_bundle/report.pdf)。Overleaf上传bundle中`l2_tex_bundle`的内容，主文件选`main.tex`，编译器选 **LuaLaTeX**。

已有LuaLaTeX、latexmk、ctex和Fandol字体时：

```bash
git clone https://github.com/lsnnnnnnnn/factor_liquidity.git
cd factor_liquidity/l2_tex_bundle
make pdf
```

修改正文后只运行`make pdf`。用已有pandas、NumPy、Matplotlib环境重新生成图和正文，或者重新打包：

```bash
make figures PYTHON=/path/to/existing/python
make pdf
make bundle PYTHON=/path/to/existing/python
```

`make figures`按包内汇总数据重建正文与图，可能覆盖手工改过的`main.tex`；它不是重新运行私有回测。引擎本轮服务器测试为417项通过，真实账户完成状态另由核账及完整日期结果确认。
