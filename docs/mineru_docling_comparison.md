# MinerU vs Docling — 比較與替換建議

## 快速結論

- 本專案（PPTAgent）目前預設並依賴 MinerU 的 API（透過環境變數 `MINERU_API` 指向類似 `http://localhost:8000/file_parse` 的端點）。若未設定，`parse_pdf` 會直接 assert 失敗，因此在現有程式碼中 MinerU（或對應的兼容 API）為解析 PDF 的預設與主要依賴。
- MinerU 為功能完整的文件解析框架，支援 layout 分析、OCR、公式轉 LaTeX、表格轉 HTML、圖像提取與 zip 輸出等，且官方提供本地部署（pip / Docker / FastAPI / Gradio）。基礎使用可自托管並免費，但官方也提供線上/商業化入口（需登入/可能有商業方案）。
- Docling 則是另一個針對文件理解與格式轉換的開源專案（MIT license），支援 PDF、DOCX、PPTX 等多格式，以及直接匯出 Markdown/JSON、支援 VLM、MCP server 與本地執行；Docling 在解析架構與輸出上與 MinerU 功能相似，通常可作為替代方案。

## 比較表（重點）

- 功能性
  - MinerU: 強調高品質版面/表格/公式/閱讀順序與多輸出格式（zip、JSON、multimodal markdown），專注於學術/複雜排版文件解析。
  - Docling: 支援多種格式（PDF、DOCX、PPTX）、layout 與表格解析、可輸出 Markdown/JSON，並提供 integrations（LangChain、LlamaIndex 等）。

- 授權
  - MinerU: 開源 repo（GitHub），須檢查 repo 中的 LICENSE（repo 上顯示 AGPL-3.0 或 LICENSE.md，請以官方 repo 為準）。AGPL 授權對商業與衍生部署有較嚴格義務。
  - Docling: MIT 授權（較寬鬆）。

- 部署與使用方式
  - MinerU: 支援 pip 安裝、Docker 部署、啟動 `mineru-api`、`mineru-gradio` 等；可本地化，且官方有線上 web 版本（需登入）。
  - Docling: pip 安裝即可使用 CLI 或 Python API，本地執行，並提供 MCP server 支援 agent 應用。

- 輸出契約（與 PPTAgent 相容性）
  - MinerU: PPTAgent 的實作預期 MinerU API 回傳一個 zip（內含 `source.md`、圖片、metadata JSON 等），`parse_pdf` 會解壓 zip 並直接把內容放到指定 `output_folder`。因此 MinerU 與 PPTAgent 的整合是透過這個「zip 檔 + 檔案結構」契約。
  - Docling: 可以輸出 Markdown 與 JSON，但不是 MinerU 的 zip 格式，因此直接替換需要提供 adapter 層，或改寫 `parse_pdf` 使其接受 Docling 的輸出格式。

- 社群與成熟度
  - MinerU: OpenDataLab 大量投入、頻繁 release、針對 document parsing 深度優化。
  - Docling: LF AI & Data 主導、IBM Research 等參與、也有技術報告（arXiv），為另一個活躍選項。

## 在本專案中替換 MinerU 的選項（具體步驟）

下面列出三種可行策略，依你想做的改動大小與可接受風險選擇：

選項 A — 建立兼容 MinerU API 的 adapter（建議最少改動）

- 概念：在本地用 docling（或其他工具）做解析，然後用一個小的服務（FastAPI 或簡單 CLI）把 docling 的輸出包裝成 PPTAgent 目前期望的 zip 結構（包含 `source.md`、提取的圖檔、任何必要的 JSON metadata），並提供一個與 MinerU API 相同路徑與回傳形式的 endpoint（例如 `POST /file_parse` 回傳 zip binary）。
- 優點：對 PPTAgent 內部程式碼改動最小；只需把 `MINERU_API` 指向這個 adapter 的 URL。
- 缺點：需實作 adapter，但通常較簡單；需要注意檔案命名、圖片相對路徑與 metadata 的一致性。
- 簡單實作步驟：
  1. 用 pip 安裝 docling： `pip install docling`。
  2. 撰寫一個小的 FastAPI 應用，接收 multipart 上傳（pdf），內部呼叫 docling 的 API 將 pdf 轉成 markdown + 圖片；把結果放到臨時資料夾（結構仿 MinerU 的 zip）；壓縮資料夾為 zip 並以 `application/zip` 回應。
  3. 啟動該 service（例如 `uvicorn adapter:app --port 8000`）並將 `MINERU_API` 設為 `http://localhost:8000/file_parse`。
  4. 於 PPTAgent 執行流程中測試（上傳 PDF）並檢查 `runs/pdf/<md5>/source.md` 與其他檔案是否按預期產生。

選項 B — 直接修改 `pptagent/model_utils.parse_pdf` 使用 Docling（中等改動）

- 概念：把 `parse_pdf` 的實作改為直接呼叫 docling Python API，並把 docling 的輸出寫到 `output_folder`（產生 `source.md`、包含圖像的 `images/` 資料夾、必要的 JSON）。
- 優點：不需建立額外網路服務，流程較單純。
- 缺點：需要改程式碼（model_utils.py），並確保 docling 輸出格式與後續 `Document.from_markdown`、`refined_doc.json` 產生流程相容。
- 主要修改點：替換 `parse_pdf` 中對 MINERU_API 的 HTTP 呼叫，改為呼叫 docling API：例如
  - from docling.document_converter import DocumentConverter
  - converter = DocumentConverter(); result = converter.convert(pdf_path)
  - md = result.document.export_to_markdown(); write `source.md`
  - 將 Result 中的 images 寫入 `output_folder/images/`（保持檔案名稱一致）
- 測試：撰寫小測試（如 `test_parse_with_docling.py`）以確保產生的 `source.md` 與既有流程相容。

選項 C — 接受不同中介格式並修改後續流程（較大改動）

- 概念：改寫整個 pipeline，直接處理 docling 或其他工具的 JSON 格式（取代 MinerU 的中介格式），包括 `Document.from_markdown` 的呼叫與預期欄位。
- 優點：可直接利用替代工具暴露的更豐富結構化資訊。
- 缺點：需要改動多處程式（Document 的產生、refined_doc.json 的內容、測試），工程量最大。

## 具體 adapter 範例（選項 A 的簡短範例）

以下是一個可放在 `tools/mineru_adapter.py` 的簡易 FastAPI 伺服器雛形（示意，需在 repo 中實作）：

- 要求：安裝 `docling` 與 `fastapi`、`uvicorn`。
- 行為：接收上傳的 pdf，呼叫 Docling 產生 Markdown 與圖片，將結果打包成 zip 回傳。

（此處為說明，程式碼實作我可替你提交 patch，如果你要我直接實作並在 repo 加測試，請回覆確認）

## 測試與驗證建議

- 測試檔案：在 `test/` 下新增 `test_parse_pdf_adapter.py`，模擬上傳一個 sample PDF 並確認 `runs/pdf/<md5>/source.md` 與 `refined_doc.json` 能被產生。
- 本地驗證：先在本機啟動 adapter（或 MinerU 本體），export `MINERU_API` 指向該服務，然後以 `python pptagent_ui/backend.py` 或測試腳本啟動流程。

## 參考與 Evidence

- Repo 內 evidence（PPTAgent）:
  - `pptagent/model_utils.py`：使用 `MINERU_API`，且 `parse_pdf` 會 assert `MINERU_API`（若未設定則不可用）並以 POST 呼叫該 API，然後將回傳 zip 解壓到 `output_folder`。
  - `DOC.md`：指示使用 MinerU 並設定 `MINERU_API` 為 `http://localhost:8000/file_parse`。
  - `pptagent_ui/backend.py`、`pptagent/mcp_server.py`：程式會讀取 `image_stats.json`、`slide_induction.json` 等檔案，顯示整個 pipeline 期待特定中介檔案存在。

- 官方文件（我抓取的網頁）:
  - MinerU docs: `https://opendatalab.github.io/MinerU/usage/quick_usage/`（描述 API、CLI、Gradio、部署選項、輸出結構、模型來源等）。
  - MinerU GitHub: `https://github.com/opendatalab/MinerU`（repo、license、releases）。
  - Docling PyPI / Docs: `https://pypi.org/project/docling/` 與 `https://docling-project.github.io/docling/`（功能、安裝、export to Markdown、integration 與 MIT license）。

---

如果你要我接下來做：
- 我可以為選項 A（adapter）實際在 repo 裡新增 `tools/mineru_adapter.py` 與對應的 `requirements-dev.txt` 更新與測試，並提交 patch；或
- 我可以為選項 B 直接修改 `pptagent/model_utils.py::parse_pdf` 加上 docling 的支援（包含測試）；或
- 先幫你抓取並比較更多替代工具（例如 pdfplumber、pypdf、pdfminer.six、paddleocr）以評估在你資料集上的適配性。

請選一個下一步，我會立即執行並更新 todo list。