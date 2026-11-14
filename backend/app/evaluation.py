import uuid
from time import perf_counter

from sqlalchemy.orm import Session

from app import models, schemas, services


def run_retrieval_evaluation(
    db: Session,
    queries: list[models.EvaluationQuery],
    modes: list[str],
    top_k: int,
    user_id: uuid.UUID,
) -> tuple[list[dict], list[dict], str | None]:
    metrics: list[dict] = []
    details: list[dict] = []

    for mode in modes:
        hits = 0
        reciprocal_rank_total = 0.0
        latency_total = 0.0
        for evaluation_query in queries:
            payload = schemas.CaseSearchRequest(
                query=evaluation_query.query_text,
                dtc_code=evaluation_query.dtc_code,
                limit=top_k,
                search_mode=mode,
                approved_only=True,
            )
            started = perf_counter()
            matches = services.search_cases(db, payload, user_id)
            latency_ms = (perf_counter() - started) * 1000
            result_ids = [match.work_order.id for match in matches]
            try:
                rank = result_ids.index(evaluation_query.expected_work_order_id) + 1
            except ValueError:
                rank = None
            reciprocal_rank = 1 / rank if rank else 0.0
            if rank:
                hits += 1
            reciprocal_rank_total += reciprocal_rank
            latency_total += latency_ms
            details.append(
                {
                    "query_id": str(evaluation_query.id),
                    "query_name": evaluation_query.name,
                    "expected_work_order_id": str(evaluation_query.expected_work_order_id),
                    "mode": mode,
                    "rank": rank,
                    "reciprocal_rank": round(reciprocal_rank, 4),
                    "latency_ms": round(latency_ms, 2),
                    "result_work_order_ids": [str(item) for item in result_ids],
                }
            )

        query_count = len(queries)
        metrics.append(
            {
                "mode": mode,
                "hit_rate": round(hits / query_count, 4) if query_count else 0.0,
                "mrr": round(reciprocal_rank_total / query_count, 4) if query_count else 0.0,
                "avg_latency_ms": round(latency_total / query_count, 2) if query_count else 0.0,
                "hits": hits,
                "query_count": query_count,
            }
        )

    best = max(
        metrics,
        key=lambda item: (item["hit_rate"], item["mrr"], -item["avg_latency_ms"]),
        default=None,
    )
    return metrics, details, best["mode"] if best else None


def build_evidence_summary(matches: list[services.CaseMatch]) -> dict:
    if not matches:
        return {
            "summary": "Onaylı geçmiş servis vakalarında yeterli kanıt bulunamadı.",
            "confidence": "insufficient",
            "confidence_score": 0.0,
            "suggested_checks": [],
            "limitations": [
                "Yeni vaka kaydı ve usta onayı olmadan güvenilir öneri üretilemez.",
                "Bu çıktı kesin teşhis değildir.",
            ],
        }

    top = matches[0]
    order = top.work_order
    vehicle = order.vehicle
    summary_parts = [
        f"En güçlü kanıt {vehicle.brand} {vehicle.model} aracına ait onaylı servis vakasıdır."
    ]
    if order.diagnosis:
        summary_parts.append(f"Bu vakada doğrulanan arıza: {order.diagnosis}.")
    if order.actions:
        summary_parts.append(f"Uygulanan işlem: {order.actions}.")
    if order.result:
        summary_parts.append(f"Kaydedilen sonuç: {order.result}.")

    suggested_checks: list[str] = []
    for match in matches[:5]:
        for value in (match.work_order.diagnosis, match.work_order.actions):
            normalized = value.strip() if value else ""
            if normalized and normalized not in suggested_checks:
                suggested_checks.append(normalized)
            if len(suggested_checks) >= 5:
                break
        if len(suggested_checks) >= 5:
            break

    confidence_score = min(1.0, top.score * 0.75 + min(len(matches), 3) / 3 * 0.25)
    if confidence_score >= 0.78 and len(matches) >= 2:
        confidence = "high"
    elif confidence_score >= 0.58:
        confidence = "medium"
    else:
        confidence = "low"

    limitations = [
        "Öneri yalnızca bu hesaptaki usta onaylı geçmiş vakalara dayanır.",
        "Nihai arıza tespiti fiziksel kontrol ve yetkili usta onayı gerektirir.",
    ]
    if len(matches) < 2:
        limitations.insert(0, "Benzerliği destekleyen vaka sayısı düşüktür.")

    return {
        "summary": " ".join(summary_parts),
        "confidence": confidence,
        "confidence_score": round(confidence_score, 4),
        "suggested_checks": suggested_checks,
        "limitations": limitations,
    }
