"""FastAPI routes for TestCase CRUD, tagging, and safe archival."""

from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.test_case import TestCase
from app.schemas.test_case import TestCaseCreate, TestCaseResponse, TestCaseUpdate

router = APIRouter()


def _to_response(tc: TestCase, db: Session) -> TestCaseResponse:
    has_evals = (
        db.scalar(
            select(func.count(CaseResult.id)).where(CaseResult.test_case_id == tc.id)
        )
        or 0
    ) > 0

    return TestCaseResponse(
        id=tc.id,
        dataset_id=tc.dataset_id,
        name=tc.name,
        input_data=tc.input_data,
        expected_output=tc.expected_output,
        expected_behavior=tc.expected_behavior,
        retrieval_context=tc.retrieval_context or [],
        ground_truth_context=getattr(tc, "ground_truth_context", None) or [],
        tags=tc.tags if isinstance(tc.tags, list) else [],
        metadata_=tc.metadata_,
        is_enabled=tc.is_enabled,
        created_at=tc.created_at,
        updated_at=tc.updated_at,
        has_evaluations=has_evals,
    )


@router.get("/datasets/{dataset_id}/test-cases", response_model=list[TestCaseResponse])
def list_test_cases(
    dataset_id: uuid.UUID,
    tag: str | None = None,
    is_enabled: bool | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[TestCaseResponse]:
    """List test cases within a dataset, with optional filtering by tag, enabled status, and search."""
    # Verify dataset exists
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id {dataset_id} not found.",
        )

    query = select(TestCase).where(TestCase.dataset_id == dataset_id)

    if is_enabled is not None:
        query = query.where(TestCase.is_enabled == is_enabled)

    if search:
        search_filter = f"%{search.strip()}%"
        query = query.where(
            TestCase.name.ilike(search_filter)
            | TestCase.expected_behavior.ilike(search_filter)
        )

    # Order by creation
    query = query.order_by(TestCase.created_at.asc()).offset(offset).limit(limit)
    cases = db.scalars(query).all()

    # In-memory tag filter to support JSONB list tags reliably across dialects
    if tag:
        tag_lower = tag.lower().strip()
        cases = [
            c for c in cases
            if isinstance(c.tags, list) and any(str(t).lower() == tag_lower for t in c.tags)
        ]

    return [_to_response(c, db) for c in cases]


@router.post(
    "/datasets/{dataset_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_case(
    dataset_id: uuid.UUID,
    payload: TestCaseCreate,
    db: Session = Depends(get_db),
) -> TestCaseResponse:
    """Add a new test case to a dataset."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id {dataset_id} not found.",
        )

    tc = TestCase(
        dataset_id=dataset_id,
        name=payload.name,
        input_data=payload.input_data if isinstance(payload.input_data, dict) else {"prompt": payload.input_data},
        expected_output=payload.expected_output if isinstance(payload.expected_output, (dict, list, type(None))) else {"output": payload.expected_output},
        expected_behavior=payload.expected_behavior,
        retrieval_context=payload.retrieval_context or [],
        ground_truth_context=payload.ground_truth_context or [],
        tags=payload.tags,
        metadata=payload.metadata,
        is_enabled=payload.is_enabled,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)

    return _to_response(tc, db)


@router.get("/test-cases/{test_case_id}", response_model=TestCaseResponse)
def get_test_case(
    test_case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> TestCaseResponse:
    """View an individual test case."""
    tc = db.get(TestCase, test_case_id)
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TestCase with id {test_case_id} not found.",
        )
    return _to_response(tc, db)


@router.put("/test-cases/{test_case_id}", response_model=TestCaseResponse)
def update_test_case(
    test_case_id: uuid.UUID,
    payload: TestCaseUpdate,
    db: Session = Depends(get_db),
) -> TestCaseResponse:
    """Edit an existing test case."""
    tc = db.get(TestCase, test_case_id)
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TestCase with id {test_case_id} not found.",
        )

    if payload.name is not None:
        tc.name = payload.name
    if payload.input_data is not None:
        tc.input_data = payload.input_data if isinstance(payload.input_data, dict) else {"prompt": payload.input_data}
    if payload.expected_output is not None:
        tc.expected_output = payload.expected_output if isinstance(payload.expected_output, (dict, list, type(None))) else {"output": payload.expected_output}
    if payload.expected_behavior is not None:
        tc.expected_behavior = payload.expected_behavior
    if payload.retrieval_context is not None:
        tc.retrieval_context = payload.retrieval_context
    if payload.ground_truth_context is not None:
        tc.ground_truth_context = payload.ground_truth_context
    if payload.tags is not None:
        tc.tags = payload.tags
    if payload.metadata is not None:
        tc.metadata_ = payload.metadata
    if payload.is_enabled is not None:
        tc.is_enabled = payload.is_enabled

    tc.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tc)

    return _to_response(tc, db)


@router.patch("/test-cases/{test_case_id}/toggle", response_model=TestCaseResponse)
def toggle_test_case(
    test_case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> TestCaseResponse:
    """Toggle a test case between enabled and disabled status."""
    tc = db.get(TestCase, test_case_id)
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TestCase with id {test_case_id} not found.",
        )

    tc.is_enabled = not tc.is_enabled
    tc.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tc)

    return _to_response(tc, db)


@router.delete("/test-cases/{test_case_id}", status_code=status.HTTP_200_OK)
def delete_test_case(
    test_case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete or archive a test case safely.

    Preserves historical evaluation results:
    If this test case is referenced by any CaseResult, it is archived (disabled)
    instead of physically deleted.
    """
    tc = db.get(TestCase, test_case_id)
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TestCase with id {test_case_id} not found.",
        )

    # Check for historical CaseResults
    case_result_count = db.scalar(
        select(func.count(CaseResult.id)).where(CaseResult.test_case_id == test_case_id)
    ) or 0

    if case_result_count > 0:
        # Archive instead of physical delete
        tc.is_enabled = False
        meta = dict(tc.metadata_) if isinstance(tc.metadata_, dict) else {}
        meta["archived"] = True
        meta["archived_at"] = datetime.now(timezone.utc).isoformat()
        tc.metadata_ = meta
        tc.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "status": "archived",
            "action": "archived",
            "message": (
                f"Test case '{tc.name}' is referenced by {case_result_count} historical "
                "evaluation result(s) and was archived (disabled) instead of deleted "
                "to preserve historical integrity."
            ),
            "test_case_id": test_case_id,
        }

    # Not referenced by any evaluations: safe to delete physically
    db.delete(tc)
    db.commit()

    return {
        "status": "deleted",
        "action": "deleted",
        "message": f"Test case '{tc.name}' was permanently deleted.",
        "test_case_id": test_case_id,
    }

