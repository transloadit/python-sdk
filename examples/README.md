# Transloadit Python SDK Examples

Run the examples from the repository root after installing the project:

```bash
poetry install
export TRANSLOADIT_KEY="YOUR_TRANSLOADIT_KEY"
export TRANSLOADIT_SECRET="YOUR_TRANSLOADIT_SECRET"
```

## Quickstart Examples

```bash
poetry run python examples/image_resize.py
poetry run python examples/async_image_resize.py
poetry run python examples/resumable_upload.py
poetry run python examples/assembly_with_template.py
poetry run python examples/template_lifecycle.py
poetry run python examples/smart_cdn_url.py
```

`smart_cdn_url.py` only signs a URL locally. The other quickstart examples contact
Transloadit and may create temporary Assemblies or Templates in your account.

## Advanced Examples

These examples require pre-created Templates and, depending on your Template, third-party
provider configuration:

```bash
export TRANSLOADIT_TTS_TEMPLATE_ID="YOUR_TEMPLATE_ID"
poetry run python examples/file_to_tts.py

export TRANSLOADIT_TRANSCRIBE_TEMPLATE_ID="YOUR_TRANSCRIBE_TEMPLATE_ID"
export TRANSLOADIT_TRANSLATE_TEMPLATE_ID="YOUR_TRANSLATE_TEMPLATE_ID"
poetry run python examples/video_translator.py
```
