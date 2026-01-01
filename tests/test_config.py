from pathlib import Path

from termdash.config import load_config


def test_load_config_defaults_when_missing(tmp_path):
    config = load_config(tmp_path / "missing.yaml")
    assert config.sources
    assert config.title


def test_load_config_from_file(tmp_path):
    content = """
    dashboard:
      title: Test Dash
      refresh_ui_seconds: 0.5
    sources:
      - name: Test
        type: rss
        refresh_seconds: 120
        options:
          url: https://example.com/feed
    """
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")

    config = load_config(Path(path))
    assert config.title == "Test Dash"
    assert config.refresh_ui_seconds == 0.5
    assert len(config.sources) == 1
    assert config.sources[0].type == "rss"


def test_config_env_expansion(tmp_path, monkeypatch):
    content = """
    sources:
      - name: Example
        type: rss
        options:
          url: ${EXAMPLE_URL}
    """
    monkeypatch.setenv("EXAMPLE_URL", "https://example.com/feed")
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")

    config = load_config(Path(path))
    assert config.sources[0].options["url"] == "https://example.com/feed"
