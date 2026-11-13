import math

from app.ml import EMBEDDING_DIMENSION, _hashing_embedding
from app.schemas import CaseSearchRequest


def test_hashing_embedding_is_stable_and_normalized() -> None:
    first = _hashing_embedding("query: turbo basıncı düşük")
    second = _hashing_embedding("query: turbo basıncı düşük")

    assert first == second
    assert len(first) == EMBEDDING_DIMENSION
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)


def test_case_search_defaults_to_hybrid_mode() -> None:
    payload = CaseSearchRequest(query="çekiş düşüklüğü")

    assert payload.search_mode == "hybrid"
    assert payload.approved_only is False
