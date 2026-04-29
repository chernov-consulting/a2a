"""Versioned, runnable payment protocol samples.

Each sub-package (ap2, mcp, a2a_proto, x402, ucp) contains:
  - README.md   — one-page how-it-works and spec reference
  - models.py   — Pydantic models for this protocol's messages
  - bench.py    — run a toy purchase and emit a standard ledger record
  - spec/       — versioned snapshots of the relevant specification
"""

from __future__ import annotations
