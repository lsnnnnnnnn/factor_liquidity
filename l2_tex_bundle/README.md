# 2024年真实因子执行研究

本目录只含本轮连续账户派生汇总、图和中文报告，不含原始L2、逐证券因子、目标及完整流水。

编译：lualatex -interaction=nonstopmode -halt-on-error main.tex（运行两次）。
重画：python scripts/make_current_report.py，仅读取本包data目录的公开派生统计。
引擎刷新：PYTHONPATH=src .venv/bin/python scripts/research_results.py --report 本次结果目录。
