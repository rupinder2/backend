from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from enum import Enum

class BookStatus(str, Enum):
    AVAILABLE = "available"
    CHECKED_OUT = "checked_out"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"

class BookCondition(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    author: str = Field(..., min_length=1, max_length=200)
    isbn: Optional[str] = Field(None, max_length=20)
    genre: str = Field(..., min_length=1, max_length=100)
    publication_year: Optional[int] = Field(None, ge=1000, le=2100)
    description: Optional[str] = Field(None, max_length=2000)
    publisher: Optional[str] = Field(None, max_length=200)
    pages: Optional[int] = Field(None, ge=1)
    language: str = Field(default="English", max_length=50)
    location: Optional[str] = Field(None, max_length=100)  # Shelf location
    condition: BookCondition = BookCondition.GOOD
    cover_image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    author: Optional[str] = Field(None, min_length=1, max_length=200)
    isbn: Optional[str] = Field(None, max_length=20)
    genre: Optional[str] = Field(None, min_length=1, max_length=100)
    publication_year: Optional[int] = Field(None, ge=1000, le=2100)
    description: Optional[str] = Field(None, max_length=2000)
    publisher: Optional[str] = Field(None, max_length=200)
    pages: Optional[int] = Field(None, ge=1)
    language: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    condition: Optional[BookCondition] = None
    cover_image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BookResponse(BookBase):
    id: str
    added_by: str  # user_id who added the book
    status: BookStatus
    checked_out_by: Optional[str] = None
    checked_out_at: Optional[datetime] = None
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BookListResponse(BaseModel):
    books: List[BookResponse]
    total: int
    page: int
    limit: int

class CheckoutRequest(BaseModel):
    checkout_days: int = Field(default=14, ge=1, le=90)  # Default 2 weeks, max 90 days

class CheckoutResponse(BaseModel):
    book_id: str
    checked_out_by: str
    checked_out_at: datetime
    due_date: date
    success: bool
    message: str

class CheckinResponse(BaseModel):
    book_id: str
    returned_at: datetime
    was_overdue: bool
    days_overdue: Optional[int] = None
    success: bool
    message: str

class BookSearchRequest(BaseModel):
    query: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    isbn: Optional[str] = None
    status: Optional[BookStatus] = None
    condition: Optional[BookCondition] = None
    publication_year_from: Optional[int] = None
    publication_year_to: Optional[int] = None

class BulkDeleteRequest(BaseModel):
    book_ids: List[str]

class ReadingListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: bool = False

class ReadingListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    user_id: str
    is_public: bool
    book_count: int
    created_at: datetime
    updated_at: datetime

class BookRecommendation(BaseModel):
    book: BookResponse
    score: float
    reason: str
