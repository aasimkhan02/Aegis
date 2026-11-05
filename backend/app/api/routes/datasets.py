"""FastAPI routes for Dataset management and JSON import/export."""

from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_or_create_default_project
from app.db.session import get_db
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.project import Project
from app.models.test_case import TestCase
from app.schemas.dataset import (
    DatasetCreate,
    DatasetExportResponse,
    DatasetImportRequest,
    DatasetResponse,
    DatasetUpdate,
    ImportResultResponse,
)
from app.schemas.test_case import TestCaseCreate, TestCaseResponse

router = APIRouter()


def _build_dataset_response(dataset: Dataset, db: Session) -> DatasetResponse:
    """Helper to populate test_case_count and aggregated tags for a DatasetResponse."""
    case_count = db.scalar(
        select(func.count(TestCase.id)).where(TestCase.dataset_id == dataset.id)
    ) or 0

    # Retrieve all distinct tags
    cases = db.scalars(select(TestCase).where(TestCase.dataset_id == dataset.id)).all()
    all_tags: set[str] = set()
    for tc in cases:
        if isinstance(tc.tags, list):
            all_tags.update(str(t).strip() for t in tc.tags if str(t).strip())

    return DatasetResponse(
        id=dataset.id,
        project_id=dataset.project_id,
        name=dataset.name,
        description=dataset.description,
        metadata_=dataset.metadata_,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        test_case_count=case_count,
        tags=sorted(all_tags),
    )


@router.get("", response_model=list[DatasetResponse])
def list_datasets(
    project_id: uuid.UUID | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[DatasetResponse]:
    """List datasets with optional project and search query filters."""
    query = select(Dataset)
    if project_id:
        query = query.where(Dataset.project_id == project_id)
    if search:
        query = query.where(Dataset.name.ilike(f"%{search.strip()}%"))

    query = query.order_by(Dataset.created_at.desc()).offset(offset).limit(limit)
    datasets = db.scalars(query).all()

    return [_build_dataset_response(d, db) for d in datasets]


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """Create a new dataset."""
    project_id = payload.project_id
    if not project_id:
        project = get_or_create_default_project(db)
        project_id = project.id
    else:
        # Verify project exists
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {project_id} not found.",
            )

    dataset = Dataset(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        metadata=payload.metadata,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return _build_dataset_response(dataset, db)


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """View details of a single dataset."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id {dataset_id} not found.",
        )
    return _build_dataset_response(dataset, db)


@router.put("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(
    dataset_id: uuid.UUID,
    payload: DatasetUpdate,
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """Edit dataset metadata or name."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id {dataset_id} not found.",
        )

    if payload.name is not None:
        dataset.name = payload.name
    if payload.description is not None:
        dataset.description = payload.description
    if payload.metadata is not None:
        dataset.metadata_ = payload.metadata

    dataset.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dataset)

    return _build_dataset_response(dataset, db)


@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
def delete_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete a dataset safely.

    Protects evaluation history: Rejects deletion if referenced by any EvaluationRun.
    """
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id {dataset_id} not found.",
        )

    # Check for evaluation run references
    eval_count = db.scalar(
        select(func.count(EvaluationRun.id)).where(EvaluationRun.dataset_id == dataset_id)
    ) or 0

    if eval_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete dataset '{dataset.name}': It is referenced by {eval_count} "
                "historical evaluation run(s). Datasets tied to evaluation records cannot be deleted."
            ),
        )

    # Check if any test cases are tied to CaseResult
    case_ids = db.scalars(select(TestCase.id).where(TestCase.dataset_id == dataset_id)).all()
    if case_ids:
        cr_count = db.scalar(
            select(func.count(CaseResult.id)).where(CaseResult.test_case_id.in_(case_ids))
        ) or 0
        if cr_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot delete dataset '{dataset.name}': Its test cases are referenced by {cr_count} "
                    "historical case result(s). Delete or archive individual test cases instead."
                ),
            )

    db.delete(dataset)
    db.commit()

    return {"status": "deleted", "dataset_id": dataset_id, "message": f"Dataset '{dataset.name}' was deleted."}


@router.get("/{dataset_id}/tags", response_model=list[str])
def get_dataset_tags(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[str]:
    """List all unique tags present across test cases in a dataset."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id {dataset_id} not found.",
        )

    cases = db.scalars(select(TestCase).where(TestCase.dataset_id == dataset_id)).all()
    unique_tags: set[str] = set()
    for tc in cases:
        if isinstance(tc.tags, list):
            unique_tags.update(str(t).strip() for t in tc.tags if str(t).strip())

    return sorted(unique_tags)


@router.get("/{dataset_id}/export", response_model=DatasetExportResponse)
def export_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DatasetExportResponse:
    """Export complete dataset and all its test cases in standardized JSON format."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id {dataset_id} not found.",
        )

    ds_resp = _build_dataset_response(dataset, db)

    # Fetch test cases
    raw_cases = db.scalars(
        select(TestCase).where(TestCase.dataset_id == dataset_id).order_by(TestCase.created_at.asc())
    ).all()

    # Determine evaluation status for each test case
    case_ids = [c.id for c in raw_cases]
    evaluated_ids: set[uuid.UUID] = set()
    if case_ids:
        rows = db.execute(
            select(CaseResult.test_case_id).where(CaseResult.test_case_id.in_(case_ids)).distinct()
        ).all()
        evaluated_ids = {r[0] for r in rows}

    case_responses = [
        TestCaseResponse(
            id=tc.id,
            dataset_id=tc.dataset_id,
            name=tc.name,
            input_data=tc.input_data,
            expected_output=tc.expected_output,
            expected_behavior=tc.expected_behavior,
            retrieval_context=tc.retrieval_context,
            tags=tc.tags if isinstance(tc.tags, list) else [],
            metadata_=tc.metadata_,
            is_enabled=tc.is_enabled,
            created_at=tc.created_at,
            updated_at=tc.updated_at,
            has_evaluations=tc.id in evaluated_ids,
        )
        for tc in raw_cases
    ]

    return DatasetExportResponse(
        dataset=ds_resp,
        test_cases=case_responses,
        exported_at=datetime.now(timezone.utc),
    )


@router.post("/{dataset_id}/import", response_model=ImportResultResponse)
def import_test_cases(
    dataset_id: uuid.UUID,
    payload: DatasetImportRequest,
    db: Session = Depends(get_db),
) -> ImportResultResponse:
    """Import multiple test cases into an existing dataset with comprehensive validation."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id {dataset_id} not found.",
        )

    if not payload.test_cases:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Import payload contains no test cases.",
        )

    existing_names = set(
        db.scalars(select(TestCase.name).where(TestCase.dataset_id == dataset_id)).all()
    )

    imported_count = 0
    skipped_count = 0
    errors: list[dict[str, Any]] = []
    created_ids: list[uuid.UUID] = []

    for idx, item in enumerate(payload.test_cases):
        try:
            # Check duplicate name within dataset
            if item.name in existing_names and not payload.overwrite_existing:
                skipped_count += 1
                errors.append({
                    "index": idx,
                    "name": item.name,
                    "error": f"Test case with name '{item.name}' already exists in dataset.",
                })
                continue

            tc = TestCase(
                dataset_id=dataset_id,
                name=item.name,
                input_data=item.input_data if isinstance(item.input_data, dict) else {"prompt": item.input_data},
                expected_output=item.expected_output if isinstance(item.expected_output, (dict, list, type(None))) else {"output": item.expected_output},
                expected_behavior=item.expected_behavior,
                retrieval_context=item.retrieval_context or [],
                tags=item.tags or [],
                metadata=item.metadata or {},
                is_enabled=item.is_enabled,
            )
            db.add(tc)
            db.flush()
            created_ids.append(tc.id)
            existing_names.add(item.name)
            imported_count += 1

        except Exception as exc:
            errors.append({
                "index": idx,
                "name": getattr(item, "name", f"item_{idx}"),
                "error": str(exc),
            })

    db.commit()

    return ImportResultResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        imported_count=imported_count,
        skipped_count=skipped_count,
        errors=errors,
        created_test_case_ids=created_ids,
    )


@router.post("/import", response_model=ImportResultResponse, status_code=status.HTTP_201_CREATED)
def import_full_dataset(
    payload: DatasetImportRequest,
    db: Session = Depends(get_db),
) -> ImportResultResponse:
    """Create a new dataset and import all test cases in a single operation."""
    if not payload.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A dataset name is required when importing a full dataset.",
        )

    project = get_or_create_default_project(db)

    # Check if a dataset with this name already exists in this project
    existing = db.scalar(
        select(Dataset).where(
            Dataset.project_id == project.id,
            Dataset.name == payload.name.strip(),
        )
    )

    if existing and not payload.overwrite_existing:
        target_dataset = existing
    else:
        target_dataset = Dataset(
            project_id=project.id,
            name=payload.name.strip(),
            description=payload.description or "Imported Golden Dataset",
            metadata=payload.metadata or {},
        )
        db.add(target_dataset)
        db.commit()
        db.refresh(target_dataset)

    # Import test cases into target_dataset
    return import_test_cases(target_dataset.id, payload, db)

