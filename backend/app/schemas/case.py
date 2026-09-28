"""Pydantic schemas for Phase 9 HSE Case Management and Operational Follow-up."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.enums import (
    CaseEventType,
    CasePriority,
    CaseSourceType,
    CaseStatus,
    CaseType,
)


class SourceReferenceInput(BaseModel):
    """Input specification for attaching a source intelligence record to a case."""
    source_type: CaseSourceType = Field(..., description="Originating source intelligence entity type")
    source_id: str = Field(..., description="Unique ID, UUID, or key of the source intelligence record")
    source_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional lightweight snapshot metadata")


class HSECaseCreateRequest(BaseModel):
    """Payload for creating a new HSE case/investigation."""
    title: str = Field(..., min_length=3, max_length=255, description="Human-readable title of the investigation")
    description: Optional[str] = Field(default=None, description="Detailed context, objective, and scope")
    case_type: CaseType = Field(default=CaseType.SIF_INVESTIGATION, description="Case classification")
    priority: CasePriority = Field(default=CasePriority.MEDIUM, description="Operational review priority")
    owner: Optional[str] = Field(default=None, description="Assigned HSE investigator or owner")
    created_by: str = Field(default="system_auditor", min_length=1, description="Actor creating the case")
    sources: Optional[List[SourceReferenceInput]] = Field(default_factory=list, description="Initial source intelligence attachments")
    idempotency_key: Optional[str] = Field(default=None, description="Optional idempotency key or desired case_key to prevent duplicate creation")


class HSECaseUpdateRequest(BaseModel):
    """Payload for updating mutable metadata of an HSE case."""
    title: Optional[str] = Field(default=None, min_length=3, max_length=255, description="Updated title")
    description: Optional[str] = Field(default=None, description="Updated description")
    priority: Optional[CasePriority] = Field(default=None, description="Updated priority")
    actor_id: str = Field(default="system_auditor", min_length=1, description="Actor initiating update")


class HSECaseAssignRequest(BaseModel):
    """Payload for assigning an HSE case to an owner."""
    owner: str = Field(..., min_length=1, description="Username or designation of assigned investigator")
    actor_id: str = Field(default="system_auditor", min_length=1, description="Actor initiating assignment")
    rationale: Optional[str] = Field(default=None, description="Optional rationale for assignment")


class HSECaseStatusUpdateRequest(BaseModel):
    """Payload for transitioning the operational lifecycle status of an HSE case."""
    status: CaseStatus = Field(..., description="Target lifecycle status")
    actor_id: str = Field(default="system_auditor", min_length=1, description="Actor initiating transition")
    rationale: Optional[str] = Field(default=None, description="Mandatory rationale for closure or cancellation")


class HSECaseReopenRequest(BaseModel):
    """Payload for reopening a closed HSE case."""
    actor_id: str = Field(default="system_auditor", min_length=1, description="Actor reopening case")
    rationale: str = Field(..., min_length=3, description="Mandatory justification for reopening the case")


class HSECaseSourceAttachRequest(BaseModel):
    """Payload for attaching a source intelligence record to an existing case."""
    source_type: CaseSourceType = Field(..., description="Source entity type")
    source_id: str = Field(..., min_length=1, description="Unique ID, UUID, or key of the source entity")
    source_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional snapshot metadata")
    actor_id: str = Field(default="system_auditor", min_length=1, description="Actor attaching source")


class HSECaseSourceDTO(BaseModel):
    """Authoritative source intelligence association linked to an HSE case."""
    id: UUID
    case_id: UUID
    source_type: CaseSourceType
    source_id: str
    source_metadata: Optional[Dict[str, Any]] = None
    attached_by: str
    attached_at: datetime


class HSECaseEventDTO(BaseModel):
    """Append-only audit event recording a case lifecycle mutation."""
    id: UUID
    case_id: UUID
    event_type: CaseEventType
    actor_id: str
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    source_reference: Optional[Dict[str, Any]] = None
    rationale: Optional[str] = None
    created_at: datetime


class HSECaseDTO(BaseModel):
    """Complete HSE case representation with attached sources."""
    id: UUID
    case_key: str
    title: str
    description: Optional[str] = None
    case_type: CaseType
    status: CaseStatus
    priority: CasePriority
    owner: Optional[str] = None
    created_by: str
    assigned_at: Optional[datetime] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None
    closure_rationale: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sources: List[HSECaseSourceDTO] = Field(default_factory=list)


class HSECaseSummaryDTO(BaseModel):
    """Deterministic, aggregate statistical summary of an HSE case."""
    case_id: UUID
    case_key: str
    title: str
    case_type: CaseType
    status: CaseStatus
    priority: CasePriority
    owner: Optional[str] = None
    report_count: int = Field(default=0, description="Count of linked safety reports")
    assessment_count: int = Field(default=0, description="Count of linked SIF assessments")
    pattern_count: int = Field(default=0, description="Count of linked precursor patterns")
    concentration_count: int = Field(default=0, description="Count of linked risk concentrations")
    review_count: int = Field(default=0, description="Count of linked triage reviews")
    action_count: int = Field(default=0, description="Total count of linked HSE actions")
    open_action_count: int = Field(default=0, description="Count of open or in-progress linked HSE actions")
    completed_action_count: int = Field(default=0, description="Count of completed linked HSE actions")
    evidence_count: int = Field(default=0, description="Count of underlying evidence items across linked sources")
    created_at: datetime
    updated_at: datetime


class CaseListResponse(BaseModel):
    """Paginated response containing HSE cases."""
    total: int
    items: List[HSECaseDTO] = Field(default_factory=list)
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
