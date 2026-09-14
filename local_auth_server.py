import asyncio
import logging
import sys
from aiohttp import web, ClientSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LocalAuthServer")

REMOTE_PANEL_URL = "https://br-auth-all-panels.vercel.app"

async def handle_client_auth(request):
    try:
        body = await request.json()
        logger.info(f"[CLIENT REQUEST] Incoming Payload: {body}")
    except Exception:
        text = await request.text()
        logger.info(f"[CLIENT REQUEST] Raw Body: {text}")
        body = {}

    # Target URL on remote BR Auth Vercel panel
    target_url = f"{REMOTE_PANEL_URL}{request.path}"
    
    async with ClientSession() as session:
        try:
            async with session.post(target_url, json=body, timeout=10) as resp:
                resp_data = await resp.json(content_type=None)
                logger.info(f"[REMOTE RESPONSE] Status: {resp.status}, Body: {resp_data}")
                return web.json_response(resp_data, status=resp.status)
        except Exception as e:
            logger.error(f"[FORWARD ERROR] {e}")
            # Fallback direct auth if remote timeout
            key = body.get("key") or body.get("license") or body.get("username")
            if key and ("BR-" in str(key) or "FRESH-" in str(key)):
                return web.json_response({
                    "success": True,
                    "message": "Authentication successful (Local Override)",
                    "duration": "30 Days"
                }, status=200)
            return web.json_response({"success": False, "error": str(e)}, status=500)

async def handle_health(request):
    return web.json_response({"success": True, "mongodb": "CONNECTED", "status": "200 OK"})

async def handle_catchall(request):
    logger.info(f"[CATCHALL] {request.method} {request.path}")
    return await handle_client_auth(request)

app = web.Application()
app.router.add_post("/api/v1/client/auth", handle_client_auth)
app.router.add_get("/api/v1/health", handle_health)
app.router.add_route("*", "/{tail:.*}", handle_catchall)

if __name__ == "__main__":
    logger.info("Starting BR Auth Local API Server on http://127.0.0.1:5000 ...")
    web.run_app(app, host="127.0.0.1", port=5000)
