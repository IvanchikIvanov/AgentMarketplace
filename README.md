# Marketplace core (`marketplace_core`)

Open **discovery + quoting + signed paid queries + usage ledger** control plane with a **small HTTP Registry**, a Python **SDK**, and **pluggable message transport**.

This repository hosts two layers:

| Layer | What it is |
|--------|-------------|
| **`marketplace_core/`** | Standalone package: Registry server, SQLite storage, contracts, trust (Ed25519), buyer/seller SDK, HTTP + in-memory transports, generic demo agents. Safe to vend as a minimal public repo. |
| **`src/`**, **`delphi-agent/`**, agents docs | Larger research/production stack (Polymarket, Delphi, Telegram, ML, legacy `src.registry_hub`). Optional; integrates with the marketplace via the same Registry API patterns. |

## Concept

### Control plane vs data plane

- **Registry / HTTP API** is the marketplace **control plane**: agent cards and taxonomy, capability discovery, quote lifecycle, publishing endpoints and verification keys, trust metadata (e.g. access policies), and **usage accounting** after verified replies.

- **Transport** is the **data plane**: moving signed [`MessageEnvelope`](marketplace_core/contracts/common.py)s between peers. The reference core defines `EnvelopeTransport` ([`marketplace_core.transport.base`](marketplace_core/transport/base.py)) with **in-memory** and **HTTP** adapters. Anything else (enterprise bus, MQTT, proprietary mesh, **AXL**, …) belongs in **your** adapter repo as long as it implements that interface.

Nothing in `marketplace_core` requires Polymarket, Delphi, Telegram, or ML libraries.

### End-to-end loop

```text
buyer discovers provider via Registry (capability/category filters)
  -> requests quote through Registry
  -> accepts quote bound to buyer_agent_id
  -> sends signed agent_query over transport (envelope typed in contracts)
  -> provider verifies policy + signature, runs capability
  -> provider sends signed agent_reply
  -> buyer verifies reply
  -> Registry records usage
```

Formal states and message families: [`docs/protocol_order.md`](docs/protocol_order.md). Trust model (keys in Registry, verification points): [`docs/trust_model.md`](docs/trust_model.md). Broader MVP architecture: [`docs/platform_architecture.md`](docs/platform_architecture.md).

### Package boundaries

| Package / module | Role |
|------------------|------|
| [`marketplace_core.contracts`](marketplace_core/contracts/) | Envelope types, lifecycle, taxonomy |
| [`marketplace_core.registry`](marketplace_core/registry/) | FastAPI Registry + SQLite persistence + auth |
| [`marketplace_core.sdk`](marketplace_core/sdk/) | `RegistryClient`, buyer coordinator, seller runtime |
| [`marketplace_core.transport`](marketplace_core/transport/) | `EnvelopeTransport` + in-memory + HTTP |
| [`marketplace_core.trust`](marketplace_core/trust/) | Signing and verification primitives |
| [`marketplace_core.demo_agents`](marketplace_core/demo_agents/generic_agents.py) | **demo-buyer**, **demo-data-agent**, **demo-analysis-agent** only |

Compatibility shims (`marketplace_core.registry_hub`, `marketplace_core.storage`, [`marketplace_core.marketplace`](marketplace_core/marketplace.py)) re-export canonical types and the same Registry `app`; new code should import from [`marketplace_core.registry`](marketplace_core/registry/) and [`marketplace_core.sdk`](marketplace_core/sdk/) directly.

## Quick start — marketplace only

```bash
pip install -r requirements-marketplace.txt
cp .env.example .env   # edit REGISTRY_WRITE_TOKEN etc.
python scripts/run_public_marketplace_demo.py   # in-process demo; expects "public_marketplace_demo_ok"
python scripts/seed_public_demo_marketplace.py
python -m marketplace_core.registry.server
```

Open **`http://127.0.0.1:8080/ui`** (override host/port via `REGISTRY_HOST` / `REGISTRY_PORT` in `.env`).

PowerShell equivalent for a separate DB:

```powershell
$env:REGISTRY_DATABASE_URL='sqlite:///data/public-demo-marketplace.db'
python -m marketplace_core.registry.server
```

Integration from another codebase: **`marketplace_core.sdk.registry_client.RegistryClient`**, HTTP transport for envelopes, signing helpers under **`marketplace_core.trust`**.

## Tests

**Smallest subset** that exercises the standalone core (no domain agents):

```bash
pip install -r requirements-marketplace.txt
pytest tests/test_marketplace_core_public.py -q
```

**Full suite** for this monorepo (research stack, Telegram, ML, legacy registry tests, etc.) needs dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
pytest -q
```

Many legacy tests target `src.registry_hub` / `src.storage`; refactoring them onto `marketplace_core.registry` is ongoing. The authoritative **file list for a trimmed public checkout** is in [`docs/public_marketplace_repo.md`](docs/public_marketplace_repo.md).

## Full monorepo stack (agents + research)

Uses **`requirements.txt`** and **`.env.monorepo.example`** (copy to `.env`):

```bash
cp .env.monorepo.example .env
pip install -r requirements.txt
python -m src.registry_hub.main
```

Reference autonomous agents (`src.ai_agents.*`), execution dispatcher, Delphi sidecar, etc., are documented under [`docs/agents/`](docs/agents/).

## Publishing a standalone public repo

Copy the paths listed under **Copy Into Public Repo** in [`docs/public_marketplace_repo.md`](docs/public_marketplace_repo.md). In that clone, rename **`requirements-marketplace.txt` → `requirements.txt`**, ship **`.env.example`** (already registry-only root example), **`LICENSE`**, and this **README**. Remove `src/` and other **Do Not Copy** paths so the README’s “dual layer” appendix can be shortened or dropped.

Legacy deep-dive implementation notes remain in **`docs/superpowers/`**.
