"""Typed exception hierarchy for the a2a package."""

from __future__ import annotations


class A2AError(Exception):
    """Base exception for all a2a errors."""


class ConfigError(A2AError):
    """Invalid or missing configuration."""


class CatalogError(A2AError):
    """Failed to fetch or parse a product catalog."""


class LLMError(A2AError):
    """LLM call failed or returned an unparseable response."""


class NegotiationError(A2AError):
    """Error during agent negotiation."""


class ReportError(A2AError):
    """Failed to generate a report."""
