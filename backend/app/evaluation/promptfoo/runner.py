"""Promptfoo CLI execution runner with asynchronous subprocess control, secret redaction, and structured output parsing."""

import asyncio
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from typing import Any
import uuid

from app.schemas.promptfoo import (
    PromptfooAssertionResult,
    PromptfooEvaluationResponse,
    PromptfooTestResultItem,
)

logger = logging.getLogger("aegis.evaluation.promptfoo")

# Regular expressions for identifying sensitive credentials in outputs and logs
SENSITIVE_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE),
    re.compile(r"(pass|password|pwd|secret|api_key|token)[=:]\s*([^\s,;]+)", re.IGNORECASE),
    re.compile(r"postgresql://[^:]+:([^@]+)@", re.IGNORECASE),
]


def redact_secrets(text: str | None) -> str:
    """Scrub sensitive keys, passwords, and tokens from text before returning or logging."""
    if not text:
        return ""

    redacted = text

    # Redact pattern matches
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)

    # Redact any explicitly known active environment variable values
    sensitive_env_keys = [
        "OPENAI_API_KEY",
        "HTTP_ADAPTER_API_KEY",
        "DATABASE_URL",
        "SECRET_KEY",
    ]
    for key in sensitive_env_keys:
        val = os.environ.get(key)
        if val and len(val) >= 6:
            redacted = redacted.replace(val, "[REDACTED_ENV_SECRET]")

    return redacted


def find_promptfoo_cli() -> str | None:
    """Locate the executable Promptfoo CLI binary on the host system."""
    # 1. Explicit override via environment
    env_cli = os.environ.get("PROMPTFOO_CLI_PATH")
    if env_cli and Path(env_cli).is_file():
        return env_cli

    # 2. System PATH lookup (e.g. promptfoo, promptfoo.cmd)
    for name in ("promptfoo.cmd", "promptfoo", "promptfoo.ps1"):
        loc = shutil.which(name)
        if loc:
            return loc

    # 3. Standard Windows npm global path
    appdata = os.environ.get("APPDATA")
    if appdata:
        npm_cmd = Path(appdata) / "npm" / "promptfoo.cmd"
        if npm_cmd.is_file():
            return str(npm_cmd)

    return None


def get_default_config_path() -> Path:
    """Return the absolute path to the default promptfooconfig.yaml."""
    return Path(__file__).resolve().parent.parent.parent.parent / "promptfoo" / "promptfooconfig.yaml"


async def execute_promptfoo_evaluation(
    assistant_version_id: uuid.UUID | None = None,
    version: str = "v1",
    provider: str = "mock",
    config_path: Path | str | None = None,
    timeout_seconds: int = 120,
    assistant_name: str | None = None,
    assistant_version: str | None = None,
) -> PromptfooEvaluationResponse:
    """Execute the Promptfoo CLI asynchronously and parse structured test results.
    
    Guarantees:
    - Never blocks the FastAPI async event loop.
    - Captures stdout, stderr, and exit codes.
    - Redacts secrets from all outputs.
    - Clearly distinguishes test assertion failures from infrastructure errors.
    """
    start_time = time.perf_counter()
    cli_path = find_promptfoo_cli()

    if not cli_path:
        logger.error("Promptfoo CLI not found on host system.")
        return PromptfooEvaluationResponse(
            status="cli_not_found",
            total_tests=0,
            passed=0,
            failed=0,
            results=[],
            duration_seconds=round(time.perf_counter() - start_time, 2),
            assistant_name=assistant_name,
            assistant_version=assistant_version or version,
            error="Promptfoo CLI is not installed or not found in system PATH.",
        )

    resolved_config = Path(config_path) if config_path else get_default_config_path()
    if not resolved_config.is_file():
        logger.error("Promptfoo configuration file not found at '%s'.", resolved_config)
        return PromptfooEvaluationResponse(
            status="error",
            total_tests=0,
            passed=0,
            failed=0,
            results=[],
            duration_seconds=round(time.perf_counter() - start_time, 2),
            assistant_name=assistant_name,
            assistant_version=assistant_version or version,
            error=f"Promptfoo configuration file not found at: {resolved_config}",
        )

    # Create temporary JSON output file
    temp_dir = tempfile.mkdtemp(prefix="aegis_promptfoo_")
    output_json_path = Path(temp_dir) / "output.json"

    # Prepare subprocess environment
    env = dict(os.environ)
    env["PROMPTFOO_DISABLE_UPDATE"] = "true"
    env["PROMPTFOO_DISABLE_TELEMETRY"] = "true"
    env["PROMPTFOO_PYTHON"] = sys.executable

    if assistant_version_id:
        env["AEGIS_ASSISTANT_VERSION_ID"] = str(assistant_version_id)
    env["AEGIS_ASSISTANT_VERSION"] = version
    env["AEGIS_ASSISTANT_PROVIDER"] = provider

    args = [
        cli_path,
        "eval",
        "-c",
        str(resolved_config),
        "--no-cache",
        "-o",
        str(output_json_path),
        "--no-table",
        "--no-progress-bar",
        "-j",
        "4",
    ]

    logger.info("Executing Promptfoo CLI: %s (target version: %s)", cli_path, version)

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(resolved_config.parent),
            env=env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(timeout_seconds),
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            duration = round(time.perf_counter() - start_time, 2)
            logger.warning("Promptfoo execution timed out after %ds.", timeout_seconds)
            return PromptfooEvaluationResponse(
                status="timeout",
                total_tests=0,
                passed=0,
                failed=0,
                results=[],
                duration_seconds=duration,
                assistant_name=assistant_name,
                assistant_version=assistant_version or version,
                error=f"Promptfoo execution timed out after {timeout_seconds} seconds.",
            )

        duration = round(time.perf_counter() - start_time, 2)
        raw_stdout = stdout_bytes.decode("utf-8", errors="replace")
        raw_stderr = stderr_bytes.decode("utf-8", errors="replace")
        redacted_stdout = redact_secrets(raw_stdout)
        redacted_stderr = redact_secrets(raw_stderr)

        # Check for JSON output file
        if not output_json_path.is_file():
            # If no JSON file generated and non-zero exit code, it's an infrastructure/process crash
            logger.error("Promptfoo failed to produce output.json. Exit code: %d. Stderr: %s", proc.returncode, redacted_stderr)
            return PromptfooEvaluationResponse(
                status="error",
                total_tests=0,
                passed=0,
                failed=0,
                results=[],
                duration_seconds=duration,
                assistant_name=assistant_name,
                assistant_version=assistant_version or version,
                error=f"Promptfoo process exited with code {proc.returncode}: {redacted_stderr.strip() or redacted_stdout.strip()}",
            )

        # Parse JSON output
        try:
            with open(output_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("Failed to parse Promptfoo JSON output: %s", e)
            return PromptfooEvaluationResponse(
                status="error",
                total_tests=0,
                passed=0,
                failed=0,
                results=[],
                duration_seconds=duration,
                assistant_name=assistant_name,
                assistant_version=assistant_version or version,
                error=f"Malformed Promptfoo JSON output: {e}",
            )

        results_data = data.get("results", {})
        stats = results_data.get("stats", {})
        successes = int(stats.get("successes", 0))
        failures = int(stats.get("failures", 0))
        errors = int(stats.get("errors", 0))
        total_tests = successes + failures + errors

        parsed_items: list[PromptfooTestResultItem] = []
        raw_results_list = results_data.get("results", [])

        for item in raw_results_list:
            tc = item.get("testCase", {})
            desc = tc.get("description") or "Promptfoo Test Case"
            vars_dict = tc.get("vars", {})
            prompt_str = vars_dict.get("query") or vars_dict.get("prompt") or str(tc.get("vars", ""))
            item_success = bool(item.get("success", False))
            score = float(item.get("score", 1.0 if item_success else 0.0))

            resp_dict = item.get("response") or {}
            output_text = resp_dict.get("output")
            if output_text is not None:
                output_text = redact_secrets(str(output_text))

            grading_res = item.get("gradingResult") or {}
            reason_str = grading_res.get("reason")
            if reason_str:
                reason_str = redact_secrets(str(reason_str))

            latency_ms = item.get("latencyMs")

            # Extract assertions
            assertions: list[PromptfooAssertionResult] = []
            component_results = grading_res.get("componentResults") or []
            for cr in component_results:
                a_info = cr.get("assertion") or {}
                assertions.append(
                    PromptfooAssertionResult(
                        type=str(a_info.get("type", "unknown")),
                        value=str(a_info.get("value")) if a_info.get("value") is not None else None,
                        passed=bool(cr.get("pass", False)),
                        reason=redact_secrets(str(cr.get("reason", ""))) if cr.get("reason") else None,
                    )
                )

            parsed_items.append(
                PromptfooTestResultItem(
                    name=desc,
                    prompt=prompt_str,
                    passed=item_success,
                    score=score,
                    reason=reason_str,
                    latency_ms=latency_ms,
                    output=output_text,
                    assertions=assertions,
                )
            )

        # Distinguish completed runs (even if some assertions failed) from infrastructure failures
        run_status = "completed"

        return PromptfooEvaluationResponse(
            status=run_status,
            total_tests=total_tests,
            passed=successes,
            failed=failures + errors,
            results=parsed_items,
            duration_seconds=duration,
            assistant_name=assistant_name,
            assistant_version=assistant_version or version,
            error=None,
        )

    except Exception as e:
        logger.exception("Unexpected error during Promptfoo evaluation: %s", e)
        return PromptfooEvaluationResponse(
            status="error",
            total_tests=0,
            passed=0,
            failed=0,
            results=[],
            duration_seconds=round(time.perf_counter() - start_time, 2),
            assistant_name=assistant_name,
            assistant_version=assistant_version or version,
            error=redact_secrets(str(e)),
        )
    finally:
        # Clean up temporary directory and files
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
