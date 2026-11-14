import uuid
from types import SimpleNamespace

from app import evaluation, services


def case_match(work_order_id: uuid.UUID, score: float = 0.8):
    vehicle = SimpleNamespace(brand="Renault", model="Clio")
    order = SimpleNamespace(
        id=work_order_id,
        vehicle=vehicle,
        diagnosis="Turbo hortumu kaçağı",
        actions="Hortum değiştirildi",
        result="Çekiş normale döndü",
    )
    return services.CaseMatch(order, "test", score, "hybrid")


def test_retrieval_metrics_calculate_hit_rate_and_mrr(monkeypatch):
    expected_first = uuid.uuid4()
    expected_second = uuid.uuid4()
    queries = [
        SimpleNamespace(
            id=uuid.uuid4(),
            name="Birinci",
            query_text="çekiş düşüklüğü",
            dtc_code=None,
            expected_work_order_id=expected_first,
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            name="İkinci",
            query_text="turbo basıncı",
            dtc_code="P0299",
            expected_work_order_id=expected_second,
        ),
    ]
    unrelated = uuid.uuid4()

    def fake_search(_db, payload, _user_id):
        if payload.query == "çekiş düşüklüğü":
            return [case_match(expected_first), case_match(unrelated)]
        return [case_match(unrelated), case_match(expected_second)]

    monkeypatch.setattr(evaluation.services, "search_cases", fake_search)
    metrics, details, best_mode = evaluation.run_retrieval_evaluation(
        object(), queries, ["hybrid"], 5, uuid.uuid4()
    )

    assert metrics[0]["hit_rate"] == 1.0
    assert metrics[0]["mrr"] == 0.75
    assert [item["rank"] for item in details] == [1, 2]
    assert best_mode == "hybrid"


def test_evidence_summary_reports_source_and_limitations():
    result = evaluation.build_evidence_summary([case_match(uuid.uuid4(), 0.9)])

    assert result["confidence"] in {"medium", "high"}
    assert "Turbo hortumu kaçağı" in result["summary"]
    assert "Hortum değiştirildi" in result["suggested_checks"]
    assert any("Nihai arıza" in item for item in result["limitations"])


def test_evidence_summary_handles_no_approved_cases():
    result = evaluation.build_evidence_summary([])

    assert result["confidence"] == "insufficient"
    assert result["confidence_score"] == 0
    assert result["suggested_checks"] == []
