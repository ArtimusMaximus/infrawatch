"""Target editing preserves inventories and rejects unsafe edits."""

from pathlib import Path
import tomllib

import pytest

from infra_watch.targets import edit_target
from infra_watch import cli


def test_add_list_remove_preserves_docker_and_comments(tmp_path: Path, capsys) -> None:
    path = tmp_path / "config.toml"
    original = '# Docker inventory\n[[docker_hosts]]\nname="server"\nssh_target="server.test"\n'
    path.write_text(original)
    assert cli.main(["targets", "add", "app", "https://app.test", "--config", str(path)]) == 0
    assert cli.main(["targets", "list", "--config", str(path)]) == 0
    assert "app: https://app.test" in capsys.readouterr().out
    assert cli.main(["targets", "remove", "app", "--config", str(path)]) == 0
    assert original.strip() in path.read_text()
    assert tomllib.loads(path.read_text())["docker_hosts"][0]["name"] == "server"


def test_create_config_and_quoted_values(tmp_path: Path) -> None:
    path = tmp_path / "nested/config.toml"
    edit_target(path, 'my "app"', "https://app.test")
    assert tomllib.loads(path.read_text())["http_targets"][0]["name"] == 'my "app"'
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("name,url", [("app", "https://other.test"), ("new", "invalid"), ("missing", None)])
def test_failed_edit_leaves_file_unchanged(tmp_path: Path, name, url) -> None:
    path = tmp_path / "config.toml"
    edit_target(path, "app", "https://app.test")
    original = path.read_bytes()
    with pytest.raises(ValueError):
        edit_target(path, name, url)
    assert path.read_bytes() == original
    assert not path.with_name("config.toml.lock").exists()
    assert not list(tmp_path.glob(".infrawatch-*"))


def test_remove_first_target_preserves_second_and_docker(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    edit_target(path, "first", "https://first.test")
    edit_target(path, "second", "https://second.test")
    with path.open("a") as stream:
        stream.write('\n# Keep me\n[[docker_hosts]]\nname="server"\nssh_target="server.test"\n')
    edit_target(path, "first")
    data = tomllib.loads(path.read_text())
    assert data["http_targets"][0]["name"] == "second"
    assert data["docker_hosts"][0]["name"] == "server"
    assert "# Keep me" in path.read_text()


def test_lock_prevents_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    lock = path.with_name("config.toml.lock")
    lock.touch()
    with pytest.raises(ValueError, match="lock"):
        edit_target(path, "app", "https://app.test")
    assert lock.exists()
    assert not path.exists()


def test_inline_layout_is_not_destroyed(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    original = 'http_targets = [{name="app", url="https://app.test"}]'
    path.write_text(original)
    with pytest.raises(ValueError, match="standard"):
        edit_target(path, "app")
    assert path.read_text() == original


def test_atomic_replace_failure_preserves_inventory(tmp_path: Path, monkeypatch) -> None:
    from infra_watch import targets
    path = tmp_path / "config.toml"
    edit_target(path, "app", "https://app.test")
    original = path.read_bytes()
    def fail_replace(source, destination):
        raise OSError("replace failed")
    monkeypatch.setattr(targets.os, "replace", fail_replace)
    with pytest.raises(ValueError, match="safely"):
        edit_target(path, "new", "https://new.test")
    assert path.read_bytes() == original
    assert not path.with_name("config.toml.lock").exists()


def test_concurrent_external_edit_is_preserved(tmp_path: Path, monkeypatch) -> None:
    from infra_watch import targets
    path = tmp_path / "config.toml"
    edit_target(path, "app", "https://app.test")
    original = path.read_bytes()
    validate = targets.load_http_targets
    def concurrent_change(candidate):
        result = validate(candidate)
        if candidate != path:
            path.write_bytes(original + b"\n# external edit\n")
        return result
    monkeypatch.setattr(targets, "load_http_targets", concurrent_change)
    with pytest.raises(ValueError, match="changed"):
        edit_target(path, "new", "https://new.test")
    assert path.read_bytes() == original + b"\n# external edit\n"
