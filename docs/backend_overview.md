# PPTAgent 后端实现详解

> 适用版本：当前仓库（2025-12-04）。如有更新，请同步修改本文件及 `GEMINI.md`。

## 整体架构
- 入口脚本：`run_backend.sh` → `tools/run_backend_helper.py`，完成环境检测（Python≥3.11、可导入 `pptagent`、定制 python-pptx）后，调用 `uvicorn` 启动 `pptagent_ui/backend.py` 中的 FastAPI 应用。
- 服务进程：FastAPI + WebSocket，提供上传、进度、下载、反馈接口；任务状态保存在 `runs/` 目录（按日期/UUID 分层）。
- 主要依赖模型通过 `pptagent.model_utils.ModelManager` 统一管理：`language_model`、`vision_model`、`image_model`、`marker_model`（用于 PDF 解析）。

## 服务接口（`pptagent_ui/backend.py`）
- `POST /api/upload`：接收 PPTX/PDF/主题、页数，写入 `runs/pptx/<md5>/source.pptx` 与 `runs/pdf/<md5>/source.pdf`，异步创建生成任务并返回 `task_id`。
- `WS /wsapi/{task_id}`：推送阶段进度，`ProgressManager` 负责计算百分比与错误上报。
- `GET /api/download`：返回生成的 `final.pptx`。
- `POST /api/feedback`：存储用户反馈到 `runs/feedback/{task_id}.txt`。

## 任务流水线（`pptagent_ui/backend.py:ppt_gen`）
1. **PPT 解析**：`Presentation.from_file` 读取参考模板；必要时调用 `ppt_to_images_async` 将幻灯片转成 JPEG；`ImageLabler` 基于视觉模型生成图片 caption（若已有 `image_stats.json` 则复用）。
2. **PDF 解析**：`parse_pdf`（Marker/LLM 辅助）将上传 PDF 转 Markdown，存入 `runs/pdf/<md5>/source.md`。
3. **文档精炼**：`Document.from_markdown` 调用一系列 prompt 提取元数据、标题、区块摘要，输出结构化 `refined_doc.json`。
4. **版式归纳**：`SlideInducter.layout_induct/content_induct` 对参考 PPT 的图像与 HTML 结构进行聚类与内容分析，生成 `slide_induction.json`（包含功能性版式、通用版式、语言信息）。
5. **生成阶段**：`PPTAgent`（继承 `PPTGen`）
   - `set_reference`：加载归纳结果，建立 `Layout` 集合与功能版式（Opening/TOC/Section Outline/Ending）。
   - `generate_outline`：`planner` 角色根据文档概览和页数生成大纲。
   - `generate_pres`：逐页选择版式（`layout_selector`）、撰写元素内容（`editor`）、提炼要点（`content_organizer`），再通过 `coder` + `apis.CodeExecutor` 将文本/图像写入 `SlidePage`，最终保存 `final.pptx`。

## 核心类与职责
- `pptagent/pptgen.py::PPTAgent(PPTGen)`：生成流程调度、版式选择、角色管理、长度系数自适应、重试机制。
- `pptagent/apis.py::CodeExecutor` 与 API 函数：暴露用于修改幻灯片的编程接口（`replace_paragraph/clone_paragraph/del_paragraph/replace_image/del_image/add_table/merge_cells` 等），并记录历史以便错误追踪。
- `pptagent/presentation/*`：`Presentation`/`SlidePage`/`ShapeElement`/`Picture`/`Layout` 等对象模型，封装 pptx 读写与版式描述。
- `pptagent/document/*`：`Document` 结构化表征解析出的 Markdown，提供媒体索引与语言信息。
- `pptagent/induct.py::SlideInducter`：对参考幻灯片进行版式与内容诱导，生成可迁移的布局模板。
- `pptagent/model_utils.py::ModelManager`：按环境变量初始化 OpenAI/自托管模型，并提供 `parse_pdf`、`caption_images_async` 等工具。

## Prompt 与角色模板（原文 + 中文意译）
以下为后端调用的全部提示词/角色模板，按文件分类。原文保留，中文为简要直译，便于审阅。

### prompts/

**ask_category.txt**
```
Analyze the content layout and media types ...
Output: Provide a one-line layout pattern description, without line breaks or other formatting.
```
中文：分析幻灯片图片的版式与媒体类型，只描述“怎么排版”，不描述主题；输出一句话版式模式。

**caption.txt**
```
Describe the main content of the image in less than 50 words ... Now give your answer in one sentence only, without line breaks:
```
中文：50 词内描述图片主内容并分类（Table/Chart/Diagram/Banner/Background/Icon/Logo/Picture），格式 `<type>:<description>`，单行输出。

**category_split.txt**
```
You are an expert presentation analyst ... Output:
```
中文：检测结构型幻灯片（开场、目录、章节封面、结束），按实际存在列出对应页码，输出 JSON。

**lengthy_rewrite.txt**
```
You are a presentation expert tasked with rewriting ... Output:
```
中文：逐项压缩改写元素内容，保持数量与原语言，字符不超限，可用常见缩写，不增删信息。

#### prompts/document/
- **heading_extract.txt**：提取 Markdown 结构中的顶级标题（基于数字或语义），输出 `{ "headings": [...] }`，每块字符 <32768。
- **markdown_image_caption.txt**：结合附近文本为图片写 50 词内描述并分类，优先图片内容。
- **markdown_table_caption.txt**：基于 Markdown 表格和邻近内容写 50 词内 caption，前缀 `Table:`。
- **merge_metadata.txt**：合并多段元数据字典，清洗冗余，输出统一 JSON。
- **section_summary.txt**：将分段内容压缩成 <100 词摘要。

#### prompts/ppteval/
- **ppteval_style.txt**：按五分制评价幻灯片视觉风格，给出 reason+score。
- **ppteval_content.txt**：按五分制评价内容质量与图文配合。
- **ppteval_coherence.txt**：按五分制评价整体连贯性与背景信息完整度。
- **ppteval_describe_style.txt**：描述可读性、配色、视觉元素。
- **ppteval_describe_content.txt**：描述信息密度、文本质量、图像相关性。
- **ppteval_extract.txt**：提取各页用途与开场/结束中的背景元数据。

### roles/

**schema_extractor.yaml**
- 系统：专家级版式 Schema 抽取，逐元素输出 `name/type/data`，`data` 对应 `<p>` 文本或 `<img alt>`。
- 模板：解析给定 HTML，遵循示例输出 JSON `elements` 列表。

**layout_selector.yaml**
- 系统：根据文本/图片/大纲选择最佳版式并给出详细理由。
- 模板：输出 `{reasoning, layout}` JSON，考量内容匹配、图片相关性、字符长度。

**coder.yaml**
- 系统：将编辑命令转成 API 调用。
- 模板：依据 `(element_class, type, quantity_change, old, new)` 序列，按克隆/删除/替换规则生成带注释的 API 调用列表。

**content_organizer.yaml**
- 系统：提取关键要点。
- 模板：输出包含 `pointName/paragraphForm/bulletForm` 的 JSON；若无内容返回空列表。

**doc_extractor.yaml**
- 系统：单章节 Markdown 抽取。
- 模板：合并段落成子节，生成 ≤5 词标题、100 词摘要和显式元数据。

**planner.yaml**
- 系统：演示文稿大纲设计。
- 模板：在指定页数内选取重点部分（方法/结果等），生成包含 `purpose/topic/indexes/images` 的 `outline` JSON，排除摘要/参考文献。

**agent.yaml**
- 系统：多功能内容与代码生成助手，按 schema+outline+metadata+text+images_info 生成 API 调用序列，限制克隆/删除互斥、保持 HTML 层级。

**editor.yaml**
- 系统：撰写幻灯片元素内容。
- 模板：根据 `outline/metadata/slide_description/slide_content/schema/language` 输出 `elements` 列表，遵守 `default_quantity` 与字符限制，必要时可少量删除但优先填满。

## 数据流小结
1. 前端上传 → `/api/upload` 存盘并启动 `ppt_gen`；WebSocket 推进度。
2. 参考 PPT → 图片 → ImageLabler 打标签；模板版式 → SlideInducter 归纳。
3. PDF → Markdown → Document 精炼 → 提供内容索引、元数据、语言。
4. 大纲规划（planner）→ 版式选择（layout_selector）→ 文本生成（editor/content_organizer）→ API 调用编排（coder/agent + CodeExecutor）。
5. `final.pptx` 写入 `runs/<task>/`，`/api/download` 提供下载；失败通过 WebSocket 返回错误信息。

## 运行提示
- 需设置 `OPENAI_API_KEY`，可选 `LANGUAGE_MODEL`/`VISION_MODEL`/`IMAGE_MODEL`/`MARKER_MODEL` 环境变量。
- 默认端口 `9297`，可用 `BACKEND_HOST/BACKEND_PORT` 覆盖。
- 依赖定制 `python-pptx` 版本（带 `+PPTAgent` 标识）。

