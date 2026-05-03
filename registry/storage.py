from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class MarketplaceStorage:
    """SQLite storage for the marketplace control plane only."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _migrate(self) -> None:
        migrations = [
            self._registry_tables(),
            self._marketplace_tables(),
        ]
        with self._conn() as conn:
            for sql in migrations:
                for stmt in [part.strip() for part in sql.split(";") if part.strip()]:
                    try:
                        conn.execute(stmt)
                    except sqlite3.OperationalError as exc:
                        if "duplicate column name" not in str(exc).lower():
                            raise

    @staticmethod
    def _registry_tables() -> str:
        return """
            CREATE TABLE IF NOT EXISTS owner_registry (
                owner_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_registry (
                agent_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                visibility_mode TEXT NOT NULL DEFAULT 'public',
                access_policy TEXT NOT NULL DEFAULT 'public',
                pricing_mode TEXT NOT NULL DEFAULT 'free',
                policy_summary TEXT,
                reputation_agent REAL NOT NULL DEFAULT 0,
                reputation_owner REAL NOT NULL DEFAULT 0,
                last_seen_at INTEGER,
                supported_protocol_versions TEXT NOT NULL DEFAULT '["2"]',
                supported_transport_modes TEXT NOT NULL DEFAULT '["axl"]',
                rate_limits TEXT NOT NULL DEFAULT '{}',
                compliance_tags TEXT NOT NULL DEFAULT '[]',
                pricing_policy TEXT NOT NULL DEFAULT '{}',
                capabilities_schema TEXT NOT NULL DEFAULT '{}',
                provenance_policy TEXT NOT NULL DEFAULT '{}',
                trust_summary TEXT NOT NULL DEFAULT '{}',
                primary_category TEXT NOT NULL DEFAULT '',
                secondary_categories TEXT NOT NULL DEFAULT '[]',
                service_types TEXT NOT NULL DEFAULT '[]',
                domains TEXT NOT NULL DEFAULT '[]',
                risk_level TEXT NOT NULL DEFAULT 'informational',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(owner_id) REFERENCES owner_registry(owner_id)
            );
            CREATE INDEX IF NOT EXISTS idx_agent_registry_owner ON agent_registry(owner_id);
            CREATE INDEX IF NOT EXISTS idx_agent_registry_status ON agent_registry(status, visibility_mode);
            CREATE INDEX IF NOT EXISTS idx_agent_registry_primary_category
                ON agent_registry(primary_category, status, visibility_mode);
            CREATE INDEX IF NOT EXISTS idx_agent_registry_risk_level
                ON agent_registry(risk_level, status, visibility_mode);

            CREATE TABLE IF NOT EXISTS agent_transport_endpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                axl_peer_id TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'axl',
                priority INTEGER NOT NULL DEFAULT 100,
                region TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                last_seen_at INTEGER,
                metadata TEXT NOT NULL DEFAULT '{}',
                UNIQUE(agent_id, axl_peer_id),
                FOREIGN KEY(agent_id) REFERENCES agent_registry(agent_id)
            );
            CREATE INDEX IF NOT EXISTS idx_agent_endpoints_lookup
                ON agent_transport_endpoints(agent_id, mode, active, priority ASC);

            CREATE TABLE IF NOT EXISTS agent_signing_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                key_id TEXT NOT NULL,
                public_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at INTEGER NOT NULL,
                rotated_at INTEGER,
                metadata TEXT NOT NULL DEFAULT '{}',
                UNIQUE(agent_id, key_id),
                FOREIGN KEY(agent_id) REFERENCES agent_registry(agent_id)
            );
            CREATE INDEX IF NOT EXISTS idx_agent_keys_lookup ON agent_signing_keys(agent_id, status);

            CREATE TABLE IF NOT EXISTS agent_peer_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_agent_id TEXT NOT NULL,
                target_agent_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'approved',
                updated_at INTEGER NOT NULL,
                UNIQUE(source_agent_id, target_agent_id)
            );

            CREATE TABLE IF NOT EXISTS agent_abuse_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_agent_id TEXT,
                target_agent_id TEXT,
                target_owner_id TEXT,
                reason TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'open',
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_reputation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                owner_id TEXT,
                score_delta REAL NOT NULL,
                reason TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_agent_reputation_agent
                ON agent_reputation_events(agent_id, created_at DESC);
        """

    @staticmethod
    def _marketplace_tables() -> str:
        return """
            CREATE TABLE IF NOT EXISTS agent_quotes (
                quote_id TEXT PRIMARY KEY,
                seller_agent_id TEXT NOT NULL,
                buyer_agent_id TEXT NOT NULL,
                capability TEXT NOT NULL,
                pricing_mode TEXT NOT NULL,
                estimated_cost REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                units REAL NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'quoted',
                request_payload TEXT NOT NULL DEFAULT '{}',
                terms TEXT NOT NULL DEFAULT '{}',
                expires_at INTEGER NOT NULL,
                accepted_at INTEGER,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(seller_agent_id) REFERENCES agent_registry(agent_id)
            );
            CREATE INDEX IF NOT EXISTS idx_agent_quotes_seller ON agent_quotes(seller_agent_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_agent_quotes_buyer ON agent_quotes(buyer_agent_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS agent_usage_events (
                usage_id TEXT PRIMARY KEY,
                quote_id TEXT,
                buyer_agent_id TEXT NOT NULL,
                seller_agent_id TEXT NOT NULL,
                buyer_owner_id TEXT,
                seller_owner_id TEXT,
                capability TEXT NOT NULL,
                message_type TEXT NOT NULL,
                units REAL NOT NULL DEFAULT 1,
                cost REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL DEFAULT 'recorded',
                request_id TEXT,
                correlation_id TEXT,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_agent_usage_seller ON agent_usage_events(seller_agent_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_agent_usage_buyer ON agent_usage_events(buyer_agent_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_agent_usage_owner ON agent_usage_events(seller_owner_id, created_at DESC);
        """

    def upsert_owner(self, *, owner_id: str, display_name: str = "", metadata: dict[str, Any] | None = None) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO owner_registry(owner_id, display_name, metadata)
                VALUES (?,?,?)
                ON CONFLICT(owner_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (owner_id, display_name, json.dumps(metadata or {}, ensure_ascii=False)),
            )

    def upsert_agent_registry(
        self,
        *,
        owner_id: str,
        agent_id: str,
        display_name: str,
        description: str = "",
        status: str = "draft",
        visibility_mode: str = "public",
        access_policy: str = "public",
        pricing_mode: str = "free",
        policy_summary: str | None = None,
        supported_protocol_versions: list[str] | None = None,
        supported_transport_modes: list[str] | None = None,
        rate_limits: dict[str, Any] | None = None,
        compliance_tags: list[str] | None = None,
        pricing_policy: dict[str, Any] | None = None,
        capabilities_schema: dict[str, Any] | None = None,
        provenance_policy: dict[str, Any] | None = None,
        trust_summary: dict[str, Any] | None = None,
        primary_category: str = "",
        secondary_categories: list[str] | None = None,
        service_types: list[str] | None = None,
        domains: list[str] | None = None,
        risk_level: str = "informational",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.upsert_owner(owner_id=owner_id)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_registry(
                    agent_id, owner_id, display_name, description, status, visibility_mode,
                    access_policy, pricing_mode, policy_summary, supported_protocol_versions,
                    supported_transport_modes, rate_limits, compliance_tags, pricing_policy,
                    capabilities_schema, provenance_policy, trust_summary, primary_category,
                    secondary_categories, service_types, domains, risk_level, metadata
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    owner_id = excluded.owner_id,
                    display_name = excluded.display_name,
                    description = excluded.description,
                    status = excluded.status,
                    visibility_mode = excluded.visibility_mode,
                    access_policy = excluded.access_policy,
                    pricing_mode = excluded.pricing_mode,
                    policy_summary = excluded.policy_summary,
                    supported_protocol_versions = excluded.supported_protocol_versions,
                    supported_transport_modes = excluded.supported_transport_modes,
                    rate_limits = excluded.rate_limits,
                    compliance_tags = excluded.compliance_tags,
                    pricing_policy = excluded.pricing_policy,
                    capabilities_schema = excluded.capabilities_schema,
                    provenance_policy = excluded.provenance_policy,
                    trust_summary = excluded.trust_summary,
                    primary_category = excluded.primary_category,
                    secondary_categories = excluded.secondary_categories,
                    service_types = excluded.service_types,
                    domains = excluded.domains,
                    risk_level = excluded.risk_level,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    agent_id,
                    owner_id,
                    display_name,
                    description,
                    status,
                    visibility_mode,
                    access_policy,
                    pricing_mode,
                    policy_summary,
                    json.dumps(supported_protocol_versions or ["2"], ensure_ascii=False),
                    json.dumps(supported_transport_modes or ["axl"], ensure_ascii=False),
                    json.dumps(rate_limits or {}, ensure_ascii=False),
                    json.dumps(compliance_tags or [], ensure_ascii=False),
                    json.dumps(pricing_policy or {}, ensure_ascii=False),
                    json.dumps(capabilities_schema or {}, ensure_ascii=False),
                    json.dumps(provenance_policy or {}, ensure_ascii=False),
                    json.dumps(trust_summary or {}, ensure_ascii=False),
                    primary_category,
                    json.dumps(secondary_categories or [], ensure_ascii=False),
                    json.dumps(service_types or [], ensure_ascii=False),
                    json.dumps(domains or [], ensure_ascii=False),
                    risk_level,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )

    def set_agent_status(self, *, agent_id: str, status: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE agent_registry SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE agent_id = ?",
                (status, agent_id),
            )

    def touch_agent_seen(self, *, agent_id: str, seen_ts: int | None = None) -> None:
        seen_ts = int(seen_ts if seen_ts is not None else time.time())
        with self._conn() as conn:
            conn.execute(
                "UPDATE agent_registry SET last_seen_at = ?, updated_at = CURRENT_TIMESTAMP WHERE agent_id = ?",
                (seen_ts, agent_id),
            )

    def upsert_agent_transport_endpoint(
        self,
        *,
        agent_id: str,
        axl_peer_id: str,
        mode: str = "axl",
        priority: int = 100,
        region: str | None = None,
        active: bool = True,
        last_seen_at: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_transport_endpoints(
                    agent_id, axl_peer_id, mode, priority, region, active, last_seen_at, metadata
                ) VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(agent_id, axl_peer_id) DO UPDATE SET
                    mode = excluded.mode,
                    priority = excluded.priority,
                    region = excluded.region,
                    active = excluded.active,
                    last_seen_at = excluded.last_seen_at,
                    metadata = excluded.metadata
                """,
                (
                    agent_id,
                    axl_peer_id,
                    mode,
                    int(priority),
                    region,
                    1 if active else 0,
                    None if last_seen_at is None else int(last_seen_at),
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )

    def resolve_agent_endpoints(
        self,
        *,
        agent_id: str,
        mode: str = "axl",
        include_inactive: bool = False,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        active_clause = "" if include_inactive else "AND active = 1"
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM agent_transport_endpoints
                WHERE agent_id = ? AND mode = ? {active_clause}
                ORDER BY priority ASC, id ASC
                LIMIT ?
                """,
                (agent_id, mode, int(limit)),
            ).fetchall()
        out = [dict(r) for r in rows]
        for row in out:
            row["metadata"] = json.loads(row.get("metadata") or "{}")
        return out

    def upsert_agent_signing_key(
        self,
        *,
        agent_id: str,
        key_id: str,
        public_key: str,
        status: str = "active",
        rotated_at: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if status not in {"active", "next", "retired"}:
            raise ValueError("invalid_signing_key_status")
        now_ts = int(time.time())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_signing_keys(agent_id, key_id, public_key, status, created_at, rotated_at, metadata)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(agent_id, key_id) DO UPDATE SET
                    public_key = excluded.public_key,
                    status = excluded.status,
                    rotated_at = excluded.rotated_at,
                    metadata = excluded.metadata
                """,
                (agent_id, key_id, public_key, status, now_ts, rotated_at, json.dumps(metadata or {}, ensure_ascii=False)),
            )

    def get_agent_public_key(
        self,
        *,
        agent_id: str,
        key_id: str,
        message_created_at: int | None = None,
    ) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT public_key, status, rotated_at FROM agent_signing_keys
                WHERE agent_id = ? AND key_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (agent_id, key_id),
            ).fetchone()
        if row is None:
            return None
        status = str(row["status"])
        if status in {"active", "next"}:
            return str(row["public_key"])
        if status == "retired" and message_created_at is not None and row["rotated_at"] is not None:
            return str(row["public_key"]) if int(message_created_at) < int(row["rotated_at"]) else None
        return None

    def list_agent_signing_keys(
        self,
        *,
        agent_id: str,
        key_id: str | None = None,
        statuses: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["agent_id = ?"]
        params: list[Any] = [agent_id]
        if key_id:
            clauses.append("key_id = ?")
            params.append(key_id)
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            clauses.append(f"status IN ({placeholders})")
            params.extend(statuses)
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM agent_signing_keys WHERE {' AND '.join(clauses)} ORDER BY id DESC",
                tuple(params),
            ).fetchall()
        out = [dict(r) for r in rows]
        for row in out:
            row["metadata"] = json.loads(row.get("metadata") or "{}")
        return out

    def add_peer_approval(self, *, source_agent_id: str, target_agent_id: str, status: str = "approved") -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_peer_approvals(source_agent_id, target_agent_id, status, updated_at)
                VALUES (?,?,?,?)
                ON CONFLICT(source_agent_id, target_agent_id) DO UPDATE SET
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (source_agent_id, target_agent_id, status, int(time.time())),
            )

    def is_peer_approved(self, *, source_agent_id: str, target_agent_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT status FROM agent_peer_approvals
                WHERE source_agent_id = ? AND target_agent_id = ?
                LIMIT 1
                """,
                (source_agent_id, target_agent_id),
            ).fetchone()
        return bool(row and row["status"] == "approved")

    def report_abuse(
        self,
        *,
        reason: str,
        reporter_agent_id: str | None = None,
        target_agent_id: str | None = None,
        target_owner_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> int:
        now_ts = int(time.time())
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO agent_abuse_reports(
                    reporter_agent_id, target_agent_id, target_owner_id, reason, payload, status, created_at
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (reporter_agent_id, target_agent_id, target_owner_id, reason, json.dumps(payload or {}, ensure_ascii=False), "open", now_ts),
            )
            return int(cur.lastrowid)

    def list_discoverable_agents(
        self,
        *,
        topics: list[str] | None = None,
        capabilities: list[str] | None = None,
        visibility_modes: list[str] | None = None,
        access_policies: list[str] | None = None,
        pricing_modes: list[str] | None = None,
        min_reputation: float | None = None,
        source_agent_id: str | None = None,
        primary_category: str | None = None,
        secondary_categories: list[str] | None = None,
        service_types: list[str] | None = None,
        domains: list[str] | None = None,
        risk_levels: list[str] | None = None,
        status: str = "active",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = ["status = ?"]
        params: list[Any] = [status]
        if visibility_modes:
            placeholders = ",".join("?" for _ in visibility_modes)
            clauses.append(f"visibility_mode IN ({placeholders})")
            params.extend(visibility_modes)
        if access_policies:
            placeholders = ",".join("?" for _ in access_policies)
            clauses.append(f"access_policy IN ({placeholders})")
            params.extend(access_policies)
        if pricing_modes:
            placeholders = ",".join("?" for _ in pricing_modes)
            clauses.append(f"pricing_mode IN ({placeholders})")
            params.extend(pricing_modes)
        if min_reputation is not None:
            clauses.append("reputation_agent >= ?")
            params.append(float(min_reputation))
        if primary_category:
            clauses.append("primary_category = ?")
            params.append(primary_category)
        for column, values in (
            ("secondary_categories", secondary_categories),
            ("service_types", service_types),
            ("domains", domains),
        ):
            if values:
                likes = [f'%"{value}"%' for value in values]
                clauses.append("(" + " OR ".join(f"{column} LIKE ?" for _ in likes) + ")")
                params.extend(likes)
        if risk_levels:
            placeholders = ",".join("?" for _ in risk_levels)
            clauses.append(f"risk_level IN ({placeholders})")
            params.extend(risk_levels)
        if topics:
            likes = [f'%"{topic}"%' for topic in topics]
            clauses.append("(" + " OR ".join("metadata LIKE ?" for _ in likes) + ")")
            params.extend(likes)
        if capabilities:
            likes = [f'%"{capability}"%' for capability in capabilities]
            clauses.append("(" + " OR ".join("metadata LIKE ?" for _ in likes) + ")")
            params.extend(likes)
        params.append(int(limit))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM agent_registry
                WHERE {' AND '.join(clauses)}
                ORDER BY (last_seen_at IS NULL) ASC, last_seen_at DESC, updated_at DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        parsed = [self._parse_agent_registry_row(dict(row)) for row in rows]
        if not source_agent_id:
            return parsed
        out: list[dict[str, Any]] = []
        for row in parsed:
            if row.get("access_policy") != "approved_only":
                out.append(row)
            elif self.is_peer_approved(source_agent_id=source_agent_id, target_agent_id=str(row["agent_id"])):
                out.append(row)
        return out

    def get_agent_registry(self, *, agent_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM agent_registry WHERE agent_id = ?", (agent_id,)).fetchone()
        if row is None:
            return None
        out = self._parse_agent_registry_row(dict(row))
        out["transport_endpoints"] = self.resolve_agent_endpoints(agent_id=agent_id, include_inactive=True)
        return out

    @staticmethod
    def _parse_agent_registry_row(row: dict[str, Any]) -> dict[str, Any]:
        row["supported_protocol_versions"] = json.loads(row.get("supported_protocol_versions") or "[]")
        row["supported_transport_modes"] = json.loads(row.get("supported_transport_modes") or "[]")
        row["rate_limits"] = json.loads(row.get("rate_limits") or "{}")
        row["compliance_tags"] = json.loads(row.get("compliance_tags") or "[]")
        row["pricing_policy"] = json.loads(row.get("pricing_policy") or "{}")
        row["capabilities_schema"] = json.loads(row.get("capabilities_schema") or "{}")
        row["provenance_policy"] = json.loads(row.get("provenance_policy") or "{}")
        row["trust_summary"] = json.loads(row.get("trust_summary") or "{}")
        row["secondary_categories"] = json.loads(row.get("secondary_categories") or "[]")
        row["service_types"] = json.loads(row.get("service_types") or "[]")
        row["domains"] = json.loads(row.get("domains") or "[]")
        row["metadata"] = json.loads(row.get("metadata") or "{}")
        return row

    @staticmethod
    def _estimate_quote_cost(
        *,
        pricing_mode: str,
        pricing_policy: dict[str, Any],
        capability: str,
        units: float,
    ) -> tuple[float, str, dict[str, Any]]:
        currency = str(pricing_policy.get("currency", "USD"))
        if pricing_mode == "free":
            return 0.0, currency, {"mode": "free"}
        prices = pricing_policy.get("capability_prices")
        raw_price = prices.get(capability) if isinstance(prices, dict) and capability in prices else pricing_policy.get("unit_price", 0.0)
        try:
            unit_price = float(raw_price)
        except (TypeError, ValueError):
            unit_price = 0.0
        return max(0.0, unit_price * max(0.0, units)), currency, {"mode": pricing_mode, "unit_price": unit_price}

    def create_agent_quote(
        self,
        *,
        seller_agent_id: str,
        buyer_agent_id: str,
        capability: str,
        request_payload: dict[str, Any] | None = None,
        units: float = 1.0,
        ttl_sec: int = 300,
    ) -> dict[str, Any]:
        seller = self.get_agent_registry(agent_id=seller_agent_id)
        if seller is None:
            raise ValueError("seller_agent_not_found")
        pricing_mode = str(seller.get("pricing_mode") or "free")
        estimated_cost, currency, terms = self._estimate_quote_cost(
            pricing_mode=pricing_mode,
            pricing_policy=dict(seller.get("pricing_policy") or {}),
            capability=capability,
            units=float(units),
        )
        now_ts = int(time.time())
        quote_id = f"quote_{uuid.uuid4().hex}"
        row = {
            "quote_id": quote_id,
            "seller_agent_id": seller_agent_id,
            "buyer_agent_id": buyer_agent_id,
            "capability": capability,
            "pricing_mode": pricing_mode,
            "estimated_cost": estimated_cost,
            "currency": currency,
            "units": float(units),
            "status": "quoted",
            "request_payload": request_payload or {},
            "terms": terms,
            "expires_at": now_ts + int(ttl_sec),
            "accepted_at": None,
            "created_at": now_ts,
        }
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_quotes(
                    quote_id, seller_agent_id, buyer_agent_id, capability, pricing_mode,
                    estimated_cost, currency, units, status, request_payload, terms,
                    expires_at, accepted_at, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    quote_id,
                    seller_agent_id,
                    buyer_agent_id,
                    capability,
                    pricing_mode,
                    estimated_cost,
                    currency,
                    float(units),
                    "quoted",
                    json.dumps(request_payload or {}, ensure_ascii=False),
                    json.dumps(terms, ensure_ascii=False),
                    row["expires_at"],
                    None,
                    now_ts,
                ),
            )
        return row

    def accept_agent_quote(self, *, quote_id: str, buyer_agent_id: str) -> dict[str, Any] | None:
        now_ts = int(time.time())
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM agent_quotes WHERE quote_id = ?", (quote_id,)).fetchone()
            if row is None:
                return None
            if str(row["buyer_agent_id"]) != buyer_agent_id:
                raise ValueError("quote_buyer_mismatch")
            if int(row["expires_at"]) < now_ts:
                conn.execute("UPDATE agent_quotes SET status = ? WHERE quote_id = ?", ("expired", quote_id))
                return self._parse_agent_quote_row(dict(row) | {"status": "expired"})
            conn.execute("UPDATE agent_quotes SET status = ?, accepted_at = ? WHERE quote_id = ?", ("accepted", now_ts, quote_id))
            updated = dict(row) | {"status": "accepted", "accepted_at": now_ts}
        return self._parse_agent_quote_row(updated)

    def get_agent_quote(self, *, quote_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM agent_quotes WHERE quote_id = ?", (quote_id,)).fetchone()
        return None if row is None else self._parse_agent_quote_row(dict(row))

    @staticmethod
    def _parse_agent_quote_row(row: dict[str, Any]) -> dict[str, Any]:
        row["request_payload"] = json.loads(row.get("request_payload") or "{}")
        row["terms"] = json.loads(row.get("terms") or "{}")
        return row

    def record_usage_event(
        self,
        *,
        buyer_agent_id: str,
        seller_agent_id: str,
        capability: str,
        message_type: str,
        units: float = 1.0,
        cost: float | None = None,
        currency: str | None = None,
        status: str = "recorded",
        quote_id: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        quote = self.get_agent_quote(quote_id=quote_id) if quote_id else None
        if quote_id:
            if quote is None:
                raise ValueError("quote_not_found")
            if quote.get("status") != "accepted":
                raise ValueError("quote_not_accepted")
            if str(quote.get("buyer_agent_id")) != buyer_agent_id:
                raise ValueError("quote_buyer_mismatch")
            if str(quote.get("seller_agent_id")) != seller_agent_id:
                raise ValueError("quote_seller_mismatch")
            if str(quote.get("capability")) != capability:
                raise ValueError("quote_capability_mismatch")
            with self._conn() as conn:
                existing = conn.execute(
                    """
                    SELECT * FROM agent_usage_events
                    WHERE quote_id = ? AND status IN ('recorded', 'completed')
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (quote_id,),
                ).fetchone()
            if existing is not None:
                row = dict(existing)
                row["payload"] = json.loads(row.get("payload") or "{}")
                return row
        seller = self.get_agent_registry(agent_id=seller_agent_id) or {}
        buyer = self.get_agent_registry(agent_id=buyer_agent_id) or {}
        usage_id = f"usage_{uuid.uuid4().hex}"
        now_ts = int(time.time())
        final_cost = float(cost if cost is not None else (quote or {}).get("estimated_cost", 0.0))
        final_currency = str(currency or (quote or {}).get("currency", "USD"))
        row = {
            "usage_id": usage_id,
            "quote_id": quote_id,
            "buyer_agent_id": buyer_agent_id,
            "seller_agent_id": seller_agent_id,
            "buyer_owner_id": buyer.get("owner_id"),
            "seller_owner_id": seller.get("owner_id"),
            "capability": capability,
            "message_type": message_type,
            "units": float(units),
            "cost": final_cost,
            "currency": final_currency,
            "status": status,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "payload": payload or {},
            "created_at": now_ts,
        }
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_usage_events(
                    usage_id, quote_id, buyer_agent_id, seller_agent_id, buyer_owner_id,
                    seller_owner_id, capability, message_type, units, cost, currency,
                    status, request_id, correlation_id, payload, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    usage_id,
                    quote_id,
                    buyer_agent_id,
                    seller_agent_id,
                    row["buyer_owner_id"],
                    row["seller_owner_id"],
                    capability,
                    message_type,
                    float(units),
                    final_cost,
                    final_currency,
                    status,
                    request_id,
                    correlation_id,
                    json.dumps(payload or {}, ensure_ascii=False),
                    now_ts,
                ),
            )
        return row

    def list_usage_events(
        self,
        *,
        owner_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if owner_id:
            clauses.append("(seller_owner_id = ? OR buyer_owner_id = ?)")
            params.extend([owner_id, owner_id])
        if agent_id:
            clauses.append("(seller_agent_id = ? OR buyer_agent_id = ?)")
            params.extend([agent_id, agent_id])
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(int(limit))
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM agent_usage_events {where_sql} ORDER BY created_at DESC LIMIT ?",
                tuple(params),
            ).fetchall()
        out = [dict(r) for r in rows]
        for row in out:
            row["payload"] = json.loads(row.get("payload") or "{}")
        return out


Storage = MarketplaceStorage
