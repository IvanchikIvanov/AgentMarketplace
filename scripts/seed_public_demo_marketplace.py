from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from marketplace_core.demo_agents.generic_agents import DEMO_PROFILES
from marketplace_core.registry.storage import MarketplaceStorage
from scripts.run_public_marketplace_demo import seed_demo_marketplace


def main() -> None:
    db_path = Path("data/public-demo-marketplace.db")
    storage = MarketplaceStorage(db_path)
    seed_demo_marketplace(storage)
    print("public_demo_marketplace_seeded")
    print(f"db_path={db_path}")
    print("agents=" + ",".join(profile.agent_id for profile in DEMO_PROFILES))
    print("run_ui=REGISTRY_DATABASE_URL=sqlite:///data/public-demo-marketplace.db python -m marketplace_core.registry.server")


if __name__ == "__main__":
    main()
