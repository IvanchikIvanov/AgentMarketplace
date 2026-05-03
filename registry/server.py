from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..contracts.agent_taxonomy import AGENT_CATEGORIES
from .auth import require_registry_write_auth, require_source_agent_auth
from .storage import Storage

app = FastAPI(title="Agent Directory + Discovery Hub", version="0.1.0")


def _registry_db_path() -> Path:
    raw = os.environ.get("REGISTRY_DATABASE_URL") or os.environ.get("REGISTRY_DB_PATH") or "sqlite:///data/registry.db"
    if raw.startswith("sqlite:///"):
        raw = raw.removeprefix("sqlite:///")
    return Path(raw)


_storage = Storage(_registry_db_path())

MARKETPLACE_UI_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'">
  <title>Marketplace Directory</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #18202b;
      --muted: #667085;
      --line: #d9dee7;
      --accent: #176b87;
      --accent-soft: #e4f3f7;
      --warn: #8a4b0f;
      --ok: #17614a;
      --shadow: 0 10px 24px rgba(24, 32, 43, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }

    button, input, select {
      font: inherit;
    }

    .shell {
      display: grid;
      grid-template-columns: 260px minmax(0, 1fr) 360px;
      min-height: 100vh;
    }

    .sidebar, .detail {
      background: var(--panel);
      border-color: var(--line);
      border-style: solid;
    }

    .sidebar {
      border-width: 0 1px 0 0;
      padding: 20px 14px;
      overflow: auto;
    }

    .detail {
      border-width: 0 0 0 1px;
      padding: 20px;
      overflow: auto;
    }

    .main {
      padding: 20px;
      overflow: auto;
    }

    h1 {
      margin: 0 0 4px;
      font-size: 22px;
      line-height: 1.2;
    }

    h2 {
      margin: 0 0 12px;
      font-size: 14px;
      text-transform: uppercase;
      color: var(--muted);
    }

    .subhead {
      margin: 0 0 20px;
      color: var(--muted);
      font-size: 13px;
    }

    .category-list {
      display: grid;
      gap: 6px;
    }

    .category-button {
      width: 100%;
      border: 1px solid transparent;
      background: transparent;
      border-radius: 7px;
      color: var(--ink);
      cursor: pointer;
      padding: 9px 10px;
      text-align: left;
    }

    .category-button:hover,
    .category-button.active {
      background: var(--accent-soft);
      border-color: #b8dce6;
      color: #0d4d62;
    }

    .toolbar {
      display: grid;
      gap: 12px;
      margin-bottom: 18px;
    }

    .search-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 8px;
    }

    .filters {
      display: grid;
      grid-template-columns: repeat(5, minmax(130px, 1fr));
      gap: 8px;
    }

    input, select {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--panel);
      color: var(--ink);
      padding: 8px 10px;
    }

    .action {
      min-height: 38px;
      border: 1px solid var(--accent);
      border-radius: 7px;
      background: var(--accent);
      color: white;
      cursor: pointer;
      padding: 8px 13px;
      white-space: nowrap;
    }

    .secondary {
      border-color: var(--line);
      background: var(--panel);
      color: var(--ink);
    }

    .status {
      min-height: 20px;
      color: var(--muted);
      font-size: 13px;
    }

    .grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    }

    .card {
      min-height: 205px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: var(--shadow);
      cursor: pointer;
      display: grid;
      gap: 12px;
      padding: 14px;
      text-align: left;
    }

    .card:hover,
    .card.active {
      border-color: var(--accent);
    }

    .card-title {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
    }

    .agent-name {
      font-weight: 700;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }

    .agent-id {
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
      overflow-wrap: anywhere;
    }

    .badge {
      border-radius: 999px;
      background: #eef1f5;
      color: #344054;
      display: inline-flex;
      font-size: 12px;
      line-height: 1;
      padding: 6px 8px;
      white-space: nowrap;
    }

    .badge.risk-high { background: #fff0e6; color: var(--warn); }
    .badge.risk-informational { background: #eaf7f2; color: var(--ok); }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .meta {
      color: var(--muted);
      display: grid;
      gap: 4px;
      font-size: 13px;
    }

    .empty {
      border: 1px dashed var(--line);
      border-radius: 8px;
      color: var(--muted);
      padding: 28px;
      text-align: center;
    }

    .detail-section {
      border-top: 1px solid var(--line);
      padding-top: 14px;
      margin-top: 14px;
    }

    .detail-name {
      font-size: 20px;
      font-weight: 700;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }

    .detail-description {
      color: var(--muted);
      margin-top: 8px;
      line-height: 1.45;
    }

    pre {
      background: #101828;
      border-radius: 8px;
      color: #e6edf3;
      font-size: 12px;
      line-height: 1.45;
      margin: 8px 0 0;
      overflow: auto;
      padding: 12px;
      white-space: pre-wrap;
    }

    @media (max-width: 1100px) {
      .shell {
        grid-template-columns: 220px minmax(0, 1fr);
      }

      .detail {
        grid-column: 1 / -1;
        border-width: 1px 0 0;
      }
    }

    @media (max-width: 760px) {
      .shell {
        display: block;
      }

      .sidebar, .detail {
        border-width: 0 0 1px;
      }

      .search-row,
      .filters {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <h1>Marketplace Directory</h1>
      <p class="subhead">Browse agent cards by category or search capabilities.</p>
      <h2>Categories</h2>
      <div id="categories" class="category-list"></div>
    </aside>

    <main class="main">
      <section class="toolbar" aria-label="Directory controls">
        <div class="search-row">
          <input id="search" type="search" placeholder="Search agents, capabilities, domains">
          <button id="searchButton" class="action" type="button">Search</button>
          <button id="clearButton" class="action secondary" type="button">Clear</button>
        </div>
        <div class="filters">
          <select id="serviceType" aria-label="Service type">
            <option value="">All service types</option>
            <option value="data_feed">Data feed</option>
            <option value="analysis">Analysis</option>
            <option value="research">Research</option>
            <option value="execution">Execution</option>
            <option value="monitoring">Monitoring</option>
            <option value="automation">Automation</option>
            <option value="review">Review</option>
            <option value="advisory">Advisory</option>
          </select>
          <input id="domain" placeholder="Domain filter">
          <select id="riskLevel" aria-label="Risk level">
            <option value="">All risk levels</option>
            <option value="informational">Informational</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <select id="pricingMode" aria-label="Pricing mode">
            <option value="">All pricing</option>
            <option value="free">Free</option>
            <option value="metered">Metered</option>
            <option value="quote_required">Quote required</option>
            <option value="subscription">Subscription</option>
          </select>
          <select id="accessPolicy" aria-label="Access policy">
            <option value="">All access</option>
            <option value="public">Public</option>
            <option value="approval_required">Approval required</option>
            <option value="private">Private</option>
          </select>
        </div>
      </section>
      <div id="status" class="status">Loading marketplace...</div>
      <section id="agents" class="grid" aria-live="polite"></section>
    </main>

    <aside id="detail" class="detail">
      <h2>Agent Card</h2>
      <div class="empty">Select an agent to inspect trust, pricing, capabilities, and endpoints.</div>
    </aside>
  </div>

  <script>
    const state = {
      categories: [],
      selectedCategory: "",
      selectedAgentId: "",
      agents: []
    };

    const els = {
      categories: document.getElementById("categories"),
      agents: document.getElementById("agents"),
      detail: document.getElementById("detail"),
      status: document.getElementById("status"),
      search: document.getElementById("search"),
      searchButton: document.getElementById("searchButton"),
      clearButton: document.getElementById("clearButton"),
      serviceType: document.getElementById("serviceType"),
      domain: document.getElementById("domain"),
      riskLevel: document.getElementById("riskLevel"),
      pricingMode: document.getElementById("pricingMode"),
      accessPolicy: document.getElementById("accessPolicy")
    };

    function label(value) {
      if (!value) return "";
      return String(value).replaceAll("_", " ").replace(/\\b\\w/g, char => char.toUpperCase());
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function cssToken(value) {
      return String(value ?? "").toLowerCase().replace(/[^a-z0-9_-]/g, "-");
    }

    async function fetchJson(url) {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
      return response.json();
    }

    function selectedFilters() {
      return {
        service_type: els.serviceType.value,
        domain: els.domain.value.trim(),
        risk_level: els.riskLevel.value,
        pricing_mode: els.pricingMode.value,
        access_policy: els.accessPolicy.value
      };
    }

    function buildDirectoryUrl() {
      const params = new URLSearchParams();
      if (state.selectedCategory) params.set("primary_category", state.selectedCategory);
      Object.entries(selectedFilters()).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      return `/directory/agents${params.toString() ? `?${params}` : ""}`;
    }

    function renderCategories() {
      const allButton = `<button class="category-button ${state.selectedCategory ? "" : "active"}" data-category="">All categories</button>`;
      const buttons = state.categories.map(category => `
        <button class="category-button ${state.selectedCategory === category.id ? "active" : ""}" data-category="${escapeHtml(category.id)}">
          ${escapeHtml(category.label || label(category.id))}
        </button>
      `).join("");
      els.categories.innerHTML = allButton + buttons;
      els.categories.querySelectorAll("button").forEach(button => {
        button.addEventListener("click", () => {
          state.selectedCategory = button.dataset.category || "";
          els.search.value = "";
          renderCategories();
          loadAgents();
        });
      });
    }

    function chipList(values) {
      return (values || []).slice(0, 5).map(value => `<span class="badge">${escapeHtml(label(value))}</span>`).join("");
    }

    function renderAgents(agents) {
      state.agents = agents;
      if (!agents.length) {
        els.agents.innerHTML = `<div class="empty">No agents match the current directory view.</div>`;
        return;
      }
      els.agents.innerHTML = agents.map(agent => `
        <button class="card ${state.selectedAgentId === agent.agent_id ? "active" : ""}" data-agent-id="${escapeHtml(agent.agent_id)}">
          <div class="card-title">
            <div>
              <div class="agent-name">${escapeHtml(agent.display_name || agent.agent_id)}</div>
              <div class="agent-id">${escapeHtml(agent.agent_id)}</div>
            </div>
            <span class="badge risk-${cssToken(agent.risk_level || "")}">${escapeHtml(label(agent.risk_level || "risk"))}</span>
          </div>
          <div class="chips">
            <span class="badge">${escapeHtml(label(agent.primary_category || "uncategorized"))}</span>
            ${chipList(agent.service_types)}
          </div>
          <div class="meta">
            <div>Domains: ${escapeHtml((agent.domains || []).join(", ") || "not specified")}</div>
            <div>Capabilities: ${escapeHtml((agent.capabilities || []).slice(0, 4).join(", ") || "not specified")}</div>
            <div>Pricing: ${escapeHtml(label(agent.pricing_mode || "free"))}</div>
            <div>Active endpoints: ${escapeHtml(agent.active_endpoint_count ?? 0)}</div>
          </div>
        </button>
      `).join("");
      els.agents.querySelectorAll(".card").forEach(card => {
        card.addEventListener("click", () => selectAgent(card.dataset.agentId));
      });
    }

    function renderDetail(agent) {
      const metadata = agent.metadata || {};
      els.detail.innerHTML = `
        <h2>Agent Card</h2>
        <div class="detail-name">${escapeHtml(agent.display_name || agent.agent_id)}</div>
        <div class="agent-id">${escapeHtml(agent.agent_id)}</div>
        <p class="detail-description">${escapeHtml(agent.description || "No description provided.")}</p>
        <div class="detail-section">
          <div class="chips">
            <span class="badge">${escapeHtml(label(agent.primary_category || "uncategorized"))}</span>
            ${(agent.secondary_categories || []).map(value => `<span class="badge">${escapeHtml(label(value))}</span>`).join("")}
          </div>
        </div>
        <div class="detail-section">
          <h2>Service</h2>
          <div class="meta">
            <div>Types: ${escapeHtml((agent.service_types || []).join(", ") || "not specified")}</div>
            <div>Domains: ${escapeHtml((agent.domains || []).join(", ") || "not specified")}</div>
            <div>Risk: ${escapeHtml(label(agent.risk_level || "informational"))}</div>
            <div>Access: ${escapeHtml(label(agent.access_policy || "public"))}</div>
            <div>Pricing: ${escapeHtml(label(agent.pricing_mode || "free"))}</div>
          </div>
        </div>
        <div class="detail-section">
          <h2>Capabilities</h2>
          <div class="chips">
            ${(metadata.capabilities || []).map(value => `<span class="badge">${escapeHtml(value)}</span>`).join("") || "<span class='badge'>None listed</span>"}
          </div>
        </div>
        <div class="detail-section">
          <h2>Trust</h2>
          <pre>${escapeHtml(JSON.stringify(agent.trust_summary || {}, null, 2))}</pre>
        </div>
        <div class="detail-section">
          <h2>Pricing Policy</h2>
          <pre>${escapeHtml(JSON.stringify(agent.pricing_policy || {}, null, 2))}</pre>
        </div>
      `;
    }

    async function selectAgent(agentId) {
      state.selectedAgentId = agentId;
      renderAgents(state.agents);
      els.detail.innerHTML = `<h2>Agent Card</h2><div class="empty">Loading agent details...</div>`;
      try {
        const agent = await fetchJson(`/directory/agents/${encodeURIComponent(agentId)}`);
        renderDetail(agent);
      } catch (error) {
        els.detail.innerHTML = `<h2>Agent Card</h2><div class="empty">Could not load details: ${escapeHtml(error.message)}</div>`;
      }
    }

    async function loadAgents() {
      els.status.textContent = "Loading agents...";
      try {
        const data = await fetchJson(buildDirectoryUrl());
        renderAgents(data.agents || []);
        els.status.textContent = `${(data.agents || []).length} agents in directory view`;
      } catch (error) {
        els.status.textContent = `Directory error: ${error.message}`;
        renderAgents([]);
      }
    }

    async function searchAgents() {
      const query = els.search.value.trim();
      if (!query) {
        await loadAgents();
        return;
      }
      els.status.textContent = "Searching agents...";
      try {
        const data = await fetchJson(`/directory/search?q=${encodeURIComponent(query)}`);
        renderAgents(data.agents || []);
        els.status.textContent = `${(data.agents || []).length} agents found for "${query}"`;
      } catch (error) {
        els.status.textContent = `Search error: ${error.message}`;
        renderAgents([]);
      }
    }

    async function loadCategories() {
      const data = await fetchJson("/directory/categories");
      state.categories = data.categories || [];
      renderCategories();
    }

    els.searchButton.addEventListener("click", searchAgents);
    els.search.addEventListener("keydown", event => {
      if (event.key === "Enter") searchAgents();
    });
    els.clearButton.addEventListener("click", () => {
      els.search.value = "";
      state.selectedCategory = "";
      state.selectedAgentId = "";
      renderCategories();
      loadAgents();
    });
    [els.serviceType, els.riskLevel, els.pricingMode, els.accessPolicy].forEach(el => {
      el.addEventListener("change", loadAgents);
    });
    els.domain.addEventListener("change", loadAgents);

    loadCategories()
      .then(loadAgents)
      .catch(error => {
        els.status.textContent = `Marketplace UI failed to load: ${error.message}`;
      });
  </script>
</body>
</html>
"""


def _query_list(value: Any) -> list[str]:
    return value if isinstance(value, list) else []


class OwnerUpsertRequest(BaseModel):
    owner_id: str
    display_name: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentUpsertRequest(BaseModel):
    owner_id: str
    agent_id: str
    display_name: str
    description: str = ""
    status: str = "draft"
    visibility_mode: str = "public"
    access_policy: str = "public"
    pricing_mode: str = "free"
    policy_summary: str | None = None
    supported_protocol_versions: list[str] = Field(default_factory=lambda: ["2"])
    supported_transport_modes: list[str] = Field(default_factory=lambda: ["axl"])
    rate_limits: dict[str, Any] = Field(default_factory=dict)
    compliance_tags: list[str] = Field(default_factory=list)
    pricing_policy: dict[str, Any] = Field(default_factory=dict)
    capabilities_schema: dict[str, Any] = Field(default_factory=dict)
    provenance_policy: dict[str, Any] = Field(default_factory=dict)
    trust_summary: dict[str, Any] = Field(default_factory=dict)
    primary_category: str = ""
    secondary_categories: list[str] = Field(default_factory=list)
    service_types: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    risk_level: str = "informational"
    topics: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    message_types_supported: list[str] = Field(default_factory=list)
    query_enabled: bool = True
    prompt_files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EndpointUpsertRequest(BaseModel):
    axl_peer_id: str
    mode: str = "axl"
    priority: int = 100
    region: str | None = None
    active: bool = True
    last_seen_at: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HeartbeatRequest(BaseModel):
    axl_peer_id: str | None = None
    mode: str = "axl"
    region: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KeyUpsertRequest(BaseModel):
    key_id: str
    public_key: str
    status: str = "active"
    rotated_at: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    source_agent_id: str
    target_agent_id: str
    status: str = "approved"


class AbuseReportRequest(BaseModel):
    reason: str
    reporter_agent_id: str | None = None
    target_agent_id: str | None = None
    target_owner_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class QuoteRequest(BaseModel):
    buyer_agent_id: str
    capability: str
    units: float = 1.0
    ttl_sec: int = 300
    request_payload: dict[str, Any] = Field(default_factory=dict)


class QuoteAcceptRequest(BaseModel):
    buyer_agent_id: str


class UsageEventRequest(BaseModel):
    buyer_agent_id: str
    seller_agent_id: str
    capability: str
    message_type: str = "agent_query"
    units: float = 1.0
    cost: float | None = None
    currency: str | None = None
    status: str = "recorded"
    quote_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ui", response_class=HTMLResponse)
def marketplace_ui() -> HTMLResponse:
    return HTMLResponse(MARKETPLACE_UI_HTML)


@app.post("/owners")
def upsert_owner(req: OwnerUpsertRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, str]:
    _storage.upsert_owner(owner_id=req.owner_id, display_name=req.display_name, metadata=req.metadata)
    return {"status": "ok", "owner_id": req.owner_id}


@app.post("/agents")
def upsert_agent(req: AgentUpsertRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, str]:
    metadata = dict(req.metadata)
    metadata.setdefault("topics", req.topics)
    metadata.setdefault("capabilities", req.capabilities)
    metadata.setdefault("message_types_supported", req.message_types_supported)
    metadata.setdefault("query_enabled", req.query_enabled)
    metadata.setdefault("prompt_files", req.prompt_files)
    _storage.upsert_agent_registry(
        owner_id=req.owner_id,
        agent_id=req.agent_id,
        display_name=req.display_name,
        description=req.description,
        status=req.status,
        visibility_mode=req.visibility_mode,
        access_policy=req.access_policy,
        pricing_mode=req.pricing_mode,
        policy_summary=req.policy_summary,
        supported_protocol_versions=req.supported_protocol_versions,
        supported_transport_modes=req.supported_transport_modes,
        rate_limits=req.rate_limits,
        compliance_tags=req.compliance_tags,
        pricing_policy=req.pricing_policy,
        capabilities_schema=req.capabilities_schema,
        provenance_policy=req.provenance_policy,
        trust_summary=req.trust_summary,
        primary_category=req.primary_category,
        secondary_categories=req.secondary_categories,
        service_types=req.service_types,
        domains=req.domains,
        risk_level=req.risk_level,
        metadata=metadata,
    )
    return {"status": "ok", "agent_id": req.agent_id}


@app.get("/agents")
def list_agents(
    status: str = "active",
    visibility_mode: list[str] = Query(default_factory=lambda: ["public", "approved_only"]),
    topic: list[str] = Query(default_factory=list),
    capability: list[str] = Query(default_factory=list),
    access_policy: list[str] = Query(default_factory=list),
    pricing_mode: list[str] = Query(default_factory=list),
    min_reputation: float | None = None,
    source_agent_id: str | None = None,
    primary_category: str | None = None,
    secondary_category: list[str] = Query(default_factory=list),
    service_type: list[str] = Query(default_factory=list),
    domain: list[str] = Query(default_factory=list),
    risk_level: list[str] = Query(default_factory=list),
    _source_auth: None = Depends(require_source_agent_auth),
) -> dict[str, Any]:
    rows = _storage.list_discoverable_agents(
        status=status,
        topics=_query_list(topic),
        capabilities=_query_list(capability),
        visibility_modes=_query_list(visibility_mode),
        access_policies=_query_list(access_policy) or None,
        pricing_modes=_query_list(pricing_mode) or None,
        min_reputation=min_reputation,
        source_agent_id=source_agent_id,
        primary_category=primary_category,
        secondary_categories=_query_list(secondary_category),
        service_types=_query_list(service_type),
        domains=_query_list(domain),
        risk_levels=_query_list(risk_level),
        limit=200,
    )
    return {"agents": rows}


def _compact_directory_card(row: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    endpoints = _storage.resolve_agent_endpoints(agent_id=str(row["agent_id"]), include_inactive=False)
    return {
        "agent_id": row["agent_id"],
        "owner_id": row["owner_id"],
        "display_name": row.get("display_name", ""),
        "primary_category": row.get("primary_category", ""),
        "secondary_categories": list(row.get("secondary_categories") or []),
        "service_types": list(row.get("service_types") or []),
        "domains": list(row.get("domains") or []),
        "topics": list(metadata.get("topics") or []),
        "capabilities": list(metadata.get("capabilities") or []),
        "risk_level": row.get("risk_level", "informational"),
        "pricing_mode": row.get("pricing_mode", "free"),
        "trust_summary": dict(row.get("trust_summary") or {}),
        "active_endpoint_count": len(endpoints),
    }


@app.get("/directory/agents")
def directory_agents(
    status: str = "active",
    visibility_mode: list[str] = Query(default_factory=lambda: ["public", "approved_only"]),
    topic: list[str] = Query(default_factory=list),
    capability: list[str] = Query(default_factory=list),
    access_policy: list[str] = Query(default_factory=list),
    pricing_mode: list[str] = Query(default_factory=list),
    min_reputation: float | None = None,
    source_agent_id: str | None = None,
    primary_category: str | None = None,
    secondary_category: list[str] = Query(default_factory=list),
    service_type: list[str] = Query(default_factory=list),
    domain: list[str] = Query(default_factory=list),
    risk_level: list[str] = Query(default_factory=list),
    _source_auth: None = Depends(require_source_agent_auth),
) -> dict[str, Any]:
    rows = _storage.list_discoverable_agents(
        status=status,
        topics=_query_list(topic),
        capabilities=_query_list(capability),
        visibility_modes=_query_list(visibility_mode),
        access_policies=_query_list(access_policy) or None,
        pricing_modes=_query_list(pricing_mode) or None,
        min_reputation=min_reputation,
        source_agent_id=source_agent_id,
        primary_category=primary_category,
        secondary_categories=_query_list(secondary_category),
        service_types=_query_list(service_type),
        domains=_query_list(domain),
        risk_levels=_query_list(risk_level),
        limit=200,
    )
    return {"agents": [_compact_directory_card(row) for row in rows]}


@app.get("/directory/categories")
def directory_categories() -> dict[str, Any]:
    return {"categories": AGENT_CATEGORIES}


def _search_score(row: dict[str, Any], tokens: list[str]) -> int:
    metadata = dict(row.get("metadata") or {})
    haystack_parts = [
        row.get("agent_id", ""),
        row.get("display_name", ""),
        row.get("description", ""),
        row.get("primary_category", ""),
        row.get("risk_level", ""),
        " ".join(str(v) for v in row.get("secondary_categories") or []),
        " ".join(str(v) for v in row.get("service_types") or []),
        " ".join(str(v) for v in row.get("domains") or []),
        " ".join(str(v) for v in metadata.get("topics") or []),
        " ".join(str(v) for v in metadata.get("capabilities") or []),
    ]
    haystack = " ".join(haystack_parts).lower().replace("_", " ")
    return sum(1 for token in tokens if token in haystack)


@app.get("/directory/search")
def directory_search(
    q: str,
    status: str = "active",
    visibility_mode: list[str] = Query(default_factory=lambda: ["public", "approved_only"]),
    source_agent_id: str | None = None,
    limit: int = 20,
    _source_auth: None = Depends(require_source_agent_auth),
) -> dict[str, Any]:
    stopwords = {"a", "an", "the", "that", "can", "who", "which", "agent", "assistant", "ai", "ии", "бот"}
    tokens = [token for token in q.lower().replace("_", " ").split() if token and token not in stopwords]
    if not tokens:
        return {"agents": []}
    rows = _storage.list_discoverable_agents(
        status=status,
        visibility_modes=_query_list(visibility_mode),
        source_agent_id=source_agent_id,
        limit=200,
    )
    scored = [(row, _search_score(row, tokens)) for row in rows]
    matches = [item for item in scored if item[1] > 0]
    matches.sort(key=lambda item: item[1], reverse=True)
    return {"agents": [_compact_directory_card(row) for row, _score in matches[: int(limit)]]}


@app.get("/directory/agents/{agent_id}")
def directory_agent_detail(agent_id: str) -> dict[str, Any]:
    row = _storage.get_agent_registry(agent_id=agent_id)
    if row is None:
        raise HTTPException(status_code=404, detail="agent_not_found")
    return row


@app.get("/agents/{agent_id}")
def get_agent(agent_id: str) -> dict[str, Any]:
    row = _storage.get_agent_registry(agent_id=agent_id)
    if row is None:
        raise HTTPException(status_code=404, detail="agent_not_found")
    return row


@app.post("/agents/{agent_id}/status")
def set_agent_status(agent_id: str, status: str, _auth: None = Depends(require_registry_write_auth)) -> dict[str, str]:
    _storage.set_agent_status(agent_id=agent_id, status=status)
    return {"status": "ok", "agent_id": agent_id}


@app.post("/agents/{agent_id}/quote")
def create_quote(agent_id: str, req: QuoteRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, Any]:
    try:
        quote = _storage.create_agent_quote(
            seller_agent_id=agent_id,
            buyer_agent_id=req.buyer_agent_id,
            capability=req.capability,
            request_payload=req.request_payload,
            units=req.units,
            ttl_sec=req.ttl_sec,
        )
    except ValueError as exc:
        if str(exc) == "seller_agent_not_found":
            raise HTTPException(status_code=404, detail="agent_not_found") from exc
        raise
    return quote


@app.post("/quotes/{quote_id}/accept")
def accept_quote(quote_id: str, req: QuoteAcceptRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, Any]:
    try:
        quote = _storage.accept_agent_quote(
            quote_id=quote_id,
            buyer_agent_id=req.buyer_agent_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if quote is None:
        raise HTTPException(status_code=404, detail="quote_not_found")
    return quote


@app.get("/agents/{agent_id}/keys")
def list_keys(agent_id: str, key_id: str | None = None) -> dict[str, Any]:
    keys = _storage.list_agent_signing_keys(
        agent_id=agent_id,
        key_id=key_id,
        statuses=["active", "next"],
    )
    return {"keys": keys}


@app.post("/usage/events")
def record_usage_event(req: UsageEventRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, Any]:
    try:
        event = _storage.record_usage_event(
            buyer_agent_id=req.buyer_agent_id,
            seller_agent_id=req.seller_agent_id,
            capability=req.capability,
            message_type=req.message_type,
            units=req.units,
            cost=req.cost,
            currency=req.currency,
            status=req.status,
            quote_id=req.quote_id,
            request_id=req.request_id,
            correlation_id=req.correlation_id,
            payload=req.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return event


@app.get("/owners/{owner_id}/usage")
def list_owner_usage(owner_id: str, limit: int = 100) -> dict[str, Any]:
    return {"usage": _storage.list_usage_events(owner_id=owner_id, limit=limit)}


@app.post("/agents/{agent_id}/heartbeat")
def heartbeat(agent_id: str, req: HeartbeatRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, Any]:
    now_ts = int(time.time())
    _storage.touch_agent_seen(agent_id=agent_id, seen_ts=now_ts)
    if req.axl_peer_id:
        _storage.upsert_agent_transport_endpoint(
            agent_id=agent_id,
            axl_peer_id=req.axl_peer_id,
            mode=req.mode,
            priority=100,
            region=req.region,
            active=True,
            last_seen_at=now_ts,
            metadata=req.metadata,
        )
    return {"status": "ok", "agent_id": agent_id, "seen_ts": now_ts}


@app.post("/agents/{agent_id}/endpoints")
def upsert_endpoint(agent_id: str, req: EndpointUpsertRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, str]:
    _storage.upsert_agent_transport_endpoint(
        agent_id=agent_id,
        axl_peer_id=req.axl_peer_id,
        mode=req.mode,
        priority=req.priority,
        region=req.region,
        active=req.active,
        last_seen_at=req.last_seen_at,
        metadata=req.metadata,
    )
    return {"status": "ok", "agent_id": agent_id, "axl_peer_id": req.axl_peer_id}


@app.post("/agents/{agent_id}/keys")
def upsert_key(agent_id: str, req: KeyUpsertRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, str]:
    _storage.upsert_agent_signing_key(
        agent_id=agent_id,
        key_id=req.key_id,
        public_key=req.public_key,
        status=req.status,
        rotated_at=req.rotated_at,
        metadata=req.metadata,
    )
    return {"status": "ok", "agent_id": agent_id, "key_id": req.key_id}


@app.post("/approvals")
def add_approval(req: ApprovalRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, str]:
    _storage.add_peer_approval(
        source_agent_id=req.source_agent_id,
        target_agent_id=req.target_agent_id,
        status=req.status,
    )
    return {"status": "ok"}


@app.post("/abuse/report")
def report_abuse(req: AbuseReportRequest, _auth: None = Depends(require_registry_write_auth)) -> dict[str, Any]:
    report_id = _storage.report_abuse(
        reason=req.reason,
        reporter_agent_id=req.reporter_agent_id,
        target_agent_id=req.target_agent_id,
        target_owner_id=req.target_owner_id,
        payload=req.payload,
    )
    return {"status": "ok", "report_id": report_id}


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("REGISTRY_HOST", "127.0.0.1")
    port = int(os.environ.get("REGISTRY_PORT", "8080"))
    uvicorn.run("marketplace_core.registry.server:app", host=host, port=port, reload=False)
