"""Edit standard HTTP target tables while preserving unrelated configuration."""

import json
import os
from pathlib import Path
import re
import tempfile
import tomllib

from infra_watch.config import load_http_targets


def edit_target(path: Path, name: str, url: str | None = None) -> None:
    """Add a target, or remove it when URL is absent, using an atomic replacement."""
    path = path.expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ValueError("Unable to create configuration directory") from error
    if path.is_symlink():
        raise ValueError("Refusing to replace a symlink configuration")
    lock_path = path.with_name(path.name + ".lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError as error:
        raise ValueError("Cannot lock configuration; another edit may be in progress") from error
    temp_path: Path | None = None
    try:
        original = path.read_bytes() if path.exists() else None
        text = original.decode("utf-8") if original is not None else ""
        entries = load_http_targets(path) if original is not None else []
        if url is not None:
            if any(target.name == name.strip() for target in entries):
                raise ValueError("Target name already exists")
            text = text.rstrip() + "\n\n[[http_targets]]\n" + (
                f"name = {json.dumps(name, ensure_ascii=False)}\n"
                f"url = {json.dumps(url, ensure_ascii=False)}\n"
            )
        else:
            if not any(target.name == name for target in entries):
                raise ValueError("Target name not found")
            lines = text.splitlines(keepends=True)
            headers = [i for i, line in enumerate(lines) if line.lstrip().startswith("[")]
            spans = []
            for position, start in enumerate(headers):
                if re.fullmatch(r"\s*\[\[http_targets\]\]\s*(?:#.*)?", lines[start].rstrip("\r\n")):
                    end = headers[position + 1] if position + 1 < len(headers) else len(lines)
                    entry = tomllib.loads("".join(lines[start:end]))["http_targets"][0]
                    spans.append((start, end, entry.get("name", "").strip()))
            if len(spans) != len(entries):
                raise ValueError("Editing requires standard [[http_targets]] tables; edit this layout manually")
            start, end, _ = next(span for span in spans if span[2] == name)
            # Keep trailing blank lines and comments belonging to the next section.
            while end > start + 1 and (not lines[end - 1].strip() or lines[end - 1].lstrip().startswith("#")):
                end -= 1
            text = "".join(lines[:start] + lines[end:])
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".infrawatch-", delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(text.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        load_http_targets(temp_path)
        if original is not None:
            if path.read_bytes() != original:
                raise ValueError("Configuration changed during edit; retry")
            os.chmod(temp_path, path.stat().st_mode & 0o777)
        elif path.exists():
            raise ValueError("Configuration appeared during edit; retry")
        os.replace(temp_path, path)
    except (OSError, UnicodeError, KeyError, StopIteration) as error:
        raise ValueError("Unable to edit configuration safely") from error
    finally:
        os.close(lock_fd)
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        lock_path.unlink(missing_ok=True)
