# Test — ITIAS Coder

分层验证。本文件写**测什么、怎么门禁**，不写测试代码本体。当前仓库无 `tests/`；单测落地走后续 PR。隐私扫描实现进 CI 也走后续 PR。命令在落地前由 agent 在提交 public 前手动执行，**有命中即失败**。

## Layer 1 — 确定性单测（无网络、无 ffmpeg、无 GUI、无真实录像）

覆盖纯函数与文件格式，用内存对象或最小 xlsx fixture（合成数字，无人名）。

| 模块 | 验证什么 |
| --- | --- |
| `models.Session` | `coded_count` / `is_complete` / `first_uncoded_index` 与片段 code_id 一致 |
| `profile` | `itias_default` 恰好 18 类，id 1–18；`analysis_padding_code == 13` |
| `analysis.padded_sequence` | 非空 codes 头尾为 13；无 padding 配置则不插入 |
| `analysis.time_matrix` | 默认箱宽 60s；3s 片段 index 映射到正确箱起点 |
| `storage` 导出/导入 | 按片段序号 round-trip `code_id`；TXT 行数 = 片段数 |
| `reliability.compute_agreement` | 全一致 → 百分比 100 且 κ 可计算；故意错位 → 混淆矩阵对应格 +1 |
| `compare_window.MAX_LESSONS` | 常量 = 30（回归锁，防止无 RFC 改上限） |

禁止：把课堂 mp4 放进 `tests/`。路径用临时目录与空文件名即可。

## Layer 2 — 集成（本机 ffmpeg，合成媒体）

适用域：开发者本机已安装 ffmpeg。CI 在门禁脚本落地前不强制。

| 场景 | 验证什么 |
| --- | --- |
| 合成短视频切片 | 用 ffmpeg 生成数秒彩条/静音 mp4（无真人），`SliceWorker` 产出至少 1 个段文件，进程返回 0 |
| 缺 ffmpeg | `find_ffmpeg` 为 None 时 UI/调用方走错误分支，不抛未捕获异常 |
| `--reliability` CLI | 两份合成 xlsx → 退出码 0 且写出报告文件 |

合成媒体命令属于测试机本地步骤，产物丢弃，不提交。

## Layer 3 — 手动 opt-in（真 GUI / 真 Win7 / 真课堂录像）

默认不跑。需要人在目标环境执行。课堂录像只留在操作者磁盘，**禁止**传入 CI 或贴到 Issue。

| 场景 | 验证什么 |
| --- | --- |
| 开发机 GUI | `python -m itias_coder` 走完切片（若有 ffmpeg）→ 编码 2 段 → 撤销 → 导出 → 分析窗打开 |
| 关 Wi-Fi | 对已有本地切片完成 1 段编码并看到 `.itias_save.json` 更新（PRD 离线标准） |
| Win7 机房或 VM | 解压 Release zip，保留 `_internal/` 与 `ffmpeg/`，双击 exe，播放一段切片（若缺 VC++ 再装红字运行库） |
| 双人信度 | 同一切片集两份 Excel，κ 与混淆矩阵可打开；片段 < 30 时只作解读警告 |

自动化能覆盖的变更，commit 前不要丢给人肉点。

## Layer 4 — 隐私 / 卫生扫描（public repo，fail-closed）

课堂录像涉真人。本层是发布硬门禁，不是提示。

在仓库根目录执行。`rg` 命中即失败（exit 1）；全无命中才允许 push/merge。

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
fail=0

# 4a 跟踪中的课堂/视频容器（合成 fixture 落地前一律禁视频进 git）
if git ls-files | grep -Ei '\.(mp4|avi|mov|mkv|m4v|wmv|flv|webm)$'; then
  echo "FAIL: video files must not be tracked"
  fail=1
fi

# 4b 密钥与私钥（排除本文件里的示例正则）
if rg -n --hidden -g '!.git/**' -g '!docs/test.md' \
  -e '-----BEGIN ([A-Z0-9]+ )?PRIVATE KEY-----' \
  -e 'sk-[A-Za-z0-9]{20,}' \
  -e 'ghp_[A-Za-z0-9]{36,}' \
  -e 'github_pat_[A-Za-z0-9_]{20,}' \
  . ; then
  echo "FAIL: secret-like material"
  fail=1
fi

# 4c 邮箱 / 大陆手机。排除本文件示例。命中真实地址 = fail。
if rg -n --hidden -g '!.git/**' -g '!docs/test.md' \
  -e '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' \
  -e '(^|[^0-9])1[3-9][0-9]{9}([^0-9]|$)' \
  . ; then
  echo "FAIL: email or phone-like PII"
  fail=1
fi

exit "$fail"
```

白名单纪律：只有文档里的**示例正则自身**可排除。不得为了让扫描变绿而排除 `docs/` 全文或 `config/`。

配套卫生（扫描命令不替代）：

- `.gitignore` 已忽略 `.itias_save.json`（编码进度常含本地绝对路径）。不要强制添加课堂目录到 git。
- README / Issue / PR 截图不得出现学生正脸或名单。
- Actions log 不得 `cat` 本地媒体路径里的学生姓名。

实现随后续 PR：把上述脚本放进 `scripts/privacy_scan.sh` 并挂到 CI `fail-closed`。本 retrofit 只定义命令，不改 workflow。

## Agent 可验证性

当前没有 ControlServer。agent 优先 Layer 1 的纯函数与 Layer 4 扫描。GUI 路径在 ControlServer（RFC Future）落地前标为 Layer 3。不要把「请用户帮我点一遍」当作默认验证。
