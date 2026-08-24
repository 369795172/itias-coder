# AGENTS.md — itias-coder

课堂录像 ITIAS 半自动编码工具（Python/PySide6/Windows 构建）。本文件当前只承担运行环境路由；工程约定按 rootgrove `rules/WORKSPACE.md` 的 itias_coder 域条目执行。

## Feishu Inbound（需求流水线运行环境）

本仓的 feishu inbound（Pipeline C–F）不在本仓运行，由 rootgrove 托管：

- 运行环境：rootgrove venv（`/Users/marvi/CursorWorks/rootgrove/venv/bin/python`）；引擎 pin SSOT = rootgrove `tools/feishu_inbound/requirements.txt`
- Instance config：rootgrove `config/feishu_inbound_itias-coder.yaml`（surface 路由见 `feishu_inbound_itias-coder_surfaces.yaml`）
- 调度：launchd `com.personal.feishu-inbound-lead-tick` → `tools/feishu_inbound/run_personal_lead_tick.sh`（umbrella tick 同时驱动 personal/dong516-rehab/engine/itias-coder/rootgrove 五个 config）
- 引擎仓：`369795172/feishu-inbound-skill`（只装 Release wheel，不跟踪其 main）

Windows 构建走本仓 GitHub Actions；与本仓本地 Python 环境无关。

## Feishu Inbound（需求流水线运行环境）

本仓的 feishu inbound（Pipeline C–F）不在本仓运行，由 rootgrove 托管：

- 运行环境：rootgrove venv（`/Users/marvi/CursorWorks/rootgrove/venv/bin/python`）；引擎 pin SSOT = rootgrove `tools/feishu_inbound/requirements.txt`
- Instance config：rootgrove `config/feishu_inbound_itias-coder.yaml`（surface 路由见 `feishu_inbound_itias-coder_surfaces.yaml`）
- 调度：launchd `com.personal.feishu-inbound-lead-tick` → `tools/feishu_inbound/run_personal_lead_tick.sh`（umbrella tick 同时驱动 personal/dong516-rehab/engine/itias-coder/rootgrove 五个 config）
- 引擎仓：`369795172/feishu-inbound-skill`（只装 Release wheel，不跟踪其 main）
