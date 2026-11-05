"""Evaluation Orchestrator coordinating execution pipelines, persistence, and state transitions.

Architecture note on in-process background execution:
Background tasks run in-process using FastAPI's background executor and local asyncio tasks.
While lightweight and zero-dependency (no Celery, Redis, or RabbitMQ required), an abrupt
server shutdown, crash, or process restart will interrupt an active run. Re-running the evaluation
will initiate a clean new EvaluationRun.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.evaluation.context import TestCaseData
from app.evaluation.evaluators.registry import get_default_evaluators, resolve_evaluators
from app.evaluation.exceptions import (
    EvaluationConfigError,
    EvaluationExecutionError,
    IncompatibleProjectError,
)
from app.evaluation.executor import (
    execute_test_case,
    resolve_assistant_adapter,
)
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.metric_result import MetricResult
from app.models.project import Project
from app.models.test_case import TestCase

logger = logging.getLogger("aegis.evaluation")


def validate_evaluation_entities(
    db: Session,
    assistant_version_id: uuid.UUID,
    dataset_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> tuple[AssistantVersion, Dataset, Project, int]:
    """Validate that assistant version and dataset exist and belong to the same project.

    Args:
        db: Active SQLAlchemy database session.
        assistant_version_id: Target AssistantVersion UUID.
        dataset_id: Target Dataset UUID.
        project_id: Optional explicit Project UUID for cross-validation.

    Returns:
        tuple containing (AssistantVersion, Dataset, Project, enabled_test_cases_count).

    Raises:
        EvaluationConfigError: If entities are missing or dataset has zero enabled cases.
        IncompatibleProjectError: If project associations do not match.
    """
    assistant = db.scalar(
        select(AssistantVersion).where(AssistantVersion.id == assistant_version_id)
    )
    if not assistant:
        raise EvaluationConfigError(
            f"AssistantVersion with ID '{assistant_version_id}' does not exist."
        )

    dataset = db.scalar(
        select(Dataset).where(Dataset.id == dataset_id)
    )
    if not dataset:
        raise EvaluationConfigError(
            f"Dataset with ID '{dataset_id}' does not exist."
        )

    # Enforce strict project matching
    if assistant.project_id != dataset.project_id:
        raise IncompatibleProjectError(
            f"Incompatible project association: AssistantVersion belongs to project "
            f"'{assistant.project_id}', but Dataset belongs to project '{dataset.project_id}'."
        )

    if project_id is not None and assistant.project_id != project_id:
        raise IncompatibleProjectError(
            f"Specified project ID '{project_id}' does not match assistant project '{assistant.project_id}'."
        )

    project = db.scalar(
        select(Project).where(Project.id == assistant.project_id)
    )
    if not project:
        raise EvaluationConfigError(
            f"Associated Project '{assistant.project_id}' was not found in the database."
        )

    # Verify enabled test cases count
    enabled_count = db.scalar(
        select(func.count(TestCase.id)).where(
            TestCase.dataset_id == dataset.id,
            TestCase.is_enabled == True,
        )
    ) or 0

    if enabled_count == 0:
        raise EvaluationConfigError(
            f"Dataset '{dataset.name}' (ID: {dataset.id}) has no enabled test cases to evaluate."
        )

    return assistant, dataset, project, enabled_count


def create_evaluation_run(
    db: Session,
    assistant_version_id: uuid.UUID,
    dataset_id: uuid.UUID,
    config: dict[str, Any] | None = None,
) -> EvaluationRun:
    """Validate entities and initialize a pending EvaluationRun record in PostgreSQL.

    Args:
        db: Request-scoped SQLAlchemy session.
        assistant_version_id: Assistant to evaluate.
        dataset_id: Golden dataset to run.
        config: Optional execution configuration (concurrency, fail_fast, etc.).

    Returns:
        EvaluationRun: Newly created evaluation run with status='pending'.
    """
    assistant, dataset, project, enabled_count = validate_evaluation_entities(
        db=db,
        assistant_version_id=assistant_version_id,
        dataset_id=dataset_id,
    )

    merged_config = dict(config or {})
    merged_config.setdefault("max_concurrency", 1)
    merged_config.setdefault("fail_fast", False)
    # Record non-secret metadata snapshots
    merged_config["assistant_snapshot"] = {
        "id": str(assistant.id),
        "name": assistant.name,
        "version": assistant.version,
        "provider": assistant.provider,
        "model_name": assistant.model_name,
    }
    merged_config["dataset_snapshot"] = {
        "id": str(dataset.id),
        "name": dataset.name,
        "total_test_cases": enabled_count,
    }

    eval_run = EvaluationRun(
        project_id=project.id,
        assistant_version_id=assistant.id,
        dataset_id=dataset.id,
        status="pending",
        total_cases=enabled_count,
        passed_cases=0,
        failed_cases=0,
        config=merged_config,
    )
    db.add(eval_run)
    db.commit()
    db.refresh(eval_run)
    logger.info(
        "Created pending EvaluationRun '%s' for assistant '%s' on dataset '%s' (%d cases).",
        eval_run.id,
        assistant.name,
        dataset.name,
        enabled_count,
    )
    return eval_run


async def execute_evaluation_run(
    evaluation_run_id: uuid.UUID,
    max_concurrency: int = 1,
    fail_fast: bool = False,
) -> None:
    """Execute an evaluation run in the background with isolated database sessions.

    Lifecycle:
    1. Mark run as 'running' and set started_at.
    2. Load enabled test cases deterministically and extract decoupled TestCaseData.
    3. Concurrently or sequentially execute test cases without holding open DB transactions.
    4. Atomically persist CaseResult and MetricResults for each finished test case.
    5. Reconcile aggregate counts and mark run 'completed' or 'failed'.
    """
    logger.info("Starting background execution for EvaluationRun '%s'.", evaluation_run_id)

    # --------------------------------------------------------------------------
    # Step 1: Initialize run state and extract decoupled test cases
    # --------------------------------------------------------------------------
    db: Session = SessionLocal()
    test_cases_data: list[TestCaseData] = []
    try:
        eval_run = db.scalar(
            select(EvaluationRun).where(EvaluationRun.id == evaluation_run_id)
        )
        if not eval_run:
            logger.error("EvaluationRun '%s' not found for background execution.", evaluation_run_id)
            return

        assistant_version = db.scalar(
            select(AssistantVersion).where(AssistantVersion.id == eval_run.assistant_version_id)
        )
        if not assistant_version:
            eval_run.status = "failed"
            eval_run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        # Fetch enabled test cases with deterministic ordering
        test_case_records = db.scalars(
            select(TestCase)
            .where(
                TestCase.dataset_id == eval_run.dataset_id,
                TestCase.is_enabled == True,
            )
            .order_by(TestCase.created_at.asc(), TestCase.id.asc())
        ).all()

        # Decouple from SQLAlchemy session to prevent DetachedInstanceError
        test_cases_data = [TestCaseData.from_orm(tc) for tc in test_case_records]

        eval_run.status = "running"
        eval_run.started_at = datetime.now(timezone.utc)
        eval_run.total_cases = len(test_cases_data)
        db.commit()

        # Instantiate adapter and evaluators based on run config
        system_prompt = assistant_version.system_prompt
        adapter = resolve_assistant_adapter(assistant_version)
        evaluators = resolve_evaluators(eval_run.config)
    except Exception as e:
        logger.exception("Failed to initialize EvaluationRun '%s': %s", evaluation_run_id, e)
        db.rollback()
        try:
            er = db.scalar(select(EvaluationRun).where(EvaluationRun.id == evaluation_run_id))
            if er:
                er.status = "failed"
                er.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
        return
    finally:
        db.close()

    # --------------------------------------------------------------------------
    # Step 2: Execute test cases with controlled concurrency
    # --------------------------------------------------------------------------
    # Enforce sequential execution if DeepEval LLM judge is active to conserve host CPU/RAM
    has_deepeval = any(isinstance(getattr(e, "name", None), str) and getattr(e, "name").startswith("deepeval_") for e in evaluators)
    if has_deepeval:
        effective_concurrency = 1
    else:
        effective_concurrency = max(1, min(max_concurrency, 3))
    semaphore = asyncio.Semaphore(effective_concurrency)

    async def _process_single_case(tc_data: TestCaseData) -> str:
        async with semaphore:
            # 1. Asynchronous execution (No DB transaction held!)
            res = await execute_test_case(
                test_case=tc_data,
                adapter=adapter,
                evaluators=evaluators,
                system_prompt=system_prompt,
            )

            # 2. Atomic persistence in a short-lived DB transaction
            case_db: Session = SessionLocal()
            try:
                case_result = CaseResult(
                    evaluation_run_id=evaluation_run_id,
                    test_case_id=tc_data.id,
                    test_case_snapshot=res.test_case_snapshot,
                    actual_output=res.actual_output,
                    status=res.status,
                    error_message=res.error_message,
                    latency_ms=res.latency_ms,
                )
                case_db.add(case_result)
                case_db.flush()  # generates case_result.id

                for metric in res.metric_results:
                    mr = MetricResult(
                        case_result_id=case_result.id,
                        metric_name=metric.metric_name,
                        score=metric.score,
                        threshold=metric.threshold,
                        passed=metric.passed,
                        details=metric.details,
                    )
                    case_db.add(mr)

                case_db.commit()
                logger.debug(
                    "Persisted CaseResult '%s' (status: %s) for test case '%s'.",
                    case_result.id,
                    res.status,
                    tc_data.name,
                )
                return res.status
            except Exception as e:
                case_db.rollback()
                logger.exception("Failed to persist CaseResult for test case '%s': %s", tc_data.id, e)
                return "error"
            finally:
                case_db.close()

    # Run sequentially (default) or concurrently under semaphore
    try:
        for tc_data in test_cases_data:
            status = await _process_single_case(tc_data)
            if fail_fast and status in ("failed", "error"):
                logger.warning("Fail-fast triggered on test case '%s' with status '%s'.", tc_data.id, status)
                break
    except Exception as e:
        logger.exception("Catastrophic error during test case loop for run '%s': %s", evaluation_run_id, e)

    # --------------------------------------------------------------------------
    # Step 3: Reconcile counts and finalize EvaluationRun
    # --------------------------------------------------------------------------
    final_db: Session = SessionLocal()
    try:
        run = final_db.scalar(
            select(EvaluationRun).where(EvaluationRun.id == evaluation_run_id)
        )
        if run:
            # Reconcile exact counts directly from persisted CaseResult rows
            results = final_db.scalars(
                select(CaseResult).where(CaseResult.evaluation_run_id == evaluation_run_id)
            ).all()

            passed_count = sum(1 for r in results if r.status == "passed")
            failed_count = sum(1 for r in results if r.status in ("failed", "error"))

            run.passed_cases = passed_count
            run.failed_cases = failed_count
            run.completed_at = datetime.now(timezone.utc)
            run.status = "completed"

            final_db.commit()
            logger.info(
                "EvaluationRun '%s' COMPLETED: %d total, %d passed, %d failed.",
                evaluation_run_id,
                run.total_cases,
                passed_count,
                failed_count,
            )
    except Exception as e:
        final_db.rollback()
        logger.exception("Failed to finalize EvaluationRun '%s': %s", evaluation_run_id, e)
    finally:
        final_db.close()
