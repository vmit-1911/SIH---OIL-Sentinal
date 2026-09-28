"""Life-Saving Rules taxonomy retrieval endpoints."""

from fastapi import APIRouter
from app.domain.taxonomy.loader import get_default_taxonomy
from app.schemas.taxonomy import (
    TaxonomyDetailResponse,
    TaxonomyListResponse,
    TaxonomyRuleItemDTO,
)

router = APIRouter()


@router.get(
    "/taxonomies",
    response_model=TaxonomyListResponse,
    summary="List Active Life-Saving Rule Taxonomies",
    description="Returns all active, versioned Life-Saving Rule taxonomies configured in the system.",
)
async def list_taxonomies() -> TaxonomyListResponse:
    """Retrieve all loaded Life-Saving Rule taxonomies."""
    default_tax = get_default_taxonomy()
    
    rules_dto = [
        TaxonomyRuleItemDTO(
            code=r.code,
            name=r.name,
            description=r.description,
            guidance=r.guidance,
            detection_patterns=r.detection_patterns,
            active=r.active,
        )
        for r in default_tax.rules
    ]
    
    tax_dto = TaxonomyDetailResponse(
        taxonomy_id=default_tax.taxonomy_id,
        authority=default_tax.authority,
        version=default_tax.version,
        name=default_tax.name,
        description=default_tax.description,
        active=default_tax.active,
        rules=rules_dto,
    )

    return TaxonomyListResponse(taxonomies=[tax_dto])
