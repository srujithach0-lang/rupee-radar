import io
import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AnalysisResult, Transaction, UploadSession
from app.models.enums import SessionStatus
from app.parsers.registry import parse_statement
from app.pipeline.categorizer import categorize_transactions
from app.pipeline.cleaner import clean_transactions
from app.pipeline.insight_types import InsightItem, serialize_insights
from app.pipeline.insights import generate_insights
from app.pipeline.metrics import compute_metrics
from app.pipeline.recurring import detect_recurring
from app.services.analysis import _metrics_to_json, persist_recurring_groups


class PipelineError(Exception):
    pass


def _set_status(db: Session, session: UploadSession, status: SessionStatus, error: str | None = None) -> None:
    session.status = status.value
    if error:
        session.error_message = error
    db.commit()


def run_pipeline(db: Session, session: UploadSession, file_content: bytes, filename: str) -> UploadSession:
    settings = get_settings()
    all_warnings: list[str] = []

    _set_status(db, session, SessionStatus.PARSING)

    if len(file_content) > settings.max_upload_size_bytes:
        _set_status(db, session, SessionStatus.FAILED, "File exceeds maximum upload size")
        return session

    if not file_content:
        _set_status(db, session, SessionStatus.FAILED, "No transactions found")
        return session

    file_obj = io.BytesIO(file_content)
    parse_result, parser = parse_statement(file_obj, filename, file_content)
    all_warnings.extend(parse_result.warnings)

    if not parser:
        _set_status(db, session, SessionStatus.FAILED, all_warnings[0] if all_warnings else "Unsupported format")
        session.parse_warnings = json.dumps(all_warnings)
        db.commit()
        return session

    if not parse_result.transactions:
        _set_status(db, session, SessionStatus.FAILED, "No transactions found")
        session.parse_warnings = json.dumps(all_warnings)
        db.commit()
        return session

    _set_status(db, session, SessionStatus.PROCESSING)

    cleaned, clean_warnings = clean_transactions(parse_result.transactions)
    all_warnings.extend(clean_warnings)

    txn_ids = [str(uuid.uuid4()) for _ in cleaned]
    categorized = categorize_transactions(cleaned, txn_ids)

    db_transactions: list[tuple[str, object, object, float]] = []
    for txn_id, (txn, category, confidence) in zip(txn_ids, categorized):
        db_txn = Transaction(
            id=txn_id,
            session_id=session.id,
            date=datetime.strptime(txn.date, "%Y-%m-%d").date(),
            description_raw=txn.description_raw,
            description_clean=txn.description_clean,
            amount=txn.amount,
            type=txn.type.value,
            balance=txn.balance,
            category=category.value,
            category_confidence=confidence,
            payment_mode=txn.payment_mode,
            merchant=txn.merchant,
            is_duplicate=txn.is_duplicate,
        )
        db.add(db_txn)
        db.flush()
        db_transactions.append((db_txn.id, txn, category, confidence))

    recurring_results = detect_recurring(db_transactions)
    persist_recurring_groups(db, session.id, recurring_results)

    metrics = compute_metrics(db_transactions, recurring_results)
    insights = generate_insights(metrics, recurring_results)

    metrics_json = _metrics_to_json(metrics)

    existing = db.query(AnalysisResult).filter(AnalysisResult.session_id == session.id).first()
    if existing:
        db.delete(existing)

    db.add(
        AnalysisResult(
            session_id=session.id,
            metrics=json.dumps(metrics_json),
            insights=serialize_insights(insights),
        )
    )

    session.status = SessionStatus.READY.value
    session.row_count = len(db_transactions)
    session.parse_warnings = json.dumps(all_warnings)
    session.expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    session.error_message = None
    db.commit()
    db.refresh(session)
    return session


def save_upload_temp(content: bytes, filename: str) -> str:
    suffix = os.path.splitext(filename)[1]
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="rupee_radar_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
    except Exception:
        os.unlink(path)
        raise
    return path


def delete_upload_temp(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass
