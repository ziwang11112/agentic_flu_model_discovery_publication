from __future__ import annotations

from src.selection.iterative_agent_feedback import prompt_audit_row
from src.selection.provider_registry import configured_providers


def test_provider_prompt_audit_catches_test_metric_injection() -> None:
    row = prompt_audit_row(
        series_name="0-4 yr",
        proposer_type="openai_gpt_iterative",
        round_idx=1,
        prompt_payload={"context": {"test_mae": 0.1}},
        feedback_context={"previous_round": {"test_rank": 1}},
        model_allowlist=["last_observed"],
    )

    assert row["safe_prompt_passed"] is False
    assert row["safe_feedback_passed"] is False


def test_missing_credentials_skip_gracefully(monkeypatch) -> None:
    for key in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)
    regs = configured_providers({"providers": [{"name": "openai_gpt"}, {"name": "deepseek"}]})

    assert all(not reg.available for reg in regs)
    assert all(reg.skip_reason.startswith("missing_env") for reg in regs)
