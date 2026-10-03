"""Persistent target configuration tests."""

from pathlib import Path

import pytest

from infra_watch.config import config_path, load_http_targets


def test_load_targets_preserves_order_and_ignores_future_docker_config(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[[http_targets]]\nname="app"\nurl="https://app.test"\n[[docker_hosts]]\nname="server"\n')
    targets = load_http_targets(path)
    assert [(target.name, target.url) for target in targets] == [("app", "https://app.test")]


@pytest.mark.parametrize("content", [
    "not valid toml", 'http_targets="bad"', 'http_targets=[1]',
    '[[http_targets]]\nname="app"',
    '[[http_targets]]\nname=""\nurl="https://app.test"',
    '[[http_targets]]\nname="app"\nurl=42',
    '[[http_targets]]\nname="app"\nurl="ftp://app.test"',
    '[[http_targets]]\nname="app"\nurl="http:///"',
    '[[http_targets]]\nname="app"\nurl="https://app.test"\n' * 2,
])
def test_invalid_configuration_is_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "config.toml"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_http_targets(path)


def test_missing_config_is_actionable(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unable to load configuration"):
        load_http_targets(tmp_path / "missing.toml")


def test_config_path_precedence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert config_path() == tmp_path / ".config/infrawatch/config.toml"
    Path("config.toml").touch()
    assert config_path() == Path("config.toml")
    assert config_path(Path("custom.toml")) == Path("custom.toml")
