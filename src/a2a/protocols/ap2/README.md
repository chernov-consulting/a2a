# AP2 — Agent Payments Protocol

> **Layer:** Authorization (IMF three-layer model, Layer 2)
> **Version implemented:** Draft 2025-Q4
> **Spec reference:** See `spec/ap2-draft-2025-q4.md`

## What it does

AP2 binds agent-initiated actions to cryptographically verifiable mandates.
A **mandate** is a JSON document signed by the principal (the human or institution
on whose behalf the agent acts) that specifies:

- **Scope:** which product categories and vendors the agent may transact with
- **Limits:** maximum spend per transaction, per day, and per month
- **Identity:** the agent's public key and a revocation endpoint
- **Expiry:** ISO-8601 timestamp after which the mandate is void

The seller verifies the mandate signature before executing any payment instruction.
Settlement (Layer 3) only proceeds if the mandate is valid and the requested amount
is within scope.

## Key insight for the article

AP2 is the "Know Your Agent" (KYA) framework in practice.
Compare it to KYC: instead of verifying a human's passport,
you verify the agent's cryptographic credentials and spending authority.
A mandate that expires, is revoked, or is over-limit is equivalent to
a declined card — clean, auditable, legally attributable.

**What AP2 doesn't solve:** if the agent's mandate is vague ("buy the best option
for our observability stack"), the scope check passes but the agent still
has probabilistic freedom over which product it selects.
The accountability gap is in the mandate scope, not the protocol.

## Running the benchmark

```bash
uv run a2a bench ap2
```

Output: one JSONL ledger record appended to stdout (or `--output <file>`).

## Protocol flow

```
Agent                           Seller
  |                               |
  |--- MandateRequest ---------->|
  |    (signed mandate JSON)      |
  |                               |
  |<-- MandateChallenge ---------|
  |    (nonce)                    |
  |                               |
  |--- ChallengeResponse ------->|
  |    (signed nonce)             |
  |                               |
  |<-- AuthorizationToken -------|
  |    (scoped, time-limited)     |
  |                               |
  |--- PurchaseRequest -------->|
  |    (product + price + token)  |
  |                               |
  |<-- PurchaseConfirmation -----|
  |    (or Rejection + reason)    |
```
