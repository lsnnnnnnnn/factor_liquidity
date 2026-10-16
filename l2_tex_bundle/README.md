# L2 买卖模拟：报告、源码和图表

`report.pdf` 是中文报告，`main.tex` 是可编辑正文，`results.tex` 中的结果由附带 CSV 自动生成。`main` 保存这次 30 股研究；此前两股 L2 实验在 [`v2`](https://github.com/lsnnnnnnnn/factor_liquidity/tree/v2)，旧分钟实验在 [`v1`](https://github.com/lsnnnnnnnn/factor_liquidity/tree/v1)。

## 编译、重画与打包

```bash
make pdf                     # 只编译已有正文和矢量图
make figures                 # 用 data/ 重画 PDF/240 dpi PNG，更新 results.tex
make all                     # 重画并编译
make bundle                  # 生成 ../dist/factor_liquidity_l2_tex_bundle.zip
```

这些命令使用 Python、Matplotlib、Fandol、LuaLaTeX 和 latexmk，不需要连接数据库。例如，已有引擎 Python 环境时可运行 `make all PYTHON=/path/to/engine/.venv/bin/python`。`latexmk`、`lualatex`、`kpsewhich` 需要在 PATH 中；macOS 现有 TeX 位于 `/Library/TeX/texbin`。也可以指定画图所用的中文字体：

```bash
python scripts/make_figures.py --font /path/to/chinese-font.otf
```

编译临时文件放在 `build/`，打包时排除缓存、日志和页面预览。使用 Overleaf 时，主文件选 `main.tex`，编译器选 **LuaLaTeX**。修改 CSV 后，需要一起更新图、`results.tex` 和 PDF，避免正文数字与图表不一致。

## 这次怎样买卖，怎样比较

每周选一天，单独做一次当天的比较。先按过去 20 个交易日的涨跌幅给股票排序：用约 50% 的资金持有排名后半的股票，其余为现金；计划卖出这些股票，再用 100% 的资金平均买入排名前半的股票。这里的动量用前 21 个官方交易日的收盘价计算，没有做复权处理。遇到缺失收盘价，只有找到停牌证据才沿用前一次收盘，并保留填补记录。

当天开始买卖前，先确定股票、股数和初始账户。同一天、同一档资金的各组比较都使用这份计划，不能因为某组买得慢就另换股票或数量。普通订单当天没完成的部分，当天停止。收盘后用官方收盘价计算账户价值。下周重新设置账户再做一次，因此各周收益不能相加或复利成三个月的策略收益。股票会重复出现、日期也相近，不能把这些订单都看成彼此无关的统计样本。原计划的 14 个日期全部保留数据覆盖记录；整日没有行情但原因不明，不能写成没有成交能力。

下单时的参考价和初始持仓估值，都取当日 09:30 前 L2 的 `pre_close`。如果有停牌证据且没有行情，就用此前最近的官方收盘价，并注明价格已经多久没有更新。参考价只是比较买贵还是买便宜的标尺；“全部按参考价成交”是用来比较的假设，不保证现实中能够这样成交。

五张图依次回答：资金增加后完成多少；不同日期和买卖方向是否一样；成交活跃程度不同的股票是否一样；完成订单等了多久、成交价差多少；这些差异怎样影响当天收益，还有哪些数量没完成。

画图前，程序会核对计划股数等于已成交加剩余股数、后一个时点的完成率不能低于前一个时点、未完成订单的完成时间必须留空，并检查每笔订单合计后是否与汇总表一致。`scenario` 会在不同日期重复，因此查找一组结果必须同时使用 `event_date + scenario`。

## 使用授权本地数据重新运行

完整执行程序、原始行情和带逐日收盘价的选股准备数据，保存在授权本地交付中。公开文件只保留重新画图所需的统计结果；公开的选股准备表只含日期和停牌填补证据。运行时请另建输出目录，避免覆盖历史结果：

```bash
PYTHONPATH=src MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/validate_l2_expanded.py \
  --sample data/company_l2_expanded_20261016 --output outputs/my-l2-expanded-quality
PYTHONPATH=src .venv/bin/python -m factor_liquidity.l2_expanded \
  --data data/company_l2_expanded_20261016 \
  --validation outputs/my-l2-expanded-quality --output outputs/my-l2-expanded-study
```

主要比较不让现金不足拖慢买单；临时借入的钱记为负债，计算净资产时扣回，利率设为 0。卖出仍不能超过实际持股和当天可卖数量。

每次最多发出多少股，用上一条有效快照所记录的区间成交量计算；同一份量不能被多笔委托重复使用。委托发出后要经过正的延迟，最早只能在更晚的盘口成交。数量按 100 股取整、每笔小委托最多 100 万股，都是这次的演示设置。延迟和盘口怎样更新也是模拟假设，尚未证明适用于全市场历史交易规则，快照本身也不能证明挂单是否真的被补回。

公司正式因子和指定的 2024 压力数据尚未接入。现在没有设定收益、完成率和用时的合格标准。原始 L2、完整账户、服务器地址、连接配置和凭据不放入公开包，也不做哈希或校验和检查。

## 实际运行与检查

最终结果包含 13 个日期、364 组比较、10,920 行订单，全部通过账户核对；72 项引擎测试通过。桌面另选 08-31、100 万元，重跑 5 种买卖方式，得到的 41 张账户与执行表逐项相等。停牌且缺少日线的股票，已把估值来源注明为此前参考价，没有改变任何账户数值，详情见 `study_metadata.json`。

6 页中文报告已用 LuaLaTeX 编译，并用 Poppler 逐页查看中文、表格、图注、分页和留白。正文数字、五张图与 CSV 使用同一批结果；ZIP 内文件与交付目录逐项直接比对。
