"""Generate a signed Smart CDN URL.

This example does not contact Transloadit. It only signs a URL locally.

Run from the repository root:

    TRANSLOADIT_KEY=xxx TRANSLOADIT_SECRET=yyy poetry run python examples/smart_cdn_url.py
"""

import os

from transloadit.client import Transloadit


def get_credentials():
    key = os.getenv("TRANSLOADIT_KEY")
    secret = os.getenv("TRANSLOADIT_SECRET")
    if not key or not secret:
        raise RuntimeError("Please set TRANSLOADIT_KEY and TRANSLOADIT_SECRET.")
    return key, secret


def main():
    key, secret = get_credentials()
    client = Transloadit(key, secret)
    url = client.get_signed_smart_cdn_url(
        workspace=os.getenv("TRANSLOADIT_WORKSPACE", "example-workspace"),
        template=os.getenv("TRANSLOADIT_TEMPLATE", "example-template"),
        input=os.getenv("TRANSLOADIT_INPUT", "image.jpg"),
        url_params={"width": 320, "height": 240, "fit": "crop"},
    )
    print(url)


if __name__ == "__main__":
    main()
