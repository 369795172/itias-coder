# ITIAS Coder

Open-source classroom video **ITIAS** interaction analysis coding tool (MVP). A free alternative to password-locked commercial CCIES-style tools.

## Features

- **Video slicing**: Split classroom recordings into segments (default 3s, configurable 1–30s) via ffmpeg
- **ITIAS coding**: Auto-play segments; click one of 18 standard ITIAS behavior codes per segment
- **Undo**: Revert the last code and replay that segment
- **Auto-save / resume**: Progress saved after each code; resume from `.itias_save.json`
- **Export**: Excel + TXT (CCIES-compatible column layout)
- **Analysis**: Single-lesson behavior matrix (60s bins), proportion charts, time-series lines
- **Multi-lesson compare**: Import up to 30 Excel exports; side-by-side stats and overlay line charts
- **Profiles**: Pluggable YAML encoding frameworks (ITIAS default; IFIAS/custom later)

## Requirements

- Python 3.10+
- PySide6, openpyxl, PyYAML
- ffmpeg on PATH (or bundled in Windows zip)

## Run (dev)

```bash
pip install -r requirements.txt
python -m itias_coder
```

## Windows portable build

**系统要求**：Windows 7 SP1 及以上（64 位）。学校机房常见 Win7 可用；旧包用 Python 3.12 打包会在 Win7 上报 `api-ms-win-core-path-l1-1-0.dll` 缺失。

```powershell
.\packaging\build_windows.ps1
```

下载：打开 [Releases](https://github.com/369795172/itias-coder/releases/latest) → 下载 `ITIAS-Coder-v*-win64-win7.zip`。改代码/打包配置推 main（或手动 `workflow_dispatch`）会自动发/更新对应版本 Release；不另存 Actions artifact，避免重复占存储。

解压整个文件夹，双击 `ITIAS-Coder.exe`（需保留 `_internal/`、`ffmpeg/`）。

若仍无法播放视频，可安装 [VC++ 2015–2022 运行库](https://aka.ms/vs/17/release/vc_redist.x64.exe)。

## Encoding framework

Default profile: `config/profiles/itias_default.yaml` (顾小清 & 王炜 2004, 18 categories).

## Roadmap

- ~~Analysis module (interaction matrix, behavior charts; ITIAS head/tail code 13 padding)~~ ✓ v0.2.0
- ~~Multi-lesson comparison reports~~ ✓ v0.2.0
- Profile picker UI, reliability metrics, optional GPU slicing

Reference: [CCIES tutorial](https://luoyaocray.github.io/post/cciestu-wen-jiao-xue/)

## License

MIT
