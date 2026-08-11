from __future__ import annotations

import os
from functools import wraps
from typing import Any


class _DummyClient:
    """No-op client used when tracing is intentionally disabled."""

    def get_current_observation_id(self) -> None:
        return None

    def update_current_trace(self, **kwargs: Any) -> None:
        return None

    def update_current_generation(self, **kwargs: Any) -> None:
        return None


try:
    from langfuse import get_client, observe as _langfuse_observe

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False
    _langfuse_observe = None

    def get_client():
        return _DummyClient()


def observe(*args: Any, **kwargs: Any):
    """Use Langfuse only when credentials are present; otherwise call directly."""

    def decorator(func):
        if not LANGFUSE_SDK_AVAILABLE or _langfuse_observe is None:
            return func

        observed = _langfuse_observe(*args, **kwargs)(func)

        @wraps(func)
        def wrapper(*func_args: Any, **func_kwargs: Any):
            if not tracing_enabled():
                return func(*func_args, **func_kwargs)
            return observed(*func_args, **func_kwargs)

        return wrapper

    return decorator


def get_langfuse_client():
    if not tracing_enabled():
        return _DummyClient()
    return get_client()


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )
