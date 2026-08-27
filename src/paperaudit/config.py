from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


@dataclass(frozen=True)
class Settings:
    api_base: str
    api_key: str
    model: str
    reasoning_effort: str = "no_think"
    temperature: float = 0.2
    top_p: float = 1.0
    timeout_seconds: int = 120
    retrieval_top_k: int = 5
    max_paper_chars: int = 120_000
    judge_batch_size: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            api_base=os.getenv("HY3_API_BASE", "").strip(),
            api_key=os.getenv("HY3_API_KEY", "").strip(),
            model=os.getenv("HY3_MODEL", "").strip(),
            reasoning_effort=os.getenv("HY3_REASONING_EFFORT", "no_think").strip(),
            temperature=_float_env("HY3_TEMPERATURE", 0.2),
            top_p=_float_env("HY3_TOP_P", 1.0),
            timeout_seconds=_int_env("HY3_TIMEOUT_SECONDS", 120),
            retrieval_top_k=_int_env("PAPERAUDIT_TOP_K", 5),
            max_paper_chars=_int_env("PAPERAUDIT_MAX_PAPER_CHARS", 120_000),
            judge_batch_size=_int_env("PAPERAUDIT_JUDGE_BATCH_SIZE", 6),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

