from pathlib import Path

import pytest

from pyprojectx.config import Config


def test_no_config():
    config = Config(Path(__file__).with_name("test-no-config.toml"))
    assert config.get_tool_requirements("tool") == []
    assert not config.is_tool("tool")
    assert config.get_alias("alias") == (None, None)


def test_no_tool_config():
    config = Config(Path(__file__).with_name("test-no-tool-config.toml"))
    assert config.get_alias("run") == (None, "run command")
    with pytest.raises(
        Warning, match=r"Invalid alias wrong-tool-alias: 'wrong-tool' is not defined in \[tool.pyprojectx\]"
    ):
        config.get_alias("wrong-tool-alias")


def test_tool_config():
    config = Config(Path(__file__).with_name("test.toml"))

    assert config.is_tool("tool-1")
    assert config.get_tool_requirements("tool-1") == ["req1", "req2"]

    assert config.is_tool("tool-2")
    assert config.get_tool_requirements("tool-2") == ["tool2 requirement"]

    assert config.is_tool("tool-3")
    assert config.get_tool_requirements("tool-3") == ["req1", "req2", "req3"]

    assert not config.is_tool("nope")
    assert config.get_tool_requirements("nope") == []


def test_alias_config():
    config = Config(Path(__file__).with_name("test.toml"))
    assert config.get_alias("alias-1") == ("tool-1", "tool-1 arg")
    assert config.get_alias("alias-2") == ("tool-2", "tool-2 arg1 arg2")
    assert config.get_alias("alias-3") == ("tool-1", "command arg")
    assert config.get_alias("alias-4") == ("tool-2", "command --default @arg:x")
    assert config.get_alias("combined-alias") == (None, "./pw alias-1 && ./pw alias-2 ./pw shell-command")
    assert config.get_alias("shell-command") == (None, "ls -al")
    assert config.get_alias("backward-compatible-tool-ref") == ("tool-1", "command arg")


def test_invalid_toml():
    with pytest.raises(Warning, match=r".+tests/invalid.toml: Illegal character '\\n' \(at line 2, column 15\)"):
        Config(Path(__file__).with_name("invalid.toml"))


def test_unexisting_toml():
    with pytest.raises(Warning, match=r"No such file or directory"):
        Config(Path(__file__).with_name("unexisting.toml"))