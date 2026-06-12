import asyncio
import logging
import sys
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from web.app import DASHBOARD_PORT, create_app


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    runner = web.AppRunner(create_app(None))
    await runner.setup()

    site = web.TCPSite(runner, "127.0.0.1", DASHBOARD_PORT)
    await site.start()

    print(f"Dashboard dev server running on http://127.0.0.1:{DASHBOARD_PORT}", flush=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
