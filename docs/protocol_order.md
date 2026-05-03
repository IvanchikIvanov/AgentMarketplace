# Protocol Order

## Startup

```text
agent starts
  -> load config/env
  -> initialize owner_id and agent_id
  -> connect to AXL
  -> register agent card in Registry
  -> publish active endpoint
  -> publish active public key
  -> heartbeat
```

## Marketplace Query

```text
buyer chooses capability
  -> discover provider in Registry
  -> request quote
  -> accept quote with buyer_agent_id
  -> send signed agent_query through AXL
  -> provider verifies signature and policy
  -> provider runs capability tool
  -> provider sends signed agent_reply
  -> buyer verifies seller signature
  -> Registry records usage event
```

The enforced marketplace states are:

```text
discovered
quote_requested
quote_accepted
query_sent
reply_received
usage_recorded
failed
```

## Action Lifecycle

```text
agent_intent
  -> optional peer risk review or counter analysis
  -> agent_request_confirmation when required
  -> signed agent_action_request
  -> execution policy gate
  -> agent_action_result or agent_execution_veto
```

Live action requests are rejected by default. Dry-run actions can return `agent_action_result`.

## Message Families

- Knowledge: `agent_query`, `agent_reply`, `agent_observation`, `agent_hypothesis`, `agent_risk_alert`, `agent_confidence_update`, `agent_summary`, `agent_counter_analysis`.
- Commercial: `agent_quote_request`, `agent_quote`, `agent_usage_receipt`.
- Action: `agent_intent`, `agent_action_request`, `agent_action_result`, `agent_execution_veto`, `agent_request_confirmation`.
- Control: `agent_heartbeat`, `agent_capability_announce`, `agent_policy_update`.
