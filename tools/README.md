# Tools

This directory contains helper and utility scripts for the PPTAgent project.

## `run_backend_helper.py`

This script is the main entry point for running the backend server. It performs environment checks (Python version, dependencies) and starts the `uvicorn` server for the FastAPI application. It is intended to be called by the main `run_backend.sh` script.

## Debugging Scripts

The following scripts were created during a debugging session to diagnose issues related to file parsing and conversion. They can be useful for future troubleshooting.

### `inspect_pdf.py`

A simple script to count the number of pages in a given PDF file.

**Usage:**
```bash
conda run -n pptagent python tools/inspect_pdf.py <path_to_pdf_file>
```

### `inspect_pptx.py`

A script that uses the `python-pptx` library to open a `.pptx` file and report how many slides it can detect. This is useful for identifying discrepancies between how `python-pptx` parses a file versus other tools like LibreOffice.

**Usage:**
```bash
conda run -n pptagent python tools/inspect_pptx.py <path_to_pptx_file>
```
