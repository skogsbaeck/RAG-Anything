# Coding Conventions

**Analysis Date:** 2026-02-20

## Naming Patterns

**Files:**
- `snake_case.py` for module names: `audio.py`, `processor.py`, `batch_parser.py`, `modalprocessors.py`
- `PascalCase` for class names within files: `AudioProcessor`, `ProcessorMixin`, `BatchParser`
- Private/internal methods prefixed with `_`: `_load_model()`, `_get_file_reference()`, `_generate_cache_key()`

**Functions:**
- `snake_case` for all functions: `separate_content()`, `encode_image_to_base64()`, `validate_image_file()`
- Async functions use standard `snake_case`: `async def process_folder_complete()`, `async def process_batch_async()`
- Functions are typically under 30 lines, often 10-20 lines

**Variables:**
- `snake_case` for all variables and parameters: `content_list`, `audio_path`, `max_concurrent_files`, `whisper_model`
- Type-hinted parameters always included: `file_path: str`, `config: Optional[AudioConfig]`, `content_list: List[Dict[str, Any]]`

**Types:**
- `PascalCase` for dataclass names: `AudioConfig`, `AudioMetadata`, `AudioTranscription`, `RAGAnythingConfig`, `ContextConfig`
- `PascalCase` for exception classes: `MineruExecutionError`
- `PascalCase` for enum values: `DocStatus.READY`, `DocStatus.PROCESSING`, `DocStatus.FAILED`
- Type hints use `typing` module: `Dict`, `List`, `Tuple`, `Optional`, `Union`, `Any`, `Callable`
- Modern union syntax used: `str | list[str]` (Python 3.10+)

## Code Style

**Formatting:**
- Handled by `ruff` format tool
- Line length: Not explicitly constrained (default ruff settings)
- Indentation: 4 spaces (Python standard)

**Linting:**
- Tool: `ruff` with configuration in `pyproject.toml`
- Target version: Python 3.10
- Configuration: `[tool.ruff]` section in `pyproject.toml`
- Pre-commit hooks: Enabled via `.pre-commit-config.yaml`
  - `ruff-format`: Auto-format code
  - `ruff`: Lint with fix (`--fix` and `--ignore=E402` flags)
  - Also includes: `trailing-whitespace`, `end-of-file-fixer`, `requirements-txt-fixer`, `check-manifest`

**Code Quality Tools:**
- Available in dev dependencies but not enforced in CI: `black`, `isort`, `flake8`, `mypy`
- `ruff` is the primary tool enforced through pre-commit hooks

## Import Organization

**Order:**
1. Standard library imports: `import os`, `import time`, `import hashlib`, `import json`, `import logging`, `from pathlib import Path`
2. Type imports: `from typing import Dict, List, Any, Tuple, Optional, Union, TYPE_CHECKING`
3. Third-party imports: `from dataclasses import dataclass`, `from lightrag import LightRAG`, `from lightrag.utils import logger`, `from dotenv import load_dotenv`
4. Local package imports: `from raganything.base import DocStatus`, `from raganything.parser import MineruParser`, `from raganything.utils import separate_content`
5. Conditional imports in TYPE_CHECKING blocks: Used in `batch.py` for forward references to avoid circular imports

**Path Aliases:**
- Not explicitly configured (uses standard relative imports from package root)
- Imports use `from raganything.module import item` pattern throughout

**Example from `processor.py`:**
```python
import os
import time
import hashlib
import json
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

from raganything.base import DocStatus
from raganything.parser import MineruParser, DoclingParser, MineruExecutionError
from raganything.utils import (
    separate_content,
    insert_text_content,
    insert_text_content_with_multimodal_content,
    get_processor_for_type,
)
import asyncio
from lightrag.utils import compute_mdhash_id
```

## Error Handling

**Patterns:**
- Try-except blocks catch specific exceptions before generic ones: `except ImportError:` for missing dependencies, `except FileNotFoundError:` for file issues, `except Exception as e:` for generic fallback
- Always log errors before re-raising or handling: `logger.error(f"Failed to encode image {image_path}: {e}")`
- Custom exceptions defined for domain-specific errors: `MineruExecutionError(return_code, error_msg)` in `parser.py`
- Guard clauses used in initialization: Check for `None` and return early
- Example from `audio.py`:
```python
try:
    from faster_whisper import WhisperModel
except ImportError:
    logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
    raise
```

## Logging

**Framework:** `logging` module (stdlib)

**Patterns:**
- Logger obtained via `logging.getLogger(__name__)` at module level: `logger = logging.getLogger(__name__)`
- Also used: Import from lightrag: `from lightrag.utils import logger`
- Log levels used: `logger.info()`, `logger.debug()`, `logger.warning()`, `logger.error()`
- Always include context: `logger.info(f"Transcribing: {audio_path.name} (language: {lang})")`
- Time tracking: `logger.info(f"Model loaded in {time.time() - start_time:.2f}s")`
- Counts and statistics: `logger.info(f"Content separation complete: Text content length: {len(text_content)} characters")`

## Comments

**When to Comment:**
- Docstrings used on all public classes and functions
- Comments kept minimal—code should be self-documenting
- `# type: ignore` used selectively (e.g., in `parser.py` for MinerU typing issues)
- Configuration comments use `# ---` dividers in dataclasses for section headers

**JSDoc/TSDoc:**
- Not applicable (Python uses docstrings, not JSDoc)
- Python docstrings follow NumPy/Google style with "Args:" and "Returns:" sections

**Docstring Example from `utils.py`:**
```python
def separate_content(
    content_list: List[Dict[str, Any]],
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Separate text content and multimodal content

    Args:
        content_list: Content list from MinerU parsing

    Returns:
        (text_content, multimodal_items): Pure text content and multimodal items list
    """
```

## Function Design

**Size:** Typically 10-30 lines, rarely exceeding 50 lines
- Example: `encode_image_to_base64()` is 12 lines
- Example: `separate_content()` is 30 lines with logging
- Larger functions (50+ lines): `_generate_cache_key()` (48 lines), `_generate_content_based_doc_id()` (60+ lines)

**Parameters:**
- Always type-hinted: `def transcribe(self, audio_path: Path, language: Optional[str] = None) -> AudioTranscription:`
- Default values for optional parameters: `config: Optional[AudioConfig] = None`
- Union types for flexible inputs: `split_by_character: str | None = None`
- Dataclass instances preferred over individual kwargs for configuration: `config: AudioConfig` instead of separate `model`, `device` params
- `**kwargs` used sparingly for additional parser parameters: `def _generate_cache_key(self, file_path: Path, parse_method: str = None, **kwargs)`

**Return Values:**
- Always type-hinted: All public functions include return type annotation
- Single return statements preferred (or early returns for errors)
- Dataclass instances returned for structured data: `-> AudioTranscription`, `-> AudioMetadata`
- Tuples for multiple related returns: `-> Tuple[str, List[Dict[str, Any]]]`

## Module Design

**Exports:**
- Explicit `__all__` in `__init__.py`: Lists public API (`RAGAnything`, `RAGAnythingConfig`, `AudioProcessor`, `AudioConfig`, `AudioTranscription`, `AudioMetadata`)
- Mixin classes use `as Mixin` in class definitions: `class RAGAnything(QueryMixin, ProcessorMixin, BatchMixin)`
- Public vs private distinction enforced through naming: `_private_method()` vs `public_method()`

**Barrel Files:**
- `__init__.py` re-exports main classes for convenient imports
- Example:
```python
from .raganything import RAGAnything as RAGAnything
from .config import RAGAnythingConfig as RAGAnythingConfig
from .audio import (
    AudioProcessor as AudioProcessor,
    AudioConfig as AudioConfig,
    AudioTranscription as AudioTranscription,
    AudioMetadata as AudioMetadata,
)
```

**Mixin Pattern:**
- Classes organized as mixins for composition: `ProcessorMixin`, `QueryMixin`, `BatchMixin` in `raganything.py`
- Each mixin handles one domain: document processing, querying, batch operations
- Type hints for mixin attributes/methods that will be available from other mixins:
```python
class BatchMixin:
    config: "RAGAnythingConfig"
    logger: logging.Logger

    async def _ensure_lightrag_initialized(self) -> None: ...
    async def process_document_complete(self, file_path: str, **kwargs) -> None: ...
```

## Dataclass Conventions

**Configuration Classes:**
- Use `@dataclass` decorator for configuration: `@dataclass class AudioConfig:`, `@dataclass class RAGAnythingConfig:`
- Use `field(default=...)` for environment variable defaults: `field(default=get_env_value("AUDIO_LANGUAGE", "auto", str))`
- Use `field(default_factory=...)` for mutable defaults: `field(default_factory=list)`
- Docstrings added for each field as comments
- Optional `__post_init__()` for computed defaults: `def __post_init__(self): if not self.word_count: self.word_count = len(self.text.split())`

**Result Classes:**
- Simple dataclasses for structured returns: `AudioTranscription`, `AudioMetadata`
- No methods except `__post_init__()` for initialization logic

## Python Version

**Target:** Python 3.10+
- Modern syntax used: `str | None` union syntax instead of `Optional[str]`
- `from __future__ import annotations` used in some modules for forward references
- `TypeVar` used for generic type handling: `T = TypeVar("T")` in `parser.py`

## Configuration Management

**Environment Variables:**
- Centralized in `config.py` using `RAGAnythingConfig` dataclass
- Integration with `lightrag.utils.get_env_value()` for type-safe env access
- `.env` file loaded via `python-dotenv` in examples: `load_dotenv(dotenv_path=".env", override=False)`
- Configuration cascades: defaults → env vars → runtime parameters

---

*Convention analysis: 2026-02-20*
