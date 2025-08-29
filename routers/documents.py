import os
import uuid
import tempfile
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime

from auth.dependencies import get_current_user
from models.document import (
    DocumentResponse, DocumentListResponse, DocumentUpdate,
    UploadUrlResponse, DocumentCreate, UploadStatus, BulkDeleteRequest
)
from services.file_processor import file_processor
from supabase_client import get_supabase_admin
import aiofiles

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a document file."""
    try:
        user_id = current_user["user_id"]
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Generate unique file name
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        storage_path = f"{user_id}/{unique_filename}"
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Create temporary file for processing
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # Detect MIME type
            mime_type = file_processor.detect_mime_type(temp_file_path)
            
            # Create document record in database
            document_data = {
                "user_id": user_id,
                "file_name": unique_filename,
                "original_name": file.filename,
                "file_size": file_size,
                "mime_type": mime_type,
                "storage_path": storage_path,
                "upload_status": UploadStatus.UPLOADING.value,
                "metadata": {}
            }
            
            # Insert document record
            result = get_supabase_admin().table("document_metadata").insert(document_data).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create document record")
            
            document_id = result.data[0]["id"]
            
            # Upload file to Supabase storage
            storage_result = get_supabase_admin().storage.from_("documents").upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": mime_type}
            )
            
            # Check for storage upload errors - the error might be in different formats
            if hasattr(storage_result, 'error') and storage_result.error:
                # Clean up database record if storage upload fails
                get_supabase_admin().table("document_metadata").delete().eq("id", document_id).execute()
                raise HTTPException(status_code=500, detail=f"Storage upload failed: {storage_result.error}")
            elif not hasattr(storage_result, 'path') and not hasattr(storage_result, 'full_path'):
                # If we don't have expected success indicators, treat as error
                get_supabase_admin().table("document_metadata").delete().eq("id", document_id).execute()
                raise HTTPException(status_code=500, detail="Storage upload failed - unexpected response format")
            
            # Process file and update metadata
            processing_result = await file_processor.process_file(temp_file_path, mime_type, file_size)
            
            update_data = {
                "upload_status": UploadStatus.COMPLETED.value if processing_result.success else UploadStatus.FAILED.value,
                "metadata": processing_result.metadata or {}
            }
            
            # Add extracted text if available
            if processing_result.extracted_text:
                update_data["metadata"]["extracted_text"] = processing_result.extracted_text
            
            # Update document record with processing results
            updated_result = get_supabase_admin().table("document_metadata").update(update_data).eq("id", document_id).execute()
            
            if not updated_result.data:
                raise HTTPException(status_code=500, detail="Failed to update document record")
            
            return DocumentResponse(**updated_result.data[0])
            
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[UploadStatus] = None,
    current_user: dict = Depends(get_current_user)
):
    """List user's documents with pagination."""
    try:
        user_id = current_user["user_id"]
        offset = (page - 1) * limit
        
        # Build query
        query = get_supabase_admin().table("document_metadata").select("*").eq("user_id", user_id)
        
        if status:
            query = query.eq("upload_status", status.value)
        
        # Get total count
        count_result = get_supabase_admin().table("document_metadata").select("id", count="exact").eq("user_id", user_id)
        if status:
            count_result = count_result.eq("upload_status", status.value)
        total = count_result.execute().count or 0
        
        # Get paginated results
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        documents = [DocumentResponse(**doc) for doc in result.data]
        
        return DocumentListResponse(
            documents=documents,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific document by ID."""
    try:
        user_id = current_user["user_id"]
        
        result = get_supabase_admin().table("document_metadata").select("*").eq("id", document_id).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get download URL for a document."""
    try:
        user_id = current_user["user_id"]
        
        # Get document metadata
        result = get_supabase_admin().table("document_metadata").select("*").eq("id", document_id).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = result.data[0]
        
        # Generate download URL (expires in 1 hour)
        try:
            download_result = get_supabase_admin().storage.from_("documents").create_signed_url(
                path=document["storage_path"],
                expires_in=3600
            )
            
            # The result is a dict with signedURL or signedUrl key
            signed_url = download_result.get("signedURL") or download_result.get("signedUrl")
            
            if not signed_url:
                raise HTTPException(status_code=500, detail="Failed to generate download URL - no URL returned")
            
            return {
                "download_url": signed_url,
                "filename": document["original_name"],
                "expires_in": 3600
            }
            
        except Exception as storage_error:
            raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(storage_error)}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process download request: {str(e)}")

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    update_data: DocumentUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update document metadata."""
    try:
        user_id = current_user["user_id"]
        
        # Check if document exists and belongs to user
        existing = get_supabase_admin().table("document_metadata").select("*").eq("id", document_id).eq("user_id", user_id).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Prepare update data
        update_dict = {}
        if update_data.upload_status is not None:
            update_dict["upload_status"] = update_data.upload_status.value
        if update_data.metadata is not None:
            update_dict["metadata"] = update_data.metadata
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        # Update document
        result = get_supabase_admin().table("document_metadata").update(update_dict).eq("id", document_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update document")
        
        return DocumentResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a document and its file from storage."""
    try:
        user_id = current_user["user_id"]
        
        # Get document metadata
        result = get_supabase_admin().table("document_metadata").select("*").eq("id", document_id).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = result.data[0]
        
        # Delete file from storage
        try:
            storage_result = get_supabase_admin().storage.from_("documents").remove([document["storage_path"]])
            # storage_result is a list, no error checking needed for successful calls
        except Exception as storage_error:
            # Log error but continue with database deletion
            print(f"Warning: Failed to delete file from storage: {storage_error}")
        
        # Delete database record
        delete_result = get_supabase_admin().table("document_metadata").delete().eq("id", document_id).execute()
        
        if not delete_result.data:
            raise HTTPException(status_code=500, detail="Failed to delete document record")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/bulk-delete")
async def bulk_delete_documents(
    request: BulkDeleteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Delete multiple documents."""
    try:
        user_id = current_user["user_id"]
        document_ids = request.document_ids
        
        if not document_ids:
            raise HTTPException(status_code=400, detail="No document IDs provided")
        
        # Get documents that belong to the user
        result = get_supabase_admin().table("document_metadata").select("*").eq("user_id", user_id).in_("id", document_ids).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No documents found")
        
        storage_paths = [doc["storage_path"] for doc in result.data]
        found_ids = [doc["id"] for doc in result.data]
        
        # Delete files from storage
        if storage_paths:
            try:
                storage_result = get_supabase_admin().storage.from_("documents").remove(storage_paths)
                # storage_result is a list, no error checking needed for successful calls
            except Exception as storage_error:
                print(f"Warning: Storage deletion failed: {storage_error}")
        
        # Delete database records
        delete_result = get_supabase_admin().table("document_metadata").delete().in_("id", found_ids).execute()
        
        if not delete_result.data:
            raise HTTPException(status_code=500, detail="Failed to delete document records from database")
        
        return {
            "message": f"Successfully deleted {len(found_ids)} documents",
            "deleted_count": len(found_ids),
            "requested_count": len(document_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete documents: {str(e)}")
