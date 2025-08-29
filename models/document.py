from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class UploadStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentBase(BaseModel):
    file_name: str
    original_name: str
    file_size: int
    mime_type: str
    storage_path: str
    upload_status: UploadStatus = UploadStatus.UPLOADING
    metadata: Optional[Dict[str, Any]] = {}

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    upload_status: Optional[UploadStatus] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentResponse(DocumentBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    limit: int

class UploadUrlResponse(BaseModel):
    upload_url: str
    file_path: str
    document_id: str

class FileProcessingResult(BaseModel):
    success: bool
    file_type: str
    extracted_text: Optional[str] = None
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None

class BulkDeleteRequest(BaseModel):
    document_ids: list[str]