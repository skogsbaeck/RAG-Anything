# Testing Patterns

**Analysis Date:** 2026-02-20

## Test Framework

**Runner:**
- `pytest` >= 6.0
- Config: Not found (using pytest defaults)

**Assertion Library:**
- `pytest` built-in assertions

**Async Testing:**
- `pytest-asyncio` available for async test support

**Run Commands:**
```bash
pytest tests/                          # Run all tests
pytest tests/ -v                       # Verbose output
pytest tests/ -k test_name             # Run specific test
pytest tests/ --cov=raganything        # Coverage report
```

## Current State: No Formal Test Suite

**Critical Finding:** This codebase has NO formal test suite. All testing is done through examples and manual scripts in `/Users/alex/Projects/RAG-Anything/examples/`.

**Test-like Files (Examples, not Tests):**
- `examples/office_document_test.py` - Example/validation script
- `examples/image_format_test.py` - Example/validation script
- `examples/text_format_test.py` - Example/validation script
- `examples/raganything_example.py` - Documented example with async patterns
- Other examples: `batch_processing_example.py`, `lmstudio_integration_example.py`, `enhanced_markdown_example.py`, `modalprocessors_example.py`

**No test directories found:**
- No `tests/` directory
- No `test_*.py` files in package
- No `conftest.py` for pytest configuration

## Test Structure (Inferred from Examples)

The codebase demonstrates testing through executable examples. Key patterns observed:

**Example Pattern from `raganything_example.py`:**
```python
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

async def process_with_rag(
    file_path: str,
    output_dir: str,
    api_key: str,
    base_url: str = None,
    working_dir: str = None,
    parser: str = None,
):
    """Process document with RAGAnything"""
    # Implementation
    pass

async def main():
    # Setup
    # Execute
    # Verify
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

**Logging for Validation:**
- Examples use logging to show execution flow
- Logging configured via `logging.config.dictConfig()` with rotating file handlers
- Log output provides validation of execution: file sizes, counts, durations
- No assertions—relies on human inspection of logs and output

## Mocking

**Not Implemented:**
- No mocking library configuration found (`unittest.mock` not imported)
- No test fixtures or factories
- Examples use real dependencies (actual LLM API calls, real file processing)

## Test Coverage

**Status:** Not measured
- Requirements: No coverage targets configured
- No coverage configuration found in `pyproject.toml` or elsewhere
- Test framework (`pytest`) available but not enforced

## Architecture and Dependencies

**What's Actually Tested:**
The codebase relies on validation through examples that exercise actual features:

1. **Document Processing:** Examples show file parsing with real documents
2. **Async Operations:** Examples execute async functions with `asyncio.run()`
3. **Configuration:** Examples demonstrate config loading and environment variables
4. **Integration:** Examples use real LightRAG integration with OpenAI APIs

**Key Dependencies for Testing:**
- `pytest>=6.0` - Test runner (not actively used)
- `pytest-asyncio` - Async test support (not actively used)
- `openai` - For testing LLM integration
- `python-dotenv` - For environment configuration in tests
- `lightrag` - Core dependency that's integration-tested via examples

## Development Workflow for Testing

**Current Practice:**
1. Write or modify code
2. Run example scripts manually: `python examples/raganything_example.py`
3. Inspect logs and output files in `/output/` directory
4. Validate content visually or through print statements

**Logging Configuration (from `raganything_example.py`):**
```python
def configure_logging():
    """Configure logging for the application"""
    log_dir = os.getenv("LOG_DIR", os.getcwd())
    log_file_path = os.path.abspath(os.path.join(log_dir, "raganything_example.log"))

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "%(levelname)s: %(message)s"},
                "detailed": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler"},
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": log_file_path,
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                },
            },
        }
    )
```

## Test Data and Fixtures

**Not Formalized:**
- Examples reference sample documents in examples directory
- No dedicated test data directory
- Configuration provided through environment variables (`.env` file)

## Known Testing Gaps

**Critical Areas Without Tests:**
1. **Parser Module** (`parser.py` - 1927 lines) - No unit tests for MinerU/Docling integration
2. **Processor Module** (`processor.py` - 1876 lines) - No tests for document processing pipeline
3. **Modal Processors** (`modalprocessors.py` - 1569 lines) - No tests for image/table/equation analysis
4. **Batch Processing** (`batch.py`, `batch_parser.py`) - No tests for concurrent processing
5. **Audio Module** (`audio.py`) - No tests for transcription pipeline
6. **Query Module** (`query.py`) - No tests for query caching and multimodal queries
7. **Configuration** (`config.py`) - No tests for config initialization and env var loading
8. **Error Handling** - No systematic error case testing

**High-Priority Testing Needs:**
- Error paths: File not found, invalid audio format, API failures
- Edge cases: Empty documents, malformed input, timeout handling
- Integration: Multi-document batch processing, concurrent operations
- Configuration: Environment variable precedence, missing required values
- Async operations: Concurrent task handling, cancellation, cleanup

## Recommendations for Test Implementation

**Phase 1: Unit Tests (High Priority)**
- Test utility functions in `utils.py` (10-20 tests)
- Test dataclass initialization in `config.py`, `audio.py` (5-10 tests)
- Test error handling in parsers and processors (10-15 tests)

**Phase 2: Integration Tests (Medium Priority)**
- Test document processing pipeline with sample files
- Test batch processing with multiple file formats
- Test audio transcription with sample audio files
- Test LightRAG integration with mock LLM responses

**Phase 3: End-to-End Tests (Lower Priority)**
- Full workflow examples with real API calls
- Multiple document formats in batch
- Error recovery and retry logic

**Test Structure Template:**
```python
import pytest
from pathlib import Path
from raganything import RAGAnything, RAGAnythingConfig
from raganything.audio import AudioProcessor, AudioConfig
from raganything.utils import separate_content

class TestAudioProcessor:
    """Test audio transcription functionality"""

    @pytest.fixture
    def config(self):
        return AudioConfig(whisper_model="base", device="cpu")

    @pytest.fixture
    def processor(self, config):
        return AudioProcessor(config)

    def test_extract_metadata_valid_file(self, processor, tmp_path):
        # Arrange: Create or use sample audio file
        # Act: Extract metadata
        # Assert: Verify metadata structure
        pass

    def test_transcribe_missing_file(self, processor):
        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            processor.transcribe(Path("/nonexistent/file.mp3"))

    @pytest.mark.asyncio
    async def test_batch_processing(self, processor, tmp_path):
        # Test concurrent transcription
        pass


class TestUtilityFunctions:
    """Test utility helper functions"""

    def test_separate_content_text_only(self):
        content = [{"type": "text", "text": "Hello"}]
        text, multimodal = separate_content(content)
        assert text == "Hello"
        assert len(multimodal) == 0

    def test_separate_content_mixed(self):
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "image", "path": "image.png"},
        ]
        text, multimodal = separate_content(content)
        assert text == "Hello"
        assert len(multimodal) == 1
        assert multimodal[0]["type"] == "image"
```

---

*Testing analysis: 2026-02-20*
