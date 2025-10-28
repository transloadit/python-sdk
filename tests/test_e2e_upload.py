import os
from pathlib import Path

import pytest

from transloadit.client import Transloadit


def _is_enabled():
    flag = os.getenv("PYTHON_SDK_E2E", "")
    return flag.lower() in {"1", "true", "yes", "on"}


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not _is_enabled(), reason="Set PYTHON_SDK_E2E=1 to run E2E tests"),
]


def test_e2e_image_resize():
    key = os.getenv("TRANSLOADIT_KEY")
    secret = os.getenv("TRANSLOADIT_SECRET")

    if not key or not secret:
        pytest.skip("TRANSLOADIT_KEY and TRANSLOADIT_SECRET must be set to run E2E tests")

    fixture_path = Path(__file__).resolve().parents[1] / "chameleon.jpg"
    if not fixture_path.exists():
        pytest.skip("chameleon.jpg fixture missing; run from repository root")

    client = Transloadit(key, secret)

    assembly = client.new_assembly()

    with fixture_path.open("rb") as upload:
        assembly.add_file(upload)
        assembly.add_step(
            "resize",
            "/image/resize",
            {
                "use": ":original",
                "width": 128,
                "height": 128,
                "resize_strategy": "fit",
                "format": "png",
            },
        )

        response = assembly.create(wait=True, resumable=False)

    data = response.data
    assembly_ssl_url = data.get("assembly_ssl_url") or data.get("assembly_url")
    assembly_id = data.get("assembly_id")
    print(f"[python-sdk][e2e] Assembly URL: {assembly_ssl_url} (id={assembly_id})")
    assert data.get("ok") == "ASSEMBLY_COMPLETED", data

    uploads = data.get("uploads") or []
    assert uploads, f"Expected uploads in assembly response: {data}"
    upload_info = uploads[0]
    basename = upload_info.get("basename")
    if basename:
        assert basename == fixture_path.stem
    filename = upload_info.get("name")
    if filename:
        assert filename == fixture_path.name

    results = (data.get("results") or {}).get("resize") or []
    assert results, f"Expected resize results in assembly response: {data}"
    first_result = results[0]

    ssl_url = first_result.get("ssl_url")
    assert ssl_url and ssl_url.startswith("https://"), f"Unexpected ssl_url: {ssl_url}"

    meta = first_result.get("meta") or {}
    width = meta.get("width")
    height = meta.get("height")
    if width is not None:
        width = int(width)
    if height is not None:
        height = int(height)
    assert width and height, f"Missing dimensions in result metadata: {meta}"
    assert 0 < width <= 128 and 0 < height <= 128
    print(
        "[python-sdk][e2e] Result dimensions: "
        f"{width}x{height}, ssl_url={ssl_url}, basename={upload_info.get('basename')}, "
        f"filename={upload_info.get('name')}"
    )
