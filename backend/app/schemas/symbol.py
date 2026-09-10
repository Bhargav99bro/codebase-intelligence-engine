from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class SymbolItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    file_id: uuid.UUID
    file_path: Optional[str] = None
    name: str
    symbol_type: str
    qualified_name: Optional[str] = None
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    parent_symbol_id: Optional[uuid.UUID] = None
    signature: Optional[str] = None
    metadata_json: Dict[str, Any] = {}
    created_at: datetime


class SymbolListResponse(BaseModel):
    items: List[SymbolItemResponse]
    total: int
    skip: int
    limit: int
