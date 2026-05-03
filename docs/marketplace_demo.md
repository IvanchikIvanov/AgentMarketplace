# Marketplace Local Demo

This demo proves the core marketplace loop without requiring a live AXL node or a running Registry API process.

## Pure Local Demo

Run:

```bash
python scripts/run_marketplace_demo.py
```

The script:

1. Creates an isolated SQLite database under `data/demo-marketplace*.db`.
2. Registers `agent-polymarket` as buyer.
3. Registers `agent-trader` as provider of `risk_review`.
4. Publishes an active local endpoint for the seller.
5. Creates buyer and seller signing keys.
6. Runs discover, quote, accept and signed `agent_query`.
7. Simulates a signed seller `agent_reply`.
8. Verifies the reply and records usage.

Expected output:

```text
marketplace_demo_ok
quote_id=...
correlation_id=...
usage_id=...
```

## Live-Service Shape

For a service-based run, start components in separate terminals:

```bash
python -m src.registry_hub.main
python -m src.ai_agents.trader_agent
python -m src.ai_agents.polymarket_agent
```

The live-service shape requires configured `.env` values for AXL and signing keys. AXL transports messages only; Registry/API owns discovery, keys, quotes and usage accounting.
