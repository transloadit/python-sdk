"""Advanced example: translate speech and merge translated audio into a video.

This requires two pre-created Templates in your Transloadit account:

1. A transcription Template that produces a `transcribe_json` result.
2. A video merge Template that accepts `video`, `target_language`, `source_language`, and
   `ffmpeg` fields and produces a `merged_video` result.

Run from the repository root:

    TRANSLOADIT_KEY=xxx TRANSLOADIT_SECRET=yyy \
      TRANSLOADIT_TRANSCRIBE_TEMPLATE_ID=xxx TRANSLOADIT_TRANSLATE_TEMPLATE_ID=yyy \
      poetry run python examples/video_translator.py
"""

import json
import os
import tempfile
import urllib.request
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


def create_assembly_with_template(client, template_id, file_path=None, fields=None):
    assembly = client.new_assembly({"template_id": template_id, "fields": fields or {}})

    if file_path is None:
        return assembly.create(retries=5, wait=True)

    with Path(file_path).open("rb") as upload:
        assembly.add_file(upload, Path(file_path).name)
        return assembly.create(retries=5, wait=True)


def download_url(url, path, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        Path(path).write_bytes(response.read())


def build_ssml_and_ffmpeg(words):
    if not words:
        raise RuntimeError("Transcription result did not contain any words.")

    sentences = []
    start_times = []
    end_times = []
    current_sentence = []

    start_times.append(words[0]["startTime"])
    for index, word in enumerate(words):
        if word["text"] == "." and index != len(words) - 1:
            start_times.append(words[index + 1]["startTime"])
        if word["text"] != ".":
            current_sentence.append(word["text"])
            continue
        sentences.append(" ".join(current_sentence) + ".")
        end_times.append(words[index - 1]["endTime"])
        current_sentence = []

    ffmpeg = "volume=enable:volume=1"
    ssml_parts = ["<speak><par>"]
    for index, sentence in enumerate(sentences):
        ssml_parts.append(f'<media begin="{start_times[index]}"><speak>{sentence}</speak></media>')
        ffmpeg += (
            f", volume=enable='between(t,{start_times[index]},{end_times[index]})':volume=0.2"
        )
    ssml_parts.append("</par></speak>")
    return "".join(ssml_parts), ffmpeg


def main():
    client = Transloadit(
        get_required_env("TRANSLOADIT_KEY"),
        get_required_env("TRANSLOADIT_SECRET"),
    )
    transcribe_template_id = get_required_env("TRANSLOADIT_TRANSCRIBE_TEMPLATE_ID")
    translate_template_id = get_required_env("TRANSLOADIT_TRANSLATE_TEMPLATE_ID")
    source_language = os.getenv("TRANSLOADIT_SOURCE_LANGUAGE", "en-GB")
    target_language = os.getenv("TRANSLOADIT_TARGET_LANGUAGE", "nl-NL")
    example_dir = Path(__file__).resolve().parent

    transcribe_response = create_assembly_with_template(
        client,
        transcribe_template_id,
        file_path=example_dir / "fixtures" / "crab.mp4",
        fields={"language": source_language},
    )
    transcription_url = first_result_url(transcribe_response.data, "transcribe_json")
    video_url = transcribe_response.data["uploads"][0]["ssl_url"]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        transcript_path = tmpdir_path / "transcribe_json.json"
        download_url(transcription_url, transcript_path)
        with transcript_path.open() as transcript:
            transcript_data = json.load(transcript)

        ssml, ffmpeg = build_ssml_and_ffmpeg(transcript_data["words"])
        text_path = tmpdir_path / "text.txt"
        text_path.write_text(ssml)

        translated_response = create_assembly_with_template(
            client,
            translate_template_id,
            file_path=text_path,
            fields={
                "target_language": target_language,
                "source_language": source_language,
                "video": video_url,
                "ffmpeg": ffmpeg,
            },
        )
    print("Translated video:", first_result_url(translated_response.data, "merged_video"))


if __name__ == "__main__":
    main()
