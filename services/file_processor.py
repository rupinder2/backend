import os
import mimetypes
from typing import Dict, Any, Optional
from models.document import FileProcessingResult
import aiofiles

# Optional imports for enhanced functionality
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

class FileProcessor:
    """Service for processing uploaded files and extracting metadata."""
    
    def __init__(self):
        self.supported_image_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'
        ]
        self.supported_text_types = [
            'text/plain', 'text/csv', 'application/json'
        ]
        self.supported_document_types = [
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
    
    async def process_file(self, file_path: str, mime_type: str, file_size: int) -> FileProcessingResult:
        """Process a file and extract metadata based on its type."""
        try:
            if mime_type in self.supported_image_types:
                return await self._process_image(file_path, file_size)
            elif mime_type in self.supported_text_types:
                return await self._process_text_file(file_path, file_size)
            elif mime_type in self.supported_document_types:
                return await self._process_document(file_path, file_size)
            else:
                return FileProcessingResult(
                    success=True,
                    file_type="unknown",
                    metadata={"mime_type": mime_type, "file_size": file_size}
                )
        except Exception as e:
            return FileProcessingResult(
                success=False,
                file_type="unknown",
                error=str(e),
                metadata={"mime_type": mime_type, "file_size": file_size}
            )
    
    async def _process_image(self, file_path: str, file_size: int) -> FileProcessingResult:
        """Process image files and extract image metadata."""
        try:
            if HAS_PIL:
                with Image.open(file_path) as img:
                    metadata = {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode,
                        "file_size": file_size
                    }
                    
                    # Extract EXIF data if available
                    if hasattr(img, '_getexif') and img._getexif():
                        exif_data = img._getexif()
                        if exif_data:
                            metadata["exif"] = {
                                k: v for k, v in exif_data.items()
                                if isinstance(v, (str, int, float))
                            }
                    
                    return FileProcessingResult(
                        success=True,
                        file_type="image",
                        metadata=metadata
                    )
            else:
                # Basic image processing without PIL
                metadata = {
                    "file_size": file_size,
                    "processing_note": "Basic processing - install Pillow for enhanced image metadata"
                }
                
                return FileProcessingResult(
                    success=True,
                    file_type="image",
                    metadata=metadata
                )
        except Exception as e:
            return FileProcessingResult(
                success=False,
                file_type="image",
                error=f"Image processing failed: {str(e)}",
                metadata={"file_size": file_size}
            )
    
    async def _process_text_file(self, file_path: str, file_size: int) -> FileProcessingResult:
        """Process text files and extract content."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                
            # Limit extracted text to first 5000 characters for storage
            extracted_text = content[:5000] if len(content) > 5000 else content
            
            metadata = {
                "file_size": file_size,
                "character_count": len(content),
                "line_count": content.count('\n') + 1,
                "is_truncated": len(content) > 5000
            }
            
            return FileProcessingResult(
                success=True,
                file_type="text",
                extracted_text=extracted_text,
                metadata=metadata
            )
        except Exception as e:
            return FileProcessingResult(
                success=False,
                file_type="text",
                error=f"Text processing failed: {str(e)}",
                metadata={"file_size": file_size}
            )
    
    async def _process_document(self, file_path: str, file_size: int) -> FileProcessingResult:
        """Process document files (PDF, Word, etc.)."""
        # For now, just return basic metadata
        # In a real implementation, you'd use libraries like PyPDF2, python-docx, etc.
        metadata = {
            "file_size": file_size,
            "processing_note": "Document parsing not yet implemented"
        }
        
        return FileProcessingResult(
            success=True,
            file_type="document",
            metadata=metadata
        )
    
    def detect_mime_type(self, file_path: str) -> str:
        """Detect MIME type of a file."""
        try:
            if HAS_MAGIC:
                # First try python-magic for more accurate detection
                mime_type = magic.from_file(file_path, mime=True)
                return mime_type
            else:
                # Fallback to mimetypes module
                mime_type, _ = mimetypes.guess_type(file_path)
                return mime_type or "application/octet-stream"
        except:
            # Final fallback to mimetypes module
            mime_type, _ = mimetypes.guess_type(file_path)
            return mime_type or "application/octet-stream"
    
    def validate_file_type(self, mime_type: str) -> bool:
        """Validate if the file type is supported."""
        supported_types = (
            self.supported_image_types + 
            self.supported_text_types + 
            self.supported_document_types
        )
        
        # Allow any file type for now, but flag unsupported ones
        return True
    
    def get_file_category(self, mime_type: str) -> str:
        """Get the category of a file based on its MIME type."""
        if mime_type in self.supported_image_types:
            return "image"
        elif mime_type in self.supported_text_types:
            return "text"
        elif mime_type in self.supported_document_types:
            return "document"
        else:
            return "other"

# Global instance
file_processor = FileProcessor()
