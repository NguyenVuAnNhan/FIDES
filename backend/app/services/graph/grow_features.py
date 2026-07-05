from __future__ import annotations

from dataclasses import dataclass

from backend.app.models import AlternativeCreditProfile
from backend.app.services.graph.neo4j_client import graph_available, run_read

REPEAT_COUNTERPARTIES = """
MATCH (b:Business {business_id: $business_id})-[r:REPEAT_WITH]->(:Counterparty)
WHERE r.tx_count >= 2
RETURN count(r) AS repeat_counterparty_count
"""

VERIFIED_REPEAT = """
MATCH (b:Business {business_id: $business_id})-[r:REPEAT_WITH]->(c:Counterparty)
WHERE r.tx_count >= 2 AND c.verified = true
RETURN count(c) AS verified_counterparty_count
"""

TOTAL_BUYERS = """
MATCH (b:Business {business_id: $business_id})-[:SOLD]->(:Invoice)<-[:BOUGHT]-(c:Counterparty)
RETURN count(DISTINCT c) AS total_buyers
"""

INVOICE_COUNT = """
MATCH (b:Business {business_id: $business_id})-[:SOLD]->(i:Invoice)
RETURN count(i) AS invoice_count
"""


@dataclass(frozen=True)
class GrowGraphFeatures:
    trust_graph_score: float
    repeat_counterparty_count: int
    verified_counterparty_count: int
    network_centrality_score: float
    signals: list[str]


def fetch_grow_graph_features(business_id: str) -> GrowGraphFeatures:
    if not graph_available() or not business_id:
        return _empty_features()

    repeat = _scalar(REPEAT_COUNTERPARTIES, business_id, "repeat_counterparty_count")
    verified = _scalar(VERIFIED_REPEAT, business_id, "verified_counterparty_count")
    total_buyers = max(1, _scalar(TOTAL_BUYERS, business_id, "total_buyers"))
    invoice_count = _scalar(INVOICE_COUNT, business_id, "invoice_count")

    centrality = min(1.0, repeat / total_buyers)
    repeat_strength = min(1.0, repeat / 15)
    verified_strength = min(1.0, verified / 10)
    depth_strength = min(1.0, invoice_count / 20)

    trust_graph_score = round(
        min(1.0, 0.4 * repeat_strength + 0.3 * verified_strength + 0.2 * centrality + 0.1 * depth_strength),
        2,
    )
    network_centrality_score = round(centrality, 2)

    signals: list[str] = []
    if repeat >= 8:
        signals.append("repeat_buyer_relationships")
    elif repeat >= 2:
        signals.append("emerging_repeat_buyers")
    else:
        signals.append("thin_network_history")
    if verified >= 3:
        signals.append("verified_counterparty_network")
    if invoice_count >= 10:
        signals.append("meaningful_invoice_history")

    return GrowGraphFeatures(
        trust_graph_score=trust_graph_score,
        repeat_counterparty_count=repeat,
        verified_counterparty_count=verified,
        network_centrality_score=network_centrality_score,
        signals=signals,
    )


def build_alternative_credit_profile(business_id: str) -> AlternativeCreditProfile | None:
    if not graph_available():
        return None

    features = fetch_grow_graph_features(business_id)
    if features.repeat_counterparty_count == 0 and features.trust_graph_score == 0:
        return AlternativeCreditProfile(
            trust_graph_score=features.trust_graph_score,
            repeat_counterparty_count=features.repeat_counterparty_count,
            verified_counterparty_count=features.verified_counterparty_count,
            network_centrality_score=features.network_centrality_score,
            signals=features.signals,
            confidence=0.55,
        )

    return AlternativeCreditProfile(
        trust_graph_score=features.trust_graph_score,
        repeat_counterparty_count=features.repeat_counterparty_count,
        verified_counterparty_count=features.verified_counterparty_count,
        network_centrality_score=features.network_centrality_score,
        signals=features.signals,
        confidence=round(min(0.92, 0.55 + features.trust_graph_score * 0.35), 2),
    )


def _empty_features() -> GrowGraphFeatures:
    return GrowGraphFeatures(
        trust_graph_score=0.0,
        repeat_counterparty_count=0,
        verified_counterparty_count=0,
        network_centrality_score=0.0,
        signals=["graph_unavailable"],
    )


def _scalar(query: str, business_id: str, key: str) -> int:
    rows = run_read(query, {"business_id": business_id})
    if not rows:
        return 0
    value = rows[0].get(key, 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
