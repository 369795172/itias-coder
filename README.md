# ITIAS Coder

Open-source classroom video **ITIAS** interaction analysis coding tool (MVP). A free alternative to password-locked commercial CCIES-style tools.

## Features

- **Video slicing**: Split classroom recordings into segments (default 3s, configurable 1–30s) via ffmpeg
- **ITIAS coding**: Auto-play segments; click one of 18 standard ITIAS behavior codes per segment
- **Undo**: Revert the last code and replay that segment
- **Auto-save / resume**: Progress saved after each code; resume from `.itias_save.json`
- **Export**: Excel + TXT (CCIES-compatible column layout)
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

```powershell
.\packaging\build_windows.ps1
```

Or use GitHub Actions → **ITIAS Coder Windows** workflow → download artifact `ITIAS-Coder-win64`.

Unzip and run `ITIAS-Coder.exe` (keep `_internal/` and `ffmpeg/` alongside the exe).

## Encoding framework

Default profile: `config/profiles/itias_default.yaml` (顾小清 & 王炜 2004, 18 categories).

## Roadmap

- Analysis module (interaction matrix, behavior charts; ITIAS head/tail code 13 padding)
- Multi-lesson comparison reports
- Profile picker UI, reliability metrics, optional GPU slicing

Reference: [CCIES tutorial](https://luoyaocray.github.io/post/cciestu-wen-jiao-xue/)

## License

MIT
