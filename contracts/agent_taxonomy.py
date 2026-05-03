from __future__ import annotations

AGENT_CATEGORIES: list[dict[str, str]] = [
    {"category": "data", "description": "Collects, cleans, normalizes, transforms, enriches, indexes, or validates data."},
    {"category": "analysis", "description": "Interprets data, documents, events, metrics, systems, markets, or decisions."},
    {"category": "research", "description": "Finds information, compares sources, builds context, and produces evidence-backed conclusions."},
    {"category": "knowledge", "description": "Answers questions from memory, documents, databases, internal docs, or RAG systems."},
    {"category": "automation", "description": "Automates repeated workflows, routing, scheduling, updates, and operational tasks."},
    {"category": "engineering", "description": "Builds, reviews, tests, debugs, deploys, or maintains software and technical systems."},
    {"category": "content", "description": "Writes, edits, summarizes, rewrites, translates, or packages text and reports."},
    {"category": "communication", "description": "Handles messages, emails, dialog flows, negotiation support, and communication drafting."},
    {"category": "business", "description": "Supports strategy, planning, prioritization, business analysis, and decision support."},
    {"category": "finance", "description": "Handles accounting, budgeting, pricing, financial review, portfolio review, or cost analysis."},
    {"category": "legal", "description": "Reviews contracts, policies, compliance material, regulatory text, and legal-risk context."},
    {"category": "security", "description": "Reviews trust, fraud, abuse, vulnerabilities, permissions, identity, and operational risk."},
    {"category": "operations", "description": "Coordinates processes, logistics, runbooks, status tracking, and cross-team workflows."},
    {"category": "sales", "description": "Supports lead generation, CRM, outreach, qualification, proposals, and account workflows."},
    {"category": "customer_support", "description": "Handles support tickets, FAQ, troubleshooting, user guidance, and escalation summaries."},
    {"category": "education", "description": "Tutors, explains, assesses, builds curricula, creates exercises, or gives learning feedback."},
    {"category": "creative", "description": "Generates ideas, designs, images, brands, stories, presentations, and creative variants."},
    {"category": "personal_productivity", "description": "Assists with personal tasks, calendar, notes, reminders, planning, and prioritization."},
    {"category": "monitoring", "description": "Watches events, data changes, alerts, SLAs, incidents, feeds, or external state."},
    {"category": "execution", "description": "Performs actions in external systems behind explicit policy, permission, and safety gates."},
]

AGENT_CATEGORY_NAMES: set[str] = {row["category"] for row in AGENT_CATEGORIES}

RISK_LEVELS: set[str] = {"informational", "decision_support", "action_gated", "execution_capable"}
