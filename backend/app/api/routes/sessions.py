import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AnalysisResult, RecurringGroup, Transaction, UploadSession
from app.pipeline.insight_types import deserialize_insights
from app.schemas.analytics import AnalyticsResponse, InsightItemResponse, InsightsResponse
from app.schemas.recurring import RecurringGroupResponse, RecurringListResponse
from app.schemas.session import SessionResponse
from app.schemas.transaction import (
    TransactionCategoryUpdate,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdateResponse,
)
from app.services.analysis import recompute_analysis
from app.services.report import render_report_html, render_report_pdf
from app.services.session_lifecycle import delete_session, get_active_session_or_404

router = APIRouter(tags=["sessions"])


def _require_ready(session: UploadSession) -> None:
    if session.status != "ready":
        raise HTTPException(status_code=409, detail="Session is still processing")


def _session_response(session: UploadSession) -> SessionResponse:
    warnings = json.loads(session.parse_warnings) if session.parse_warnings else []
    return SessionResponse(
        id=session.id,
        filename=session.filename,
        file_type=session.file_type,
        status=session.status,
        uploaded_at=session.uploaded_at,
        expires_at=session.expires_at,
        row_count=session.row_count,
        error_message=session.error_message,
        parse_warnings=warnings,
    )


def _transaction_response(t: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=t.id,
        date=t.date.isoformat(),
        description_raw=t.description_raw,
        description_clean=t.description_clean,
        amount=float(t.amount),
        type=t.type,
        balance=float(t.balance) if t.balance is not None else None,
        category=t.category,
        category_confidence=t.category_confidence,
        category_overridden=t.category_overridden,
        is_recurring=t.is_recurring,
        payment_mode=t.payment_mode,
        merchant=t.merchant,
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)) -> SessionResponse:
    return _session_response(get_active_session_or_404(db, session_id))


@router.delete("/sessions/{session_id}", status_code=204)
def remove_session(session_id: str, db: Session = Depends(get_db)) -> Response:
    session = get_active_session_or_404(db, session_id)
    delete_session(db, session)
    return Response(status_code=204)


@router.get("/sessions/{session_id}/transactions", response_model=TransactionListResponse)
def list_transactions(
    session_id: str,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = Query("date", pattern="^(date|amount|category)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
) -> TransactionListResponse:
    get_active_session_or_404(db, session_id)
    query = db.query(Transaction).filter(Transaction.session_id == session_id)

    sort_column = {
        "date": Transaction.date,
        "amount": Transaction.amount,
        "category": Transaction.category,
    }[sort_by]
    query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return TransactionListResponse(
        items=[_transaction_response(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/sessions/{session_id}/transactions/{txn_id}", response_model=TransactionUpdateResponse)
def update_transaction_category(
    session_id: str,
    txn_id: str,
    body: TransactionCategoryUpdate,
    db: Session = Depends(get_db),
) -> TransactionUpdateResponse:
    session = get_active_session_or_404(db, session_id)
    _require_ready(session)

    txn = (
        db.query(Transaction)
        .filter(Transaction.id == txn_id, Transaction.session_id == session_id)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.category = body.category.value
    txn.category_confidence = 1.0
    txn.category_overridden = True
    db.commit()
    db.refresh(txn)

    recompute_analysis(db, session)

    return TransactionUpdateResponse(transaction=_transaction_response(txn))


@router.get("/sessions/{session_id}/analytics", response_model=AnalyticsResponse)
def get_analytics(session_id: str, db: Session = Depends(get_db)) -> AnalyticsResponse:
    session = get_active_session_or_404(db, session_id)
    _require_ready(session)

    result = db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")

    data = json.loads(result.metrics)
    return AnalyticsResponse(**data)


@router.get("/sessions/{session_id}/insights", response_model=InsightsResponse)
def get_insights(session_id: str, db: Session = Depends(get_db)) -> InsightsResponse:
    session = get_active_session_or_404(db, session_id)
    _require_ready(session)

    result = db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")

    items = deserialize_insights(result.insights)
    return InsightsResponse(
        insights=[InsightItemResponse(text=i.text, source=i.source) for i in items]
    )


@router.get("/sessions/{session_id}/recurring", response_model=RecurringListResponse)
def get_recurring(session_id: str, db: Session = Depends(get_db)) -> RecurringListResponse:
    session = get_active_session_or_404(db, session_id)
    _require_ready(session)

    groups = db.query(RecurringGroup).filter(RecurringGroup.session_id == session_id).all()
    recurring_total = sum(
        float(g.typical_amount) for g in groups if g.frequency == "monthly"
    )

    return RecurringListResponse(
        groups=[
            RecurringGroupResponse(
                id=g.id,
                label=g.label,
                category=g.category,
                frequency=g.frequency,
                typical_amount=float(g.typical_amount),
                last_seen_date=g.last_seen_date.isoformat(),
                transaction_ids=json.loads(g.transaction_ids),
                confidence=g.confidence,
            )
            for g in groups
        ],
        recurring_total_monthly=round(recurring_total, 2),
    )


@router.get("/sessions/{session_id}/report")
def get_report(
    session_id: str,
    db: Session = Depends(get_db),
    format: str = Query("html", pattern="^(html|pdf)$"),
) -> Response:
    session = get_active_session_or_404(db, session_id)
    _require_ready(session)

    try:
        html = render_report_html(db, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if format == "pdf":
        try:
            pdf_bytes = render_report_pdf(html)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="PDF generation unavailable") from exc
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="rupeeradar-report-{session_id[:8]}.pdf"'},
        )

    return Response(content=html, media_type="text/html")
