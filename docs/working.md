# Working log — ITIAS Coder

日期键倒序。只记特性级变化，不记 commit 流水。每次有意义改动后更新本文件。

## Changelog

### 2026-09-21

- **修复 #14 Win7 启动闪退（PySide2 QtCharts 顶层导入崩溃）**：Win7 下 Qt5Charts.dll 系统级加载失败，`qt_bindings.py:75` 顶层 `from PySide2.QtCharts import ...` 抛 ImportError、双击闪退；v0.3.0 zip 取证确认 QtCharts.pyd/Qt5Charts.dll 均已打包（非采集缺失）。
- 修复 = 防御式导入 + `CHARTS_AVAILABLE` 四处图表块降级守卫（矩阵/统计/导出不受影响）、启动 crash log（exe 同目录，APPDATA 回退）、`--selftest` 冻结包自检、CI 双档 selftest 门禁、pyinstaller==6.21.0 pin。
- `tests/` 首次落地（Layer 1，10 项）；版本 bump 0.3.1。
- CI selftest gate 修正等待语义（GUI 子系统 exe 需 Start-Process -Wait）+ 冻结包补 PySide2.QtCharts hiddenimports/collect_dynamic_libs（在场≠可导入）。
- CI 实证 PySide2.QtCharts 绑定级导出失败（python 3.8 + PySide2 5.15.2.1，非冻结/非文件缺失）；win7 栈图表按设计降级（编码/矩阵/统计/导出不受影响），图表恢复立项 follow-up #17；selftest 门禁 tier1 改为「全模块导入 + 不崩」硬门禁、图表状态记录式。

### 2026-08-21

- **scaffold v2 retrofit（#11）**：补齐 `AGENTS.md` 与 `docs/{prd,rfc,test,working}.md`；README 尾部与 AGENTS 互指。不改运行时、不改 Windows Actions、不把隐私扫描脚本挂进 CI。
- PRD/RFC 数值从已上线行为 harvest（切片 1–30s 默认 3s、18 类、padding 13、60s 箱、对比 30 课、Win7 + PySide2 包、Release-only zip）。
- 设计自攻砍掉空 `design.md`、空 `tests/`、以及把 GPU 切片误写成非目标（改放 RFC Future）。
- 隐私 fail-closed 命令写进 `docs/test.md` Layer 4，实现留给后续 PR。

## Lessons Learned

- 飞行中项目补 scaffold 时，已上线的数字就是 Gate A 的原材料：把 README/UI/常量收成可勾选标准，而不是 agent 另造一套「更圆」的阈值。
- 含真人课堂媒体的 public 工具，隐私扫描是产品约束（失败路径：有命中就不许发），不是 CI 装饰。扫描实现可以后置，定义必须与 PRD 非目标同一天出现。
- 有窗口不等于有设计系统。没有状态×视觉表和 token 时不建 `design.md`，空完整比缺席更贵。
- ffmpeg stream copy 的段长受关键帧约束。把它写成已知测量域，而不是用静默重编码去「修准 3.000 秒」。
- 学校 Win7 交付面一旦承诺，Python/PySide 升级就是 RFC，不是依赖整理。`qt_bindings.py` 双栈是在付这笔税，不是临时代码。
- 文档 retrofit 与门禁脚本分 PR：否则「只改文档」的 issue 会夹带 CI，review 无法按层验收。
- hiddenimports ≠ 符号级可用性；冻结包发布前必须 exe selftest 门禁。
