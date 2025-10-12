"""A minimal FastAPI backend to accept a PDF, save it under runs/, and (optionally)
call pptagent.model_utils.parse_pdf if MINERU_API is configured.

Usage:
  pip install -e .
  uvicorn tools.simple_backend:app --host 0.0.0.0 --port 9297

This file is intentionally small and dependency-light; it focuses on the "upload -> parse" step.
"""
import hashlib
import os
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

from pptagent.model_utils import parse_pdf

app = FastAPI()

ROOT = os.getcwd()
RUNS_DIR = os.path.join(ROOT, "runs")
os.makedirs(RUNS_DIR, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def index():
    # Serve the simple frontend stored in tools/simple_frontend.html
    path = os.path.join(ROOT, "tools", "simple_frontend.html")
    if os.path.exists(path):
        return HTMLResponse(open(path, "r", encoding="utf-8").read())
    return HTMLResponse("<h3>Simple PPTAgent backend</h3><p>Create tools/simple_frontend.html to use the UI.</p>")


def md5_bytes(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


@app.post("/api/upload")
async def upload_pdf(pdfFile: UploadFile = File(...), numberOfPages: int = Form(10)):
    """Save uploaded PDF to runs/pdf/<md5>/source.pdf and call parse_pdf if possible.

    Returns JSON with task_id (md5) and parsed flag.
    """
    content = await pdfFile.read()
    pdf_md5 = md5_bytes(content)
    pdf_dir = os.path.join(RUNS_DIR, "pdf", pdf_md5)
    os.makedirs(pdf_dir, exist_ok=True)
    source_pdf_path = os.path.join(pdf_dir, "source.pdf")
    with open(source_pdf_path, "wb") as f:
        f.write(content)

    parsed = False
    try:
        # parse_pdf requires MINERU_API to be set; it will assert otherwise
        await parse_pdf(source_pdf_path, pdf_dir)
        parsed = os.path.exists(os.path.join(pdf_dir, "source.md"))
    except AssertionError as e:
        # MINERU_API not set or parse_pdf not available; return tidy message
        return JSONResponse({"task_id": pdf_md5, "parsed": False, "message": str(e)})
    except Exception as e:
        return JSONResponse({"task_id": pdf_md5, "parsed": False, "error": str(e)})

    return JSONResponse({"task_id": pdf_md5, "parsed": parsed, "timestamp": datetime.now().isoformat()})


@app.get("/api/download")
async def download(task_id: str):
    # Serve final.pptx if present under runs/<task_id>/final.pptx (or runs/pdf/<task_id>/final.pptx)
    candidates = [
        os.path.join(RUNS_DIR, task_id, "final.pptx"),
        os.path.join(RUNS_DIR, "pdf", task_id, "final.pptx"),
        os.path.join(RUNS_DIR, "pdf", task_id, "source.pdf"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return FileResponse(p, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename="generated.pptx")
    return JSONResponse({"error": "file not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9297)
