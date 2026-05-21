"""Create, fetch, update, and delete a Template with the async client.

Run from the repository root:

    TRANSLOADIT_KEY=xxx TRANSLOADIT_SECRET=yyy poetry run python examples/async_template_lifecycle.py
"""

import asyncio
import os
from uuid import uuid4

from transloadit.async_client import AsyncTransloadit


def get_credentials():
    key = os.getenv("TRANSLOADIT_KEY")
    secret = os.getenv("TRANSLOADIT_SECRET")
    if not key or not secret:
        raise RuntimeError("Please set TRANSLOADIT_KEY and TRANSLOADIT_SECRET.")
    return key, secret


def extract_template_id(response_data):
    template_id = response_data.get("id") or response_data.get("template_id")
    if not template_id:
        raise RuntimeError(f"Template response did not contain an id: {response_data}")
    return template_id


async def main():
    key, secret = get_credentials()
    template_id = None
    deleted = False
    template_name = f"python-sdk-async-example-{uuid4().hex[:12]}"

    async with AsyncTransloadit(key, secret) as client:
        try:
            template = client.new_template(template_name)
            template.add_step(
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
            created = await template.create()
            template_id = extract_template_id(created.data)
            print("Created template:", template_id)

            fetched = await client.get_template(template_id)
            print("Fetched template:", fetched.data.get("name") or fetched.data.get("template_name"))

            updated = await client.update_template(
                template_id,
                {
                    "name": f"{template_name}-updated",
                    "template": {
                        "steps": {
                            "resize": {
                                "use": ":original",
                                "robot": "/image/resize",
                                "width": 96,
                                "height": 96,
                                "resize_strategy": "fit",
                                "format": "jpg",
                            },
                        },
                    },
                },
            )
            print("Updated template:", updated.data.get("ok"))

            deleted_response = await client.delete_template(template_id)
            print("Deleted template:", deleted_response.data.get("ok"))
            deleted = True
        finally:
            if template_id and not deleted:
                await client.delete_template(template_id)


if __name__ == "__main__":
    asyncio.run(main())
