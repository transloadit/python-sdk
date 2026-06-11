"""Advanced example: process a document with a pre-created text-to-speech template.

This requires a Template in your Transloadit account with steps similar to:

{
  "steps": {
    ":original": {"robot": "/upload/handle"},
    "convert": {"use": ":original", "robot": "/document/convert", "format": "txt"},
    "speech": {
      "use": "convert",
      "robot": "/text/speak",
      "result": true,
      "provider": "gcp",
      "target_language": "en-US",
      "voice": "female-1"
    }
  }
}

Run from the repository root:

    TRANSLOADIT_KEY=xxx TRANSLOADIT_SECRET=yyy TRANSLOADIT_TTS_TEMPLATE_ID=xxx \
      poetry run python examples/file_to_tts.py
"""

import os
from pathlib import Path

from transloadit.client import Transloadit


def get_required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Please set {name}.")
    return value


def first_result_url(response_data, step_name):
    results = (response_data.get("results") or {}).get(step_name) or []
    if not results:
        raise RuntimeError(f"No results found for step {step_name!r}: {response_data}")
    url = results[0].get("ssl_url") or results[0].get("url")
    if not url:
        raise RuntimeError(f"No result URL found for step {step_name!r}: {response_data}")
    return url


def main():
    client = Transloadit(
        get_required_env("TRANSLOADIT_KEY"),
        get_required_env("TRANSLOADIT_SECRET"),
    )
    template_id = get_required_env("TRANSLOADIT_TTS_TEMPLATE_ID")
    document_path = Path(__file__).resolve().parent / "fixtures" / "document.doc"

    assembly = client.new_assembly({"template_id": template_id})
    with document_path.open("rb") as upload:
        assembly.add_file(upload, "document")
        response = assembly.create(retries=5, wait=True)

    print("Generated speech:", first_result_url(response.data, "speech"))


if __name__ == "__main__":
    main()
