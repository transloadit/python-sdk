"""Create, fetch, update, and delete a Template.

Run from the repository root:

    TRANSLOADIT_KEY=xxx TRANSLOADIT_SECRET=yyy poetry run python examples/template_lifecycle.py
"""

import os
from uuid import uuid4

from transloadit.client import Transloadit


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


def main():
    key, secret = get_credentials()
    client = Transloadit(key, secret)
    template_id = None
    deleted = False
    template_name = f"python-sdk-example-{uuid4().hex[:12]}"

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
        created = template.create()
        template_id = extract_template_id(created.data)
        print("Created template:", template_id)

        fetched = client.get_template(template_id)
        print("Fetched template:", fetched.data.get("name") or fetched.data.get("template_name"))

        updated = client.update_template(
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

        deleted_response = client.delete_template(template_id)
        print("Deleted template:", deleted_response.data.get("ok"))
        deleted = True
    finally:
        if template_id and not deleted:
            client.delete_template(template_id)


if __name__ == "__main__":
    main()
