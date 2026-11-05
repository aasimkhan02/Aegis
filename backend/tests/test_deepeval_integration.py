"""Unit and integration tests for Step 7: DeepEval LLM-as-a-judge integration."""

import os
import unittest
from unittest.mock import MagicMock, patch
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.evaluation.context import EvaluationContext, TestCaseData
from app.evaluation.deepeval.evaluators import (
    DeepEvalAnswerRelevancyEvaluator,
    DeepEvalFaithfulnessEvaluator,
    DeepEvalHallucinationEvaluator,
    DeepEvalTechnicalSafetyEvaluator,
)
from app.evaluation.deepeval.judge import JudgeUnavailableError, OllamaJudgeModel
from app.evaluation.deepeval.metrics import CustomerTroubleshootingSafetyMetric
from app.evaluation.deepeval.utils import (
    calculate_aggregate_metric_score,
    extract_context_strings,
    extract_input_text,
    is_evaluator_error,
    is_metric_applicable,
    is_metric_result_applicable,
    summarize_run_metrics,
)
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult
from app.evaluation.evaluators.registry import get_default_evaluators, resolve_evaluators
from app.evaluation.executor import execute_test_case
from app.evaluation.orchestrator import create_evaluation_run, execute_evaluation_run
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.metric_result import MetricResult
from app.models.project import Project
from app.models.test_case import TestCase
from app.schemas.adapter import AssistantResponse
from deepeval.metrics import HallucinationMetric
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase


class MockJudgeModel(DeepEvalBaseLLM):
    """Deterministic, fast mock judge model for isolated unit tests."""

    def __init__(
        self,
        model_name: str = "mock-judge",
        should_fail: bool = False,
        timeout_fail: bool = False,
        malformed: bool = False,
    ):
        self.model_name = model_name
        self.should_fail = should_fail
        self.timeout_fail = timeout_fail
        self.malformed = malformed
        super().__init__(model=model_name)

    def load_model(self):
        return self

    def get_model_name(self) -> str:
        return self.model_name

    def supports_log_probs(self) -> bool:
        return False

    def supports_structured_outputs(self) -> bool:
        return True

    def supports_json_mode(self) -> bool:
        return True

    def generate(self, prompt: str, schema=None, *args, **kwargs) -> str:
        if self.should_fail:
            raise JudgeUnavailableError("Mocked connection refused: Ollama daemon is offline at http://localhost:11434.")
        if self.timeout_fail:
            raise JudgeUnavailableError("Mocked timeout: Local Ollama judge timed out after 120s.")
        if self.malformed:
            return "This is NOT valid JSON {{{ bad output"

        # If schema is requested, supply minimal valid JSON
        if schema:
            name = getattr(schema, "__name__", "")
            if "Statements" in name:
                return '{"statements": ["The appliance requires power disconnect."]}'
            if "ReasonScore" in name:
                return '{"score": 9.0, "reason": "Guidance properly emphasizes electrical safety."}'
            if "Verdicts" in name or "Verdict" in name:
                return '{"verdicts": [{"verdict": "yes", "reason": "Accurately answered."}]}'
            if "Truths" in name:
                return '{"truths": ["Compressor warranty is 5 years."]}'
            if "Claims" in name:
                return '{"claims": ["Compressor warranty is 5 years."]}'

        # Default fallback JSON
        return '{"verdicts": [{"verdict": "yes", "reason": "Accurate."}], "reason": "Supported by context.", "score": 1.0}'

    async def a_generate(self, prompt: str, schema=None, *args, **kwargs) -> str:
        return self.generate(prompt, schema=schema, *args, **kwargs)


class TestDeepEvalUtils(unittest.TestCase):
    """Test text and context extraction helpers and status validators."""

    def test_extract_input_text_string(self):
        self.assertEqual(extract_input_text("How to fix error E4?"), "How to fix error E4?")

    def test_extract_input_text_dict_query(self):
        self.assertEqual(extract_input_text({"query": "What is the warranty?"}), "What is the warranty?")
        self.assertEqual(extract_input_text({"prompt": "How to clean filter?"}), "How to clean filter?")

    def test_extract_input_text_messages(self):
        data = {
            "messages": [
                {"role": "system", "content": "You are a helper."},
                {"role": "user", "content": "Can I replace the plug myself?"},
            ]
        }
        self.assertEqual(extract_input_text(data), "Can I replace the plug myself?")

    def test_extract_context_strings(self):
        # Empty / None
        self.assertEqual(extract_context_strings(None), [])
        self.assertEqual(extract_context_strings([]), [])

        # List of strings
        self.assertEqual(extract_context_strings(["doc 1", "doc 2"]), ["doc 1", "doc 2"])

        # List of dicts
        raw = [
            {"text": "Text from snippet 1", "section": "Safety"},
            {"content": "Content from snippet 2"},
            {"other": "Raw other"},
        ]
        extracted = extract_context_strings(raw)
        self.assertEqual(len(extracted), 3)
        self.assertIn("Text from snippet 1", extracted)
        self.assertIn("Content from snippet 2", extracted)

    def test_evaluator_error_and_applicable_helpers(self):
        err_details = {"status": "evaluator_error", "evaluator_error": True, "error": "Connection refused"}
        self.assertTrue(is_evaluator_error(err_details))
        self.assertFalse(is_metric_applicable(err_details))

        skipped_details = {"skipped": True, "status": "skipped", "reason": "No context"}
        self.assertFalse(is_evaluator_error(skipped_details))
        self.assertFalse(is_metric_applicable(skipped_details))

        normal_details = {"status": "completed", "reason": "All good"}
        self.assertFalse(is_evaluator_error(normal_details))
        self.assertTrue(is_metric_applicable(normal_details))


class TestHallucinationAndFaithfulnessSeparation(unittest.TestCase):
    """Rigorous tests ensuring Faithfulness and Hallucination use strictly separated context fields."""

    def setUp(self):
        self.judge = MockJudgeModel()

    def test_faithfulness_uses_retrieval_context_only(self):
        """Faithfulness must strictly use retrieval_context and ignore ground_truth_context."""
        evaluator = DeepEvalFaithfulnessEvaluator(threshold=0.5, model=self.judge)
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Faithfulness retrieval context check",
            input_data={"query": "What is the warranty?"},
            retrieval_context=["Retrieved document snippet A"],
            ground_truth_context=["Curated reference ground truth B"],
            actual_response=AssistantResponse(
                output="The warranty is 2 years.",
                provider="mock",
                model="test",
                latency_ms=10,
            ),
        )

        with patch("app.evaluation.deepeval.evaluators.FaithfulnessMetric") as mock_metric_cls:
            mock_inst = MagicMock()
            mock_inst.measure.return_value = 1.0
            mock_inst.is_successful.return_value = True
            mock_inst.reason = "Supported"
            mock_metric_cls.return_value = mock_inst

            evaluator.evaluate(context)

            # Verify the LLMTestCase passed to FaithfulnessMetric
            self.assertTrue(mock_inst.measure.called)
            test_case_arg = mock_inst.measure.call_args[0][0]
            self.assertEqual(test_case_arg.retrieval_context, ["Retrieved document snippet A"])
            # Ensure it did NOT switch to ground_truth_context
            self.assertNotEqual(test_case_arg.retrieval_context, ["Curated reference ground truth B"])

    def test_hallucination_uses_ground_truth_context_only(self):
        """Hallucination must strictly use ground_truth_context and ignore retrieval_context and expected_output."""
        evaluator = DeepEvalHallucinationEvaluator(threshold=0.5, model=self.judge)
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Hallucination ground truth context check",
            input_data={"query": "Can the oven grill?"},
            expected_output={"contains": ["grill"]},
            retrieval_context=["Retrieved passage that should be ignored by Hallucination"],
            ground_truth_context=["Curated reference ground truth: Solo models do not grill"],
            actual_response=AssistantResponse(
                output="Solo models cannot grill.",
                provider="mock",
                model="test",
                latency_ms=10,
            ),
        )

        with patch("app.evaluation.deepeval.evaluators.HallucinationMetric") as mock_metric_cls:
            mock_inst = MagicMock()
            mock_inst.measure.return_value = 1.0
            mock_inst.is_successful.return_value = True
            mock_inst.reason = "No hallucination detected"
            mock_metric_cls.return_value = mock_inst

            evaluator.evaluate(context)

            self.assertTrue(mock_inst.measure.called)
            test_case_arg = mock_inst.measure.call_args[0][0]
            # DeepEval HallucinationMetric uses 'context' for curated reference information
            self.assertEqual(test_case_arg.context, ["Curated reference ground truth: Solo models do not grill"])
            self.assertNotEqual(test_case_arg.context, ["Retrieved passage that should be ignored by Hallucination"])

    def test_hallucination_missing_ground_truth_context_is_explicitly_skipped(self):
        """Missing ground_truth_context must produce an explicit not-applicable result without calling judge."""
        evaluator = DeepEvalHallucinationEvaluator(threshold=0.5, model=self.judge)
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Missing ground truth context",
            input_data={"query": "Hello!"},
            expected_output={"contains": ["Hello"]},
            retrieval_context=["Some retrieved text"],  # Populated, but ground_truth_context is missing!
            ground_truth_context=None,  # Missing!
            actual_response=AssistantResponse(
                output="Hello! How can I assist you?",
                provider="mock",
                model="test",
                latency_ms=10,
            ),
        )

        with patch("app.evaluation.deepeval.evaluators.HallucinationMetric") as mock_metric_cls:
            res = evaluator.evaluate(context)
            # The judge metric should NOT have been invoked
            self.assertFalse(mock_metric_cls.called)

        self.assertEqual(res.metric_name, "deepeval_hallucination")
        self.assertFalse(res.applicable)
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 1.0)
        self.assertTrue(res.details.get("skipped", False))
        self.assertIn("ground_truth_context", res.details.get("reason", ""))

    def test_existing_test_cases_without_ground_truth_context_remain_usable(self):
        """Existing test cases (where ground_truth_context is None) run cleanly."""
        evaluator = DeepEvalHallucinationEvaluator(threshold=0.5, model=self.judge)
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Legacy test case",
            input_data={"query": "What is the return period?"},
            ground_truth_context=[],  # Empty list
            actual_response=AssistantResponse(
                output="Return period is 10 days.",
                provider="mock",
                model="test",
                latency_ms=10,
            ),
        )
        res = evaluator.evaluate(context)
        self.assertFalse(res.applicable)
        self.assertTrue(res.passed)
        self.assertTrue(res.details["skipped"])


class TestHallucinationScoringDirection(unittest.TestCase):
    """Regression tests verifying Hallucination scoring direction in DeepEval 4.3.3.
    
    In DeepEval 4.3.3:
    - 1.0 = complete alignment (pass)
    - 0.0 = contradiction / hallucination (fail)
    - passes when score >= threshold
    """

    def setUp(self):
        self.judge = MockJudgeModel()
        self.evaluator = DeepEvalHallucinationEvaluator(threshold=0.5, model=self.judge)

    def _evaluate_with_mock_score(self, score: float, threshold: float = 0.5) -> EvaluatorResult:
        evaluator = DeepEvalHallucinationEvaluator(threshold=threshold, model=self.judge)
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Scoring direction check",
            input_data={"query": "Query"},
            ground_truth_context=["Trusted ground truth"],
            actual_response=AssistantResponse(
                output="Assistant output",
                provider="mock",
                model="test",
                latency_ms=10,
            ),
        )

        with patch("app.evaluation.deepeval.evaluators.HallucinationMetric") as mock_metric_cls:
            mock_inst = MagicMock()
            mock_inst.measure.return_value = score
            # Simulate DeepEval 4.3.3 is_successful(): score >= threshold
            mock_inst.is_successful.return_value = score >= threshold
            mock_inst.reason = f"Score is {score}"
            mock_metric_cls.return_value = mock_inst

            return evaluator.evaluate(context)

    def test_score_1_passes(self):
        """Score 1.0 represents complete alignment and must pass."""
        res = self._evaluate_with_mock_score(1.0, threshold=0.5)
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 1.0)

    def test_score_0_fails(self):
        """Score 0.0 represents contradiction/hallucination and must fail."""
        res = self._evaluate_with_mock_score(0.0, threshold=0.5)
        self.assertFalse(res.passed)
        self.assertEqual(res.score, 0.0)

    def test_score_exactly_at_threshold_passes(self):
        """Score exactly equal to threshold must pass."""
        res = self._evaluate_with_mock_score(0.5, threshold=0.5)
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 0.5)

    def test_score_below_threshold_fails(self):
        """Score strictly below threshold must fail."""
        res = self._evaluate_with_mock_score(0.49, threshold=0.5)
        self.assertFalse(res.passed)
        self.assertEqual(res.score, 0.49)


class TestJudgeFailureHandling(unittest.IsolatedAsyncioTestCase):
    """Tests ensuring judge model infrastructure failures are handled gracefully
    without reducing assistant pass rates or crashing runs."""

    def test_ollama_unavailable_records_evaluator_error(self):
        """Judge offline must record evaluator_error with applicable=False, not an assistant quality failure."""
        failing_judge = MockJudgeModel(should_fail=True)
        evaluator = DeepEvalAnswerRelevancyEvaluator(threshold=0.5, model=failing_judge)
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Judge offline test",
            input_data={"query": "Check status"},
            actual_response=AssistantResponse(
                output="System operating normally.",
                provider="mock",
                model="test",
                latency_ms=5,
            ),
        )

        result = evaluator.evaluate(context)
        self.assertEqual(result.metric_name, "deepeval_answer_relevancy")
        self.assertFalse(result.passed)
        self.assertFalse(result.applicable)  # MUST be non-applicable
        self.assertFalse(result.mandatory)   # MUST be non-mandatory
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.details.get("status"), "evaluator_error")
        self.assertTrue(result.details.get("evaluator_error"))
        self.assertIn("Ollama daemon is offline", result.details.get("error", ""))

    def test_judge_timeout_records_evaluator_error(self):
        """Judge timeout must record evaluator_error with applicable=False."""
        timeout_judge = MockJudgeModel(timeout_fail=True)
        evaluator = DeepEvalTechnicalSafetyEvaluator(threshold=0.5, model=timeout_judge)
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Timeout test",
            input_data={"query": "How to repair cord?"},
            actual_response=AssistantResponse(
                output="Disconnect power first.",
                provider="mock",
                model="test",
                latency_ms=5,
            ),
        )

        result = evaluator.evaluate(context)
        self.assertEqual(result.metric_name, "deepeval_technical_safety")
        self.assertFalse(result.applicable)
        self.assertEqual(result.details.get("status"), "evaluator_error")
        self.assertIn("timed out", result.details.get("error", "").lower())

    def test_malformed_judge_response_records_evaluator_error(self):
        """Malformed judge response must not crash evaluator or fail assistant."""
        malformed_judge = MockJudgeModel(malformed=True)
        evaluator = DeepEvalAnswerRelevancyEvaluator(threshold=0.5, model=malformed_judge)
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Malformed response test",
            input_data={"query": "Status"},
            actual_response=AssistantResponse(
                output="All systems operational.",
                provider="mock",
                model="test",
                latency_ms=5,
            ),
        )

        result = evaluator.evaluate(context)
        self.assertFalse(result.applicable)
        self.assertEqual(result.details.get("status"), "evaluator_error")

    async def test_judge_error_does_not_fail_assistant_case(self):
        """When judge fails, test case status must remain 'passed' if assistant output was valid."""
        failing_judge = MockJudgeModel(should_fail=True)
        failing_evaluator = DeepEvalAnswerRelevancyEvaluator(threshold=0.5, model=failing_judge)

        tc_data = TestCaseData(
            id=uuid.uuid4(),
            name="Assistant resilience test",
            input_data={"query": "Hello"},
            expected_output={"contains": "Hello"},
        )

        from unittest.mock import AsyncMock
        mock_adapter = MagicMock()
        mock_adapter.generate = AsyncMock(return_value=AssistantResponse(
            output="Hello! How can I help?",
            provider="mock",
            model="mock",
            latency_ms=10,
        ))

        # Deterministic evaluator passes, judge fails
        from app.evaluation.evaluators.response_presence import ResponsePresenceEvaluator
        evaluators = [ResponsePresenceEvaluator(), failing_evaluator]

        exec_res = await execute_test_case(
            test_case=tc_data,
            adapter=mock_adapter,
            evaluators=evaluators,
        )

        # The test case MUST pass because the assistant gave a good response
        # and the evaluator failure was an infrastructure error, NOT an assistant flaw.
        self.assertEqual(exec_res.status, "passed")
        self.assertEqual(len(exec_res.metric_results), 2)
        # Verify the failing evaluator was recorded with status=evaluator_error and applicable=False
        err_mr = next(m for m in exec_res.metric_results if m.metric_name == "deepeval_answer_relevancy")
        self.assertFalse(err_mr.applicable)
        self.assertEqual(err_mr.details.get("status"), "evaluator_error")


class TestEvaluatorResolutionAndControls(unittest.TestCase):
    """Test resolution of evaluators and opt-in configuration controls."""

    def test_default_resolution_omits_deepeval(self):
        """Standard runs must only include deterministic evaluators."""
        evaluators = resolve_evaluators({})
        names = [e.name for e in evaluators]
        self.assertEqual(names, ["response_presence", "expected_output", "tool_usage"])
        self.assertFalse(any("deepeval" in n for n in names))

    def test_opt_in_enable_deepeval(self):
        """Config enable_deepeval=True must append all 4 DeepEval evaluators."""
        evaluators = resolve_evaluators({"enable_deepeval": True})
        names = [e.name for e in evaluators]
        self.assertEqual(len(names), 7)
        self.assertIn("deepeval_answer_relevancy", names)
        self.assertIn("deepeval_faithfulness", names)
        self.assertIn("deepeval_hallucination", names)
        self.assertIn("deepeval_technical_safety", names)

    def test_explicit_evaluators_list(self):
        """Explicit evaluator list overrides defaults."""
        evaluators = resolve_evaluators({"evaluators": ["expected_output", "deepeval_answer_relevancy"]})
        names = [e.name for e in evaluators]
        self.assertEqual(names, ["expected_output", "deepeval_answer_relevancy"])


class TestDeepEvalPostgreSQLPersistence(unittest.IsolatedAsyncioTestCase):
    """Integration test verifying end-to-end execution, ground_truth_context, and MetricResult persistence in PostgreSQL."""

    def setUp(self):
        super().setUp()
        self.db: Session = SessionLocal()

        # Create isolated test project, assistant, and dataset
        proj_suffix = uuid.uuid4().hex[:8]
        self.project = Project(
            name=f"DeepEval Test Project {proj_suffix}",
            slug=f"deepeval-test-{proj_suffix}",
        )
        self.db.add(self.project)
        self.db.flush()

        self.assistant = AssistantVersion(
            project_id=self.project.id,
            name="Generic Mock Assistant",
            version="2.0",
            provider="mock",
            model_name="mock-model",
            system_prompt="You are a helpful customer service assistant.",
        )
        self.db.add(self.assistant)

        self.dataset = Dataset(
            project_id=self.project.id,
            name="DeepEval Golden Dataset",
        )
        self.db.add(self.dataset)
        self.db.flush()

        # TC1 has both retrieval_context and ground_truth_context
        self.tc1 = TestCase(
            dataset_id=self.dataset.id,
            name="Compressor Warranty Inquiry",
            input_data={"query": "What is the compressor warranty for 10 years on my refrigerator?"},
            expected_output={"contains": "Mock response"},
            retrieval_context=[{"text": "BharatHome refrigerators feature a 10-year warranty on the inverter compressor."}],
            ground_truth_context=["Curated reference: Inverter compressors carry a 10-year limited warranty."],
            is_enabled=True,
        )
        # TC2 has neither context (both None)
        self.tc2 = TestCase(
            dataset_id=self.dataset.id,
            name="General Politeness",
            input_data={"query": "Good morning! Can you help me?"},
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

    def test_database_crud_and_json_import_export_for_ground_truth_context(self):
        """Verify ground_truth_context survives create, read, update, and API serialization."""
        tc = self.db.scalar(select(TestCase).where(TestCase.id == self.tc1.id))
        self.assertIsNotNone(tc)
        self.assertEqual(tc.ground_truth_context, ["Curated reference: Inverter compressors carry a 10-year limited warranty."])

        # Test Update
        tc.ground_truth_context = ["Updated reference truth A", "Updated reference truth B"]
        self.db.commit()

        refreshed_tc = self.db.scalar(select(TestCase).where(TestCase.id == self.tc1.id))
        self.assertEqual(len(refreshed_tc.ground_truth_context), 2)
        self.assertIn("Updated reference truth A", refreshed_tc.ground_truth_context)

    async def test_end_to_end_deepeval_evaluation_run(self):
        """Execute evaluation run with enable_deepeval=True and verify DB MetricResults."""
        eval_run = create_evaluation_run(
            db=self.db,
            assistant_version_id=self.assistant.id,
            dataset_id=self.dataset.id,
            config={"enable_deepeval": True, "max_concurrency": 1},
        )
        self.assertEqual(eval_run.status, "pending")
        self.assertEqual(eval_run.total_cases, 2)

        mock_judge = MockJudgeModel()
        mock_deepeval_evaluators = [
            DeepEvalAnswerRelevancyEvaluator(threshold=0.5, model=mock_judge),
            DeepEvalFaithfulnessEvaluator(threshold=0.5, model=mock_judge),
            DeepEvalHallucinationEvaluator(threshold=0.5, model=mock_judge),
            DeepEvalTechnicalSafetyEvaluator(threshold=0.5, model=mock_judge),
        ]
        with patch("app.evaluation.evaluators.registry.get_deepeval_evaluators", return_value=mock_deepeval_evaluators):
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
                self.assertEqual(len(metrics), 7, f"Expected 7 metrics, got {metric_names}")

                self.assertIn("deepeval_answer_relevancy", metric_names)
                self.assertIn("deepeval_faithfulness", metric_names)
                self.assertIn("deepeval_hallucination", metric_names)
                self.assertIn("deepeval_technical_safety", metric_names)

                for m in metrics:
                    self.assertGreaterEqual(m.score, 0.0)
                    self.assertLessEqual(m.score, 1.0)
                    self.assertIsInstance(m.details, dict)

            # TC2 had neither retrieval_context nor ground_truth_context -> both should be marked skipped
            tc2_cr = next(cr for cr in case_results if cr.test_case_id == self.tc2.id)
            tc2_metrics = refreshed_db.scalars(
                select(MetricResult).where(MetricResult.case_result_id == tc2_cr.id)
            ).all()
            faith_m = next(m for m in tc2_metrics if m.metric_name == "deepeval_faithfulness")
            self.assertTrue(faith_m.details.get("skipped", False))
            self.assertIn("no retrieval_context", faith_m.details.get("reason", "").lower())

            halluc_m = next(m for m in tc2_metrics if m.metric_name == "deepeval_hallucination")
            self.assertTrue(halluc_m.details.get("skipped", False))
            self.assertIn("no ground_truth_context", halluc_m.details.get("reason", "").lower())
        finally:
            refreshed_db.close()


class TestMetricScoreAggregation(unittest.TestCase):
    """Rigorous acceptance tests for aggregate score calculation rules.
    
    Ensures non-applicable metrics and evaluator errors never distort aggregate evaluation scores
    or assistant pass rates.
    """

    def test_1_two_applicable_metrics_average(self):
        """Scenario 1: Two applicable metrics with scores 1.0 and 0.0 must average to 0.5."""
        metrics = [
            EvaluatorResult(metric_name="m1", score=1.0, threshold=0.5, passed=True, applicable=True),
            EvaluatorResult(metric_name="m2", score=0.0, threshold=0.5, passed=False, applicable=True),
        ]
        avg = calculate_aggregate_metric_score(metrics)
        self.assertEqual(avg, 0.5)

    def test_2_applicable_plus_non_applicable_not_inflated(self):
        """Scenario 2: Applicable (1.0) + Non-applicable (1.0, skipped) must yield average 1.0, NOT affected by non-applicable score."""
        metrics = [
            EvaluatorResult(metric_name="m1", score=1.0, threshold=0.5, passed=True, applicable=True),
            EvaluatorResult(
                metric_name="deepeval_faithfulness",
                score=1.0,
                threshold=0.5,
                passed=True,
                applicable=False,
                mandatory=False,
                details={"skipped": True, "applicable": False, "reason": "No retrieval context"},
            ),
        ]
        avg = calculate_aggregate_metric_score(metrics)
        self.assertEqual(avg, 1.0)

        summary = summarize_run_metrics(metrics)
        self.assertEqual(summary["applicable_metrics"], 1)
        self.assertEqual(summary["total_metrics"], 2)
        self.assertEqual(summary["overall_average_score"], 1.0)
        self.assertEqual(summary["by_metric"]["deepeval_faithfulness"]["skipped_count"], 1)
        self.assertEqual(summary["by_metric"]["deepeval_faithfulness"]["applicable_count"], 0)
        self.assertIsNone(summary["by_metric"]["deepeval_faithfulness"]["average_score"])

    def test_3_applicable_plus_evaluator_error_not_penalized(self):
        """Scenario 3: Applicable (1.0) + Evaluator error (0.0) must yield average 1.0, NOT penalized by evaluator outage."""
        metrics = [
            EvaluatorResult(metric_name="m1", score=1.0, threshold=0.5, passed=True, applicable=True),
            EvaluatorResult(
                metric_name="deepeval_technical_safety",
                score=0.0,
                threshold=0.5,
                passed=False,
                applicable=False,
                mandatory=False,
                details={"status": "evaluator_error", "evaluator_error": True, "error": "Connection refused"},
            ),
        ]
        avg = calculate_aggregate_metric_score(metrics)
        self.assertEqual(avg, 1.0)

        summary = summarize_run_metrics(metrics)
        self.assertEqual(summary["applicable_metrics"], 1)
        self.assertEqual(summary["overall_average_score"], 1.0)
        self.assertEqual(summary["by_metric"]["deepeval_technical_safety"]["error_count"], 1)
        self.assertIsNone(summary["by_metric"]["deepeval_technical_safety"]["average_score"])

    def test_4_applicable_genuine_failure_remains_counted(self):
        """Scenario 4: Applicable (0.0) genuine failure remains counted (average 0.0)."""
        metrics = [
            EvaluatorResult(metric_name="m1", score=0.0, threshold=0.5, passed=False, applicable=True),
        ]
        avg = calculate_aggregate_metric_score(metrics)
        self.assertEqual(avg, 0.0)

    def test_5_only_non_applicable_metrics_returns_none(self):
        """Scenario 5: When only non-applicable metrics exist, aggregate is None (unavailable), NEVER 0.0 or 1.0."""
        metrics = [
            EvaluatorResult(
                metric_name="deepeval_faithfulness",
                score=1.0,
                threshold=0.5,
                passed=True,
                applicable=False,
                mandatory=False,
                details={"skipped": True, "applicable": False},
            ),
            EvaluatorResult(
                metric_name="deepeval_hallucination",
                score=1.0,
                threshold=0.5,
                passed=True,
                applicable=False,
                mandatory=False,
                details={"skipped": True, "applicable": False},
            ),
        ]
        avg = calculate_aggregate_metric_score(metrics)
        self.assertIsNone(avg)

        summary = summarize_run_metrics(metrics)
        self.assertIsNone(summary["overall_average_score"])
        self.assertEqual(summary["applicable_metrics"], 0)

    def test_6_only_evaluator_errors_returns_none(self):
        """Scenario 6: When only evaluator errors exist, aggregate is None (unavailable), NEVER 0.0 or 1.0."""
        metrics = [
            EvaluatorResult(
                metric_name="deepeval_answer_relevancy",
                score=0.0,
                threshold=0.5,
                passed=False,
                applicable=False,
                mandatory=False,
                details={"evaluator_error": True, "status": "evaluator_error"},
            ),
        ]
        avg = calculate_aggregate_metric_score(metrics)
        self.assertIsNone(avg)

        summary = summarize_run_metrics(metrics)
        self.assertIsNone(summary["overall_average_score"])
        self.assertEqual(summary["applicable_metrics"], 0)

    def test_7_assistant_pass_rate_unaffected_by_judge_failure(self):
        """Scenario 7: Assistant pass rates remain unchanged when judge fails (test case status remains 'passed')."""
        import asyncio
        from unittest.mock import AsyncMock
        from app.evaluation.evaluators.response_presence import ResponsePresenceEvaluator

        tc = TestCaseData(
            id=uuid.uuid4(),
            name="Pass rate preservation test",
            input_data={"messages": [{"role": "user", "content": "How do I turn on the fan?"}]},
            expected_output={"contains": "power button"},
            expected_behavior="Turn on instructions",
            retrieval_context=None,
            ground_truth_context=None,
        )

        mock_adapter = MagicMock()
        mock_adapter.generate = AsyncMock(return_value=AssistantResponse(
            output="Press the power button on the remote or console.",
            provider="mock",
            model="mock-v1",
            latency_ms=15,
        ))

        failing_judge_evaluator = DeepEvalAnswerRelevancyEvaluator(
            threshold=0.5,
            model=MockJudgeModel(should_fail=True),
        )
        presence_evaluator = ResponsePresenceEvaluator()

        result = asyncio.run(execute_test_case(
            test_case=tc,
            adapter=mock_adapter,
            evaluators=[presence_evaluator, failing_judge_evaluator],
        ))

        # Test case status must remain 'passed' despite judge infrastructure crash
        self.assertEqual(result.status, "passed")
        self.assertIsNone(result.error_message)

        # Confirm metric results contain 1 applicable passed metric and 1 evaluator error
        self.assertEqual(len(result.metric_results), 2)
        judge_res = next(m for m in result.metric_results if m.metric_name == "deepeval_answer_relevancy")
        self.assertFalse(judge_res.applicable)
        self.assertTrue(judge_res.details.get("evaluator_error"))

        # Aggregate score over these metric results must be 1.0 (from presence), not penalized by judge error
        agg_score = calculate_aggregate_metric_score(result.metric_results)
        self.assertEqual(agg_score, 1.0)

