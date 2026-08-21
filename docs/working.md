# Working log — ITIAS Coder

日期键倒序。只记特性级变化，不记 commit 流水。每次有意义改动后更新本文件。

## Changelog

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
