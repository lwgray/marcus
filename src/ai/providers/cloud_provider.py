"""
Cloud LLM Provider for Marcus AI.

Generic OpenAI-compatible cloud provider. Works with any service that
exposes an OpenAI-style ``/chat/completions`` endpoint — Fireworks AI,
Groq, Together AI, Mistral, DeepSeek, and others.

Classes
-------
CloudLLMProvider
    Cloud model provider for OpenAI-compatible hosted inference APIs

Examples
--------
>>> provider = CloudLLMProvider(
...     model="accounts/fireworks/models/qwen2p5-coder-7b-instruct",
...     api_key="fw_abc123",  # pragma: allowlist secret
...     url="https://api.fireworks.ai/inference/v1",
... )
>>> result = await provider.analyze_task(task, context)
"""

import logging
from typing import Optional

import httpx

from .local_provider import LocalLLMProvider, _strip_reasoning_blocks

logger = logging.getLogger(__name__)


class CloudLLMProvider(LocalLLMProvider):
    """Generic cloud LLM provider for OpenAI-compatible hosted APIs.

    Inherits all semantic-analysis business logic from ``LocalLLMProvider``
    and overrides the transport layer only: the HTTP client is pointed at
    an explicit remote URL with a required API key.  The Ollama native-API
    fallback present in the parent is intentionally omitted — cloud
    endpoints do not implement it.

    Parameters
    ----------
    model : str
        Full model identifier as expected by the remote service
        (e.g. ``"accounts/fireworks/models/qwen2p5-coder-7b-instruct"``).
    api_key : str
        Bearer token for the remote service.
    url : str
        Base URL of the OpenAI-compatible inference endpoint
        (e.g. ``"https://api.fireworks.ai/inference/v1"``).

    Raises
    ------
    ValueError
        If ``model``, ``api_key``, or ``url`` is empty.
    """

    def __init__(self, model: str, api_key: str, url: str) -> None:
        """Initialize cloud LLM provider.

        Parameters
        ----------
        model : str
            Model identifier for the remote service.
        api_key : str
            Bearer token — must not be empty.
        url : str
            Base URL for the OpenAI-compatible API — must not be empty.
        """
        if not model:
            raise ValueError("CloudLLMProvider requires a non-empty model name")
        if not api_key:
            raise ValueError("CloudLLMProvider requires a non-empty api_key")
        if not url:
            raise ValueError("CloudLLMProvider requires a non-empty cloud_url")

        # Pull global settings (temperature, max_tokens) from config; skip
        # LocalLLMProvider.__init__ entirely because it reads local_model /
        # local_url / local_key — none of which apply here.
        from src.config.marcus_config import get_config

        config = get_config()

        self.base_url: str = url
        self.model: str = model
        self.max_tokens: int = config.ai.max_tokens
        self.temperature: float = config.ai.temperature
        # Cloud APIs respond faster than local inference
        self.timeout: float = 60.0

        self.client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=self.timeout,
            base_url=url,
        )

        logger.info("Cloud LLM provider initialized: model=%s url=%s", model, url)

    async def _call_cloud_llm(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Make a request to the cloud OpenAI-compatible endpoint.

        Unlike ``LocalLLMProvider._call_local_llm``, this method does NOT
        fall back to the Ollama native API on a 404; cloud services are not
        Ollama and a 404 is always an error.

        Parameters
        ----------
        prompt : str
            User prompt to send.
        max_tokens : int, optional
            Token budget; defaults to ``self.max_tokens`` from config.
        temperature : float, optional
            Sampling temperature; defaults to ``self.temperature`` from config.

        Returns
        -------
        str
            Decoded model response with leading ``<think>`` blocks stripped.

        Raises
        ------
        Exception
            On any HTTP or network error.
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
        if temperature is None:
            temperature = self.temperature

        request_data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant helping with software "
                        "development task analysis. Provide clear, structured "
                        "responses focusing on practical implementation details."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        try:
            response = await self.client.post("/chat/completions", json=request_data)
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise Exception(f"Expected string response, got {type(content)}")
            return _strip_reasoning_blocks(content)

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Cloud LLM API error: {e.response.status_code} - " f"{e.response.text}"
            )
        except Exception:
            logger.error("Cloud LLM call failed for model %s", self.model)
            raise

    # Override the internal dispatch used by all inherited business methods
    async def _call_local_llm(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> str:
        """Delegate to ``_call_cloud_llm``.

        ``LocalLLMProvider`` routes all LLM calls through this method.
        We override it here so every inherited business method
        (``analyze_task``, ``infer_dependencies``, etc.) transparently uses
        the cloud endpoint instead of a local server.
        """
        return await self._call_cloud_llm(
            prompt, max_tokens=max_tokens, temperature=temperature
        )
