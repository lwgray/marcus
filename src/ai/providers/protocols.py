"""
Structural typing protocols for LLM-client surfaces.

Marcus's :class:`LLMAbstraction` is the concrete implementation, but
many call sites (and most test doubles) only care about a tiny slice
of its interface — typically just :py:meth:`analyze`. Defining a
narrow :class:`typing.Protocol` for that slice lets:

- Production code type-annotate its dependency as ``LLMAnalyzeClient``
  rather than the whole concrete class, decoupling consumers from
  the abstraction's full surface area.
- Tests build mocks (``MagicMock(spec=LLMAnalyzeClient)``) that pin
  the contract at construction time — when a new kwarg is added to
  ``analyze``, mypy and pyright flag every offending mock instead of
  the change quietly slipping past.

Why a separate module
---------------------
``llm_abstraction.py`` imports providers (which import HTTP clients,
config, etc.) at module load. Tests and lightweight consumers
shouldn't pay that cost just to type-check the call surface. This
module has no runtime dependencies beyond stdlib so it's safe to
import from anywhere — including tests that don't have API keys
configured.

Kaia review on the operation-taxonomy PR flagged the
``**kwargs``-fan-out fragility we hit when adding the ``operation``
kwarg to ``analyze``: every test mock needed updating. A Protocol
fixes that root cause rather than patching individual call sites.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMAnalyzeClient(Protocol):
    """Minimum surface for callers of ``analyze()``.

    Implementations must provide an awaitable :py:meth:`analyze` that
    accepts ``(prompt, context)`` positionally and ``operation`` as a
    keyword-only argument. :class:`LLMAbstraction` is the canonical
    production implementation; tests can use
    ``unittest.mock.MagicMock(spec=LLMAnalyzeClient)`` to build a
    typed double.

    The ``runtime_checkable`` decorator allows ``isinstance(obj,
    LLMAnalyzeClient)`` checks for defensive code paths, though most
    callers should rely on the static type checker.
    """

    async def analyze(
        self,
        prompt: str,
        context: Any,
        *,
        operation: Optional[str] = None,
    ) -> str:
        """Run the prompt through the active provider and return text.

        Parameters
        ----------
        prompt : str
            Prompt text to send to the LLM.
        context : Any
            Arbitrary caller-provided context. Implementations may
            inspect ``context.max_tokens`` to override the provider's
            configured default; everything else is opaque.
        operation : str, optional
            Operation key from :mod:`src.cost_tracking.operations` so
            the resulting ``token_events`` row carries a meaningful
            label for the cost dashboard. ``None`` falls through to
            whatever default the provider stamps.

        Returns
        -------
        str
            Raw text response from the LLM.
        """
        ...
