import aiohttp
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("KeyAuthSellerAPI")

class KeyAuthSellerAPI:
    def __init__(self, seller_key: str, api_url: str = "https://br-auth-all-panels.vercel.app"):
        self.seller_key = seller_key
        self.api_url = api_url.rstrip("/")

    async def add_key(self, expiry: int = 1, mask: str = "XXXXXX-XXXXXX-XXXXXX", level: int = 1, amount: int = 1, note: str = "", prefix: str = "XCHEAT") -> Dict[str, Any]:
        url = f"{self.api_url}/api/seller/"
        params = {
            "sellerkey": self.seller_key,
            "type": "add",
            "expiry": str(expiry),
            "mask": mask,
            "level": str(level),
            "amount": str(amount),
            "note": note,
            "prefix": prefix
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status == 200:
                        try:
                            data = await resp.json()
                            return data
                        except Exception:
                            text = await resp.text()
                            return {"success": True, "key": text, "message": text}
                    else:
                        text = await resp.text()
                        return {"success": False, "message": f"HTTP {resp.status}: {text}"}
        except Exception as e:
            logger.error(f"API Error in add_key: {e}")
            return {"success": False, "message": str(e)}
