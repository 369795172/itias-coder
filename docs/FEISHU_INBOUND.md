# Feishu Inbound — ITIAS Coder

飞书需求 → GitHub Issue → 分析 → 执行（引擎在 rootgrove monorepo）。

## 提需求

1. 飞书多维表格（`FI_PERSONAL_*` Bitable）新增一行，或 `repository_dispatch`
2. **GitHub**：https://github.com/369795172/itias-coder/issues/new ，label `feishu-inbound`

## rootgrove 配置

| 文件 | 说明 |
| --- | --- |
| `config/feishu_inbound_itias_coder.yaml` | Instance 配置 |
| `config/feishu_inbound_itias_coder_surfaces.yaml` | Worktree `projects/itias-coder` |

Pipeline A：本仓库 `.github/workflows/feishu-inbound.yml`

## 本机（Marvin Mac）

```bash
bash tools/feishu_inbound/bootstrap_labels.sh 369795172/itias-coder
GITHUB_REPO=369795172/itias-coder bash tools/feishu_inbound/setup_pipeline_a_github_secrets.sh
./venv/bin/python tools/feishu_inbound/triage_agent.py --config config/feishu_inbound_itias_coder.yaml --scan-only
```

详见 rootgrove `rules/skills/workflow_feishu_inbound_pipeline.md`。
