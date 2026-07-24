import json
import pathlib

import pytest

from app.models import CompanyProfile, OctenResult
from app.seed import DEMO_PROFILE

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def profile() -> CompanyProfile:
    return DEMO_PROFILE.model_copy(deep=True)


@pytest.fixture
def octen_payload() -> dict:
    """Recorded Octen response — tests run against fixtures, never the live API."""
    return load_fixture("octen_search.json")


@pytest.fixture
def annotated_results() -> list[OctenResult]:
    from app.models import OctenQuery
    from app.octen.local_index import LocalIndex

    index = LocalIndex()
    return index.search(OctenQuery(query="bone conduction hearing thesis partner", max_results=10))
