> **Note:** This document is related to `GEMINI.md`. Please ensure both files are kept in sync when making changes.

## Agent Conduct

- Do not modify existing source code or any pre-existing files (e.g., contents under `runs/`) without explicit user approval.
- If changes appear necessary after thorough analysis, obtain user consent before proceeding.
- Avoid injecting or pre-populating runtime output artifacts (e.g., `runs/` cache files) unless explicitly requested.
- Keep `docs/quick_start.md` up to date whenever setup or execution steps change and ensure its presence is documented here.
- 尽量用大陆用语的简体中文回应，但专有名词请用英文。

## Debugging Tools

The `tools/` directory contains scripts that can be useful for debugging and troubleshooting common issues.

- **`inspect_pdf.py`**: Counts the number of pages in a PDF file. This is useful for diagnosing discrepancies in file conversion.
- **`inspect_pptx.py`**: Reports the number of slides in a `.pptx` file as detected by the `python-pptx` library. This helps identify parsing issues where the library may not be reading all slides.
