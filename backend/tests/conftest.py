"""Shared test fixtures.

`target_list` gives every test a validated `TargetList` loaded from the pinned
JSON fixture — the same object shape your teammate's pipeline will hand you.
Build and test the Composio side against this without running Octen.
"""

import pathlib

import pytest

from app.models.output import TargetList

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "target_list.json"


@pytest.fixture
def target_list() -> TargetList:
    return TargetList.model_validate_json(FIXTURE.read_text())
