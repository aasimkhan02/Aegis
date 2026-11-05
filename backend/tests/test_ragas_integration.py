"""Unit and integration tests for Step 8: Ragas RAG Evaluation integration."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.evaluation.context import EvaluationContext, TestCaseData
from app.evaluation.deepeval.utils import calculate_aggregate_metric_score, summarize_run_metrics
from app.evaluation.evaluators.base import EvaluatorResult
from app.evaluation.evaluators.registry import get_default_evaluators, get_evaluator, resolve_evaluators
from app.evaluation.evaluators.response_presence import ResponsePresenceEvaluator
from app.evaluation.executor import execute_test_case
from app.evaluation.orchestrator import create_evaluation_run, execute_evaluation_run
from app.evaluation.ragas import (
    MockRagasEmbeddings,
    MockRagasJudgeModel,
    RagasContextPrecisionEvaluator,
    RagasContextRecallEvaluator,
    RagasEmbeddingUnavailableError,
    RagasFaithfulnessEvaluator,
    RagasJudgeUnavailableError,
    RagasOllamaEmbeddings,
    RagasOllamaJudgeModel,
    extract_reference_text,
    get_ragas_evaluators,
    is_ragas_evaluator_error,
    is_ragas_metric_applicable,
)
from app.evaluation.ragas.utils import run_async
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.metric_result import MetricResult
from app.models.project import Project
from app.models.test_case import TestCase
from app.schemas.adapter import AssistantResponse


class TestRagasExtractionAndUtils(unittest.TestCase):
    """Test data extraction, reference mapping, and async utility execution."""

    def test_expected_output_is_preferred_to_ground_truth_context(self):
        ref = extract_reference_text(
            ["Source evidence that is longer and must not be treated as the answer."],
            {"summary": "The motor has a 2-year warranty."},
        )
        self.assertEqual(ref, "The motor has a 2-year warranty.")

    def test_ground_truth_context_explicit_answer_equivalent_fallback(self):
        ref = extract_reference_text({"answer": "The motor warranty is two years."}, None)
        self.assertEqual(ref, "The motor warranty is two years.")

    def test_evidence_chunks_are_not_reference_answers(self):
        self.assertEqual(extract_reference_text(["Evidence chunk one", "Evidence chunk two"], None), "")

    def test_both_reference_fields_missing(self):
        self.assertEqual(extract_reference_text(None, None), "")

    def test_empty_or_malformed_reference_data(self):
        self.assertEqual(extract_reference_text([], {"summary": "  "}), "")
        self.assertEqual(extract_reference_text({"text": "document body"}, {"threshold": 0.8}), "")

    def test_extract_reference_text_fallback_to_expected_output_dict(self):
        eo = {"summary": "2-year motor warranty with exclusions for physical damage.", "threshold": 0.8}
        ref = extract_reference_text(ground_truth_context=None, expected_output=eo)
        self.assertEqual(ref, "2-year motor warranty with exclusions for physical damage.")

        eo2 = {"response": "The warranty lasts 2 years."}
        ref2 = extract_reference_text(ground_truth_context=[], expected_output=eo2)
        self.assertEqual(ref2, "The warranty lasts 2 years.")

    def test_extract_reference_text_fallback_to_expected_output_string(self):
        ref = extract_reference_text(None, expected_output="The product warranty is 12 months.")
        self.assertEqual(ref, "The product warranty is 12 months.")

    def test_extract_reference_text_empty(self):
        self.assertEqual(extract_reference_text(None, None), "")
        self.assertEqual(extract_reference_text([], {}), "")

    def test_run_async_in_sync_environment(self):
        async def sample_coro():
            return "sync_test_ok"

        res = run_async(sample_coro())
        self.assertEqual(res, "sync_test_ok")

    def test_run_async_in_running_event_loop(self):
        async def nested_coro():
            return "nested_test_ok"

        async def outer_coro():
            return run_async(nested_coro())

        res = asyncio.run(outer_coro())
        self.assertEqual(res, "nested_test_ok")

    def test_ragas_evaluator_error_helpers(self):
        err_details = {"status": "evaluator_error", "evaluator_error": True, "error": "Ollama down"}
        self.assertTrue(is_ragas_evaluator_error(err_details))
        self.assertFalse(is_ragas_metric_applicable(err_details))

        skip_details = {"skipped": True, "status": "skipped", "reason": "No retrieval context"}
        self.assertFalse(is_ragas_evaluator_error(skip_details))
        self.assertFalse(is_ragas_metric_applicable(skip_details))


class TestRagasJudgeAndEmbeddings(unittest.TestCase):
    """Test Mock and Ollama judge/embedding adapters."""

    def test_mock_judge_model_success(self):
        judge = MockRagasJudgeModel(
            mock_statements=["Compressor has 10-year warranty."],
            faithfulness_verdict=1,
            precision_verdict=1,
            recall_attributed=1,
        )
        self.assertEqual(judge.get_model_name(), "mock-ragas-judge")
        self.assertTrue(judge.is_finished(None))

    def test_mock_judge_model_failures(self):
        failing_judge = MockRagasJudgeModel(should_fail=True)
        with self.assertRaises(RagasJudgeUnavailableError):
            failing_judge.generate_text("test prompt")

        timeout_judge = MockRagasJudgeModel(timeout_fail=True)
        with self.assertRaises(RagasJudgeUnavailableError):
            timeout_judge.generate_text("test prompt")

    def test_ollama_judge_caches_only_exact_repeat_prompts(self):
        judge = RagasOllamaJudgeModel(model_name="qwen2.5:1.5b")
        response = MagicMock(status_code=200)
        response.json.return_value = {"response": '{"verdict": 1}'}
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response
        with patch("app.evaluation.ragas.judge.httpx.Client", return_value=client):
            first = judge.generate_text("same prompt")
            second = judge.generate_text("same prompt")
            judge.generate_text("different prompt")
        self.assertEqual(first.generations[0][0].text, second.generations[0][0].text)
        self.assertEqual(client.post.call_count, 2)

    def test_mock_embeddings(self):
        embs = MockRagasEmbeddings(dimension=4)
        docs = embs.embed_documents(["doc 1", "doc 2"])
        self.assertEqual(len(docs), 2)
        self.assertEqual(len(docs[0]), 4)
        q = embs.embed_query("query")
        self.assertEqual(len(q), 4)

    def test_ollama_embeddings_missing_model_raises_error(self):
        # Point to a nonexistent model name without downloading
        embs = RagasOllamaEmbeddings(model_name="nonexistent-model-xyz")
        with patch.object(embs, "is_available", return_value=False):
            with self.assertRaises(RagasEmbeddingUnavailableError) as ctx:
                embs.embed_documents(["test text"])
            self.assertIn("Run `ollama pull", str(ctx.exception))


class TestRagasEvaluatorsUnit(unittest.TestCase):
    """Isolated unit tests for Faithfulness, Context Precision, and Context Recall evaluators."""

    def setUp(self):
        self.mock_judge = MockRagasJudgeModel()
        self.faithfulness = RagasFaithfulnessEvaluator(threshold=0.5, model=self.mock_judge)
        self.precision = RagasContextPrecisionEvaluator(threshold=0.5, model=self.mock_judge)
        self.recall = RagasContextRecallEvaluator(threshold=0.5, model=self.mock_judge)

    def test_faithfulness_success(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="AeroCool Warranty",
            input_data={"query": "What is the warranty?"},
            retrieval_context=["BharatHome AeroCool fans feature a 2-year motor warranty."],
            actual_response=AssistantResponse(
                output="The AeroCool fan features a 2-year motor warranty.",
                provider="mock",
                model="mock-v1",
                latency_ms=10,
            ),
        )
        res = self.faithfulness.evaluate(ctx)
        self.assertEqual(res.metric_name, "ragas_faithfulness")
        self.assertEqual(res.score, 1.0)
        self.assertTrue(res.passed)
        self.assertTrue(res.applicable)
        self.assertIn("status", res.details)

    def test_faithfulness_missing_retrieval_context_is_skipped(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Greeting Case",
            input_data={"query": "Hello!"},
            retrieval_context=None,
            actual_response=AssistantResponse(
                output="Hello, how can I assist you today?",
                provider="mock",
                model="mock-v1",
                latency_ms=10,
            ),
        )
        res = self.faithfulness.evaluate(ctx)
        self.assertFalse(res.applicable)
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 1.0)
        self.assertTrue(res.details.get("skipped"))
        self.assertIn("no retrieval_context", res.details.get("reason", "").lower())

    def test_faithfulness_empty_output_fails(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Silent Crash Case",
            input_data={"query": "Help me!"},
            retrieval_context=["Some valid troubleshooting snippet."],
            actual_response=AssistantResponse(
                output="",
                provider="mock",
                model="mock-v1",
                latency_ms=10,
            ),
        )
        res = self.faithfulness.evaluate(ctx)
        self.assertTrue(res.applicable)
        self.assertFalse(res.passed)
        self.assertEqual(res.score, 0.0)
        self.assertIn("Empty or missing assistant output", res.details.get("error", ""))

    def test_context_precision_success(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Precision Test",
            input_data={"query": "What is the compressor warranty?"},
            retrieval_context=["BharatHome refrigerators carry a 10-year inverter compressor warranty."],
            expected_output={"summary": "10-year compressor warranty on inverter refrigerators."},
            actual_response=AssistantResponse(
                output="The compressor warranty is 10 years.",
                provider="mock",
                model="mock-v1",
                latency_ms=10,
            ),
        )
        res = self.precision.evaluate(ctx)
        self.assertEqual(res.metric_name, "ragas_context_precision")
        self.assertEqual(res.score, 1.0)
        self.assertTrue(res.passed)
        self.assertTrue(res.applicable)
        self.assertEqual(res.details.get("reference_source"), "expected_output")

    def test_context_precision_fallback_to_expected_output_summary(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Precision Fallback Test",
            input_data={"query": "What is the compressor warranty?"},
            expected_output={"summary": "10-year compressor warranty on inverter refrigerators."},
            retrieval_context=["BharatHome refrigerators carry a 10-year inverter compressor warranty."],
            ground_truth_context=None,  # missing ground_truth_context, must fallback to expected_output
            actual_response=AssistantResponse(
                output="The compressor warranty is 10 years.",
                provider="mock",
                model="mock-v1",
                latency_ms=10,
            ),
        )
        res = self.precision.evaluate(ctx)
        self.assertTrue(res.applicable)
        self.assertTrue(res.passed)
        self.assertEqual(res.details.get("reference_source"), "expected_output")

    def test_context_precision_missing_retrieval_context_is_skipped(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="No Retrieval Precision Test",
            input_data={"query": "Hello"},
            retrieval_context=None,
            ground_truth_context=["Some ground truth reference."],
            actual_response=AssistantResponse(output="Hi", provider="mock", model="mock-v1", latency_ms=10),
        )
        res = self.precision.evaluate(ctx)
        self.assertFalse(res.applicable)
        self.assertTrue(res.passed)
        self.assertTrue(res.details.get("skipped"))

    def test_context_precision_missing_reference_is_skipped(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="No Reference Precision Test",
            input_data={"query": "Hello"},
            retrieval_context=["Some retrieved snippet."],
            ground_truth_context=None,
            expected_output=None,
            actual_response=AssistantResponse(output="Hi", provider="mock", model="mock-v1", latency_ms=10),
        )
        res = self.precision.evaluate(ctx)
        self.assertFalse(res.applicable)
        self.assertTrue(res.passed)
        self.assertTrue(res.details.get("skipped"))
        self.assertIn("no valid answer reference", res.details.get("reason", "").lower())

    def test_context_recall_success(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Recall Test",
            input_data={"query": "What is the water heater warranty?"},
            retrieval_context=["BharatHome water heaters include 2-year comprehensive and 5-year tank warranty."],
            expected_output={"summary": "2-year comprehensive and 5-year tank warranty."},
            actual_response=AssistantResponse(
                output="2-year product and 5-year tank warranty.",
                provider="mock",
                model="mock-v1",
                latency_ms=10,
            ),
        )
        res = self.recall.evaluate(ctx)
        self.assertEqual(res.metric_name, "ragas_context_recall")
        self.assertEqual(res.score, 1.0)
        self.assertTrue(res.passed)
        self.assertTrue(res.applicable)

    def test_context_recall_missing_reference_is_skipped(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="No Reference Recall Test",
            input_data={"query": "Hello"},
            retrieval_context=["Some retrieved snippet."],
            ground_truth_context=None,
            expected_output=None,
            actual_response=AssistantResponse(output="Hi", provider="mock", model="mock-v1", latency_ms=10),
        )
        res = self.recall.evaluate(ctx)
        self.assertFalse(res.applicable)
        self.assertTrue(res.details.get("skipped"))

    def test_evidence_only_context_is_not_reference(self):
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(), test_case_name="Evidence only", input_data={"query": "Warranty?"},
            retrieval_context=["The appliance is silver."],
            ground_truth_context=["The warranty lasts 2 years."],
            actual_response=AssistantResponse(output="Two years.", provider="mock", model="mock-v1", latency_ms=1),
        )
        result = self.recall.evaluate(ctx)
        self.assertFalse(result.applicable)
        self.assertIn("no valid answer reference", result.details["reason"].lower())

    def test_invalid_judge_score_is_error_and_excluded_from_aggregate(self):
        evaluator = RagasFaithfulnessEvaluator(model=self.mock_judge)
        evaluator.metric.single_turn_ascore = AsyncMock(return_value=1.5)
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(), test_case_name="Invalid judge", input_data={"query": "Q"},
            retrieval_context=["Evidence."],
            actual_response=AssistantResponse(output="Answer.", provider="mock", model="mock-v1", latency_ms=1),
        )
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.applicable)
        self.assertEqual(result.details["status"], "evaluator_error")
        self.assertIn("within [0, 1]", result.details["error"])
        self.assertIsNone(calculate_aggregate_metric_score([result]))

    def test_malformed_judge_response_is_error_not_success(self):
        evaluator = RagasFaithfulnessEvaluator(model=MockRagasJudgeModel(malformed=True))
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(), test_case_name="Malformed judge", input_data={"query": "Q"},
            retrieval_context=["Evidence."],
            actual_response=AssistantResponse(output="Answer.", provider="mock", model="mock-v1", latency_ms=1),
        )
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.applicable)
        self.assertEqual(result.details["status"], "evaluator_error")
        self.assertTrue(result.details["judge_explanations"])
        self.assertIsNone(calculate_aggregate_metric_score([result]))

    def test_metric_timeout_is_reported_and_excluded_from_aggregate(self):
        evaluator = RagasFaithfulnessEvaluator(model=self.mock_judge, timeout_seconds=0.001)
        async def slow_score(sample):
            await asyncio.sleep(0.02)
            return 0.5
        evaluator.metric.single_turn_ascore = slow_score
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(), test_case_name="Timeout", input_data={"query": "Q"},
            retrieval_context=["Evidence."],
            actual_response=AssistantResponse(output="Answer.", provider="mock", model="mock-v1", latency_ms=1),
        )
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.applicable)
        self.assertEqual(result.details["error_type"], "TimeoutError")
        self.assertIsNone(calculate_aggregate_metric_score([result]))

    def test_judge_error_handling_graceful(self):
        failing_judge = MockRagasJudgeModel(should_fail=True)
        evaluator = RagasFaithfulnessEvaluator(threshold=0.5, model=failing_judge)
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Judge Outage Case",
            input_data={"query": "Test query"},
            retrieval_context=["Some snippet."],
            actual_response=AssistantResponse(output="Some output", provider="mock", model="mock-v1", latency_ms=10),
        )
        res = evaluator.evaluate(ctx)
        self.assertFalse(res.applicable)
        self.assertFalse(res.mandatory)
        self.assertTrue(res.details.get("evaluator_error"))
        self.assertEqual(res.details.get("status"), "evaluator_error")
        self.assertEqual(res.score, 0.0)


class TestRagasRegistryAndConfig(unittest.TestCase):
    """Test registry discovery, opt-in execution, and independent metric selection."""

    def test_default_evaluators_only_deterministic(self):
        evaluators = resolve_evaluators({})
        names = [e.name for e in evaluators]
        self.assertEqual(len(names), 3)
        self.assertIn("response_presence", names)
        self.assertIn("expected_output", names)
        self.assertIn("tool_usage", names)
        self.assertNotIn("ragas_faithfulness", names)

    def test_ragas_opt_in_independent(self):
        evaluators = resolve_evaluators({"enable_ragas": True})
        names = [e.name for e in evaluators]
        self.assertEqual(len(names), 6)
        self.assertIn("ragas_faithfulness", names)
        self.assertIn("ragas_context_precision", names)
        self.assertIn("ragas_context_recall", names)
        self.assertNotIn("deepeval_answer_relevancy", names)

    def test_ragas_and_deepeval_combined(self):
        evaluators = resolve_evaluators({"enable_ragas": True, "enable_deepeval": True})
        names = [e.name for e in evaluators]
        self.assertEqual(len(names), 10)  # 3 deterministic + 4 deepeval + 3 ragas
        self.assertIn("ragas_faithfulness", names)
        self.assertIn("deepeval_faithfulness", names)

    def test_ragas_metrics_subset_selection(self):
        evaluators = resolve_evaluators({
            "enable_ragas": True,
            "ragas_metrics": ["ragas_faithfulness"],
        })
        names = [e.name for e in evaluators]
        self.assertEqual(len(names), 4)  # 3 deterministic + 1 ragas
        self.assertIn("ragas_faithfulness", names)
        self.assertNotIn("ragas_context_precision", names)

    def test_get_evaluator_by_name(self):
        ev1 = get_evaluator("ragas_faithfulness")
        self.assertIsInstance(ev1, RagasFaithfulnessEvaluator)
        ev2 = get_evaluator("ragas_context_precision")
        self.assertIsInstance(ev2, RagasContextPrecisionEvaluator)
        ev3 = get_evaluator("ragas_context_recall")
        self.assertIsInstance(ev3, RagasContextRecallEvaluator)


class TestRagasExecutionAndPassRatePreservation(unittest.TestCase):
    """Test execute_test_case preserves assistant pass rate when judge fails, and aggregates properly."""

    def test_assistant_pass_rate_preserved_on_ragas_judge_error(self):
        tc = TestCaseData(
            id=uuid.uuid4(),
            name="Pass rate preservation test",
            input_data={"messages": [{"role": "user", "content": "How do I turn on the fan?"}]},
            expected_output={"contains": "power button"},
            expected_behavior="Turn on instructions",
            retrieval_context=["Power button is on the top panel."],
            ground_truth_context=None,
        )

        mock_adapter = MagicMock()
        mock_adapter.generate = AsyncMock(return_value=AssistantResponse(
            output="Press the power button on the top panel.",
            provider="mock",
            model="mock-v1",
            latency_ms=15,
        ))

        # A failing Ragas judge
        failing_judge_evaluator = RagasFaithfulnessEvaluator(
            threshold=0.5,
            model=MockRagasJudgeModel(should_fail=True),
        )
        presence_evaluator = ResponsePresenceEvaluator()

        result = asyncio.run(execute_test_case(
            test_case=tc,
            adapter=mock_adapter,
            evaluators=[presence_evaluator, failing_judge_evaluator],
        ))

        # Case status must remain 'passed' despite judge error
        self.assertEqual(result.status, "passed")
        self.assertIsNone(result.error_message)

        # Confirm metric results
        self.assertEqual(len(result.metric_results), 2)
        judge_res = next(m for m in result.metric_results if m.metric_name == "ragas_faithfulness")
        self.assertFalse(judge_res.applicable)
        self.assertTrue(judge_res.details.get("evaluator_error"))

        # Aggregate score must be 1.0 (from presence), not penalized by judge error
        agg_score = calculate_aggregate_metric_score(result.metric_results)
        self.assertEqual(agg_score, 1.0)


class TestRagasPostgreSQLPersistence(unittest.IsolatedAsyncioTestCase):
    """Database integration test for Ragas evaluation execution and persistence."""

    def setUp(self):
        self.db: Session = SessionLocal()
        proj_suffix = uuid.uuid4().hex[:8]
        self.project = Project(
            name=f"Ragas Test Project {proj_suffix}",
            slug=f"ragas-test-{proj_suffix}",
            description="Testing Ragas integration",
        )
        self.db.add(self.project)
        self.db.flush()

        self.assistant = AssistantVersion(
            project_id=self.project.id,
            name="Ragas Test Assistant",
            version="1.0",
            provider="mock",
            model_name="mock-model",
            system_prompt="You are a helpful assistant.",
            config={},
        )
        self.dataset = Dataset(
            project_id=self.project.id,
            name=f"Ragas Test Dataset {proj_suffix}",
            description="Dataset for testing Ragas metrics",
        )
        self.db.add_all([self.assistant, self.dataset])
        self.db.flush()

        # TC1 has retrieval_context and ground_truth_context
        self.tc1 = TestCase(
            dataset_id=self.dataset.id,
            name="AeroCool Warranty Case",
            input_data={"query": "What is the warranty?"},
            expected_output={"contains": "Mock response"},
            retrieval_context=[{"text": "BharatHome AeroCool fan has a 2-year warranty."}],
            ground_truth_context=["The fan carries a 2-year motor warranty."],
            is_enabled=True,
        )
        # TC2 has neither context -> should skip
        self.tc2 = TestCase(
            dataset_id=self.dataset.id,
            name="General Politeness Case",
            input_data={"query": "Hello!"},
            expected_output={"contains": "Mock response"},
            retrieval_context=None,
            ground_truth_context=None,
            is_enabled=True,
        )
        self.db.add_all([self.tc1, self.tc2])
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        try:
            self.db.query(MetricResult).filter(
                MetricResult.case_result_id.in_(
                    select(CaseResult.id).join(EvaluationRun).filter(EvaluationRun.project_id == self.project.id)
                )
            ).delete(synchronize_session=False)
            self.db.query(CaseResult).filter(
                CaseResult.evaluation_run_id.in_(
                    select(EvaluationRun.id).filter(EvaluationRun.project_id == self.project.id)
                )
            ).delete(synchronize_session=False)
            self.db.query(EvaluationRun).filter(EvaluationRun.project_id == self.project.id).delete()
            self.db.query(TestCase).filter(TestCase.dataset_id == self.dataset.id).delete()
            self.db.query(Dataset).filter(Dataset.id == self.dataset.id).delete()
            self.db.query(AssistantVersion).filter(AssistantVersion.id == self.assistant.id).delete()
            self.db.query(Project).filter(Project.id == self.project.id).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()
        super().tearDown()

    async def test_end_to_end_ragas_evaluation_run(self):
        """Execute evaluation run with enable_ragas=True and verify DB MetricResults."""
        eval_run = create_evaluation_run(
            db=self.db,
            assistant_version_id=self.assistant.id,
            dataset_id=self.dataset.id,
            config={"enable_ragas": True, "max_concurrency": 1},
        )
        self.assertEqual(eval_run.status, "pending")
        self.assertEqual(eval_run.total_cases, 2)

        mock_judge = MockRagasJudgeModel()
        mock_ragas_evaluators = [
            RagasFaithfulnessEvaluator(threshold=0.5, model=mock_judge),
            RagasContextPrecisionEvaluator(threshold=0.5, model=mock_judge),
            RagasContextRecallEvaluator(threshold=0.5, model=mock_judge),
        ]
        with patch("app.evaluation.evaluators.registry.get_ragas_evaluators", return_value=mock_ragas_evaluators):
            await execute_evaluation_run(
                evaluation_run_id=eval_run.id,
                max_concurrency=1,
            )

        refreshed_db = SessionLocal()
        try:
            run = refreshed_db.scalar(select(EvaluationRun).where(EvaluationRun.id == eval_run.id))
            self.assertIsNotNone(run)
            self.assertEqual(run.status, "completed")
            self.assertEqual(run.total_cases, 2)
            self.assertEqual(run.passed_cases, 2)
            self.assertEqual(run.failed_cases, 0)

            case_results = refreshed_db.scalars(
                select(CaseResult).where(CaseResult.evaluation_run_id == eval_run.id)
            ).all()
            self.assertEqual(len(case_results), 2)

            for cr in case_results:
                metrics = refreshed_db.scalars(
                    select(MetricResult).where(MetricResult.case_result_id == cr.id)
                ).all()
                metric_names = [m.metric_name for m in metrics]
                self.assertEqual(len(metrics), 6, f"Expected 6 metrics (3 deterministic + 3 ragas), got {metric_names}")

                self.assertIn("ragas_faithfulness", metric_names)
                self.assertIn("ragas_context_precision", metric_names)
                self.assertIn("ragas_context_recall", metric_names)

                for m in metrics:
                    self.assertGreaterEqual(m.score, 0.0)
                    self.assertLessEqual(m.score, 1.0)
                    self.assertIsInstance(m.details, dict)

            # TC2 had neither retrieval_context nor ground_truth_context -> all 3 should be marked skipped
            tc2_cr = next(cr for cr in case_results if cr.test_case_id == self.tc2.id)
            tc2_metrics = refreshed_db.scalars(
                select(MetricResult).where(MetricResult.case_result_id == tc2_cr.id)
            ).all()
            faith_m = next(m for m in tc2_metrics if m.metric_name == "ragas_faithfulness")
            self.assertTrue(faith_m.details.get("skipped", False))
            self.assertIn("no retrieval_context", faith_m.details.get("reason", "").lower())

            prec_m = next(m for m in tc2_metrics if m.metric_name == "ragas_context_precision")
            self.assertTrue(prec_m.details.get("skipped", False))

            rec_m = next(m for m in tc2_metrics if m.metric_name == "ragas_context_recall")
            self.assertTrue(rec_m.details.get("skipped", False))
        finally:
            refreshed_db.close()
