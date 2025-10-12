# 在 PPTAgent 的 conda 環境中從無到有生成 PPT（Step-by-step）

這份文件說明如何在本 repository (`PPTAgent`) 的 conda 環境中，從零開始建立環境、安裝相依、解析一份 PDF（或使用本地 adapter）到中間格式，最後用 PPTAgent 產生 PowerPoint 檔案。

Answer
------

以下教學完全依據本 repository 的內容撰寫，並在 Evidence 區列出所引用的檔案路徑。

環境：macOS，shell: zsh。

Prerequisites（先決條件）
- 已安裝 Anaconda 或 Miniconda（本文以 conda 指令為主）。
- Python >= 3.11（本專案 pyproject.toml 要求）

主要步驟摘要
- 建立 conda 環境並安裝套件
- 設定必要的環境變數（例如 MINERU_API、API_BASE、OPENAI_API_KEY）
- 解析 PDF -> 產生 runs/pdf/<md5>/source.md 與 images
- 使用 PPTAgent 的生成流程產生 PPT

詳細步驟
1) 取得 repo（假設你已經在本地有專案）

2) 建立 conda 環境

   建議使用 Python 3.11：

   ```bash
   conda create -n pptagent python=3.11 -y
   conda activate pptagent
   ```

3) 安裝相依（使用 pyproject.toml 的 dependencies 為依據）

   - 開發時建議使用 pip 來安裝 requirements 中列出的套件。pyproject.toml 中有 main dependencies 與 optional `full`。在有限資源下，可先安裝主要依賴：

   ```bash
   pip install -e .
   # 若想安裝 full 能力（transformers、timm 等），可執行：
   pip install -e .[full]
   ```

   注意：安裝過程中若有需要安裝大型 ML 套件（transformers、torch 等），請依你系統的 CUDA / CPU 配置特別處理。

4) 設定必要的環境變數

   在本專案中幾個重要的環境變數（程式碼與文件中有使用）：

   - `MINERU_API`：用於 `pptagent/model_utils.py::parse_pdf`，若未設定，`parse_pdf` 會 assert 失敗。此變數應指向能回傳 zip 的 endpoint，如 `http://localhost:8000/file_parse`。
   - `API_BASE`、`LANGUAGE_MODEL`、`VISION_MODEL`、以及你的 LLM 提供者的金鑰（例如 OpenAI 的 `OPENAI_API_KEY` 或其他 provider 的 API key，具體 key 名稱視你使用的客戶端而定）。

   範例（使用本機 adapter 或 MinerU 本體）：

   ```bash
   # 若你已啟動 MinerU 或本地 adapter，指向 parse endpoint
   export MINERU_API="http://localhost:8000/file_parse"

   # LLM 設定（依你使用的 provider 與 client 而異）
   export API_BASE="https://api.openai.com/v1"
   export OPENAI_API_KEY="sk-..."

   # 可選：覆寫模型名稱
   export LANGUAGE_MODEL="gpt-4.1"
   export VISION_MODEL="gpt-4.1"
   ```

   參考證據：`pptagent/model_utils.py` 會讀取 `MINERU_API`，並在未設定時 warning（或 assert 在 `parse_pdf` 被呼叫時）。

5) 解析 PDF（產生中間資料）

   - 你有三種選擇（參考 `docs/mineru_docling_comparison.md`）：
     A) 直接使用 MinerU API（若有 MinerU 服務）來解析 PDF。PPTAgent 預期 MinerU 回傳一個 zip（內含 `source.md`、images、metadata），`parse_pdf` 會把 zip 解壓到 `output_folder`。
     B) 使用 Docling 或其他工具，把 PDF 轉成 Markdown + images，然後包成與 MinerU 相容的 zip（或修改 `pptagent/model_utils.parse_pdf` 以直接寫入 `output_folder`）。
     C) 撰寫一個小的 adapter（FastAPI）來提供 `MINERU_API` 相容的 endpoint（repo 的比對文件有具體建議）。

   - 範例：假設你使用 MinerU 或 adaptor 並已設定 `MINERU_API`，可用下列 Python 範例呼叫 `parse_pdf`（或直接在你的 script 中使用）

   ```python
   from pptagent.model_utils import parse_pdf

   await parse_pdf('/path/to/your.pdf', 'runs/pdf/your_md5')
   ```

   或使用一個簡單的腳本：

   ```bash
   python - <<'PY'
   import asyncio
   from pptagent.model_utils import parse_pdf

   asyncio.run(parse_pdf('paper.pdf', 'runs/pdf/sample'))
   PY
   ```

   解析成功後，請確認 `runs/pdf/<folder>/source.md` 與 `images/` 目錄存在（`pptagent/pptgen.py` 與 UI、MCP server 會讀取這些檔案）。

6) 以解析後的 Document 生成 PPT

   - 產生 PPT 需要兩件事：reference presentation（templates）與解析後的 Document（`Document.from_markdown` 會被 pipeline 使用）。repo 中 `pptagent/pptgen.py` 展示如何透過 `PPTAgent` 類別產生簡報。

   - 範例腳本（最小流程示意）：

   ```python
   import asyncio
   from pptagent.document.document import Document
   from pptagent.pptgen import PPTAgent
   from pptagent.llms import AsyncLLM
   from pptagent.presentation.presentation import Presentation

   async def main():
       # 初始化模型（以環境變數設定為主）
       language = AsyncLLM('gpt-4.1')
       vision = AsyncLLM('gpt-4.1')

       # 讀取 reference presentation template（repo 中有 template folder）
       prs = Presentation.from_template('pptx/default_template')

       agent = PPTAgent(language, vision)

       # slide_induction、presentation 需從參考 prs 與 slide induction json 產生
       # 簡化流程：假設你已有 runs/pdf/<id>/slide_induction.json 與 prs
       import json
       with open('runs/pdf/your_md/slide_induction.json', 'r') as f:
           slide_induction = json.load(f)

       agent.set_reference(slide_induction, prs)

       doc = Document.from_markdown('runs/pdf/your_md/source.md')

       prs_out, history = await agent.generate_pres(doc, num_slides=10, image_dir='runs/pdf/your_md/images')
       prs_out.save('output/generated_presentation.pptx')

   asyncio.run(main())
   ```

   注意：上例是簡化版本；實務上 `slide_induction.json` 與 `Presentation` 的來源可由 `pptagent_ui` 或 `ppteval` pipeline 生成。請參考 `pptagent/pptgen.py` 的 `PPTAgent` 類別與 `pptagent/presentation` 模組以了解更完整流程。

7) 驗證與除錯

   - 若 `parse_pdf` 失敗，請檢查 `MINERU_API` 是否正確、服務是否可達，以及回傳是否為 zip 並包含單一 top-level 資料夾（`model_utils.parse_pdf` 會檢查此條件）。
   - 若 LLM 連線失敗，請確認 `API_BASE`、相關 API key（例如 `OPENAI_API_KEY`）與模型名稱是否正確。`pptagent/llms.py` 包含 `test_connection` 方法可用於檢查。

   附錄：可直接在 shell（zsh）執行的範例指令與驗證步驟
   -------------------------------------------------

   下面是一組從安裝、啟動到上傳並下載結果的最小可複製指令（zsh），前提是你已在 repo 根目錄並已執行 `pip install -e .`。這樣你可以不用另外寫 Python 就能試跑整個 pipeline（假設已部署 MinerU 或本地 adapter）。

   1) 啟動後端（以 uvicorn 啟動 FastAPI）

   ```bash
   # 在 zsh 中啟動 backend
   uvicorn pptagent_ui.backend:app --host 0.0.0.0 --port 9297
   ```

   2) 上傳 PDF（觸發後端 pipeline）

   ```bash
   # 注意：上傳檔案時 -F 欄位必須以 @ 開頭表示檔案路徑，否則 FastAPI 會把它當字串處理
   curl -s -X POST "http://localhost:9297/api/upload" \
      -F "pdfFile=@/Users/xjp/Desktop/Survey-with-LLMs/PPTAgent/docs/https:arxiv.org:pdf:2501.03936.pdf" \
      -F "numberOfPages=10" | jq
   # 回傳範例：{"task_id":"2025-10-11|<uuid>"}
   ```

   說明：你剛剛看到的錯誤

   ```
   Value error, Expected UploadFile, received: <class 'str'>
   ```

   是因為 curl 的 `-F "pdfFile=..."` 少了 `@`，因此後端收到的是字串（file path string），而不是 multipart 上傳的檔案物件（UploadFile）。使用上面正確帶 `@` 的指令即可把本機檔案作為 multipart/form-data 上傳，FastAPI 的 endpoint 將會收到 `UploadFile`。

   3) 監看進度（選用：WebSocket）

   後端支援 WebSocket 來回報進度（`/wsapi/{task_id}`）。可用 `websocat` 或 `wscat` 監看（示範使用 websocat）：

   ```bash
   # 安裝 websocat（若尚未安裝）
   # brew install websocat

   # 以 task_id 為例：2025-10-11|<uuid>
   websocat "ws://localhost:9297/wsapi/2025-10-11|<uuid>"
   ```

   4) 下載結果（完成後）

   ```bash
   curl -o generated.pptx "http://localhost:9297/api/download?task_id=2025-10-11|<uuid>"
   ```

   快速檢查 runs 資料夾（在本機上除錯很有用）

   ```bash
   ls -la runs/pdf
   ls -la runs/pptx
   # 檢查特定任務資料夾
   ls -la runs/pdf/<md5>/
   # 期待看到 source.md, refined_doc.json, images/ 等
   ```

   使用 Docker 的選項（快速上手）
   --------------------------------

   若你偏好用 Docker（README/DOC 建議的方式），repo 含 `docker/Dockerfile` 與 `docker/launch.sh`，可以用 Docker 啟動整套環境（省去本機相依問題）：

   ```bash
   # 範例（在 repo 根目錄）：
   docker build -t pptagent:local -f docker/Dockerfile .
   docker run --rm -p 9297:9297 -e MINERU_API="http://host.docker.internal:8000/file_parse" pptagent:local
   ```

   建議：若用 Docker 啟動 MinerU 或 adapter，請把 `MINERU_API` 指向 container 可存取的 host（例如 `host.docker.internal` 或 container network 中的 service 名稱）。

   建立本地 adapter 的最小建議（如果你沒有 MinerU）
   --------------------------------------------------

   若你沒有 MinerU，最簡單的方式是建立一個小的 FastAPI adapter（接受 multipart 上傳，內部呼叫 Docling 或 pdf2image+markdown 邏輯，並回傳 zip）。`docs/mineru_docling_comparison.md` 已給出三種策略：

   - Option A（推薦）: 建一個 `tools/mineru_adapter.py`，啟動後把 `MINERU_API` 指向 `http://localhost:8000/file_parse`。啟動指令示例：

   ```bash
   uvicorn tools.mineru_adapter:app --host 0.0.0.0 --port 8000
   export MINERU_API="http://localhost:8000/file_parse"
   ```

   - Option B: 直接用 Docling CLI/Python 在本地把 PDF 轉成 `runs/pdf/<md5>/source.md`、images、並手動放到 runs 目錄（較少程式改動）

   - Option C: 修改 `pptagent/model_utils.parse_pdf` 以直接使用 Docling Python API（需要修改程式碼並加測試）。

   常見錯誤與排解
   ------------------

   - parse_pdf 斷言失敗（AssertionError: MINERU_API is not set）
      - 原因：`MINERU_API` 未設定或 adapter/MinerU 未啟動。
      - 解法：啟動你的 adapter 或 MinerU，或設定 `MINERU_API` 指向正確 endpoint。

   - 解析後沒有 `source.md` 或 images
      - 原因：MinerU/adaptor 回傳 zip 結構不符合（`model_utils.parse_pdf` 要求 zip 只有一個 top-level folder），或 adapter 沒有把檔案寫入 `output_folder`。
      - 解法：解壓 adapter 回傳的 zip，確認 zip 內的 top-level 資料夾與 `source.md`、images、metadata 是否存在；或直接在本機手動建立 `runs/pdf/<md5>/source.md` 作為測試。

   - LLM 連線錯誤（模型不可達或金鑰錯誤）
      - 原因：`API_BASE`、`OPENAI_API_KEY`（或其他 provider key）未設定，或模型名稱錯誤。
      - 解法：檢查環境變數、使用 `pptagent.llms.AsyncLLM.test_connection()` 進行檢查，或查看啟動日誌錯誤訊息。

   - 模組找不到或 ImportError（執行 uvicorn 時）
      - 原因：尚未用 `pip install -e .` 安裝 package，或 Python path 不包含 repo 根目錄。
      - 解法：先執行 `pip install -e .`，或從 repo 根目錄使用 `PYTHONPATH=. uvicorn pptagent_ui.backend:app`。

   下一步建議
   --------------

   - 如果你想快速本地測試且沒有 MinerU，我可以直接在 repo 新增 `tools/mineru_adapter.py`（一個最小 FastAPI 實作），並加入 `requirements-dev.txt` 與 `test/test_parse_pdf_adapter.py` 測試範例，讓你能用 `uvicorn tools.mineru_adapter:app --port 8000` 本地模擬 MinerU；或
   - 我可以把 `docs/generate_ppt_conda.md` 再加上更完整的 `curl` 測試範例與 `jq` / `websocat` 範例以方便排查（目前已包含基本示例）。

   Evidence（補充）
   -----------------

   - `pptagent_ui/backend.py`：包含 upload route、wsapi、以及 `if __name__ == "__main__": uvicorn.run(app, host=ip, port=9297)`，因此可直接用 `uvicorn pptagent_ui.backend:app` 或 `python pptagent_ui/backend.py` 啟動後端。路徑：`/pptagent_ui/backend.py`。
   - `docs/mineru_docling_comparison.md`：描述如何建立 adapter，並建議 `uvicorn adapter:app --port 8000`。路徑：`/docs/mineru_docling_comparison.md`。


Evidence
--------

- `pyproject.toml` (requires Python >= 3.11; dependencies 列表)：`/pyproject.toml`
- `pptagent/model_utils.py`（`MINERU_API` 與 `parse_pdf` 的實作）：`/pptagent/model_utils.py`
- `docs/mineru_docling_comparison.md`（說明如何使用 MinerU、Docling、或 adapter）：`/docs/mineru_docling_comparison.md`
- `pptagent/pptgen.py`（展示如何用 `PPTAgent` 產生 PPT）：`/pptagent/pptgen.py`
- `pptagent/llms.py`（LLM 初始化與環境變數使用說明）：`/pptagent/llms.py`

Unknowns / Gaps
-----------------

- 本 repo 未包含 MinerU 的本體服務或本地 adapter 的實作檔（adapter 建議範例存在於比對文件，但未加入 repo）；若你沒有 MinerU 服務，需要自行搭建 adapter（參考 `docs/mineru_docling_comparison.md` 中的建議）。
- 真正的 reference `slide_induction.json` 與 reference `Presentation` 產生流程在 UI 或 pipeline 中（例如 `pptagent_ui/backend.py` 與 `pptagent/mcp_server.py`），實務上你可能需要先執行 UI pipeline 或準備 `slide_induction.json`。

---

如果你想，我可以：

- 幫你在 repo 中新增一個簡單的 `tools/mineru_adapter.py` FastAPI 範例（Option A 的實作），並新增對應的 `requirements-dev.txt` 與測試範例；或者
- 直接修改 `pptagent/model_utils.py::parse_pdf` 使其能以 Docling 的 Python API 直接產生 `output_folder`（Option B），並提交測試。

請回覆你想要哪個選項（或只要文件即可）—我會接著執行下一步。
