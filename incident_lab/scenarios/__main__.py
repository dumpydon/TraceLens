from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import UTC, datetime

import httpx

from incident_lab.runtime.store import (
    SCENARIOS,
    activate_scenario,
    clear_logs,
    load_scenario,
)


async def generate_traffic(
    count: int, checkout_url: str, traffic_batch_id: str | None = None
) -> dict[str, int]:
    traffic_batch_id = traffic_batch_id or f"BATCH-{uuid.uuid4().hex[:12].upper()}"
    results: dict[str, int] = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for _ in range(count):
            try:
                response = await client.post(
                    f"{checkout_url}/checkout",
                    json={"amount_cents": 4999, "currency": "USD"},
                    headers={
                        "X-Request-ID": str(uuid.uuid4()),
                        "X-Traffic-Batch-ID": traffic_batch_id,
                    },
                )
                key = str(response.status_code)
            except httpx.RequestError:
                key = "connection_error"
            results[key] = results.get(key, 0) + 1
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Control the TraceLens Incident Lab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    activate = subparsers.add_parser("activate")
    activate.add_argument("name", choices=SCENARIOS)
    subparsers.add_parser("reset")
    subparsers.add_parser("status")
    traffic = subparsers.add_parser("traffic")
    traffic.add_argument("--count", type=int, default=12)
    traffic.add_argument("--checkout-url", default="http://127.0.0.1:8101")
    args = parser.parse_args()

    if args.command == "activate":
        print(json.dumps(activate_scenario(args.name), indent=2))
    elif args.command == "reset":
        clear_logs()
        print(json.dumps(activate_scenario("baseline"), indent=2))
    elif args.command == "status":
        print(json.dumps(load_scenario(), indent=2))
    elif args.command == "traffic":
        batch_id = f"BATCH-{uuid.uuid4().hex[:12].upper()}"
        started_at = datetime.now(UTC)
        results = asyncio.run(generate_traffic(args.count, args.checkout_url, batch_id))
        ended_at = datetime.now(UTC)
        print(
            json.dumps(
                {
                    "traffic_batch_id": batch_id,
                    "started_at": started_at.isoformat(),
                    "ended_at": ended_at.isoformat(),
                    "requests": args.count,
                    "results": results,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
