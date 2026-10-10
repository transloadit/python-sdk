"""Incremental, bounded Server-Sent Event decoding shared by both transports."""
import codecs
from dataclasses import dataclass
import json

from ._contract import CONTRACT


class StreamError(RuntimeError):
    def __init__(self, status_code, message="Assembly stream is unavailable"):
        self.status_code = status_code
        super().__init__(f"{message} (HTTP {status_code}).")


@dataclass(frozen=True)
class AssemblyEvent:
    event: str
    data: object
    id: str = ""
    retry: int | None = None

    @property
    def terminal(self):
        return any(item["name"] == self.event and item["terminal"] for item in CONTRACT["stream_events"])


class EventParser:
    def __init__(self, max_event_size=1048576):
        if not isinstance(max_event_size, int) or max_event_size < 1:
            raise ValueError("max_event_size must be positive.")
        self.maximum = max_event_size
        self.decoder = codecs.getincrementaldecoder("utf-8-sig")("replace")
        self.line = []
        self.data = []
        self.event = ""
        self.id = ""
        self.retry = None
        self.size = 0
        self.after_cr = False

    def feed(self, chunk):
        for char in self.decoder.decode(chunk):
            if self.after_cr and char == "\n":
                self.after_cr = False
                continue
            self.after_cr = char == "\r"
            self.size += len(char.encode("utf-8"))
            if self.size > self.maximum:
                raise ValueError("Assembly stream event exceeds max_event_size.")
            if char in "\r\n":
                line = "".join(self.line)
                self.line.clear()
                if not line:
                    event = self._dispatch()
                    self.size = 0
                    if event is not None:
                        yield event
                elif not line.startswith(":"):
                    field, _, value = line.partition(":")
                    if value.startswith(" "):
                        value = value[1:]
                    if field == "data":
                        self.data.append(value)
                    elif field == "event":
                        self.event = value
                    elif field == "id" and "\x00" not in value:
                        self.id = value
                    elif field == "retry" and value.isascii() and value.isdecimal():
                        self.retry = int(value)
            else:
                self.line.append(char)

    def _dispatch(self):
        event = None
        if self.data:
            text = "\n".join(self.data)
            kind = self.event or "message"
            known_messages = {item["name"] for item in CONTRACT["stream_events"] if item["kind"] == "message"}
            if kind == "message" and text in known_messages:
                kind = text
            try:
                data = json.loads(text)
            except ValueError:
                data = text
            event = AssemblyEvent(kind, data, self.id, self.retry)
        self.data.clear()
        self.event = ""
        return event
