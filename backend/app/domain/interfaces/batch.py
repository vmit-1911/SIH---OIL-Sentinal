"""Abstract interfaces for batch file parsing and background batch task processing."""

from abc import ABC, abstractmethod
from typing import List, Tuple
from uuid import UUID

from app.domain.batch.models import ParsedReportRow


class BatchParserInterface(ABC):
    """Port for parsing uploaded batch files into structured ParsedReportRow DTOs."""

    @abstractmethod
    def parse(
        self,
        file_content: bytes,
        filename: str,
    ) -> Tuple[List[ParsedReportRow], List[Tuple[int, str, str, str]]]:
        """Parse raw file bytes into parsed rows and structural row-level syntax errors.
        
        Returns:
            Tuple of:
            - List of ParsedReportRow objects
            - List of structural parse error tuples (row_number, field_name, error_code, error_message)
        """
        pass

    @abstractmethod
    def supports_format(self, filename: str) -> bool:
        """Return True if this parser supports the given filename extension."""
        pass


class BatchProcessorInterface(ABC):
    """Port for batch ingestion and processing orchestration."""

    @abstractmethod
    async def process_batch_job(
        self,
        batch_id: UUID,
        file_content: bytes,
        filename: str,
    ) -> None:
        """Execute full batch ingestion and analysis processing."""
        pass

