"""Retry with exponential backoff utilities for transient failures."""

import time
from typing import Callable, Optional, Tuple, Type, TypeVar

import pytesseract  # type: ignore[import-untyped]

from src.utils.logger import logger

T = TypeVar("T")

# Default exceptions to retry on (transient/recoverable errors).
_DEFAULT_RETRY_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    pytesseract.TesseractError,
    OSError,
)


def retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = 3,
    backoff_ms: int = 200,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
) -> T:
    """
    Retry a function with exponential backoff on specific exceptions.

    Retries with exponential backoff (2^attempt * backoff_ms). Only retries on specified
    exceptions; other exceptions propagate immediately without retry.

    Default retryable exceptions:
    - pytesseract.TesseractError: Transient OCR processing failures.
    - OSError: Transient I/O errors.

    Args:
        func: Callable that performs the operation (takes no arguments).
        max_attempts: Maximum number of attempts (default: 3).
        backoff_ms: Initial backoff in milliseconds (default: 200).
        retry_on: Optional tuple of exception classes to retry on.
                  If provided, overrides the default exceptions.
                  Non-matching exceptions propagate immediately.

    Returns:
        Result of the function call on successful attempt.

    Raises:
        Last exception encountered if all retryable attempts fail.
        Other exceptions propagate immediately without retry.

    Example:
        result = retry_with_backoff(lambda: my_function(), max_attempts=3)
    """
    exceptions_to_retry = (
        retry_on if retry_on is not None else _DEFAULT_RETRY_EXCEPTIONS
    )
    last_exception: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except exceptions_to_retry as e:
            last_exception = e
            if attempt < max_attempts:
                # Exponential backoff: backoff_ms * (2 ^ (attempt - 1))
                wait_time = (backoff_ms / 1000.0) * (2 ** (attempt - 1))
                logger.debug(
                    "Attempt %d/%d failed, retrying in %.2fs: %s",
                    attempt,
                    max_attempts,
                    wait_time,
                    e,
                )
                time.sleep(wait_time)
            else:
                logger.warning(
                    "Operation failed after %d attempts: %s", max_attempts, e
                )

    # All attempts exhausted, raise the last exception
    if last_exception is not None:
        raise last_exception
    # This should never be reached
    raise RuntimeError("Unexpected error in retry_with_backoff")
