# Working log — ITIAS Coder

日期键倒序。只记特性级变化，不记 commit 流水。每次有意义改动后更新本文件。

## Changelog

### 2026-10-14

- **修复 #21 v0.3.2 行为判断页黑屏无声（Win7 + 源视频 HEVC 直通切片不可解码）**：用户定向反馈四项证据齐（无 crash 日志 / 全黑无声 / App 流程存活 / 样本视频特征与手机 HEVC 竖屏源吻合）；根因 = `slicer.py` `-c copy` 直通保留源编码，Win7 股票 DirectShow 无 HEVC 解码器，且 `SegmentPlayer._last_error` 只存内存完全静默。
- 修复三层：`runlog.py` 运行日志（exe 同目录 `ITIAS-Coder-run-*.log`、APPDATA 回退、保留 5 份、环境头 + 播放状态迁移 + 错误详情）；`slicer.py` 切片前 ffprobe 预检，视频非 H.420p/音频非 AAC·MP3 自动转码 `libx264 main + aac`（bundled gyan essentials 含 libx264），兼容源维持直通快路径；`SegmentPlayer` 错误回调 → encoder_window 状态栏 + 一次性指引弹窗（含日志路径与「重切片边界不变可续用进度」）。
- 转码路径 `-force_key_frames expr:gte(t,n_forced*段长)`：libx264 默认 GOP 250 帧会吞掉段边界，转码模式必须显式放关键帧，否则段粒度漂移破坏编码会话语义（e2e 实测：无此参数 7s 源只出 1 段，加后 3+3+1）。
- e2e 实测修正一处真 bug：ffprobe `-select_streams` 不支持 `v:0:a:0` 复合 specifier（静默返回空 → 永远回退直通），改为全量 JSON 解析后按 codec_type 取首流。
- 对既有会话：重切片段边界不变，`.itias_save.json` 按序号续用。
- 版本 bump 0.3.3（`packaging/version.txt` 同步）。

### 2026-09-28

- **修复 #19 选中文名视频报 `'gbk' codec can't decode byte 0xb9`**：zh-CN locale（cp936）下 Python 用本地 ANSI codepage 解码 ffmpeg stderr，遇到非 GBK 字节即 UnicodeDecodeError，切片直接失败；`slicer.py` 两处 subprocess 显式 `encoding="utf-8", errors="replace"`。
- 配套机械锁定：`tests/test_slicer_locale.py`（Popen/probe_duration 显式 encoding）+ `tests/test_source_no_locale_io.py`（源扫描禁止裸 `text=True` 与无 `encoding` 的 `open()`）。
- 版本 bump 0.3.2；`packaging/version.txt` 同步（此前滞留 0.3.0，消除人肉陷阱）。

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

- 直通（`-c copy`）交付的「能切片」不等于「App 内能播」：解码面在目标机系统（Win7 DirectShow），不在 ffmpeg。凡 stream copy，编码兼容性必须在切片前显式判定，而不是等播放失败再取证。
- 转码切片必须 `-force_key_frames` 对齐段边界：segment muxer 只在关键帧切，编码器 GOP 是隐含合约，换编码器时要重签。
- 每次运行写 run log 不是可选项：静默失败类 bug（播放、音频、图表降级）在没有现场日志时，用户侧「全黑没声音」就是全部信息，定位成本全压在猜测上。
- 飞行中项目补 scaffold 时，已上线的数字就是 Gate A 的原材料：把 README/UI/常量收成可勾选标准，而不是 agent 另造一套「更圆」的阈值。
- 含真人课堂媒体的 public 工具，隐私扫描是产品约束（失败路径：有命中就不许发），不是 CI 装饰。扫描实现可以后置，定义必须与 PRD 非目标同一天出现。
- 有窗口不等于有设计系统。没有状态×视觉表和 token 时不建 `design.md`，空完整比缺席更贵。
- ffmpeg stream copy 的段长受关键帧约束。把它写成已知测量域，而不是用静默重编码去「修准 3.000 秒」。
- 学校 Win7 交付面一旦承诺，Python/PySide 升级就是 RFC，不是依赖整理。`qt_bindings.py` 双栈是在付这笔税，不是临时代码。
- 文档 retrofit 与门禁脚本分 PR：否则「只改文档」的 issue 会夹带 CI，review 无法按层验收。
- hiddenimports ≠ 符号级可用性；冻结包发布前必须 exe selftest 门禁。
- zh-CN locale（cp936）是 Windows 交付的一等验收环境：subprocess 文本 I/O 必须显式 `encoding="utf-8", errors="replace"`；CI 的英文 locale 无法模拟中文 ANSI codepage，须以单测 + 源扫描测试机械锁定（`tests/test_slicer_locale.py`、`tests/test_source_no_locale_io.py`），禁止裸 `text=True` 与无 `encoding` 的 `open()`。
