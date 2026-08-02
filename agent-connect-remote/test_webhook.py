from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI()

DUMP_DIR = Path(__file__).parent / "webhook_dumps"
DUMP_DIR.mkdir(exist_ok=True)


@app.post("/webhook")
async def catch_all(request: Request):
    raw_body = await request.body()
    raw_text = raw_body.decode("utf-8", errors="replace")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = DUMP_DIR / f"webhook_{timestamp}.json"

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = {"_raw": raw_text}

    dump = {
        "timestamp": timestamp,
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "payload": payload,
        "raw": raw_text,
    }

    with open(dump_file, "w") as f:
        json.dump(dump, f, indent=2, default=str)

    logger.info("=" * 60)
    logger.info(f"WEBHOOK HIT — dumped to {dump_file}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Raw body ({len(raw_text)} chars):")
    logger.info(raw_text[:5000])
    logger.info("=" * 60)

    if isinstance(payload, dict):
        logger.info(f"Top-level keys: {list(payload.keys())}")

        for key in ["from", "sender", "fromAddress", "return_path", "to", "recipient"]:
            if key in payload:
                logger.info(f"  {key}: {payload[key]}")

        for key in ["subject", "title"]:
            if key in payload:
                logger.info(f"  {key}: {payload[key]}")

        for key in ["body", "text", "html", "message_body", "content", "message", "description"]:
            if key in payload:
                val = payload[key]
                if isinstance(val, dict):
                    logger.info(f"  {key} (dict keys): {list(val.keys())}")
                else:
                    logger.info(f"  {key} ({len(str(val))} chars): {str(val)[:300]}")

    return {"status": "ok", "dump_file": str(dump_file)}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all_routes(request: Request, path: str):
    raw_body = await request.body()
    logger.info(f"OTHER HIT: {request.method} /{path}")
    logger.info(f"Body: {raw_body.decode('utf-8', errors='replace')[:1000]}")
    return {"status": "caught", "path": path, "method": request.method}


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
    logger.info(f"Webhook test server starting on port {port}")
    logger.info(f"Dumps going to: {DUMP_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=port)
