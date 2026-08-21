# AGENTS.md: ITIAS Coder

课堂录像 **ITIAS** 半自动编码桌面工具：把一节课切成等长片段，人工点选 18 类行为代码，导出 Excel/TXT，并做单课分析、多课对比与双编码者信度。开源替代加密码的商业 CCIES 类工具。Windows 便携包是学校机房交付面。

README 给人看；本文件给 agent。先读本文件，再读 [docs/prd.md](docs/prd.md) 与 [docs/rfc.md](docs/rfc.md)。专题素材（不替代四件套）：[README.md](README.md)、[docs/reliability_metrics.md](docs/reliability_metrics.md)、[docs/FEISHU_INBOUND.md](docs/FEISHU_INBOUND.md)。

## Structure

| 路径 | 职责 |
| --- | --- |
| `itias_coder/` | 运行时：切片、编码 UI、分析、对比、信度、存盘 |
| `itias_coder/qt_bindings.py` | PySide6（开发/macOS）与 PySide2（Win7 包）的唯一 Qt 入口 |
| `config/profiles/` | 编码框架 YAML；默认 `itias_default.yaml`（顾小清 & 王炜 2004，18 类） |
| `packaging/` | Windows onedir PyInstaller + 捆绑 ffmpeg |
| `.github/workflows/itias-coder-windows.yml` | 推 `main` 相关路径或手动 dispatch → Release zip |
| `docs/prd.md` | What & Why：非目标硬边界、可勾选成功标准 |
| `docs/rfc.md` | How：架构、状态机、Key Decisions（含否案） |
| `docs/test.md` | 分层验证 + 隐私 fail-closed 门禁命令 |
| `docs/working.md` | Changelog + Lessons；每次有意义改动后更新 |

本仓是 **public** GitHub。课堂录像含真人，隐私红线见下方 What NOT to do 与 `docs/test.md`。

无界面设计系统。当前 UI 是功能向 Qt Fusion，**不维护 `docs/design.md`**（retrofit 自攻砍掉：无 token 级规格时空文档比缺席更糟）。视觉改版时再补。

## Git

- 分支：`issue-{N}`（飞书入站 / GitHub Issue），PR base `main`
- Issue 相关 commit：`fix: #{N} — <简述>`（必须引用 issue number）
- 粒度：文档 retrofit、运行时实现、验证/门禁脚本分 commit，不混在一笔
- **每次有意义改动后更新 `docs/working.md`**（日期键倒序 + 特性级 bullet）。决策变更同步回写受影响的 prd/rfc/test/AGENTS，禁止口径漂移
- 不改 Windows 构建链路，除非 Issue 明确要求并先改 RFC

## Build / Run / Test

开发（Python 3.10+，本机需 ffmpeg 在 PATH 或常见 Homebrew 路径）：

```bash
pip install -r requirements.txt
python -m itias_coder
python -m itias_coder --reliability coder1.xlsx coder2.xlsx [out.xlsx]
```

Windows 便携包（必须在 Windows 上，或走 Actions；**Python 3.8 + PySide2**，见 `requirements-build-win7.txt`）：

```powershell
.\packaging\build_windows.ps1
```

产物：`dist/ITIAS-Coder-v{version}-win64-win7.zip`。版本号 SSOT 是 `itias_coder/__init__.py` 的 `__version__`（当前 0.3.0）。

当前仓库 **没有 pytest 目录**。验证方案与门禁命令在 [docs/test.md](docs/test.md)。提交运行时改动前：能用确定性单测覆盖的必须先写再跑；隐私扫描命令在门禁落地前由 agent 手动跑，零命中才可推 public。

## Key Decisions（摘要）

细节与否案见 [docs/rfc.md](docs/rfc.md)。

1. ffmpeg `-f segment` + `-c copy` 切片，默认 3s（UI 限制 1–30s 整数），不重编码
2. 学校交付面 = Win7 SP1+ x64 便携 zip（PyInstaller onedir + 旁路 `ffmpeg/`）；CI 用 Python 3.8 + PySide2；开发用 PySide6
3. 只发 GitHub Release，不上传 Actions artifact
4. 编码框架是 YAML profile，不是写死的 18 键；默认 ITIAS 18 类
5. 进度写在切片目录 `.itias_save.json`，每点一次编码/撤销即存盘
6. 导出 Excel + TXT，列布局对标 CCIES 工作流；信度做百分比一致 + Cohen's κ + 混淆矩阵，不做 ANOVA F
7. 全部本地。ffmpeg 失败就报错，禁止静默走云 API 或静默重编码

## What NOT to do

- 不要把课堂录像、学生/教师真名、学校名、人脸截图、真实邮箱/手机写进仓库、fixture、README 截图或 Actions log
- 不要为了「测得更真」提交 `.mp4/.avi/.mov/.mkv/.m4v` 课堂素材；测试只用合成静音短片或 mock 路径
- 不要把隐私扫描当成 warning；门禁命令有命中 = 失败（fail-closed）
- 不要「升级」Windows CI 的 Python/PySide 去追 PySide6，除非先改 RFC 并放弃 Win7 或另开双产物
- 不要把 PyInstaller 改成 onefile：ffmpeg/ffprobe 必须作为 exe 旁路目录
- 不要在切片失败时自动 `-c:v libx264` 重编码（耗时与片长漂移会 silently 毁掉编码者预期）
- 不要做云端账号、视频上传、自动 AI 行为分类、实时课堂观察、通用视频编辑器
- 不要把 SPSS/推断统计（ANOVA F 等）做进本工具；信度文档已写明边界
- 不要为完整而补空的 `docs/design.md` 或空测试文件
- 不要改运行时代码来「顺便」完成文档 Issue；文档-only 的 issue 只动文档
- 不要跳过 `docs/working.md` 更新

## Maintenance

- 文档质量纪律：`prd` 禁止 personas/功能清单/排期；`rfc` 每条决策必须「Why X, not Y」；`test` 写验证方案不写测试代码本体；`working` Lessons 写可迁移原则
- 里程碑后往 `docs/working.md` Lessons 蒸馏一条原则
- 飞书入站：rootgrove `config/feishu_inbound_itias-coder.yaml`；本仓 Pipeline A 见 `.github/workflows/feishu-inbound.yml` 与 `docs/FEISHU_INBOUND.md`
- Public intake：改 `.gitignore` / 加隐私扫描实现走单独 Issue，不在文档 retrofit 里夹带运行时
