from __future__ import annotations

import time
from dataclasses import dataclass

from structlog.contextvars import get_contextvars

from . import metrics
from .logging_config import get_logger
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .prompt_management import ResolvedPrompt, resolve_prompt
from .tracing import get_langfuse_client, observe, tracing_enabled

log = get_logger()


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


@dataclass
class GenerationStep:
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe(name="agent_run", as_type="span", capture_input=False, capture_output=False)
    def run(self, user_id: str, feature: str, session_id: str, message: str) -> AgentResult:
        started = time.perf_counter()
        langfuse_client = get_langfuse_client()
        current_observation = getattr(langfuse_client, "get_current_observation_id", None)
        is_observed = False
        if callable(current_observation):
            try:
                is_observed = bool(current_observation())
            except Exception:
                is_observed = False

        retrieval_started = time.perf_counter()
        retrieve_step = self._retrieve if is_observed else self._retrieve.__wrapped__
        docs = retrieve_step(self, message) if not is_observed else retrieve_step(message)
        retrieval_latency_ms = int((time.perf_counter() - retrieval_started) * 1000)
        if "correlation_id" in get_contextvars():
            log.info(
                "retrieval_completed",
                service="agent",
                tool_name="mock_rag",
                latency_ms=retrieval_latency_ms,
                payload={"doc_count": len(docs)},
            )
        prompt = resolve_prompt(
            langfuse_client,
            feature=feature,
            docs=docs,
            message=message,
            enabled=tracing_enabled(),
        )
        generate_step = self._generate if is_observed else self._generate.__wrapped__
        generation = (
            generate_step(prompt, message, docs)
            if is_observed
            else generate_step(self, prompt, message, docs)
        )
        quality_score = self._heuristic_quality(message, generation.text, docs)
        latency_ms = int((time.perf_counter() - started) * 1000)

        langfuse_client.update_current_trace(
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model],
            metadata={
                "prompt_name": prompt.name,
                "prompt_label": prompt.label,
                "prompt_version": prompt.version,
                "prompt_source": prompt.source,
            },
        )

        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=generation.cost_usd,
            tokens_in=generation.tokens_in,
            tokens_out=generation.tokens_out,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=generation.text,
            latency_ms=latency_ms,
            tokens_in=generation.tokens_in,
            tokens_out=generation.tokens_out,
            cost_usd=generation.cost_usd,
            quality_score=quality_score,
        )

    @observe(name="rag_retrieval", as_type="span", capture_input=False, capture_output=False)
    def _retrieve(self, message: str) -> list[str]:
        return retrieve(message)

    @observe(name="llm_generation", as_type="generation", capture_input=False, capture_output=False)
    def _generate(self, prompt: ResolvedPrompt, message: str, docs: list[str]) -> GenerationStep:
        started = time.perf_counter()
        response = self.llm.generate(prompt.text)
        generation_latency_ms = int((time.perf_counter() - started) * 1000)
        cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)

        get_langfuse_client().update_current_generation(
            model=self.model,
            metadata={
                "doc_count": len(docs),
                "query_preview": summarize_text(message),
                "prompt_name": prompt.name,
                "prompt_label": prompt.label,
                "prompt_version": prompt.version,
                "prompt_source": prompt.source,
                "prompt_fetch_error": prompt.fetch_error,
            },
            usage_details={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
            cost_details={"total": cost_usd},
            prompt=prompt.managed_prompt,
        )
        if "correlation_id" in get_contextvars():
            log.info(
                "generation_completed",
                service="agent",
                latency_ms=generation_latency_ms,
                tokens_in=response.usage.input_tokens,
                tokens_out=response.usage.output_tokens,
                cost_usd=cost_usd,
                payload={
                    "prompt_name": prompt.name,
                    "prompt_label": prompt.label,
                    "prompt_version": prompt.version,
                    "prompt_source": prompt.source,
                },
            )
        return GenerationStep(
            text=response.text,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            latency_ms=generation_latency_ms,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * 3
        output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)
