# 中文 LaTeX bundle 使用说明

本目录可以独立复制或解压使用。`report.pdf` 是已编译报告；`main.tex` 是完整正文。报告保留作者在 GitHub 更新的结论与实验设置，精简后部重复解释，不包含下一步计划；运行命令放在这份说明中，不占用实验正文。五张图各附一份矢量 PDF 和 220 dpi PNG。正文使用 TeX 自带 Fandol 字体。

## 只阅读或修改正文

打开 `report.pdf` 即可阅读。修改文字、表格、图注和后续研究计划时，编辑 `main.tex`。

安装 TeX Live / MacTeX，并保证 `latexmk` 与 `lualatex` 在 PATH 中，然后在本目录运行：

```bash
make pdf
```

该命令执行 LuaLaTeX，处理交叉引用后把 `build/main.pdf` 复制为 `report.pdf`。临时编译文件和字体缓存留在被 Git 忽略的 `build` 目录。不需要数据库或 Python。LuaLaTeX 输出附有中文 Unicode 映射，正文可搜索和复制。

没有 `make` 时可直接运行：

```bash
latexmk -lualatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build main.tex
```

在 Overleaf 上传本目录内容（不要再套一层目录），主文件设为 `main.tex`，编译器设为 **LuaLaTeX**。完整 ZIP 位于仓库 `dist` 目录，其第一层为 `tex_bundle`。

## 重画图表

Python 3.11 为本次验证环境。新环境可安装列出的依赖：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/make_figures.py
make pdf
```

`make_figures.py` 默认读取本目录的 `data` 并写入 `figures`，也支持 `--data`、`--output` 和 `--font`。默认优先使用 TeX 的 FandolHei；没有 TeX 字体时，选择本机可用的中文字体，也可以显式传入字体文件：

```bash
python scripts/make_figures.py --font /path/to/chinese-font.ttf
```

五组图分别表达：

1. **01_synthetic**：合成数据的净收益与金额完成率，说明资金扩大后的执行约束。
2. **02_real_nav**：真实净值、21 日预热和持仓阶段现金比例。
3. **03_real_returns**：真实资金阶梯的绝对净收益及相对计费参考组的基点差。
4. **05_real_clock**：交易分钟的均值及分布，区分周末等待。
5. **06_order_timeline**：同一买单在三种参与率下的累计完成路径。

订单未开始的情况已合并为正文中的一段说明，对应的 `04_real_completion` 图不再生成。

颜色、字体、网格和线型在脚本前部定义。数据不随风格变化；修改图表后需重新编译正文。图中资金阶梯按类别等距排列，单位为万元，不把等距视觉当作线性资金距离。

## 从既有回测产物重新提取汇总

这一步需要本地保存的完整合成、真实回放产物；附带 CSV 已足够重绘，无需重复提取。

```bash
python scripts/prepare_data.py \
  --synthetic /path/to/engine/outputs/demo-final \
  --real /path/to/engine/outputs/company-replay \
  --output data
python scripts/make_figures.py
make pdf
```

真实目录必须包含 `summary.csv`、`company_replay_bars.parquet` 和每情景的 `orders.csv`、`fills.csv`、`nav.csv`、`daily_nav.csv`；合成目录需要 `summary.csv`。脚本针对**本次固定样本**核对期末截断、完整观察订单和执行时钟，不是任意历史区间的通用分析器；换成新实验时需要同时更新这些日期与断言，并重写正文结论。

提取程序不会调用数据库，不会重跑策略，不把原始分钟行情、完整账户账本、机器路径或凭据写入汇总 CSV。附带的匿名母单计时记录用于复算分位数；一笔示例的累计比例用于解释余单，二者都不提供原始行情序列。

## 完整回测和指标口径

本仓库是报告交付物，完整策略执行仍在已有 `factor-liquidity` 引擎仓库中运行。进入已经安装依赖的引擎目录，可运行：

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m factor_liquidity.handcalc
PYTHONPATH=src .venv/bin/python -m factor_liquidity.demo \
  --config configs/demo.yaml --output outputs/my-demo
PYTHONPATH=src .venv/bin/python -m factor_liquidity.company \
  --config configs/company.example.yaml --output outputs/my-company-replay
```

公司入口要求本地已有授权导出的行情文件及配置。每次使用新的输出目录。回测输出包括：`summary.csv`、`orders.csv`、`fills.csv`、`children.csv`、`events.csv`、`positions.csv`、`nav.csv`、`daily_nav.csv` 和 `audit.json`。

统计定义放在报告前部，也可查阅 [data/README.md](data/README.md)。现金均值同时列出分钟记录与日终两种口径，正文和图 02 使用分钟记录口径。完成时间只在已完成订单上统计，尚未完成的订单另外说明。订单金额完成比例采用下单参考价，不是实际成交现金额的比值。

本次真实回放的市场事件时间、D+1 可得和可修订历史表，不能等同严格 PIT。历史状态、规则、官方收盘和公司行动仍未完整验收；最低收益、最低完成率和最长延迟参数保持未设置。附带的数据和报告不提供资金容量结论。

## 打包

```bash
make bundle
```

或在已更新 `report.pdf` 后执行 `python scripts/build_bundle.py`。ZIP 写到上一层 `dist/factor_liquidity_tex_bundle.zip`，包含正文、报告、图、数据和脚本，排除编译日志和缓存。
