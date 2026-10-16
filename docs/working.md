# Working log — ITIAS Coder

日期键倒序。只记特性级变化，不记 commit 流水。每次有意义改动后更新本文件。

## Changelog

### 2026-10-16（二）

- **修复 #25 终章：兜底引擎全链路在她机器已跑通，黑屏锁定在绘制层**。v0.3.6 run log 实证：spawn 688×502、first frame 逐圈到达、end-of-media 3s 实时节奏正确、media_dlls 揭示 msauddecm=0（系统缺 AAC 解码器 → DShow 整图建不起来了，这才是 Qt 路径连 H.264 都 ResourceError 的原始病因）。她仍见黑屏 → 帧到了画不出来：**PySide2 QImage 拒绝不可变 bytes 缓冲区**（null image），而离屏测试只数了帧没断言真实 paint——测试盲区，不是代码对了。
- 修复：`VideoSurface._on_frame` 存可写 `bytearray` 拷贝 + `isNull()` 守卫；音频重启（stop() 后 replay 需重开 push device，此前只有第一圈有声）。
- 测试补盲区：`test_ffplayer_integration.py`（Layer 2，dev 机）：widget 真实 show + paintEvent 计数断言「有帧必画」，帧数 alone 不再算证据。
- 版本 bump 0.3.7（`packaging/version.txt` 同步）。

### 2026-10-16


- **修复 #25 兜底播放器三缺陷（本机 18s 合成视频离屏集成测试实证）**：①音频双栈 API 写错（Qt5 `QAudioOutput.open()` 不存在、Qt6 应写 `start()` 返回的 QIODevice）→ 两栈一律静音；②收尾死锁：音频线程孤儿队列无 drain 通道，`end of media` 永不触发、循环断；③几何竞态：切兜底后立即取 `currentWidget().width()`，布局未完成得 0 → `scale=2:2` → 2×2 像素「视频」肉眼看即黑屏（与用户「一直是黑屏在调」症状吻合，高度疑似她机器实况）。
- 修复：统一 push-mode 写 `start()` 返回的 QIODevice；尺寸钳制（<160×90 回落 640×360 并记日志）；孤儿队列在 video-EOF 时直接清除；新增首帧到达日志（`first frame WxH`）让下份日志一锤定音。
- 主窗口标题带版本号：用户截图自证所装版本，消灭「不知道她装的是哪版」这个往返。
- 用户侧时间线：10-15 17:23 收到 v0.3.5，10-16 上午测 18 秒视频仍黑屏（未回传日志，此轮修复由本机集成测试驱动，不再等一轮往返）。
- 版本 bump 0.3.6（`packaging/version.txt` 同步）。

### 2026-10-15（二）


- **修复 #25 v0.3.4 run log 推翻编码假设后的终端修复：ffmpeg 直解回放兜底**。日志实证源本就是 H.264 High+AAC（兼容格式）仍 InvalidMedia+ResourceError → 根因重定性为**该机系统缺 DirectShow 解码组件**（学校机 N 版/精简镜像常见）；probe 只能读容器编码，读不出系统解码器有无。
- `ffmpeg_player.py`：Qt 播放 ResourceError 后自动切换 bundled ffmpeg 直解路径——`-re` 实时限速双进程（rawvideo BGRA 帧 + s16le 44100/2ch PCM），VideoSurface(QImage/ARGB32) 重绘 + QAudioOutput(Qt5)/QAudioSink(Qt6) 播放，EOF 复用既有 end-of-media 循环语义；音频设备缺失降级视频单路并记日志。encoder_window 以 QStackedWidget 承载两路视频面，错误自动切换、状态栏提示「兼容播放」。
- runlog 新增 Windows 媒体组件探针（quartz/msmpeg2vdec/msauddecm/mfplat/wmplayer 存在性），下份日志直接定位系统缺口。
- 误报修正：源扫描测试把 Qt `QAudioOutput.open()` 误判为内建 `open()`，规则补属性调用排除（内建 open 不会以 `.open(` 出现）。
- 版本 bump 0.3.5（`packaging/version.txt` 同步）。

### 2026-10-15


- **修复 #23 ffprobe 路径推导缺陷（v0.3.3 转码修复在用户机器未触发的直接原因）**：用户回传 run log 实证 `probe-unavailable (stream copy fallback)`——`replace("ffmpeg","ffprobe")` 把打包布局 `...\ffmpeg\ffmpeg.exe` 的**目录名一并替换**成不存在的 `...\ffprobe\ffprobe.exe`，预检静默失败回退直通；同时日志实锤用户环境为 Win10 19045（此前系统截图未解开的悬案）、Qt5 media service 正常、播放错误为 InvalidMedia+ResourceError（空 errorString，典型缺解码器形态）。
- 修复 = `ffprobe_path()`：按最后路径分隔符只换文件名（字符串推导，Windows 反斜杠路径在 macOS 开发/CI 侧行为一致，`Path.with_name` 在 POSIX 不认 `\` 会整串丢目录——单测抓住）；`probe_duration`/`probe_streams` 统一接入。
- 该缺陷自 `probe_duration` 起潜伏（旧症状 = 进度条总段数恒 0，无感），#21 将其变为承重路径后暴露——预检类逻辑的可观测性（runlog 记录 reason）正是这次能在无远程调试下定位的原因。
- 版本 bump 0.3.4（`packaging/version.txt` 同步）。

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

- 跨平台路径推导禁止整串 `replace`：打包布局里目录名与可执行名可能同名（`ffmpeg/ffmpeg.exe`），且 `pathlib` 在 POSIX 不认反斜杠——路径变换要用显式分隔符逻辑并用对方平台的路径形态写测试。
- 用户侧「自证清白」的日志必须在第一天就有：v0.3.3 的 runlog 让 #23 在一次往返内定位（reason 字段直接指出 probe 失败），没有它就是又一轮猜测。
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
