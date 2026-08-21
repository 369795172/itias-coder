# RFC — ITIAS Coder

Gate B 来源：否案从已上线代码与 commit 理由还原；无法还原的标「决策考古缺口」。文末「设计自攻」是本 retrofit 的 reviewer 清单，已回写去留。

## Architecture

本地单进程桌面应用。无服务端。

```text
                    ┌─────────────────────────────────────────┐
                    │              MainWindow                  │
                    │  profile combo │ slice │ encode │ analyze│
                    │  compare │ reliability                     │
                    └──────┬──────────┬──────────┬─────────────┘
                           │          │          │
              ┌────────────▼──┐  ┌────▼─────┐  ┌─▼──────────────┐
              │ SlicerDialog  │  │ Encoder  │  │ Analysis/Compare│
              │ SliceWorker   │  │ Window   │  │ Reliability     │
              │ (QThread)     │  │ Segment  │  │                 │
              └──────┬────────┘  │ Player   │  └────────┬────────┘
                     │           └───┬──────┘           │
                     ▼               ▼                  ▼
              ffmpeg/ffprobe    .itias_save.json    openpyxl xlsx
              (-c copy segment)  + export xlsx/txt  + QtCharts
                     │
                     ▼
              config/profiles/*.yaml
                     │
              qt_bindings.py ── PySide6 (dev) / PySide2 (Win7 freeze)
                     │
              packaging/ ── PyInstaller onedir + sidecar ffmpeg/
```

数据面：切片产物是磁盘上的短视频文件；编码状态是同目录 JSON；交付给研究流程的是 Excel/TXT。课堂媒体永不进 git。

## State machine

编码主路径（含错误）：

```text
[launcher]
    │ 选视频 / 选切片目录 / 选 Excel
    ▼
[need_ffmpeg] ──找不到──► [error: 提示安装或使用便携包] ──► launcher
    │ 找到
    ▼
[slicing] ──用户取消──► [error: 已取消] ──► launcher
    │
    ├── ffmpeg 非 0 ──► [error: 返回码] ──► launcher   （不重编码）
    ├── 输出 0 个 mp4 ──► [error: 无片段] ──► launcher
    ▼
[sliced]
    │ 打开编码；若有 .itias_save.json 则 resume
    ▼
[encoding]
    │ 播放当前未编码段
    ├── 点代码 ──► 写 session + autosave ──► 下一段未编码
    ├── 撤销 ──► 清上一段 + autosave ──► 重播该段
    ├── 重播 ──► 当前段 seek 0
    ├── 关闭且 dirty ──► 确认对话框（保存已由 autosave 覆盖磁盘）
    ▼
[complete] ──询问导出──► [exported] xlsx+txt
    │
    ├── 分析 ──► [analysis_view] （padding 13；60s bins）
    ├── 多课 ──► [compare_view] （最多 30 课；第 31 拒绝）
    └── 信度 ──► [reliability_view] 或 CLI
```

切片与编码可分开：用户可跳过切片，直接打开已有片段文件夹。

## Component contracts

不写函数签名。只约束输入、输出、失败。

**Profile loader**  
输入：`config/profiles/{id}.yaml`（frozen 包内从 bundle 读）。  
输出：类目列表、快捷键、`analysis_padding_code`。  
失败：文件不存在则加载失败，主窗不能开始编码。不在运行时联网拉框架。

**SliceWorker**  
输入：源视频路径、输出目录、时长整数秒、ffmpeg 路径。  
输出：`{stem}_%04d.mp4` 若干；finished 信号带实际个数。  
失败：无二进制、非 0、取消。超时仅作用于 ffprobe（30s）；切片过程跟源片长度走，不设全局墙钟超时。  
副作用：不改源文件。

**Encoder + SegmentPlayer**  
输入：片段路径列表、当前 Profile。  
输出：每个片段至多一个 `code_id`；每次编码/撤销后覆盖 `.itias_save.json`。  
失败：播放器报错时把错误字串留在 player 上，不崩溃退出。缺片段文件则该段无法播。

**Storage export**  
输入：完整或部分 session + profile。  
输出：xlsx（表「ITIAS编码」+「汇总」）与 txt（每行一个代码或空）。  
失败：磁盘写失败弹窗。导入 Excel 按「片段序号」列对齐，不按文件名。

**Analysis**  
输入：session + profile。  
输出：计数、占比、60s 箱矩阵、类别时间序列。  
padding：若 profile 定义了 `analysis_padding_code`，分析序列头尾各加一次（默认 13）。导出的原始编码表不加 padding。

**Reliability**  
输入：两份导出 xlsx。  
输出：一致率、κ、18×18 混淆矩阵、分编码统计、xlsx 报告。  
失败：文件读失败 CLI 非 0。未实现「校验是否同一视频」。片段 < 30 仍计算，解读风险写在 `docs/reliability_metrics.md`。

**Windows packaging**  
输入：本仓库 + CI windows-latest + Python 3.8。  
输出：`dist/ITIAS-Coder-v{version}-win64-win7.zip`，内含 exe、`_internal/`、`ffmpeg/ffmpeg.exe` 与 `ffprobe.exe`。  
失败：缺 exe 或 PyInstaller 非 0 则 job 失败。不上传 artifact。同 tag 覆盖 Release。

## Key Decisions

### Why ffmpeg segment + `-c copy`, not re-encode or Python 解码器

教室录像常见 40–45 分钟。stream copy 只重新封装，机房电脑可在短时间内切完。`-f segment` + `-segment_time` 是 ffmpeg 内置等长切分。

**Why not** moviepy/OpenCV/逐帧重编码：依赖重、CPU 要跑满节课时长的倍数，机房不可用。  
**Why not** 失败后自动 `libx264`： silently 改变片长、画质与等待时间，编码者以为仍是 3s copy。失败路径 = 显示 ffmpeg 返回码。  
已知行为：copy 模式下切点对齐关键帧，实际段长可以 **大于** 设定的 3s。这是封装限制，不是 UI 范围 bug。测量域见 PRD 约束表。

### Why 默认 3s 且 UI 锁 1–30s 整数, not 1s Flanders 或事件时长编码

ITIAS 课堂互动分析的常用取样间隔是 3 秒；UI 文案写明「ITIAS 标准为 3 秒」。上限 30s 防止误填成分钟级导致一节课只有几段。

**Why not** 变长事件编码（按下开始/结束）：与 CCIES 等间隔切片工作流不兼容，导出「片段序号」语义会崩。  
**Why not** 允许 0 或小数秒：编码格子必须是整数秒取样，SpinBox 就是合同。

### Why PySide 桌面, not Web 或 Electron

必须本机播视频、本机跑 ffmpeg、断网可编码。Web 意味着上传或本地 HTTP 暴露媒体，和「课堂录像含真人 + public 仓库」冲突。Electron 再打一份 Chromium，Win7 机房更劝退。

**Why not** 纯 CLI：目标用户是教研员，主路径必须是按钮。CLI 只留给信度批处理（`--reliability`）。

### Why Win7 + Python 3.8 + PySide2 便携 zip, not 只支持 Win10/PySide6

学校机房仍有 Win7。Python 3.12 包在 Win7 上会缺 `api-ms-win-core-path-l1-1-0.dll`（README 已写）。因此 Release 配方钉死 3.8 + PySide2 5.15.2.1；开发机用 PySide6，经 `qt_bindings.py` 分流。

**Why not** 放弃 Win7 换单一 PySide6：会切掉明确承诺的交付面。要放弃必须先改本 RFC 与 PRD。  
**Why not** 给教师 `pip install`：机房无权限、无 Python。必须解压双击。  
**Why not** MSI/安装器：需要管理员；便携目录可放 U 盘。

### Why PyInstaller onedir + sidecar `ffmpeg/`, not onefile

frozen 后 `app_dir()` 是 exe 旁目录。`find_ffmpeg` 先看 `app_dir()/ffmpeg/ffmpeg.exe`。onedir 让 `_internal/` 与 `ffmpeg/` 稳定存在。

**Why not** onefile：解压到临时目录，sidecar 路径漂，启动慢，杀毒软件更敏感。  
**Why not** 假设用户已装系统 ffmpeg：机房通常没有。

### Why Release-only zip, not Actions artifact

zip 约 220MB。artifact 与 Release 双存浪费存储；分享入口统一为 Releases。commit `5392f7f` 明确去掉 artifact。

**Why not** 只保留 artifact：教师没有 Actions 权限，下载链不稳。

### Why YAML profiles, not 写死 18 个按钮

ITIAS 是默认框架，IFIAS/自定义通过加 YAML 完成。主界面 combo 列出 `config/profiles/*.yaml`。写死 18 键会让第二次框架变成分叉。

**Why not** 可视化编辑器：PRD 非目标。改框架 = 改文件，可 code review。

### Why `.itias_save.json` 放在切片目录, not SQLite/AppData

进度必须跟着那一盒片段走（U 盘拷走仍能续）。JSON 可打开检查。每点一次编码就写盘，避免崩溃丢整节课。

**Why not** 用户主目录统一数据库：换电脑/换盘即丢上下文。  
**Why not** 只在退出时保存：机房断电是常规失败模式。

### Why Excel+TXT 对标 CCIES 列, not 只 CSV

下游是教研表格与既有 CCIES 教程工作流。TXT 一行一码方便贴进其他脚本。列「片段序号」是续作与信度对齐键。

**Why not** 专有二进制：无法用 Excel 打开，信度与多课导入会无输入。

### Why 分析头尾补码 13, not 对原始序列直接画图

ITIAS 矩阵分析习惯在序列两端补「沉寂/混乱」（码 13）。profile 字段 `analysis_padding_code: 13` 把该文献约定收成数据，而不是写死在绘图里。导出表保持原始逐段编码，避免污染信度输入。

**Why not** 把 padding 写进 Excel：双编码者文件会被人为插入两行，κ 失真。

### Why 信度做 κ 与混淆矩阵, not ANOVA F

CCIES 工作流的核心可比指标是一致率、κ、混淆矩阵。F 检验依赖研究设计，应在 SPSS 做。见 `docs/reliability_metrics.md` 局限第 5 条。

**Why not** 只报百分比：类别极不均衡时（大量「沉寂」）会虚高。κ 是最低补丁。

### Why 全部本地、失败即停, not 云 fallback

public 仓 + 真人课堂录像。任何「失败了传到某 API」都是事故。与 PRD 非目标第 1、7 条同一约束。

## Deploy / 安全

- License：MIT。公开文件禁止真实隐私（PRD 非目标 7）。
- CI：`itias-coder-windows.yml` 只在 `itias_coder/**`、`packaging/**`、`config/**`、`requirements*.txt`、workflow 自身变更时打包。
- 凭证：Windows 构建不需要课堂媒体；不要把测试录像塞进 Actions cache。
- 飞书入站是需求入口，不接触课堂媒体。

## Dependencies

运行（开发）：Python 3.10+，PySide6，openpyxl，PyYAML，本机 ffmpeg。  
Win7 包：Python 3.8，PySide2==5.15.2.1，同左其余，ffmpeg essentials 在构建时从 gyan.dev 下载后打进 zip。  
明确不引入：云 SDK、ORM/数据库、Web 框架、GPU 转码、AI 模型。

## Future (Phase 2, not in MVP)

从当前依赖里拿掉，不是从选项空间删除：

- GPU/硬件加速切片（README roadmap）。仍必须本机，仍禁止云。
- IFIAS 等更多内置 YAML（框架文件，不是编辑器）。
- 切片失败后的**显式、用户确认**重编码模式（默认仍 copy）。
- 合成视频 fixture + pytest 分层（见 `docs/test.md`）；隐私扫描进 CI。
- 给 agent 的本机 ControlServer（opt-in HTTP）以便无 GUI 脚本验播放。不在本次文档 retrofit 实现。

## 设计自攻（2026-08-21 retrofit）

去留三问。人工拍板点在「已上线行为保持」；本清单只砍文档层过度完整，不改运行时。

| 项 | 三问命中 | 裁决 |
| --- | --- | --- |
| 补 `docs/design.md` | 更便宜等价：无 token/Prohibit 表时空文档违反 scaffold §5 | **砍**。有界面但无设计系统；视觉改版再写 |
| ffmpeg 静默重编码 fallback | 失败面：耗时与片长漂移超过「总能切出来」的价值 | **砍**。保持报错 |
| GUI ControlServer | 更便宜等价：本 issue 禁止运行时；test.md 先写手动/单测层 | **推迟**到 Phase 2 |
| 放弃 Win7 统一 PySide6 | 与 PRD 交付面冲突 | **留** 双栈 |
| 信度 GUI + CLI 双入口 | 冗余？CLI 服务批处理，GUI 服务教师，职责不同 | **留** |
| 把 GPU 切片写进非目标 | 非目标≠future work；GPU 是 Phase 2 选项 | **不放进 Non-Goals**，放 Future |
| 为完整而加空 `tests/` | scaffold 禁止空文档/空测试充数 | **砍**。只在 test.md 写命令 |

## 决策考古缺口

- `MAX_LESSONS = 30` 的相邻备选未入 git。保持 30，新上限必须带否案。
- 时间箱 60s 同理。
