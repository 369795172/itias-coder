# PRD — ITIAS Coder

Gate A 来源：数值与边界从已上线 README / UI / 配置 harvest（2026-08-20 Human Gate 批准本 retrofit 执行；阈值不由 agent 新造）。开放考古缺口见文末。

## Problem

师范院校与教研场景要用 ITIAS（18 类课堂互动编码）分析课堂录像。商业 CCIES 类工具常加密、难部署到学校机房（大量 Windows 7），且工作流默认假设编码者能拿到完整桌面软件。开源替代必须在**本机**完成「切片 → 逐段播放编码 → 导出/分析」，不能把含真人的课堂录像送上云。

## Users

一句话用户问题：教研员或师范生在课后对课堂录像做 ITIAS 18 类编码时，怎样在不购买商业加密码工具、不把含真人的录像上传网络的前提下，完成切片、逐段编码、导出与基础分析？

使用者是编码者本人（教师、教研员、学生编码员），在本机或机房电脑上操作。不是平台运营、不是云端标注众包。

## Goals

1. 用本机 ffmpeg 把一节课切成等长片段，供逐段编码。
2. 对每个片段点选恰好一个 ITIAS 行为代码（默认 18 类），支持撤销并重播该段。
3. 编码进度可中断恢复；结果能导出为可交给 CCIES/SPSS 后续流程的 Excel 与 TXT。
4. 单课给出行为占比、60s 时间箱矩阵与类别时间序列；多课可并排对比。
5. 两名编码者对同一切片集的 Excel 可算一致性（百分比 + Cohen's κ + 混淆矩阵）。
6. 学校机房交付：解压即用的 Windows 7 SP1+ x64 便携包，ffmpeg 打在包内。

## Non-Goals（硬边界）

砍错即翻车。这些不是 backlog。

1. **不上云、不上传录像。** 本工具没有账号体系和远程媒体服务。本地 ffmpeg 失败时展示错误，禁止静默调用任何云转码/云存储 API。
2. **不做通用视频编辑器。** 不提供裁剪时间线、字幕、调色、合并多机位。唯一视频职责是等长切片 + 片段回放。
3. **不做实时课堂观察。** 只编码已录好的文件。不接摄像头直播、不在上课过程中打点。
4. **不做自动 AI 行为分类。** 代码必须由人点选。不把片段送进视觉/语音模型出 1–18 类标签。
5. **不做推断统计套件。** 不实现 ANOVA F 及其他 SPSS 级检验。信度停在百分比一致、Cohen's κ、18×18 混淆矩阵、分编码一致率（见 `docs/reliability_metrics.md`）。
6. **不做 Web/SaaS/移动端。** 交付面是桌面 Python 应用与 Windows 便携 zip。浏览器上传录像会直接撞上隐私红线。
7. **git 与 CI 不含课堂真人素材。** 禁止把课堂 `.mp4` 等、学生/教师真名、学校名、人脸截图作为 fixture 或文档插图提交。public 仓发布前隐私扫描必须零命中。
8. **不提供可视化编码框架编辑器。** 框架以 `config/profiles/*.yaml` 落地；主界面只选择已有 profile。改类目 = 改 YAML。
9. **不把 macOS/Linux 便携安装包当作交付面。** 开发者可 `python -m itias_coder` 跑。学校安装包只承诺 Windows zip。
10. **切片失败不自动重编码。** 保持 stream copy。不能播的编码格式报错退出，不在后台转码「帮用户修好」。

## Success Criteria

每条可勾选。验证方式写在括号内。阈值精确。

- [ ] 切片时长：UI 整数范围 **1–30 秒**（含端点），默认 **3 秒**（打开切片对话框，确认 QSpinBox 无法选 0 或 31；不改控件时值为 3）
- [ ] 默认框架：`config/profiles/itias_default.yaml` 恰好 **18** 条 codes，id 为 **1–18** 连续整数（`python -c` 读 YAML 计数；或打开编码窗数 18 个按钮）
- [ ] 点选某一代码后，该片段 `code_id` 写入 session，并在 **同一切片目录** 写出 `.itias_save.json`（编码 1 段后确认该文件存在且 JSON 含该 `code_id`）
- [ ] 撤销：Ctrl+Z 或「撤销」清除**上一条**编码，重播该段，并再次写入 `.itias_save.json`（编码 A→B 后撤销，B 段无 code，播放回到 B）
- [ ] 关闭再打开「开始编码」并选同一文件夹：从 `.itias_save.json` 恢复已编码进度，从第一个未编码片段续播（编码 5/N 后重启应用验证）
- [ ] 导出同时得到 `.xlsx` 与 `.txt`；Excel 活动表表头为「片段序号, 文件名, 编码, 编码描述, 类别, 编码时间」，TXT 一行一个 code_id 或空行（导出后用表格软件与文本编辑器打开）
- [ ] 单课分析时间箱宽度 **60 秒**；ITIAS 分析序列在有效 codes 两端各补一个 **13**（沉寂/混乱 padding）（对 3s×N 的完整 session 跑分析，箱标签步进 60s；序列首尾为 13）
- [ ] 多课对比最多导入 **30** 份 Excel；第 31 份被拒绝（连续导入直到上限；第 31 次不得加入列表）
- [ ] 信度：两份同切片序号的 Excel → 报告含整体百分比一致、仅双编码百分比一致、Cohen's κ、18×18 混淆矩阵（GUI「第四步」或 `python -m itias_coder --reliability a.xlsx b.xlsx`）
- [ ] Windows 便携包：GitHub Release 资源名匹配 `ITIAS-Coder-v*-win64-win7.zip`；解压后存在 `ITIAS-Coder.exe`、`_internal/`、`ffmpeg/ffmpeg.exe`（打开 Releases 页或本地 `build_windows.ps1` 产物）
- [ ] Win7 兼容构建配方冻结为 **Python 3.8 + PySide2==5.15.2.1**（读 `.github/workflows/itias-coder-windows.yml` 的 `python-version` 与 `requirements-build-win7.txt`）
- [ ] 开发机离线可编码已有切片：断开网络后仍能播放本地片段并写 `.itias_save.json`（关 Wi-Fi 复测；切片步骤若本机已有 ffmpeg 二进制同样不访问网络）
- [ ] public 工作树隐私扫描命令零命中（按 `docs/test.md` 门禁命令执行，exit code 0）

## Constraints

三条落地形式。冲突时优先序（人审不可委派，此处记录已上线选择）：**隐私 > Win7 可运行 > 切片速度（stream copy）> 片长绝对精确到毫秒**。

### 1. 数字 + 测量点 + 适用域

| 约束 | 数字 | 测量点 | 适用域 |
| --- | --- | --- | --- |
| 切片时长 | 默认 3s，可调 1–30s 整数 | `SlicerDialog` 的 QSpinBox；写入 `Session.segment_duration` | 仅 UI 与 SliceWorker；ffmpeg segment 实际切点受关键帧约束，允许长于设定值 |
| 编码类目 | 18 类，id 1–18 | `itias_default.yaml` 的 `codes` 长度与 id | 默认 ITIAS profile；其他 YAML 可不同，分析/信度 UI 按当前 profile |
| 分析时间箱 | 60s | `analysis.time_matrix(..., bin_seconds=60)` 默认实参 | 单课分析与多课叠加图的时间轴 |
| 分析 padding | 码 13，头尾各 1 | `analysis_padding_code` + `padded_sequence` | 仅分析序列，不改导出 Excel 的原始逐段编码 |
| 多课上限 | 30 | `compare_window.MAX_LESSONS` | 仅多课对比导入 |
| 信度样本警告 | 片段数 < 30 时 κ 不稳 | `docs/reliability_metrics.md` 说明，非运行时硬拒 | 研究解读；工具仍计算 |
| ffprobe | timeout 30s | `slicer.probe_duration` | 仅探测时长；失败则进度条无精确总分母 |
| Win7 | SP1+，64-bit | README 系统要求 + CI `python-version: "3.8"` | 仅 Windows Release 产物；开发机不受此限 |
| 版本 | `__version__` 字符串 | `itias_coder/__init__.py` | Release tag `v{version}` 与 zip 文件名 |

### 2. 测试程序

- 离线编码：关 Wi-Fi 后对**本地已有切片文件夹**完成至少 1 段编码 + 存盘成功。
- Win7 配方未漂：CI workflow 的 Python 仍是 3.8，且 `requirements-build-win7.txt` 钉死 `PySide2==5.15.2.1`。
- 隐私：`docs/test.md` 门禁命令在干净 clone 上 exit 0。

### 3. 排除清单（含失败路径）

- 无 ffmpeg：对话框报错，提示安装或使用带 `ffmpeg/` 的 zip；不下载、不调用云。
- stream copy 无法切该容器/编码：ffmpeg 非 0 退出，向用户显示返回码；**不**自动重编码。
- 切片目录无视频：编码入口提示，不创建空 session。
- 信度两个文件片段序号对不齐：按序号做 outer join；不校验视频文件名（已知局限，写在信度文档）。
- 本机非 Windows：不生成便携 zip；开发用 `python -m itias_coder`。

## 决策考古缺口

以下数字已上线，git 历史未留下「为什么是这个数而不是相邻值」的否案。retrofit **不改数值**。从本文件起新决策按 RFC 纪律记。

- 多课对比上限恰好 30（而非 20/50/无上限）
- 分析时间箱恰好 60s（而非 30s/120s）
