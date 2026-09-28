"""Integration tests for POST /api/v1/sif/analyze unified inference endpoint."""

from uuid import UUID
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
from app.db.models.taxonomy import LSRReportMapping
from app.domain.enums import (
    ActualOutcome,
    PotentialOutcome,
    SIFClassification,
    SourceType,
)
from app.schemas.report import SingleReportAnalysisResponse


@pytest.mark.asyncio
async def test_a_valid_near_miss_returns_real_analysis(async_client: AsyncClient):
    """Requirement A: Valid near-miss narrative returns real explainable analysis."""
    payload = {
        "raw_text": (
            "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
            "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
        ),
        "source_type": "NEAR_MISS",
        "reported_location": "Rig-04 / Moran Field",
        "reported_department": "Drilling Operations",
        "actual_severity": "NO_INJURY",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert UUID(data["report_id"])
    assert data["sif_classification"] == SIFClassification.POTENTIAL_SIF
    assert data["scoring"]["evidence_score"] >= 0.70
    assert data["scoring"]["evidence_strength"] == "HIGH"
    assert data["potential_outcome"]["severity"] == "FATALITY"
    assert "explainability" in data
    assert len(data["explainability"]["evidence_spans"]) > 0
    assert len(data["life_saving_rules"]) > 0


@pytest.mark.asyncio
async def test_b_high_energy_barrier_produces_potential_sif(async_client: AsyncClient):
    """Requirement B: High-energy hazard + barrier failure produces POTENTIAL_SIF."""
    payload = {
        "raw_text": (
            "During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body "
            "harness lanyard without 100% tie-off."
        ),
        "source_type": "UA",
        "reported_location": "Rig-07 / Digboi",
        "actual_severity": "NO_INJURY",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["sif_classification"] == SIFClassification.POTENTIAL_SIF
    assert data["potential_outcome"]["severity"] == "FATALITY"
    mapped_codes = [r["rule_code"] for r in data["life_saving_rules"]]
    assert "LSR_09_WORKING_AT_HEIGHT" in mapped_codes


@pytest.mark.asyncio
async def test_c_low_risk_narrative_produces_non_sif(async_client: AsyncClient):
    """Requirement C: Low-risk routine housekeeping produces NON_SIF."""
    payload = {
        "raw_text": "Empty paint cans and cleaning rags left unattended near workshop entrance, creating trip hazard.",
        "source_type": "UC",
        "reported_location": "Central Workshop",
        "actual_severity": "NO_INJURY",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["sif_classification"] == SIFClassification.NON_SIF
    assert data["scoring"]["evidence_score"] <= 0.20
    assert data["triage_recommendation"] == "ROUTINE_LOGGING"


@pytest.mark.asyncio
async def test_d_ambiguous_narrative_produces_undetermined(async_client: AsyncClient):
    """Requirement D: Ambiguous / minimal context produces UNDETERMINED."""
    payload = {
        "raw_text": "Observed unsafe condition near the compressor shed area yesterday.",
        "source_type": "UC",
        "reported_location": "Compressor Shed",
        "actual_severity": "NO_INJURY",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["sif_classification"] == SIFClassification.UNDETERMINED
    assert data["triage_recommendation"] == "HSE_OFFICER_REVIEW"


@pytest.mark.asyncio
async def test_e_actual_severity_does_not_create_actual_sif(async_client: AsyncClient):
    """Requirement E: Severe actual injury does not automatically create ACTUAL_SIF."""
    payload = {
        "raw_text": (
            "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
            "across the rig floor near floormen."
        ),
        "source_type": "INCIDENT",
        "actual_severity": "LOST_TIME_INJURY",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["actual_outcome"]["severity"] == "LOST_TIME_INJURY"
    # SIF potential is evaluated, NOT automatically converted to ACTUAL_SIF
    assert data["sif_classification"] == SIFClassification.POTENTIAL_SIF
    assert data["sif_classification"] != SIFClassification.ACTUAL_SIF


@pytest.mark.asyncio
async def test_f_lsr_mappings_included_in_response(async_client: AsyncClient):
    """Requirement F: Defensible IOGP Life-Saving Rules mappings are included."""
    payload = {
        "raw_text": (
            "Contractor personnel entered the crude oil storage tank compartment for sludge cleaning "
            "without gas test clearance and without a dedicated standby man."
        ),
        "source_type": "NEAR_MISS",
        "actual_severity": "NO_INJURY",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    rules = data["life_saving_rules"]
    assert len(rules) > 0
    rule_codes = [r["rule_code"] for r in rules]
    assert "LSR_02_CONFINED_SPACE" in rule_codes
    primary_rules = [r for r in rules if r["is_primary"]]
    assert len(primary_rules) == 1
    assert primary_rules[0]["rule_code"] == "LSR_02_CONFINED_SPACE"


@pytest.mark.asyncio
async def test_g_evidence_spans_refer_to_original_text(async_client: AsyncClient):
    """Requirement G: Evidence character spans accurately point to source text."""
    raw = "Technician began unbolting high pressure flange on production manifold at EPS-02. Trapped gas vented."
    payload = {
        "raw_text": raw,
        "source_type": "NEAR_MISS",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    for span in data["explainability"]["evidence_spans"]:
        start = span["start_char"]
        end = span["end_char"]
        assert raw[start:end] == span["text"]


@pytest.mark.asyncio
async def test_h_derivation_type_is_preserved(async_client: AsyncClient):
    """Requirement H: Concept derivation type (DIRECT_MATCH / LEXICON_INFERENCE) is preserved."""
    payload = {
        "raw_text": "While running 9-5/8 inch casing, winch line parted.",
        "source_type": "NEAR_MISS",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    extracted = data["extracted_entities"]
    assert "activity" in extracted
    assert extracted["activity"]["derivation_type"] in ["DIRECT_MATCH", "LEXICON_INFERENCE"]


@pytest.mark.asyncio
async def test_i_j_no_fake_pattern_or_embedding_fabricated(async_client: AsyncClient):
    """Requirements I & J: pattern_id is null, no fake random/mock vectors, precursor is structured."""
    payload = {
        "raw_text": "While running casing on rig floor, air winch line parted near floormen.",
        "source_type": "NEAR_MISS",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["pattern_id"] is None
    assert data["structured_precursor"] is not None
    assert data["precursor_signature"] is not None


@pytest.mark.asyncio
async def test_k_invalid_short_input_validation(async_client: AsyncClient):
    """Requirement K: Short or invalid narrative returns 422 Unprocessable Entity."""
    payload = {
        "raw_text": "Too short",
        "source_type": "NEAR_MISS",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_l_m_persistence_and_no_corrupt_duplicate(async_client: AsyncClient, db_session: AsyncSession):
    """Requirements L & M: Persistence saves models and subsequent analyses maintain data integrity."""
    payload = {
        "raw_text": (
            "During working at height on monkey board, derrickman unhooked his full body harness lanyard without 100% tie-off."
        ),
        "source_type": "UA",
        "reported_location": "Rig-01",
        "actual_severity": "NO_INJURY",
    }

    # Run analysis 1
    res1 = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert res1.status_code == 200
    report_id_1 = UUID(res1.json()["report_id"])

    # Run analysis 2 with same text
    res2 = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert res2.status_code == 200
    report_id_2 = UUID(res2.json()["report_id"])

    # Both produce unique reports and assessments without corruption
    assert report_id_1 != report_id_2

    # Verify report 1 in DB
    report_db_1 = await db_session.get(SafetyReport, report_id_1)
    assert report_db_1 is not None
    assert report_db_1.raw_text == payload["raw_text"]

    # Verify assessment 1 in DB
    stmt = select(SIFAssessment).where(SIFAssessment.report_id == report_id_1)
    ass_res = await db_session.execute(stmt)
    ass_db_1 = ass_res.scalar_one_or_none()
    assert ass_db_1 is not None
    assert ass_db_1.sif_classification == SIFClassification.POTENTIAL_SIF
    assert ass_db_1.text_embedding is not None
    assert len(ass_db_1.text_embedding) == 384
    assert ass_db_1.pattern_id is None
    assert ass_db_1.structured_precursor is not None
    assert ass_db_1.structured_precursor["hazard"] == "Working at Height Fall Exposure"


    # Verify LSR mappings in DB
    lsr_stmt = select(LSRReportMapping).where(LSRReportMapping.report_id == report_id_1)
    lsr_res = await db_session.execute(lsr_stmt)
    mappings = list(lsr_res.scalars().all())
    assert len(mappings) > 0
    assert any(m.rule_code == "LSR_09_WORKING_AT_HEIGHT" for m in mappings)


@pytest.mark.asyncio
async def test_n_response_schema_validates_successfully(async_client: AsyncClient):
    """Requirement N: API response validates against Pydantic SingleReportAnalysisResponse schema."""
    payload = {
        "raw_text": "While running casing on rig floor, air winch line parted near floormen.",
        "source_type": "NEAR_MISS",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    parsed_dto = SingleReportAnalysisResponse.model_validate(response.json())
    assert parsed_dto.report_id is not None
    assert parsed_dto.structured_precursor is not None
    assert parsed_dto.structured_precursor.barrier_failure == "Lifting Line / Rigging Failure"
    assert parsed_dto.precursor_signature is not None


@pytest.mark.asyncio
async def test_phase_1d_structured_precursor_synthesis_and_api_contract(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Phase 1D validation: Ensure structured precursor and provenance are synthesized, returned, and persisted."""
    payload = {
        "raw_text": (
            "During unbolting flange on production manifold at EPS Moran, trapped high pressure crude oil "
            "vented because isolation not verified. Floorman stepped back into safety zone."
        ),
        "source_type": "NEAR_MISS",
        "reported_location": "EPS Moran",
        "actual_severity": "NO_INJURY",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    report_id = UUID(data["report_id"])

    # 1. API contract: Precursor fields populated with canonical concepts in Phase 1D
    assert data["structured_precursor"] is not None
    precursor = data["structured_precursor"]
    assert precursor["activity"] == "Manifold & Valve Maintenance"
    assert precursor["barrier_failure"] == "Energy Isolation (LOTO) Failure"
    assert precursor["potential_consequence"] in ["FATALITY", "MAJOR_PROCESS_SAFETY_EVENT"]
    assert precursor["life_saving_rule"] == "LSR_04_ENERGY_ISOLATION"
    assert precursor["location"] == "EPS Moran"
    assert "field_provenance" in precursor
    assert len(precursor["field_provenance"]) > 0


    # 2. Canonical precursor signature is present
    assert data["precursor_signature"] is not None
    assert "Manifold & Valve Maintenance" in data["precursor_signature"]
    assert "Energy Isolation (LOTO) Failure" in data["precursor_signature"]

    # 3. Pattern ID remains unpopulated (deferred to Phase 2B/clustering)
    assert data["pattern_id"] is None
    assert isinstance(data["similar_reports"], list)


    # 4. Raw Safety Event Extraction remains present and explainable
    assert "extracted_entities" in data
    assert data["extracted_entities"]["activity"] is not None
    assert len(data["extracted_entities"]["hazards"]) > 0
    assert len(data["extracted_entities"]["barrier_failures"]) > 0

    # 5. Persistence verification: DB record must have structured_precursor JSONB, valid 384-dim text_embedding, pattern_id=None
    stmt = select(SIFAssessment).where(SIFAssessment.report_id == report_id)
    ass_res = await db_session.execute(stmt)
    assessment = ass_res.scalar_one_or_none()
    assert assessment is not None
    assert assessment.structured_precursor is not None
    assert assessment.structured_precursor["activity"] == "Manifold & Valve Maintenance"
    assert assessment.structured_precursor["barrier_failure"] == "Energy Isolation (LOTO) Failure"
    assert assessment.precursor_signature == data["precursor_signature"]
    assert assessment.text_embedding is not None
    assert len(assessment.text_embedding) == 384
    assert assessment.pattern_id is None


@pytest.mark.asyncio
async def test_phase_2a_embedding_persistence_and_similarity_retrieval(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Phase 2A validation: Ensure embeddings are persisted and historical similar reports are retrieved."""
    # 1. First report: Suspended load near-miss
    payload_1 = {
        "raw_text": (
            "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
            "across the rig floor, narrowly missing two floormen in line of fire."
        ),
        "source_type": "NEAR_MISS",
        "reported_location": "Rig-04 / Moran Field",
        "reported_department": "Drilling Operations",
        "actual_severity": "NO_INJURY",
    }
    res1 = await async_client.post("/api/v1/sif/analyze", json=payload_1)
    assert res1.status_code == 200
    data1 = res1.json()
    report1_id = UUID(data1["report_id"])
    assert data1["pattern_id"] is None

    # Check embedding in DB
    stmt1 = select(SIFAssessment).where(SIFAssessment.report_id == report1_id)
    ass1 = (await db_session.execute(stmt1)).scalar_one_or_none()
    assert ass1 is not None
    assert ass1.text_embedding is not None
    assert len(ass1.text_embedding) == 384

    # 2. Second report: Another hoisting / rigging near-miss
    payload_2 = {
        "raw_text": (
            "During casing hoisting operation at Rig-04, the winch cable failed causing suspended load "
            "to swing directly towards the rigger standing in line of fire."
        ),
        "source_type": "NEAR_MISS",
        "reported_location": "Rig-04 / Moran Field",
        "reported_department": "Drilling Operations",
        "actual_severity": "NO_INJURY",
    }
    res2 = await async_client.post("/api/v1/sif/analyze", json=payload_2)
    assert res2.status_code == 200
    data2 = res2.json()
    report2_id = UUID(data2["report_id"])

    # Second report must match the first report via hybrid similarity
    assert len(data2["similar_reports"]) >= 1
    matched_ids = [s["report_id"] for s in data2["similar_reports"]]
    assert str(report1_id) in matched_ids
    for s in data2["similar_reports"]:
        assert s["similarity_score"] >= 0.65
        assert s["similarity_type"] == "HYBRID"
    assert data2["pattern_id"] is None

    # 3. Third report: Unrelated housekeeping (NON_SIF)
    payload_3 = {
        "raw_text": "Empty paint cans and cleaning rags left unattended near workshop entrance.",
        "source_type": "UC",
        "reported_location": "Central Workshop",
        "actual_severity": "NO_INJURY",
    }
    res3 = await async_client.post("/api/v1/sif/analyze", json=payload_3)
    assert res3.status_code == 200
    data3 = res3.json()
    # Unrelated event must NOT match the crane lifting reports above the 0.65 threshold
    assert not any(s["report_id"] in [str(report1_id), str(report2_id)] for s in data3["similar_reports"])
    assert data3["pattern_id"] is None



