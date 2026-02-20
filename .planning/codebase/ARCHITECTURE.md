# Architecture

**Analysis Date:** 2026-02-20

## Pattern Overview

**Overall:** Modular, composition-based pipeline with mixin layers for separation of concerns

**Key Characteristics:**
- Mixin-based architecture for feature separation (ProcessorMixin, QueryMixin, BatchMixin)
- Wrapper/facade around LightRAG for multimodal document processing
- Event-driven async pipeline with caching at multiple levels
- Multi-stage document processing: Parse → Separate → Process → Insert → Query

## Layers

**Core Orchestration Layer:**
- Purpose: Central coordination of all operations
- Location: `raganything/raganything.py`
- Contains: RAGAnything dataclass, initialization, resource management, configuration
- Depends on: LightRAG, Config, all Mixins
- Used by: All client code

**Document Parsing Layer:**
- Purpose: Convert documents to structured content lists and markdown
- Location: `raganything/parser.py`
- Contains: MineruParser, DoclingParser base classes, document format conversion (PDF, Office, Images, Audio)
- Depends on: External parsers (mineru, docling), LibreOffice for Office conversions
- Used by: ProcessorMixin for document ingestion

**Content Processing Layer:**
- Purpose: Parse multimodal documents and separate text from modal content
- Location: `raganything/processor.py`
- Contains: Document parsing orchestration, content separation, cache key generation, multimodal processing
- Depends on: Document parsers, utility functions
- Used by: ProcessorMixin methods (process_document_complete, process_document_complete_lightrag_api)

**Multimodal Analysis Layer:**
- Purpose: Specialized analysis of different content types (images, tables, equations, audio)
- Location: `raganything/modalprocessors.py`, `raganything/audio.py`
- Contains: ImageModalProcessor, TableModalProcessor, EquationModalProcessor, GenericModalProcessor, ContextExtractor, AudioProcessor
- Depends on: LightRAG, Vision/LLM models, tokenizer
- Used by: ProcessorMixin when inserting with multimodal content

**Query Layer:**
- Purpose: Support both text and multimodal queries against the knowledge graph
- Location: `raganything/query.py`
- Contains: QueryMixin with aquery/query methods, multimodal cache generation, prompt routing
- Depends on: LightRAG, modal processors for vision-enhanced queries
- Used by: Client code for retrieving answers

**Batch Processing Layer:**
- Purpose: Concurrent processing of multiple documents
- Location: `raganything/batch.py`, `raganything/batch_parser.py`
- Contains: BatchMixin with folder/batch processing methods, result aggregation
- Depends on: ProcessorMixin, asyncio for concurrency
- Used by: Applications needing bulk document ingestion

**Configuration Layer:**
- Purpose: Centralized configuration management with environment variable support
- Location: `raganything/config.py`
- Contains: RAGAnythingConfig dataclass with parsing, multimodal, batch, context, and path settings
- Depends on: LightRAG utilities for environment variable parsing
- Used by: RAGAnything initialization and all feature layers

**Utility Layer:**
- Purpose: Shared helper functions across layers
- Location: `raganything/utils.py`
- Contains: Content separation, image encoding, validation, processor resolution
- Depends on: None (no circular dependencies)
- Used by: ProcessorMixin, modal processors, query layer

**Prompt Templates Layer:**
- Purpose: Centralized prompt management for different analysis types
- Location: `raganything/prompt.py`
- Contains: PROMPTS dictionary with system prompts and analysis templates for images, tables, equations, generic content
- Depends on: None
- Used by: Modal processors for LLM/Vision model prompting

## Data Flow

**Document Ingestion Flow:**

1. User calls `process_document_complete(file_path)` on RAGAnything instance
2. RAGAnything ensures LightRAG is initialized via `_ensure_lightrag_initialized()`
3. ProcessorMixin parses document using configured parser (mineru/docling)
4. Parser returns content_list (structured items with types: text, image, table, equation, etc.)
5. ProcessorMixin calls `separate_content()` utility to split text from multimodal items
6. Pure text content inserted into LightRAG via standard insertion pipeline
7. Each multimodal item routed to appropriate modal processor (ImageModalProcessor, TableModalProcessor, etc.)
8. Modal processors:
   - Extract context using ContextExtractor if configured
   - Generate analysis using vision/LLM models via prompts
   - Insert knowledge graph entities/relations into LightRAG
9. Document marked as processed in LightRAG status tracking

**Query Flow:**

1. User calls `aquery(query_text, mode='local')` or similar
2. QueryMixin generates multimodal_cache_key if multimodal content provided
3. Checks LightRAG cache for existing results
4. If cache miss:
   - Calls LightRAG's standard query for text content retrieval
   - If mode='vlm' and multimodal_content provided:
     - Routes to appropriate modal processor for vision analysis
     - Merges results with text retrieval
5. Returns combined results to user

**Batch Processing Flow:**

1. User calls `process_folder_complete(folder_path)` or `process_documents_batch(file_list)`
2. BatchMixin collects files matching configured extensions
3. Creates async task for each file up to max_concurrent_files limit
4. Each task calls `process_document_complete()` on individual files
5. Results aggregated into BatchProcessingResult
6. Summary statistics logged and returned

**State Management:**

- **Parse Cache**: KV storage in LightRAG using `key_string_value_json_storage_cls` with namespace "parse_cache"
  - Key: MD5 hash of file path + mtime + parser config
  - Value: (content_list, doc_id, parse_config, mtime)
  - Purpose: Avoid re-parsing unchanged files

- **Modal Processor State**: Processors hold reference to LightRAG instance and model functions
  - ImageModalProcessor caches vision model function
  - All processors share context_extractor for consistent context extraction

- **LightRAG State**: Manages graph DB, vector storage, KV storage, document status tracking
  - RAGAnything inherits model functions (llm_model_func, embedding_func, vision_model_func)
  - Delegates all knowledge graph operations to LightRAG

## Key Abstractions

**Parser Interface:**
- Purpose: Unified document parsing regardless of format
- Examples: `MineruParser`, `DoclingParser` in `raganything/parser.py`
- Pattern: Base Parser class with format detection, subclasses implement parse() method returning (content_list, markdown_text)

**Modal Processor Interface:**
- Purpose: Pluggable analysis for different content modalities
- Examples: `ImageModalProcessor`, `TableModalProcessor`, `EquationModalProcessor` in `raganything/modalprocessors.py`
- Pattern: Each processor has `process_modal_item()` method, receives (item_dict, context_extractor, lightrag) and inserts entities/relations into knowledge graph

**ContextExtractor:**
- Purpose: Universal context extraction supporting multiple content formats
- Location: `raganything/modalprocessors.py`
- Pattern: Auto-detects content source format (minerU, text_chunks, dict, str) and extracts surrounding content for modal item analysis
- Supports windowing by page, chunk, or token count

**Mixin Pattern:**
- Purpose: Modular feature composition without deep inheritance
- Examples: ProcessorMixin, QueryMixin, BatchMixin combined into RAGAnything
- Pattern: Each mixin is a class with related methods, mixed into RAGAnything via multiple inheritance

## Entry Points

**RAGAnything Initialization:**
- Location: `raganything/raganything.py` RAGAnything.__post_init__()
- Triggers: When RAGAnything() created with config, LightRAG instance, and model functions
- Responsibilities:
  - Load environment variables
  - Initialize parser (mineru or docling)
  - Set up working directory
  - Register cleanup handler via atexit

**LightRAG Lazy Initialization:**
- Location: `raganything/raganything.py` _ensure_lightrag_initialized()
- Triggers: Before first document processing, querying, or batch operation
- Responsibilities:
  - Check parser installation
  - Create LightRAG instance if not provided
  - Initialize storages (KV, vector, graph)
  - Initialize parse cache and modal processors

**Document Processing Entry:**
- Location: `raganything/processor.py` ProcessorMixin.process_document_complete()
- Triggers: User calls process_document_complete(file_path, ...)
- Responsibilities:
  - Generate cache key from file path + modification time
  - Check parse cache for existing results
  - Invoke parser to generate content_list
  - Separate text from multimodal content
  - Insert text into LightRAG
  - Route multimodal items to modal processors

**Query Entry:**
- Location: `raganything/query.py` QueryMixin.aquery()
- Triggers: User calls query(query_text, ...) or aquery()
- Responsibilities:
  - Check multimodal cache if applicable
  - Call LightRAG query for retrieval
  - Optionally enhance with modal processor analysis (vlm mode)
  - Return results to caller

**Batch Processing Entry:**
- Location: `raganything/batch.py` BatchMixin.process_folder_complete()
- Triggers: User calls process_folder_complete(folder_path)
- Responsibilities:
  - Discover files matching extensions
  - Create concurrent tasks up to max_workers
  - Aggregate results and error handling

## Error Handling

**Strategy:** Exception propagation with logging, structured error returns in async contexts

**Patterns:**

- **Parser Errors**: MineruExecutionError with return code and error message, caught and logged in ProcessorMixin
- **Installation Checks**: _ensure_lightrag_initialized() validates parser installation before use, returns {"success": False, "error": message}
- **Cache Errors**: Wrapped in try-catch, falls back to fresh parsing if cache access fails
- **Model Loading Errors**: Modal processors catch ImportError for optional dependencies (librosa, soundfile, faster-whisper), log with installation instructions
- **File Validation**: Utility functions validate file existence and format before processing, return False or raise FileNotFoundError

## Cross-Cutting Concerns

**Logging:**
- Uses LightRAG's logger instance (imported from lightrag.utils)
- Propagates through all layers for debugging
- Log levels: info (milestones), debug (cache hits, config updates), warning (missing files), error (parser failures)

**Validation:**
- `validate_image_file()` checks existence, format, file size before processing
- Parser checks file extensions match supported formats
- Config environment variables have type conversion and defaults
- Modal processors validate input dictionaries have required fields

**Authentication:**
- None - local processing only, no external API authentication required
- Model functions (llm_model_func, vision_model_func) provided by user at initialization
- User responsible for configuring LightRAG with proper model endpoints/credentials

---

*Architecture analysis: 2026-02-20*
