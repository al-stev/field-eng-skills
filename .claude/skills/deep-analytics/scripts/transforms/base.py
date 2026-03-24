"""Base transform contract for deep analytics page transforms."""

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class BaseTransform(ABC):
    """
    Base class for page-specific data transforms.

    Each analytics page has a transform that takes raw DataFrames
    from BigQuery and produces the PAGE_DATA dict for HTML injection.
    """

    @abstractmethod
    def transform(self, **dataframes: pd.DataFrame) -> dict[str, Any]:
        """
        Transform raw query results into PAGE_DATA structure.

        Args:
            **dataframes: Named DataFrames from query execution

        Returns:
            Dict matching PAGE_DATA schema for the page type.
            Must include 'available' (bool) and 'reason' (str|None) keys.
        """
        ...

    def empty_result(self, reason: str = "no_data") -> dict[str, Any]:
        """Return a standard empty/error result."""
        return {"available": False, "reason": reason}
