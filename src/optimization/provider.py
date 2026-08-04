from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProviderConfig:
    provider: str
    generation_model: str
    optimization_model: str


def _qualified_model(provider: str, model: str) -> str:
    model = model.strip()
    if not model:
        raise RuntimeError("LLM_MODEL cannot be empty")

    if provider == "openai":
        if model.startswith("openai/"):
            return model
        if "/" in model:
            raise RuntimeError(
                "LLM_MODEL must be an OpenAI model when LLM_PROVIDER=openai"
            )
        return f"openai/{model}"

    if model.startswith("vertex_ai/"):
        return model
    if "/" in model:
        raise RuntimeError(
            "LLM_MODEL must be a Vertex AI model when LLM_PROVIDER=vertex_ai"
        )
    return f"vertex_ai/{model}"


def resolve_model_provider(
    environ: Mapping[str, str] | None = None,
) -> ModelProviderConfig:
    """Resolve one provider/model choice for CoverUp and GEPA.

    LLM_PROVIDER and LLM_MODEL are the preferred configuration. The older
    COVERUP_MODEL and OPTIMIZE_MODEL variables remain supported only when
    LLM_PROVIDER is absent.
    """

    env = os.environ if environ is None else environ
    raw_provider = env.get("LLM_PROVIDER", "").strip().lower()

    if not raw_provider:
        generation_model = env.get("COVERUP_MODEL", "").strip()
        optimization_model = env.get("OPTIMIZE_MODEL", "").strip()
        if generation_model and optimization_model:
            provider = (
                "openai"
                if generation_model.startswith("openai/")
                else "vertex_ai"
                if generation_model.startswith("vertex_ai/")
                else "legacy"
            )
            return ModelProviderConfig(
                provider=provider,
                generation_model=generation_model,
                optimization_model=optimization_model,
            )
        if env.get("OPENAI_API_KEY", "").strip():
            raw_provider = "openai"
        elif (
            env.get("VERTEXAI_PROJECT", "").strip()
            and env.get("VERTEXAI_LOCATION", "").strip()
        ):
            raw_provider = "vertex_ai"
        else:
            raise RuntimeError(
                "Configure LLM_PROVIDER and LLM_MODEL in .env. When "
                "OPENAI_API_KEY is present, the pipeline automatically uses "
                "OpenAI with gpt-4o-mini. Legacy COVERUP_MODEL and "
                "OPTIMIZE_MODEL are also supported when both are set."
            )

    aliases = {
        "openai": "openai",
        "vertex": "vertex_ai",
        "vertex_ai": "vertex_ai",
    }
    try:
        provider = aliases[raw_provider]
    except KeyError as error:
        raise RuntimeError(
            "LLM_PROVIDER must be one of: openai, vertex_ai"
        ) from error

    if provider == "openai":
        if not env.get("OPENAI_API_KEY", "").strip():
            raise RuntimeError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
            )
        default_model = "gpt-4o-mini"
    else:
        if not env.get("VERTEXAI_PROJECT", "").strip():
            raise RuntimeError(
                "VERTEXAI_PROJECT is required when LLM_PROVIDER=vertex_ai"
            )
        if not env.get("VERTEXAI_LOCATION", "").strip():
            raise RuntimeError(
                "VERTEXAI_LOCATION is required when LLM_PROVIDER=vertex_ai"
            )
        default_model = "gemini-3.6-flash"

    model = _qualified_model(
        provider, env.get("LLM_MODEL", default_model)
    )
    return ModelProviderConfig(
        provider=provider,
        generation_model=model,
        optimization_model=model,
    )
