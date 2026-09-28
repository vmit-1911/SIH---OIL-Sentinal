"""Pydantic schemas for Phase 8 HSE Action & Recommendation Intelligence."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
)


class HSEActionRecommendationDTO(BaseModel):
    """Auditable HSE action recommendation model."""
    id: UUID
    action_key: str = Field(..., description="Deterministic unique action identifier")
    source_type: ActionSourceType = Field(..., description="Originating source entity type")
    source_id: str = Field(..., description="UUID or identifier of the source entity")
    action_category: ActionCategory = Field(..., description="Categorical recommendation classification")
    action_title: str = Field(..., description="Short title of the recommended action")
    action_description: str = Field(..., description="Detailed operational steps and control verification guidance")
    priority: ActionPriority = Field(..., description="Priority level: CRITICAL_REVIEW, HIGH, MEDIUM, INFORMATIONAL")
    rationale: str = Field(..., description="Explicit reasoning connecting source evidence to the recommendation")
    evidence_refs: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Supporting evidence items and narrative spans")
    source_dimensions: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Captured precursor or concentration dimensions")
    lsr_code: Optional[str] = Field(default=None, description="Associated IOGP Life-Saving Rule code")
    precursor_signature: Optional[str] = Field(default=None, description="Precursor signature of the source assessment")
    pattern_key: Optional[str] = Field(default=None, description="Associated pattern key")
    concentration_key: Optional[str] = Field(default=None, description="Associated concentration key")
    rule_id: str = Field(..., description="Deterministic rule ID that triggered this recommendation")
    rule_version: str = Field(default="1.0.0", description="Rule version")
    status: ActionStatus = Field(default=ActionStatus.OPEN, description="Lifecycle status")
    assigned_to: Optional[str] = Field(default=None, description="Assigned HSE officer or team")
    actor_id: Optional[str] = Field(default=None, description="Actor who last modified status")
    status_rationale: Optional[str] = Field(default=None, description="Rationale for dismissal or completion")
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None


class ActionListResponse(BaseModel):
    """Paginated list of HSE action recommendations."""
    total: int
    items: List[HSEActionRecommendationDTO] = Field(default_factory=list)
    page: int = 1
    limit: int = 50


class ActionGenerateRequest(BaseModel):
    """Request payload to generate deterministic HSE action recommendations."""
    report_id: Optional[UUID] = Field(default=None, description="Target report UUID")
    assessment_id: Optional[UUID] = Field(default=None, description="Target assessment UUID")
    pattern_id: Optional[UUID] = Field(default=None, description="Target pattern UUID")
    concentration_key: Optional[str] = Field(default=None, description="Target concentration key")
    persist: bool = Field(default=True, description="Whether to persist generated recommendations")


class ActionGenerateResponse(BaseModel):
    """Result of action recommendation generation."""
    total_generated: int
    new_actions: int
    existing_actions: int
    recommendations: List[HSEActionRecommendationDTO] = Field(default_factory=list)


class ActionAcknowledgeRequest(BaseModel):
    """Request payload to acknowledge an HSE action recommendation."""
    actor_id: str = Field(..., min_length=1, description="Username or badge ID of the HSE officer acknowledging the action")
    assigned_to: Optional[str] = Field(default=None, description="Optional assignee for follow-up")


class ActionStatusUpdateRequest(BaseModel):
    """Request payload to update the lifecycle state of an HSE action recommendation."""
    status: ActionStatus = Field(..., description="New status: IN_PROGRESS, COMPLETED, DISMISSED")
    actor_id: str = Field(..., min_length=1, description="Username or badge ID of the actor updating the status")
    status_rationale: Optional[str] = Field(default=None, description="Mandatory rationale when completing or dismissing an action")
    assigned_to: Optional[str] = Field(default=None, description="Updated assignee if applicable")
