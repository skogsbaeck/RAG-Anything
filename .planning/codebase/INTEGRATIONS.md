# External Integrations

**Analysis Date:** 2026-02-20

## APIs & External Services

**LightRAG Integration:**
- Service: LightRAG knowledge graph backend
  - What it's used for: Core RAG pipeline, entity extraction, relationship discovery, knowledge graph storage
  - SDK/Client: `lightrag-hku` Python package
  - Implementation: `raganything/raganything.py` lines 27, 50-83; `raganything/modalprocessors.py` lines 20-27
  - Configuration: Via `lightrag_kwargs` parameter in `RAGAnything` dataclass for LightRAG initialization
  - Auth: Depends on underlying LightRAG storage backends (KV store, vector DB, graph DB credentials)

**HuggingFace Model Hub:**
- Service: Model repository hosting
  - What it's used for: Accessing pre-trained Whisper models, embeddings, and other ML models
  - SDK/Client: `huggingface_hub` Python package
  - Configuration: Models downloaded on-demand via library
  - Auth: Optional HuggingFace token (via `huggingface_hub` environment variable support)

**OpenAI Whisper Models:**
- Service: Speech-to-text models (via faster-whisper optimization)
  - What it's used for: Audio transcription from various formats (MP3, WAV, M4A, OGG, FLAC, AAC)
  - SDK/Client: `faster-whisper` Python package
  - Implementation: `raganything/audio.py` lines 73-92
  - Models: `tiny`, `base`, `small`, `medium`, `large` sizes
  - Configuration: `AUDIO_WHISPER_MODEL` in `RAGAnythingConfig`
  - Device: CPU or CUDA GPU via `AUDIO_DEVICE` config
  - Compute type: INT8 quantization for performance via `faster_whisper.WhisperModel()`

## Data Storage

**Databases:**
- Configuration through LightRAG abstraction
  - Storage types: KV storage, vector storage, graph storage, doc status storage
  - Client: Configured via `lightrag_kwargs` parameter passed to LightRAG initialization
  - Implementation: `raganything/raganything.py` lines 72-83
  - Note: RAG-Anything is storage-agnostic; actual backend determined by LightRAG instance configuration

**File Storage:**
- Local filesystem only
  - Working directory: `WORKING_DIR` environment variable (default: `./rag_storage`)
  - Parser output: `OUTPUT_DIR` environment variable (default: `./output`)
  - Implementation: `raganything/config.py` lines 18, 26
  - Batch processing: Files processed from local filesystem via directory scanning
  - Implementation: `raganything/batch.py`, `raganything/batch_parser.py`

**Caching:**
- LightRAG KV storage for parse result caching
  - Purpose: Cache document parsing results to avoid re-parsing
  - Implementation: `raganything/raganything.py` line 93-94 (`parse_cache` field)
  - Backend: Uses LightRAG's configured KV storage

## Authentication & Identity

**Auth Provider:**
- Custom/None for core system
  - Note: RAG-Anything itself does not implement authentication
  - LightRAG authentication: Depends on configured storage backend
  - HuggingFace optional: Token-based authentication for private models
  - Environment variable: `HF_TOKEN` (HuggingFace library standard)

**Credentials Location:**
- Environment variables (via `.env` file)
  - Loaded in: `raganything/raganything.py` line 25 via `load_dotenv()`
  - Override behavior: OS environment variables take precedence
  - Storage: `.env` file in project root (not committed to version control)

## Monitoring & Observability

**Error Tracking:**
- None detected in core codebase
- Logging infrastructure in place for debugging

**Logs:**
- Approach: Python `logging` module
  - Logger instances: Created via `logging.getLogger(__name__)` in each module
  - Main logger: `lightrag.utils.logger` used for core operations
  - Implementation locations:
    - `raganything/audio.py` line 14
    - `raganything/enhanced_markdown.py` line 14
    - `raganything/batch_parser.py` line 9
    - `raganything/parser.py` line 60
    - `raganything/modalprocessors.py` lines 20-21
  - Log levels: INFO, WARNING, ERROR used throughout
  - Console output: Default Python logging to stderr

## CI/CD & Deployment

**Hosting:**
- Not detected - RAG-Anything is a Python library/framework
- Deployable as: Standalone Python package, embedded in applications

**CI Pipeline:**
- Pre-commit hooks configured in `.pre-commit-config.yaml`
- Hooks:
  - `trailing-whitespace` - Removes trailing whitespace
  - `end-of-file-fixer` - Ensures files end with newline
  - `requirements-txt-fixer` - Sorts requirements.txt
  - `ruff-format` - Code formatting (ruff v0.6.4)
  - `ruff` - Linting with auto-fix (ignores E402 import errors)
  - `check-manifest` - Validates MANIFEST.in (manual stage)
- Installation: `pre-commit install` to enable hooks
- Execution: Runs before commits via git hooks

## Environment Configuration

**Required Environment Variables:**
- `WORKING_DIR` - Storage directory (default: `./rag_storage`)
- `PARSE_METHOD` - Parsing strategy (default: `auto`)
- `PARSER` - Parser selection: `mineru` or `docling` (default: `mineru`)
- `OUTPUT_DIR` - Parser output directory (default: `./output`)
- `AUDIO_LANGUAGE` - Transcription language (default: `auto`)
- `AUDIO_WHISPER_MODEL` - Model size (default: `base`)
- `AUDIO_DEVICE` - Processing device (default: `cpu`)

**LightRAG Configuration:**
- Configurable via `lightrag_kwargs` parameter to `RAGAnything`
- Examples of configurable parameters:
  - `kv_storage` - Key-value storage backend
  - `vector_storage` - Vector database backend
  - `graph_storage` - Graph database backend
  - `llm_model_name` - LLM model identifier
  - `embedding_func` - Embedding function
  - Additional parameters documented in LightRAG library

**Secrets Location:**
- `.env` file in project root
  - Note: This file should NOT be committed to version control
  - Loaded at runtime: `raganything/raganything.py` line 25
  - Critical for: TIKTOKEN_CACHE_DIR (offline use), LightRAG credentials

## Webhooks & Callbacks

**Incoming:**
- None detected - RAG-Anything is a processing library, not a server

**Outgoing:**
- None detected - System processes documents sequentially without callback mechanisms

## External Programs

**LibreOffice:**
- Purpose: Convert Office documents to PDF
  - Formats handled: `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`
  - Implementation: `raganything/parser.py` method `convert_office_to_pdf()`
  - Invocation: Via `subprocess` with libreoffice command-line
  - Optional: Only required if Office document processing is needed
  - Installation: System package (e.g., `apt install libreoffice` on Linux)

**Pandoc:**
- Purpose: Optional document conversion tool
  - Detection: `raganything/enhanced_markdown.py` lines 36-42
  - Status: Detected if present, but optional
  - Use case: Alternative markdown/document conversion strategy

## Document Format Support

**Supported Input Formats:**

**Documents:**
- PDF (`.pdf`) - Via MinerU/Docling parsers
- Office: (`.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`) - Via LibreOffice conversion to PDF
- Text: (`.txt`, `.md`) - Direct text parsing
- Images: (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`, `.gif`, `.webp`) - Image processing pipeline

**Audio:**
- `.mp3` - MP3 audio files
- `.wav` - WAV audio files
- `.m4a` - AAC audio files in M4A container
- `.ogg` - Ogg Vorbis audio files
- `.flac` - FLAC audio files
- `.aac` - AAC audio files

**Configuration:**
- Full list: `SUPPORTED_FILE_EXTENSIONS` in `RAGAnythingConfig`
- Default (line 74-80): `.pdf,.jpg,.jpeg,.png,.bmp,.tiff,.tif,.gif,.webp,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.mp3,.wav,.m4a,.ogg,.flac,.aac`
- Extensible: Custom extensions configurable via environment variable

---

*Integration audit: 2026-02-20*
