"""Create a temporary Template and use it to process an uploaded image.

Run from the repository root:

    TRANSLOADIT_KEY=xxx TRANSLOADIT_SECRET=yyy poetry run python examples/assembly_with_template.py
"""

import os
from pathlib import Path
from uuid import uuid4

from transloadit.client import Transloadit


def get_credentials():
    key = os.getenv("TRANSLOADIT_KEY")
    secret = os.getenv("TRANSLOADIT_SECRET")
    if not key or not secret:
        raise RuntimeError("Please set TRANSLOADIT_KEY and TRANSLOADIT_SECRET.")
    return key, secret


def get_example_image_path():
    return Path(__file__).resolve().parent / "fixtures" / "lol_cat.jpg"


def extract_template_id(response_data):
    template_id = response_data.get("id") or response_data.get("template_id")
    if not template_id:
        raise RuntimeError(f"Template response did not contain an id: {response_data}")
    return template_id


def first_result_url(response_data, step_name):
    results = (response_data.get("results") or {}).get(step_name) or []
    if not results:
        raise RuntimeError(f"No results found for step {step_name!r}: {response_data}")
    url = results[0].get("ssl_url") or results[0].get("url")
    if not url:
        raise RuntimeError(f"No result URL found for step {step_name!r}: {response_data}")
    return url


def create_resize_template(client):
    template = client.new_template(f"python-sdk-template-example-{uuid4().hex[:12]}")
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
    return extract_template_id(template.create().data)


def main():
    key, secret = get_credentials()
    client = Transloadit(key, secret)
    template_id = create_resize_template(client)

    try:
        assembly = client.new_assembly({"template_id": template_id})
        with get_example_image_path().open("rb") as upload:
            assembly.add_file(upload, "image")
            response = assembly.create(wait=True, resumable=False)

        print("Assembly:", response.data.get("assembly_ssl_url") or response.data.get("assembly_url"))
        print("Template result:", first_result_url(response.data, "resize"))
    finally:
        client.delete_template(template_id)


if __name__ == "__main__":
    main()
