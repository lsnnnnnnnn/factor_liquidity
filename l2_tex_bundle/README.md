# L2 中文 LaTeX bundle

`report.pdf` 是实际编译的中文报告；`main.tex` 是可编辑正文，`results.tex` 由公开汇总表生成。与旧 `tex_bundle/` 的分钟 VWAP 实验分开保留。本目录可独立复制和离线重画，不连接数据库。

## 编译、重画、打包

本次沿用已有 Python、Matplotlib、Fandol、LuaLaTeX 和 latexmk；没有安装新的文档框架。

```bash
make pdf                     # 只编译现有正文和矢量图
make figures                 # 用 data/ 重画 PDF + 240 dpi PNG，并更新 results.tex
make all                     # 重画并编译
make bundle                  # 生成 ../dist/factor_liquidity_l2_tex_bundle.zip
```

例如复用已有引擎环境：`make all PYTHON=/path/to/engine/.venv/bin/python`。

需让 `latexmk`、`lualatex`、`kpsewhich` 在 PATH；macOS 的现有 TeX 位于 `/Library/TeX/texbin`。`PYTHON` 可指向已有引擎虚拟环境，或使用安装了 `requirements.txt` 所列库的 Python。编译缓存都留在 `build/`，ZIP 排除缓存、日志和临时预览。Overleaf 的主文件为 `main.tex`，编译器选择 **LuaLaTeX**。

```bash
python scripts/make_figures.py --font /path/to/chinese-font.otf
```

公开 CSV、图和 `results.tex` 使用同一组数值。重画脚本检查三个时点完成率单调、需求数量守恒和未完成用时为空；数值改变后须同步重新编译报告。五张图依次为逐档手算、完成率矩阵、逐单用时与滑点、净值与收益差、余单原因与工程敏感性。没有把两单小样画成平滑的总体分布。

## 真实实验复现

完整执行器、授权样本和逐笔账户在本地引擎交付中；本轮代码提交为 `8b9bb63`。公共 bundle 只提供足够重画的精简派生数据；没有原始公司 L2、服务器配置、凭据或完整账户账本。

在已经具有授权样本的引擎目录运行：

```bash
PYTHONPATH=src MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m pytest -q
PYTHONPATH=src MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m factor_liquidity.handcalc \
  --output outputs/my-minute-handcalc
PYTHONPATH=src .venv/bin/python scripts/validate_l2_sample.py \
  --sample data/company_l2_20261016 --output outputs/my-l2-quality
PYTHONPATH=src MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m factor_liquidity.l2_study \
  --data data/company_l2_20261016 --daily data/company_l2_20261016/daily.csv \
  --validation outputs/my-l2-quality \
  --output outputs/my-l2-study
```

每次使用新的输出目录，避免覆盖历史结果。研究入口同时运行可控买卖手算、25 组主矩阵和 3 组敏感性；主实验使用资金充足模式，保留卖出持仓限制、手续费和融资负债。固定20日动量只用两只事先确定的股票调试接口，没有搜索新因子。原参考价来自前一日官方收盘，09-30 盘前按日线归档规则读取。

本次权威结果为本地 `outputs/l2-study-verified-20261016/`，共 28 组、56 笔冻结母单、84 个日终净值点；28 份账户核对通过。实际 L2 逐档成交共 23,644 笔，原参考对照另有 10 笔，可控手算另有 4 笔。公开数据的每个时点完成率、目标数量和收益差均独立对本地源产物复算通过。全套 356 项测试通过，其中 L2 执行器专项 45 项；旧分钟手算与固定种子合成回归均实际运行通过。

1 亿元、10% 额度参与率在 30/60 分钟/当日的参考金额完成率为 12.1052%/19.4081%/34.0589%，期末净收益 +0.3838798%，原参考 +0.5264218%，差 -0.1425420 个百分点。买单只完成 216,500/19,880,700 股，卖单 4,405,200 股全部完成；正收益不意味着目标持仓完成。普通余量 09-30 当日终止，随后两天只估值。

正式公司因子未提供授权文件夹及输入合同，尚未连接。指定两股在 2024-01-01 至 2024-09-24（不含后者）的实际查询均为 0 行，未完成该压力回放。容量收益、完成率与延迟门槛均未设置。

## PDF 检查

报告以 LuaLaTeX 实际编译。交付前用 Poppler 渲染每页，检查中文、表格、图注、分页和留白，并将图源与表格逐项核对。渲染页面是本地检查中间文件，不纳入 ZIP。指标详见 [data/README.md](data/README.md)。
