"""Canonical Parquet/metadata loading with file signatures and provenance.

Loads only the three launch-required files. The raw CSV is never read here and
raw data is never re-cleaned on startup.
"""
import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..analysis import load_processed
from ..config import ROOT, START_DATE
from . import settings
from .validation import (DataError, recovery_for, validate_dictionary, validate_frame,
                         validate_quality)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Bundle:
    frame: pd.DataFrame = field(repr=False)
    quality: dict = field(repr=False)
    dictionary: pd.DataFrame = field(repr=False)
    meta: dict


def file_signature(path):
    """(relative path, bytes, mtime_ns) used as the cache key. Raises DataError if absent."""
    path = Path(path)
    rel = settings.relative(path)
    if not path.is_file():
        raise DataError('Required data file missing', f'`{rel}` was not found.', recovery_for(rel))
    stat = path.stat()
    return rel, stat.st_size, stat.st_mtime_ns


def launch_signature(paths=settings.LAUNCH_FILES):
    return tuple(file_signature(p) for p in paths)


def sha256_file(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def code_revision():
    """Git commit of the working tree, or 'unavailable' (never raises)."""
    try:
        out = subprocess.run(['git', 'rev-parse', '--short=12', 'HEAD'], cwd=ROOT, capture_output=True,
                             text=True, timeout=5, check=True).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain', '--', 'src', 'app.py'], cwd=ROOT,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return out + ('+uncommitted changes' if dirty else '')
    except Exception:  # noqa: BLE001 - provenance is optional, never blocking
        return 'unavailable'


def load_bundle(processed=settings.PROCESSED, quality_path=settings.QUALITY_PATH,
                dictionary_path=settings.DICTIONARY_PATH):
    """Load and validate the canonical frame and metadata, or raise a named DataError."""
    signatures = launch_signature((processed, quality_path, dictionary_path))
    q_rel, d_rel, p_rel = settings.relative(Path(quality_path)), settings.relative(Path(dictionary_path)), \
        settings.relative(Path(processed))
    try:
        quality = json.loads(Path(quality_path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        log.exception('quality load failed')
        raise DataError('Data-quality metadata error', f'`{q_rel}` could not be read as JSON.',
                        recovery_for(q_rel)) from exc
    validate_quality(quality, q_rel)
    try:
        dictionary = pd.read_csv(dictionary_path, dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001
        log.exception('dictionary load failed')
        raise DataError('Data dictionary error', f'`{d_rel}` could not be read as CSV.',
                        recovery_for(d_rel)) from exc
    validate_dictionary(dictionary, d_rel)
    try:
        frame = load_processed(processed)
    except Exception as exc:  # noqa: BLE001
        log.exception('parquet load failed')
        raise DataError('Processed data error', f'`{p_rel}` could not be loaded as the canonical Parquet '
                        'or lacks required columns.', recovery_for(p_rel)) from exc
    checks = validate_frame(frame, dictionary, quality, p_rel)
    dates = frame['offense_date']
    data_max = dates.max()
    meta = dict(
        app_version=settings.APP_VERSION,
        code_revision=code_revision(),
        processed_file=p_rel,
        processed_bytes=signatures[0][1],
        processed_modified_utc=datetime.fromtimestamp(signatures[0][2] / 1e9, timezone.utc).isoformat(
            timespec='seconds'),
        processed_sha256=sha256_file(processed),
        quality_file=q_rel,
        dictionary_file=d_rel,
        source_filename=quality['source']['filename'],
        source_sha256=quality['source']['sha256'],
        rows=len(frame),
        columns=len(frame.columns),
        full_min_date=None if pd.isna(dates.min()) else dates.min().date().isoformat(),
        full_max_date=None if pd.isna(data_max) else data_max.date().isoformat(),
        analysis_start=START_DATE,
        data_through=None if pd.isna(data_max) else data_max.date().isoformat(),
        invariant_checks=checks,
        loaded_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
        signature=signatures,
    )
    return Bundle(frame=frame, quality=quality, dictionary=dictionary, meta=meta)
