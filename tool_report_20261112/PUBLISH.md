# 发布报告

本目录使用独立发布子目录，保留原 `l2_tex_bundle/` 和仓库根 README 的用户编辑。脚本不执行 Git 提交或推送。

先从已生成、已核账的报告读取目录清单：

```bash
python3 tool_report_20261112/publish_report.py \
  --source /path/to/completed-report-output \
  --name representative_v3 \
  --role representative --dry-run
```

确认实际金融版本、参考价规则、报告时间和逐档状态后，去掉 `--dry-run`。脚本只把明列的公开文件复制到 `tool_report_20261112/representative_v3/`，并从这些文件新建 `representative_v3_tex_bundle.zip`。目标已存在时拒绝覆盖，应使用新目录名。

历史49档使用 `--name historical_baseline_49 --role historical_baseline`；正式五 N 搜索使用独立目录及 `--role capacity_study`。`publication.json` 保存发布角色、实际金融版本、参考价规则、来源结果时点和已测档数，不保存本地或服务器私有路径。该角色标签不改变账户验收结论。

白名单由脚本显式列出：

- 正文：`main.tex`、`main.pdf`、`README.md`。
- 汇总：`trial_summary`、`capacity_summary`、`special_cases_summary`、`run_progress`、`completion_time_summary`；可选匿名案例为 `turnover_case`、`intraday_cases`，均为 CSV。
- 说明：`data/report_metadata.json`。
- 图：`capital_return`、`capital_completion`、`capital_impact`、`turnover_case`、`intraday_1` 至 `intraday_3` 的 PDF／PNG。

CSV 必须符合公开列名单；源目录中其他文件不会复制。发布脚本不读取或复制原输出的 ZIP、`private/`、`portable/`、逐证券输入及金融检查点。新 ZIP 由白名单文件直接生成，不运行哈希、校验和或压缩包完整性测试。

脚本使用标准库。其测试只验证复制范围、元数据语义和拒绝私有列行为：

```bash
python3 -m unittest discover -s tool_report_20261112/tests -v
```

最终提交前只暂存本次新目录的实际公开文件；不把用户其他未提交修改一起提交，不使用 `git add .`。PDF和源码的内容一致性与排版仍由报告生成阶段负责。
