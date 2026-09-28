"""Security and authentication dependency placeholders."""

from typing import Optional
from fastapi import Header, HTTPException, status


async def get_optional_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")
) -> Optional[str]:
    """Dependency placeholder for API key extraction.
    
    Enterprise authentication is deferred; this provides the extraction hook.
    """
    return x_api_key
