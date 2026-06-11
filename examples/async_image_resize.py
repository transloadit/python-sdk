"""Upload and resize an image with the async client.

Run from the repository root:

    TRANSLOADIT_KEY=xxx TRANSLOADIT_SECRET=yyy poetry run python examples/async_image_resize.py
"""

import asyncio
import os
from pathlib import Path

from transloadit.async_client import AsyncTransloadit


def get_credentials():
    key = os.getenv("TRANSLOADIT_KEY")
    secret = os.getenv("TRANSLOADIT_SECRET")
    if not key or not secret:
        raise RuntimeError("Please set TRANSLOADIT_KEY and TRANSLOADIT_SECRET.")
    return key, secret


def get_example_image_path():
    return Path(__file__).resolve().parent / "fixtures" / "lol_cat.jpg"


def first_result_url(response_data, step_name):
    results = (response_data.get("results") or {}).get(step_name) or []
    if not results:
        raise RuntimeError(f"No results found for step {step_name!r}: {response_data}")
    url = results[0].get("ssl_url") or results[0].get("url")
    if not url:
        raise RuntimeError(f"No result URL found for step {step_name!r}: {response_data}")
    return url


async def main():
    key, secret = get_credentials()

    async with AsyncTransloadit(key, secret) as client:
        assembly = client.new_assembly()
        with get_example_image_path().open("rb") as upload:
            assembly.add_file(upload, "image")
            assembly.add_step(
                "resize",
                "/image/resize",
                {
                    "use": ":original",
                    "width": 120,
                    "height": 120,
                    "resize_strategy": "fit",
                    "format": "png",
                },
            )
            response = await assembly.create(wait=True, resumable=False)

    print("Assembly:", response.data.get("assembly_ssl_url") or response.data.get("assembly_url"))
    print("Resized image:", first_result_url(response.data, "resize"))


if __name__ == "__main__":
    asyncio.run(main())
