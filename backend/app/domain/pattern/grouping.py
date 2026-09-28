"""Candidate grouping and graph clustering engine for precursor pattern discovery."""

import uuid
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.domain.pattern.models import PatternRelationshipEvidence
from app.domain.similarity.hybrid import HybridPrecursorSimilarity


class CandidateGroupResult(BaseModel):
    """Result of grouping candidate precursor assessments into recurring patterns."""
    qualifying_groups: List[Dict[str, Any]] = Field(default_factory=list)
    unassigned_report_ids: List[uuid.UUID] = Field(default_factory=list)
    total_candidates: int = 0
    total_relationships: int = 0
    qualifying_group_count: int = 0


class PatternGroupingEngine:
    """Groups candidate safety reports into recurring precursor patterns using hybrid similarity, graph connectivity, and group cohesion."""

    def __init__(
        self,
        hybrid_engine: Optional[HybridPrecursorSimilarity] = None,
        min_report_count: int = 3,
        candidate_threshold: float = 0.65,
        min_cohesion: float = 0.65,
    ):
        self.hybrid_engine = hybrid_engine or HybridPrecursorSimilarity()
        self.min_report_count = max(2, min_report_count)
        self.candidate_threshold = candidate_threshold
        self.min_cohesion = min_cohesion

    def group_candidates(
        self,
        candidates: List[Dict[str, Any]],
        threshold: Optional[float] = None,
        min_count: Optional[int] = None,
        min_cohesion: Optional[float] = None,
    ) -> CandidateGroupResult:
        """Evaluate candidate pairs, build similarity graph, and extract cohesive recurring patterns."""
        eff_threshold = threshold if threshold is not None else self.candidate_threshold
        eff_min_count = min_count if min_count is not None else self.min_report_count
        eff_min_cohesion = min_cohesion if min_cohesion is not None else self.min_cohesion

        total_candidates = len(candidates)
        if total_candidates < eff_min_count:
            return CandidateGroupResult(
                qualifying_groups=[],
                unassigned_report_ids=[c["report_id"] for c in candidates],
                total_candidates=total_candidates,
                total_relationships=0,
                qualifying_group_count=0,
            )

        # 1. Compute pairwise similarities across all distinct candidates
        candidate_map = {c["report_id"]: c for c in candidates}
        report_ids = [c["report_id"] for c in candidates]

        adjacency: Dict[uuid.UUID, Set[uuid.UUID]] = {rid: set() for rid in report_ids}
        all_relationships: List[PatternRelationshipEvidence] = []
        pair_relationship_map: Dict[Tuple[uuid.UUID, uuid.UUID], PatternRelationshipEvidence] = {}
        pair_score_map: Dict[Tuple[uuid.UUID, uuid.UUID], float] = {}

        for i in range(len(candidates)):
            cand_a = candidates[i]
            id_a = cand_a["report_id"]
            prec_a = cand_a.get("precursor")
            vec_a = cand_a.get("embedding")

            for j in range(i + 1, len(candidates)):
                cand_b = candidates[j]
                id_b = cand_b["report_id"]
                prec_b = cand_b.get("precursor")
                vec_b = cand_b.get("embedding")

                sim_res = self.hybrid_engine.compute_hybrid_similarity(
                    precursor_a=prec_a,
                    precursor_b=prec_b,
                    vec_a=vec_a,
                    vec_b=vec_b,
                )

                # Scoring mode awareness: NO_DATA_AVAILABLE must NEVER create a pattern relationship
                if sim_res.mode == "NO_DATA_AVAILABLE":
                    score = 0.0
                else:
                    score = sim_res.hybrid_score

                pair_score_map[(id_a, id_b)] = score
                pair_score_map[(id_b, id_a)] = score

                if sim_res.mode != "NO_DATA_AVAILABLE" and score >= eff_threshold:
                    rel = PatternRelationshipEvidence(
                        report_a=id_a,
                        report_b=id_b,
                        score=score,
                        mode=sim_res.mode,
                        dimension_scores=sim_res.dimension_scores,
                        structured_score=sim_res.structured_score,
                        semantic_score=sim_res.semantic_score,
                    )
                    all_relationships.append(rel)
                    pair_relationship_map[(id_a, id_b)] = rel
                    pair_relationship_map[(id_b, id_a)] = rel

                    adjacency[id_a].add(id_b)
                    adjacency[id_b].add(id_a)

        # 2. Extract connected components deterministically
        visited: Set[uuid.UUID] = set()
        components: List[List[uuid.UUID]] = []

        # Sort report_ids for deterministic traversal
        sorted_report_ids = sorted(report_ids, key=lambda x: str(x))

        for rid in sorted_report_ids:
            if rid in visited:
                continue

            # BFS / DFS traversal
            component: List[uuid.UUID] = []
            queue = [rid]
            visited.add(rid)

            while queue:
                curr = queue.pop(0)
                component.append(curr)
                # Sort neighbors for determinism
                neighbors = sorted(list(adjacency[curr]), key=lambda x: str(x))
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            # Sort component member IDs
            component.sort(key=lambda x: str(x))
            components.append(component)

        # 3. Filter components by minimum recurrence count AND group cohesion (preventing chaining)
        qualifying_groups: List[Dict[str, Any]] = []
        assigned_report_ids: Set[uuid.UUID] = set()

        for comp in components:
            if len(comp) < eff_min_count:
                continue

            n_members = len(comp)
            # Intra-group pairwise scores for all n*(n-1)/2 pairs
            intra_scores: List[float] = []
            for i in range(n_members):
                for j in range(i + 1, n_members):
                    s = pair_score_map.get((comp[i], comp[j]), 0.0)
                    intra_scores.append(s)

            group_cohesion = sum(intra_scores) / len(intra_scores) if intra_scores else 0.0

            # Per-member cohesion: average similarity of each member to all other group members
            member_cohesions: Dict[uuid.UUID, float] = {}
            for i in range(n_members):
                u = comp[i]
                u_scores = [pair_score_map.get((u, comp[j]), 0.0) for j in range(n_members) if j != i]
                member_cohesions[u] = sum(u_scores) / len(u_scores) if u_scores else 0.0

            min_member_cohesion = min(member_cohesions.values()) if member_cohesions else 0.0

            # Cohesion requirement: overall group cohesion AND every individual member relationship must meet threshold
            if group_cohesion < eff_min_cohesion or min_member_cohesion < eff_min_cohesion:
                # Reject chained or insufficiently cohesive group
                continue

            # Build qualifying relationships
            comp_members = [candidate_map[rid] for rid in comp]
            comp_rels: List[PatternRelationshipEvidence] = []
            for i in range(n_members):
                for j in range(i + 1, n_members):
                    pair_key = (comp[i], comp[j])
                    if pair_key in pair_relationship_map:
                        comp_rels.append(pair_relationship_map[pair_key])

            qualifying_groups.append({
                "member_records": comp_members,
                "member_report_ids": comp,
                "relationships": comp_rels,
                "group_cohesion": round(group_cohesion, 4),
                "min_member_cohesion": round(min_member_cohesion, 4),
            })
            assigned_report_ids.update(comp)

        unassigned_ids = [rid for rid in report_ids if rid not in assigned_report_ids]

        return CandidateGroupResult(
            qualifying_groups=qualifying_groups,
            unassigned_report_ids=unassigned_ids,
            total_candidates=total_candidates,
            total_relationships=len(all_relationships),
            qualifying_group_count=len(qualifying_groups),
        )
