import json
import os
import pathlib

import pytest

# Tests run against fixtures and the local index only — never a live provider,
# regardless of what happens to be sitting in .env.
for _key in ("COMPOSIO_API_KEY", "OPENAI_API_KEY", "OPENAI_MODEL_PLANNER", "OPENAI_MODEL_EXTRACTOR", "OCTEN_API_KEY"):
    os.environ.pop(_key, None)
os.environ["PROOFLINE_SIMULATE_LATENCY"] = "0"

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
