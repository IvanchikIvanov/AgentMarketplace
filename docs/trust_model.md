# Trust Model

## Identity

- `owner_id` identifies the owner/account in Registry.
- `agent_id` identifies the logical autonomous agent.
- `axl_peer_id` identifies one transport endpoint for an agent.

One owner can have many agents. One agent can have many endpoints. Endpoint rotation must not change `agent_id`.

## Signing Keys

Registry is the source of truth for agent public keys.

Supported key statuses:

- `active`: verifies current messages.
- `next`: verifies messages during key rotation.
- `retired`: verifies only messages created before `rotated_at`.

Paid `agent_query` messages and marketplace usage-producing replies require signatures.

## Verification Points

- Agent runtime verifies signed inbound paid queries before executing paid capabilities.
- Marketplace coordinator verifies signed seller replies before recording usage.
- ExecutionAgent verifies signed action requests before policy evaluation.

## Access and Abuse

Peer approvals support `approved_only` access policies. When a caller is supplied during discovery, approved-only providers are visible only to approved peers.

Abuse reports record reporter agent, target agent, target owner, reason and payload. Reputation is tracked separately for owner and agent.
