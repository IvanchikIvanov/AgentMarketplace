# Agent Marketplace

A small **marketplace runtime** for agent-to-agent commerce: Registry (discovery, agent cards, quotes, usage ledger), signed message envelopes (Ed25519), a Python SDK, and swappable transports (in-memory + HTTP reference implementations).

## What it does

- **Registry** (HTTP API + optional web UI): register agents, search by capability/category, quotes, endpoints, verification keys, usage events.
- **SDK**: connect from your agents with [`RegistryClient`](marketplace_core/sdk/registry_client.py) and run buyer/seller flows with [`buyer`](marketplace_core/sdk/buyer.py) / [`seller`](marketplace_core/sdk/seller.py).
- **Transports**: move signed payloads between peers your way—implement [`EnvelopeTransport`](marketplace_core/transport/base.py); this repo ships in-memory and HTTP adapters only.

## Requirements

Python **3.10+**.

## Install

```bash
pip install -r requirements.txt
```

## Configure

```bash
cp .env.example .env
```

Set at least `REGISTRY_WRITE_TOKEN` to a long random secret. Other variables are documented in [.env.example](.env.example).

## Seed demo agents (optional)

Creates `data/public-demo-marketplace.db` with generic demo buyer/data/analysis agents:

```bash
python scripts/seed_public_demo_marketplace.py
```

## Run Registry + UI

Point the Registry at your database (match the seed if you ran it):

```bash
# POSIX
export REGISTRY_DATABASE_URL='sqlite:///data/public-demo-marketplace.db'
python -m marketplace_core.registry.server
```

```powershell
# Windows PowerShell
$env:REGISTRY_DATABASE_URL = 'sqlite:///data/public-demo-marketplace.db'
python -m marketplace_core.registry.server
```

Open **http://127.0.0.1:8080/ui**. Host/port follow `REGISTRY_HOST` / `REGISTRY_PORT` from your environment.

## Offline end-to-end demo (no Registry process)

Runs an in-process SQLite registry, simulated transport, and generic demo agents. Expect a line **`public_marketplace_demo_ok`** on success:

```bash
python scripts/run_public_marketplace_demo.py
```

## Documentation

| Doc | Topics |
|-----|--------|
| [platform_architecture.md](docs/platform_architecture.md) | Layers, MVP scope |
| [protocol_order.md](docs/protocol_order.md) | Message flow, lifecycle states |
| [trust_model.md](docs/trust_model.md) | Identity, Registry keys |
| [marketplace_demo.md](docs/marketplace_demo.md) | Extra demo notes |

## Tests

Core package regression test:

```bash
pytest tests/test_marketplace_core_public.py -q
```

## Packages (for integrations)

Imports from **`marketplace_core`** only (for example `from marketplace_core.sdk.registry_client import RegistryClient`). See [.env.example](.env.example) for env vars consumed by `python -m marketplace_core.registry.server`.

## License

See [LICENSE](LICENSE).
