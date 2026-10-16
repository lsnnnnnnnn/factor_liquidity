# 周频独立券单的 L2 中文 LaTeX bundle

`main.tex` 是可编辑中文正文，`results.tex` 由实际派生表生成，`report.pdf` 是交付报告。`main` 维护扩样研究；两股 L2 小样在 [`v2`](https://github.com/lsnnnnnnnn/factor_liquidity/tree/v2)，旧分钟实验在 [`v1`](https://github.com/lsnnnnnnnn/factor_liquidity/tree/v1)。

## 编译、重画与打包

```bash
make pdf                     # 只编译已有正文和矢量图
make figures                 # 由 data/ 重画 PDF/240 dpi PNG，更新 results.tex
make all                     # 重画并编译
make bundle                  # 生成 ../dist/factor_liquidity_l2_tex_bundle.zip
```

使用已有 Python、Matplotlib、Fandol、LuaLaTeX 与 latexmk，不依赖数据库或新文档框架。例如复用引擎环境：`make all PYTHON=/path/to/engine/.venv/bin/python`。`latexmk`、`lualatex`、`kpsewhich` 须在 PATH；macOS 现有 TeX 位于 `/Library/TeX/texbin`。也可为重画脚本显式传入中文字体：

```bash
python scripts/make_figures.py --font /path/to/chinese-font.otf
```

编译缓存保存在 `build/`，ZIP 排除缓存、日志和临时预览。Overleaf 主文件为 `main.tex`，编译器选 **LuaLaTeX**。修改 CSV 后须重新生成图、`results.tex` 和 PDF，不能只改正文数字。

## 研究语义与图源核对

每个周频事件从共同基线独立初始化：约 50% 下半动量池等权持仓，其余现金；固定卖出原持仓，买入上半池等权 100% 目标。同事件、同资金跨模型冻结股数和初始账户，普通余单当日终止，使用当日官方收盘估值。动量采用前 21 个官方交易日的未复权收盘；只有有停牌证据的缺日才沿用前收盘并留标记。参考与初始估值来自当日 09:30 前 L2 `pre_close`，有证据停牌且无行情时用此前最近官方收盘并标陈旧价。

各事件不是连续策略账户，不串联、复利或累计其收益。股票重复、日期相近，描述性分位数也不意味着所有母单或事件统计独立。计划 14 次事件的数据覆盖表保留零行记录，无停牌证据的整日未知缺失不能写成零流动性。

五张图分别展示资金/参与率下三个观察时点、日期与买卖稳定性、预热流动性层和方向、已完成用时与成交滑点、独立事件收益差及未完约束。重画入口核对每事件/情景唯一、数量守恒、时点完成率单调、完整需求分母、未完成时间空值，以及母单与场景参考金额一致；`scenario` 在日期之间重复，因此所有核对使用 `event_date + scenario`。

## 授权本地样本的实际运行

完整 L2 执行器、原始样本及带逐日收盘价的信号预热表留在授权引擎交付，公开 bundle 只含足够复算图表的派生数据，公开预热表只保留日期与填补证据。使用自己的新输出目录，避免覆盖历史实验：

```bash
PYTHONPATH=src MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/validate_l2_expanded.py \
  --sample data/company_l2_expanded_20261016 --output outputs/my-l2-expanded-quality
PYTHONPATH=src .venv/bin/python -m factor_liquidity.l2_expanded \
  --data data/company_l2_expanded_20261016 \
  --validation outputs/my-l2-expanded-quality --output outputs/my-l2-expanded-study
```

主实验排除现金不足阻塞，融资缺口列负债，工程利率 0；不取消持仓与可卖量约束。每一来源快照的前一区间量只能预占一次，子单加正延迟后用严格更晚盘口执行。100 股和单子单 100 万股上限为演示参数，延迟与深度刷新为工程假设，未认证全市场历史规则或真实补单。

正式因子接口和指定 2024 压力回补未接入本研究；收益、完成率和延迟门槛保持未设置。原始 L2、完整账户、服务器地址、连接配置及凭据不纳入公开 bundle，也不做哈希或校验和检查。

## 本次实际交付核验

最终数据为 13 个事件、364 个场景、10,920 行母单，所有账户核对通过；72 项引擎测试通过。桌面另选 08-31、100 万元、5 模型复跑，41 张账户与执行表逐项相等。缺日线停牌股的估值来源标记已改为陈旧参考价，未改变任何财务内容，详情保存在 `study_metadata.json`。

5 页中文报告以 LuaLaTeX 实际编译，并用 Poppler 逐页渲染检查中文、表格、图注、分页及留白。正文结果、五张图与 CSV 同源；ZIP 中的文件与交付目录逐项直接比对。
