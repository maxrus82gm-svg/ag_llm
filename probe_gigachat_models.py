import asyncio
import json

import httpx

from server import CHAT_URL, get_access_token


MODELS_URL = CHAT_URL.rsplit("/", 2)[0] + "/models"


async def main() -> None:
    token = await get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            MODELS_URL,
            headers=headers,
        )

    print(f"HTTP: {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(response.text)
        response.raise_for_status()
        return

    if response.is_error:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        response.raise_for_status()

    models = data.get("data")

    if not isinstance(models, list):
        print("Unexpected response:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print(f"MODELS: {len(models)}")
    print()

    for item in models:
        print(
            f"{item.get('id')}"
            f" | object={item.get('object')}"
            f" | owned_by={item.get('owned_by')}"
        )


if __name__ == "__main__":
    asyncio.run(main())
