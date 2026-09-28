"""Database-backed hybrid precursor matcher using structured dimensions and pgvector embeddings."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
from app.domain.interfaces.matcher import PrecursorMatcherInterface
from app.domain.similarity.hybrid import HybridPrecursorSimilarity

logger = get_logger(__name__)


class DatabasePrecursorMatcher(PrecursorMatcherInterface):
    """Retrieves previous SIF assessments from database and computes hybrid similarity."""

    def __init__(
        self,
        session: AsyncSession,
        hybrid_engine: Optional[HybridPrecursorSimilarity] = None,
    ):
        self.session = session
        self.hybrid_engine = hybrid_engine or HybridPrecursorSimilarity()

    def compute_similarity(
        self,
        precursor_a: Optional[Dict[str, Any]],
        precursor_b: Optional[Dict[str, Any]],
        vec_a: Optional[List[float]] = None,
        vec_b: Optional[List[float]] = None,
    ) -> float:
        """Compute hybrid similarity between two precursor records."""
        result = self.hybrid_engine.compute_hybrid_similarity(
            precursor_a=precursor_a,
            precursor_b=precursor_b,
            vec_a=vec_a,
            vec_b=vec_b,
        )
        return result.hybrid_score

    async def find_similar_reports(
        self,
        target_precursor: Optional[Dict[str, Any]],
        target_embedding: Optional[List[float]],
        exclude_report_id: Optional[UUID] = None,
        top_k: int = 5,
        threshold: float = 0.65,
    ) -> List[Dict[str, Any]]:
        """Find historical safety reports matching the target precursor using hybrid scoring.
        
        Threshold Semantics Note:
            `threshold` is an engineering candidate-retrieval/filtering parameter.
            It is not calibrated and must not be interpreted as probability, SIF severity,
            recurrence, or official OIL/IOGP guidance.
        """
        if target_precursor is None and target_embedding is None:
            logger.info("Neither structured precursor nor embedding provided; returning no similar reports")
            return []

        # 1. Candidate retrieval query from database
        stmt = (
            select(SIFAssessment, SafetyReport)
            .join(SafetyReport, SIFAssessment.report_id == SafetyReport.id)
            .where(
                (SIFAssessment.structured_precursor.isnot(None))
                | (SIFAssessment.text_embedding.isnot(None))
            )
        )

        if exclude_report_id:
            stmt = stmt.where(SIFAssessment.report_id != exclude_report_id)

        res = await self.session.execute(stmt)
        candidates = res.all()

        logger.info(f"Retrieved {len(candidates)} candidate assessments for hybrid similarity evaluation")

        # 2. Score candidates using hybrid similarity engine
        scored_results: List[Dict[str, Any]] = []

        for assessment, report in candidates:
            cand_precursor = assessment.structured_precursor
            cand_embedding = assessment.text_embedding

            sim_res = self.hybrid_engine.compute_hybrid_similarity(
                precursor_a=target_precursor,
                precursor_b=cand_precursor,
                vec_a=target_embedding,
                vec_b=cand_embedding,
            )

            if sim_res.hybrid_score >= threshold:
                raw_text = report.raw_text or ""
                summary_text = (raw_text[:140] + "...") if len(raw_text) > 140 else raw_text

                # Map scoring mode to explicit similarity type label
                if sim_res.mode == "FULL_HYBRID":
                    sim_type = "HYBRID"
                elif sim_res.mode == "STRUCTURED_ONLY_FALLBACK":
                    sim_type = "STRUCTURED_ONLY"
                elif sim_res.mode == "SEMANTIC_ONLY_FALLBACK":
                    sim_type = "SEMANTIC_ONLY"
                else:
                    sim_type = "NO_DATA"

                scored_results.append({
                    "report_id": report.id,
                    "similarity_score": sim_res.hybrid_score,
                    "similarity_type": sim_type,
                    "mode": sim_res.mode,
                    "summary": summary_text,
                    "location": report.reported_location,
                    "event_timestamp": report.event_timestamp,
                    "structured_score": sim_res.structured_score,
                    "semantic_score": sim_res.semantic_score,
                    "structured_weight": sim_res.structured_weight,
                    "semantic_weight": sim_res.semantic_weight,
                    "dimension_scores": sim_res.dimension_scores,
                    "compared_dimensions": sim_res.compared_dimensions,
                    "comparison_metadata": sim_res.comparison_metadata,
                })

        # 3. Deterministic ranking: highest score first, then stable UUID ordering
        scored_results.sort(
            key=lambda x: (-x["similarity_score"], str(x["report_id"])),
        )

        top_results = scored_results[:top_k]
        logger.info(
            f"Matched {len(top_results)} similar reports above threshold={threshold} (top_k={top_k})"
        )
        return top_results

