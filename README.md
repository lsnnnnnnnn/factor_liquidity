# 因子流动性实验

[中文报告](l2_tex_bundle/report.pdf) · [可编辑正文](l2_tex_bundle/main.tex) · [LaTeX bundle](dist/factor_liquidity_l2_tex_bundle.zip) · [编译与重画](l2_tex_bundle/README.md) · [汇总数据说明](l2_tex_bundle/data/README.md)

本仓库展示2026年10月26日完成的真实因子执行实验：沿用 N20、sample3、H20_equal_G1 的原目标与调仓相位，从2024年1月2日现金、零持仓起步，1月11日首次建仓，连续运行至8月30日，共162个官方交易日、8次新目标。五档资金为100万、300万、1000万、3000万、1亿元；每档分别运行参考、L2不限参与率、5%、10%、20%参与率，共25个独立账户，均已完成全窗口与账户审计。

| 初始资金1亿元，162日 | 参考账户 | L2 10%参与率 |
|---|---:|---:|
| 账户收益 | −9.4077% | −10.7623% |
| 相对参考收益差 | — | −1.3546个百分点 |
| 新目标日可定量计划的当日完成率 | 99.8239% | 99.6426% |

费用和税费为零，不融资。参考账户也保留现金、真实数量、T+1、权益、延迟和共同数据约束，仅不设盘口数量及参与率上限。完成率按新目标日已定量计划金额加权，缺参考或共同权益限制的原权重另列。小资金账户受数量单位影响，建仓较少、现金较多，因此要结合实际持仓和现金解释收益差异。

本批次统一限制215只关键权益分配资料不足的证券，保留原目标权重，不向其他证券重新分配。源库原清单581个整日零L2证券日已补出记录，但本轮沿用已保存缓存，没有将新记录替换回去。结果对应这一明确的数据批次和共同规则。

最新引擎测试记录为 **462项通过**。2024年参与过原策略参数选择，本研究不称为独立样本外检验；尚未确定业务收益要求，不据此给出资金容量上限。公开包只含派生汇总、图表与重画脚本，不含原始L2、逐证券目标、完整账户流水或凭据。

## 查看、编译与重画

已有LuaLaTeX、latexmk、ctex和Fandol字体时：

```bash
git clone https://github.com/lsnnnnnnnn/factor_liquidity.git
cd factor_liquidity/l2_tex_bundle
make pdf
```

Overleaf上传bundle内`l2_tex_bundle`的内容，主文件选`main.tex`，编译器选 **LuaLaTeX**。修改正文后运行`make pdf`即可。

使用已有pandas、NumPy、Matplotlib环境：

```bash
make figures PYTHON=/path/to/existing/python
make pdf
make bundle PYTHON=/path/to/existing/python
```

`make figures`只从公开汇总数据重画5组图，**不覆盖手工编辑的`main.tex`**。`make bundle`重画、编译并打包。公开材料可以重画和编译报告，不能仅凭这些汇总重跑私有L2回测。
