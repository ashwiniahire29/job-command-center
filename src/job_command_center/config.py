from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    db_path: Path
    data_cache_dir: Path
    master_resume_path: Path


def get_settings() -> Settings:
    return Settings(
        db_path=Path(os.getenv("JCC_DB_PATH", ROOT / "data" / "job_command_center.sqlite3")),
        data_cache_dir=Path(os.getenv("JCC_DATA_CACHE_DIR", ROOT / "data" / "source_cache")),
        master_resume_path=Path(os.getenv("JCC_MASTER_RESUME_PATH", ROOT / "data" / "master_resume.docx")),
    )
