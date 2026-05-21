import os
from pathlib import Path
from uuid import uuid4
from unittest import IsolatedAsyncioTestCase

import pytest

from transloadit.async_client import AsyncTransloadit
from transloadit.client import Transloadit


def _is_enabled():
    flag = os.getenv("PYTHON_SDK_E2E", "")
    return flag.lower() in {"1", "true", "yes", "on"}


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not _is_enabled(), reason="Set PYTHON_SDK_E2E=1 to run E2E tests"),
]


def _get_e2e_credentials():
    key = os.getenv("TRANSLOADIT_KEY")
    secret = os.getenv("TRANSLOADIT_SECRET")

    if not key or not secret:
        pytest.skip("TRANSLOADIT_KEY and TRANSLOADIT_SECRET must be set to run E2E tests")

    return key, secret


def _get_fixture_path():
    fixture_path = Path(__file__).resolve().parents[1] / "chameleon.jpg"
    if not fixture_path.exists():
        pytest.skip("chameleon.jpg fixture missing; run from repository root")

    return fixture_path


def _add_resize_step(assembly, width=128, height=128):
    assembly.add_step(
        "resize",
        "/image/resize",
        {
            "use": ":original",
            "width": width,
            "height": height,
            "resize_strategy": "fit",
            "format": "png",
        },
    )


def _assert_e2e_image_resize(data, fixture_path, expected_field=None, expected_fields=None):
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
    if expected_field:
        assert upload_info.get("field") == expected_field

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
    if expected_fields:
        fields = data.get("fields") or {}
        for key, value in expected_fields.items():
            assert fields.get(key) == value, f"Expected field {key}={value!r}, got {fields!r}"
    print(
        "[python-sdk][e2e] Result dimensions: "
        f"{width}x{height}, ssl_url={ssl_url}, basename={upload_info.get('basename')}, "
        f"filename={upload_info.get('name')}"
    )


def _extract_template_id(data):
    template_id = data.get("id") or data.get("template_id")
    assert template_id, f"Template response did not contain an id: {data}"
    return template_id


def _extract_template_name(data):
    return data.get("name") or data.get("template_name")


def _extract_template_content(data):
    return data.get("content") or data.get("template_content") or data.get("template")


def _assert_template(data, expected_name, expected_width):
    assert _extract_template_name(data) == expected_name, data
    content = _extract_template_content(data)
    assert isinstance(content, dict), data
    steps = content.get("steps") or {}
    resize = steps.get("resize") or {}
    assert resize.get("robot") == "/image/resize", data
    assert int(resize.get("width")) == expected_width, data


def test_e2e_image_resize():
    key, secret = _get_e2e_credentials()
    fixture_path = _get_fixture_path()
    client = Transloadit(key, secret)

    assembly = client.new_assembly()

    with fixture_path.open("rb") as upload:
        assembly.add_file(upload)
        _add_resize_step(assembly)
        response = assembly.create(wait=True, resumable=False)

    _assert_e2e_image_resize(response.data, fixture_path)


def test_e2e_resumable_image_resize():
    key, secret = _get_e2e_credentials()
    fixture_path = _get_fixture_path()
    expected_fields = {"python_sdk_e2e": "sync-resumable"}
    client = Transloadit(key, secret)

    assembly = client.new_assembly(params={"fields": expected_fields})

    with fixture_path.open("rb") as upload:
        assembly.add_file(upload, "resumable_file")
        _add_resize_step(assembly)
        response = assembly.create(wait=True, resumable=True)

    _assert_e2e_image_resize(
        response.data,
        fixture_path,
        expected_field="resumable_file",
        expected_fields=expected_fields,
    )


class TestAsyncE2EUpload(IsolatedAsyncioTestCase):
    async def test_e2e_image_resize(self):
        key, secret = _get_e2e_credentials()
        fixture_path = _get_fixture_path()

        async with AsyncTransloadit(key, secret) as client:
            assembly = client.new_assembly()

            with fixture_path.open("rb") as upload:
                assembly.add_file(upload)
                _add_resize_step(assembly)
                response = await assembly.create(wait=True, resumable=False)

        _assert_e2e_image_resize(response.data, fixture_path)

    async def test_e2e_resumable_image_resize(self):
        key, secret = _get_e2e_credentials()
        fixture_path = _get_fixture_path()
        expected_fields = {"python_sdk_e2e": "async-resumable"}

        async with AsyncTransloadit(key, secret) as client:
            assembly = client.new_assembly(params={"fields": expected_fields})

            with fixture_path.open("rb") as upload:
                assembly.add_file(upload, "async_resumable_file")
                _add_resize_step(assembly)
                response = await assembly.create(wait=True, resumable=True)

        _assert_e2e_image_resize(
            response.data,
            fixture_path,
            expected_field="async_resumable_file",
            expected_fields=expected_fields,
        )

    async def test_e2e_template_lifecycle(self):
        key, secret = _get_e2e_credentials()
        template_name = f"python-sdk-e2e-{uuid4().hex[:12]}"
        updated_name = f"{template_name}-updated"
        template_id = None
        deleted = False

        async with AsyncTransloadit(key, secret) as client:
            try:
                template = client.new_template(template_name)
                _add_resize_step(template, width=64, height=64)
                created = await template.create()

                template_id = _extract_template_id(created.data)
                fetched = await client.get_template(template_id)
                _assert_template(fetched.data, template_name, 64)

                updated = await client.update_template(
                    template_id,
                    {
                        "name": updated_name,
                        "template": {
                            "steps": {
                                "resize": {
                                    "robot": "/image/resize",
                                    "use": ":original",
                                    "width": 96,
                                    "height": 96,
                                    "resize_strategy": "fit",
                                    "format": "jpg",
                                },
                            },
                        },
                    },
                )
                assert updated.data.get("ok") == "TEMPLATE_UPDATED", updated.data

                refetched = await client.get_template(template_id)
                _assert_template(refetched.data, updated_name, 96)

                deleted_response = await client.delete_template(template_id)
                assert deleted_response.data.get("ok") == "TEMPLATE_DELETED", deleted_response.data
                deleted = True
            finally:
                if template_id and not deleted:
                    await client.delete_template(template_id)
