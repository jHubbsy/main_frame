"""Tests for session state and persistence."""

from __future__ import annotations

from pathlib import Path

from mainframe.core.session import Session
from mainframe.providers.base import Message, Role


def test_session_add_message(tmp_path: Path):
    session = Session(sessions_path=tmp_path)
    session.add_message(Message(role=Role.USER, content="hello"))
    assert len(session.messages) == 1
    assert session.messages[0].text == "hello"
    assert session.meta.turn_count == 1


def test_session_auto_title(tmp_path: Path):
    session = Session(sessions_path=tmp_path)
    session.add_message(Message(role=Role.USER, content="What is a monad?"))
    assert session.meta.title == "What is a monad?"


def test_session_persistence(tmp_path: Path):
    # Create and populate
    s1 = Session(session_id="test123", sessions_path=tmp_path)
    s1.add_message(Message(role=Role.USER, content="hello"))
    s1.add_message(Message(role=Role.ASSISTANT, content="hi there"))
    s1.add_message(Message(role=Role.USER, content="how are you"))

    # Reload
    s2 = Session(session_id="test123", sessions_path=tmp_path)
    loaded = s2.load()
    assert loaded is True
    assert len(s2.messages) == 3
    assert s2.messages[0].text == "hello"
    assert s2.messages[1].text == "hi there"
    assert s2.meta.turn_count == 2


def test_session_list(tmp_path: Path):
    Session(session_id="aaa", sessions_path=tmp_path).add_message(
        Message(role=Role.USER, content="first")
    )
    Session(session_id="bbb", sessions_path=tmp_path).add_message(
        Message(role=Role.USER, content="second")
    )
    sessions = Session.list_sessions(tmp_path)
    assert len(sessions) == 2


def test_session_load_nonexistent(tmp_path: Path):
    s = Session(session_id="nope", sessions_path=tmp_path)
    assert s.load() is False
