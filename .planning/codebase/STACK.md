# Technology Stack

**Analysis Date:** 2026-02-20

## Languages

**Primary:**
- Python 3.10+ - All core application code, RAG system, document parsing, and multimodal processing

**Secondary:**
- Bash - Build scripts and utilities (found in `.pre-commit-config.yaml`)

## Runtime

**Environment:**
- Python 3.10 (minimum requirement specified in `pyproject.toml`)
- CPython interpreter

**Package Manager:**
- `uv` - Modern package manager (noted as "uv-Ready" in README)
- `pip` - Standard installation method
- `setuptools` - Package building and distribution

**Lockfile:**
- `requirements.txt` - Present; pins core dependencies

## Frameworks

**Core RAG Framework:**
- `lightrag-hku` - LightRAG library from Hong Kong University (HKUDS/LightRAG)
  - Location: `raganything/raganything.py`, `raganything/modalprocessors.py`
  - Purpose: Knowledge graph construction, entity extraction, multimodal RAG pipeline
  - Version: Flexible (pinned via `lightrag-hku` in `requirements.txt`)

**Document Parsing:**
- `mineru[core]` - MinerU 2.0 library for high-fidelity document parsing
  - Location: `raganything/parser.py`
  - Purpose: PDF and complex document structure extraction, semantic preservation
  - Supported formats: PDFs, complex multi-layout documents
  - Version: Latest (flexible)

- `docling` - Alternative document parsing library
  - Location: `raganything/parser.py` (via `DoclingParser`)
  - Purpose: Fallback/alternative document parsing strategy
  - Configurable via `parser` setting in `RAGAnythingConfig`

**Audio Processing:**
- `faster-whisper` 0.10.0+ - OpenAI Whisper speech-to-text engine
  - Location: `raganything/audio.py`
  - Purpose: Audio transcription with optimized inference
  - Optional dependency (installable via `raganything[audio]`)

**Testing:**
- `pytest` 6.0+ - Test runner
- `pytest-asyncio` - Async test support for concurrent operations
- Location: Development dependencies in `pyproject.toml` under `[tool.uv] dev-dependencies`

**Code Quality:**
- `black` - Code formatter (development)
- `isort` - Import sorting utility (development)
- `flake8` - Linter (development)
- `mypy` - Static type checker (development)
- `ruff` - Fast Python linter and formatter (pre-commit hook)
  - Config: `.pre-commit-config.yaml` uses ruff v0.6.4
  - Targets Python 3.10+ code

**Build/Dev:**
- `setuptools` 64+ - Package building
- `wheel` - Wheel distribution format
- `python-dotenv` - Environment variable loading from `.env` files

## Key Dependencies

**Critical:**
- `lightrag-hku` - Core knowledge graph and RAG infrastructure
  - Why it matters: Entire system is built on LightRAG for entity extraction, relationship discovery, and multimodal knowledge graph construction
  - Used in: `raganything/raganything.py`, `raganything/modalprocessors.py`, `raganything/query.py`

- `mineru[core]` - Document parsing
  - Why it matters: Handles high-fidelity extraction of complex document structures including text, tables, equations, and images
  - Enables multimodal content decomposition in `raganything/parser.py`

- `huggingface_hub` - Model hosting and downloading
  - Why it matters: Required for accessing Whisper models and other HuggingFace hosted models
  - Used implicitly by `faster-whisper` and other ML libraries

**Infrastructure:**
- `tqdm` - Progress bars for batch processing
  - Location: `raganything/batch_parser.py`
  - Purpose: User feedback during long-running batch operations

**Optional - Image Processing:**
- `Pillow` 10.0.0+ - Image format conversion (BMP, TIFF, GIF, WebP)
  - Installable via `raganything[image]`
  - Location: Core parsing pipeline

**Optional - Text to PDF Conversion:**
- `reportlab` 4.0.0+ - Text/Markdown to PDF conversion
  - Installable via `raganything[text]`
  - Used in `raganything/enhanced_markdown.py` for text document conversion

**Optional - Markdown Processing:**
- `markdown` 3.4.0+ - Markdown parsing and rendering
  - Installable via `raganything[markdown]`
  - Location: `raganything/enhanced_markdown.py`

- `weasyprint` 60.0+ - HTML/CSS to PDF conversion
  - Installable via `raganything[markdown]`
  - Location: `raganything/enhanced_markdown.py`
  - Purpose: Enhanced markdown to PDF with styling support

- `pygments` 2.10.0+ - Syntax highlighting for code blocks
  - Installable via `raganything[markdown]`
  - Location: `raganything/enhanced_markdown.py`

**Optional - Office Document Processing:**
- `LibreOffice` - External program (not Python package) for converting Office documents to PDF
  - Required for `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx` processing
  - Invoked via subprocess in `raganything/parser.py` method `convert_office_to_pdf()`

**Development Only:**
- `openai` - OpenAI API client (for testing/development)
  - Not in production dependencies
  - Listed in `[tool.uv] dev-dependencies`

## Configuration

**Environment Variables:**
- Loaded via `python-dotenv` from `.env` file (path: `raganything/raganything.py` line 25)
- Override behavior: OS environment variables take precedence over `.env` file
- Critical for: `TIKTOKEN_CACHE_DIR` (offline environments), LightRAG credentials, audio device selection

**Configuration Class:**
- `RAGAnythingConfig` in `raganything/config.py`
- Environment variable support via `lightrag.utils.get_env_value()`
- Key settings:
  - `WORKING_DIR` - RAG storage/cache location (default: `./rag_storage`)
  - `PARSER` - Parser selection: `mineru` or `docling` (default: `mineru`)
  - `PARSE_METHOD` - Parsing strategy: `auto`, `ocr`, or `txt` (default: `auto`)
  - `AUDIO_LANGUAGE` - Audio transcription language (default: `auto`)
  - `AUDIO_WHISPER_MODEL` - Model size: `tiny`, `base`, `small`, `medium`, `large` (default: `base`)
  - `AUDIO_DEVICE` - Processing device: `cpu` or `cuda` (default: `cpu`)
  - `ENABLE_IMAGE_PROCESSING` - Image content processing (default: `True`)
  - `ENABLE_TABLE_PROCESSING` - Table content processing (default: `True`)
  - `ENABLE_EQUATION_PROCESSING` - Equation content processing (default: `True`)
  - `MAX_CONCURRENT_FILES` - Batch processing concurrency (default: `1`)
  - `SUPPORTED_FILE_EXTENSIONS` - Comma-separated list of allowed formats

**Build Configuration:**
- `pyproject.toml` - PEP 518 build system specification
  - Build backend: `setuptools.build_meta`
  - Dynamic versioning from `raganything/__init__.py`

- `setup.py` - Alternative legacy build script
  - Reads metadata from `raganything/__init__.py` (`__version__`, `__author__`, `__url__`)
  - Defines extras_require for optional feature groups

- `ruff.toml` configuration in `pyproject.toml`
  - Target version: Python 3.10
  - Pre-commit hook configuration in `.pre-commit-config.yaml`

## Platform Requirements

**Development:**
- Python 3.10+ interpreter
- pip or uv package manager
- Git (for version control)
- LibreOffice (optional, for Office document conversion)
- CUDA toolkit (optional, for GPU audio transcription)

**Production:**
- Python 3.10+ runtime
- All core dependencies from `requirements.txt`
- Optional dependencies depend on use case:
  - Image processing: Pillow
  - Text-to-PDF: reportlab
  - Markdown processing: markdown, weasyprint, pygments
  - Audio transcription: faster-whisper, librosa, soundfile
  - Office document processing: LibreOffice system package

**Optional System Dependencies:**
- `librosa` - Audio analysis library (for audio metadata extraction)
- `soundfile` - Audio file I/O library (for audio metadata extraction)
- Both installed via `raganything[audio]`

---

*Stack analysis: 2026-02-20*
