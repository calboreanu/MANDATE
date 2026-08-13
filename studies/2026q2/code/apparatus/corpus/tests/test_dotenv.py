"""Tests for the corpus CLI's .env auto-loader."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.corpus.cli import _load_dotenv


def test_loads_simple_key_value(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("FOO_KEY=value123\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FOO_KEY", raising=False)
    n = _load_dotenv()
    assert n == 1
    assert os.environ.get("FOO_KEY") == "value123"


def test_skips_comments_and_blank_lines(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "# a comment\n\n  \nBAR_KEY=ok\n# another\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BAR_KEY", raising=False)
    assert _load_dotenv() == 1
    assert os.environ["BAR_KEY"] == "ok"


def test_does_not_overwrite_existing_environ(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("KEEP_KEY=from_file\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KEEP_KEY", "from_shell")
    n = _load_dotenv()
    assert n == 0
    assert os.environ["KEEP_KEY"] == "from_shell"


def test_strips_surrounding_quotes(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text('QUOTED_KEY="abc"\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QUOTED_KEY", raising=False)
    _load_dotenv()
    assert os.environ["QUOTED_KEY"] == "abc"


def test_walks_one_parent_directory(tmp_path, monkeypatch):
    # .env at the project root, CLI run from a subdirectory
    (tmp_path / ".env").write_text("PARENT_KEY=p\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    monkeypatch.delenv("PARENT_KEY", raising=False)
    _load_dotenv()
    assert os.environ["PARENT_KEY"] == "p"


def test_missing_file_is_silent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert _load_dotenv() == 0
