import os


def get_upload_filename(file_stream, fallback):
    name = getattr(file_stream, "name", None)
    if isinstance(name, (bytes, os.PathLike)):
        name = os.fsdecode(name)

    if isinstance(name, str):
        filename = os.path.basename(name)
        if filename:
            return filename
    return fallback
