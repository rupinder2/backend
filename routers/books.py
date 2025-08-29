from fastapi import APIRouter, HTTPException, Depends, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime, date, timedelta
import uuid
import os
import base64

from auth.dependencies import get_current_user
from models.book import (
    BookResponse, BookListResponse, BookCreate, BookUpdate, 
    CheckoutRequest, CheckoutResponse, CheckinResponse,
    BookSearchRequest, BulkDeleteRequest, BookStatus, BookCondition,
    ReadingListCreate, ReadingListResponse, BookRecommendation
)
from supabase_client import supabase_admin
from services.ai_service import ai_service

router = APIRouter(prefix="/books", tags=["books"])

# Default book cover image as base64 encoded SVG
DEFAULT_BOOK_COVER_SVG = """
<svg width="300" height="400" viewBox="0 0 300 400" xmlns="http://www.w3.org/2000/svg">
  <rect width="300" height="400" fill="#f3f4f6"/>
  <rect x="20" y="20" width="260" height="360" fill="#e5e7eb" stroke="#9ca3af" stroke-width="2"/>
  <rect x="40" y="60" width="220" height="4" fill="#6b7280"/>
  <rect x="40" y="80" width="180" height="4" fill="#6b7280"/>
  <rect x="40" y="100" width="200" height="4" fill="#6b7280"/>
  <circle cx="150" cy="200" r="40" fill="#9ca3af"/>
  <path d="M130 185 L150 205 L170 185" stroke="#6b7280" stroke-width="2" fill="none"/>
  <text x="150" y="250" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#6b7280">No Cover</text>
  <text x="150" y="270" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#9ca3af">Available</text>
</svg>
"""

async def upload_book_cover(file: UploadFile, user_id: str) -> str:
    """Upload book cover image to Supabase storage and return public URL"""
    try:
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed.")
        
        # Validate file size (5MB limit)
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(status_code=400, detail="File size too large. Maximum 5MB allowed.")
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"book-cover-{uuid.uuid4()}.{file_extension}"
        
        # Upload to Supabase storage
        result = supabase_admin.storage.from_("book-covers").upload(
            filename, 
            content,
            {"content-type": file.content_type}
        )
        
        # Get public URL
        public_url = supabase_admin.storage.from_("book-covers").get_public_url(filename)
        return public_url
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

def get_default_book_cover_url() -> str:
    """Return a default book cover URL"""
    # Convert SVG to data URI
    svg_data = DEFAULT_BOOK_COVER_SVG.strip()
    encoded_svg = base64.b64encode(svg_data.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{encoded_svg}"

@router.post("", response_model=BookResponse)
async def create_book(
    book_data: BookCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add a new book to the library."""
    try:
        user_id = current_user["user_id"]
        
        # Prepare book data
        book_dict = book_data.dict()
        book_dict.update({
            "added_by": user_id,
            "status": BookStatus.AVAILABLE.value
        })
        
        # If no cover image URL provided, use default
        if not book_dict.get("cover_image_url"):
            book_dict["cover_image_url"] = get_default_book_cover_url()
        
        # Insert book record
        result = supabase_admin.table("books").insert(book_dict).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create book record")
        
        return BookResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create book: {str(e)}")

@router.post("/with-image", response_model=BookResponse)
async def create_book_with_image(
    title: str = Form(...),
    author: str = Form(...),
    genre: str = Form(...),
    isbn: Optional[str] = Form(None),
    publication_year: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    publisher: Optional[str] = Form(None),
    pages: Optional[int] = Form(None),
    language: str = Form("English"),
    location: Optional[str] = Form(None),
    condition: str = Form("good"),
    cover_image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """Add a new book to the library with optional image upload."""
    try:
        user_id = current_user["user_id"]
        
        # Handle image upload
        cover_image_url = None
        if cover_image and cover_image.filename:
            cover_image_url = await upload_book_cover(cover_image, user_id)
        else:
            cover_image_url = get_default_book_cover_url()
        
        # Prepare book data
        book_dict = {
            "title": title,
            "author": author,
            "genre": genre,
            "isbn": isbn,
            "publication_year": publication_year,
            "description": description,
            "publisher": publisher,
            "pages": pages,
            "language": language,
            "location": location,
            "condition": condition,
            "cover_image_url": cover_image_url,
            "added_by": user_id,
            "status": BookStatus.AVAILABLE.value
        }
        
        # Remove None values
        book_dict = {k: v for k, v in book_dict.items() if v is not None}
        
        # Insert book record
        result = supabase_admin.table("books").insert(book_dict).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create book record")
        
        return BookResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create book: {str(e)}")

@router.get("", response_model=BookListResponse)
async def list_books(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[BookStatus] = None,
    genre: Optional[str] = None,
    author: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List books with pagination and filtering."""
    try:
        offset = (page - 1) * limit
        
        # Build query
        query = supabase_admin.table("books").select("*")
        
        # Apply filters
        if status:
            query = query.eq("status", status.value)
        if genre:
            query = query.eq("genre", genre)
        if author:
            query = query.ilike("author", f"%{author}%")
        if search:
            # Search across title, author, and description
            search_pattern = f"%{search}%"
            query = query.or_(f"title.ilike.{search_pattern},author.ilike.{search_pattern},description.ilike.{search_pattern}")
        
        # Get total count for pagination
        count_query = supabase_admin.table("books").select("id", count="exact")
        if status:
            count_query = count_query.eq("status", status.value)
        if genre:
            count_query = count_query.eq("genre", genre)
        if author:
            count_query = count_query.ilike("author", f"%{author}%")
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.or_(f"title.ilike.{search_pattern},author.ilike.{search_pattern},description.ilike.{search_pattern}")
        
        total = count_query.execute().count or 0
        
        # Get paginated results
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        # Ensure default cover images for books without one
        books_data = result.data
        for book in books_data:
            if not book.get("cover_image_url"):
                book["cover_image_url"] = get_default_book_cover_url()
        
        books = [BookResponse(**book) for book in books_data]
        
        return BookListResponse(
            books=books,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list books: {str(e)}")

@router.get("/my-checkouts", response_model=BookListResponse)
async def get_my_checkouts(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get books currently on loan to the user."""
    try:
        user_id = current_user["user_id"]
        print(f"DEBUG: Getting checkouts for user_id: {user_id}")
        offset = (page - 1) * limit
        
        # Get checked out books
        query = supabase_admin.table("books").select("*").eq("checked_out_by", user_id).eq("status", BookStatus.CHECKED_OUT.value)
        
        # Get total count
        count_result = supabase_admin.table("books").select("id", count="exact").eq("checked_out_by", user_id).eq("status", BookStatus.CHECKED_OUT.value).execute()
        total = count_result.count or 0
        
        # Get paginated results
        result = query.order("checked_out_at", desc=True).range(offset, offset + limit - 1).execute()
        
        # Process the books data and handle None values
        books_data = result.data or []
        books = []
        for book_data in books_data:
            # Ensure all required fields are present and handle None values
            if not book_data.get('cover_image_url'):
                book_data['cover_image_url'] = get_default_book_cover_url()
            
            books.append(BookResponse(**book_data))
        
        return BookListResponse(
            books=books,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in get_my_checkouts: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to get checkouts: {str(e)}")

@router.get("/my-checkouts/notifications")
async def get_checkout_notifications(
    current_user: dict = Depends(get_current_user)
):
    """Get notification summary for user's loans (overdue and due soon)."""
    try:
        user_id = current_user["user_id"]
        
        # Get all checked out books for this user
        result = supabase_admin.table("books").select("*").eq("checked_out_by", user_id).eq("status", BookStatus.CHECKED_OUT.value).execute()
        
        books = result.data or []
        current_date = date.today()
        
        overdue_books = []
        due_soon_books = []
        
        for book in books:
            if book.get("due_date"):
                due_date = datetime.strptime(book["due_date"], "%Y-%m-%d").date()
                days_diff = (due_date - current_date).days
                
                if days_diff < 0:  # Overdue
                    overdue_books.append({
                        "id": book["id"],
                        "title": book["title"],
                        "author": book["author"],
                        "due_date": book["due_date"],
                        "days_overdue": abs(days_diff)
                    })
                elif days_diff <= 3:  # Due soon (within 3 days)
                    due_soon_books.append({
                        "id": book["id"],
                        "title": book["title"],
                        "author": book["author"],
                        "due_date": book["due_date"],
                        "days_until_due": days_diff
                    })
        
        return {
            "total_checkouts": len(books),
            "overdue_count": len(overdue_books),
            "due_soon_count": len(due_soon_books),
            "overdue_books": overdue_books,
            "due_soon_books": due_soon_books,
            "has_notifications": len(overdue_books) > 0 or len(due_soon_books) > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get checkout notifications: {str(e)}")

@router.get("/genres/list")
async def list_genres(current_user: dict = Depends(get_current_user)):
    """Get list of all genres in the library."""
    try:
        result = supabase_admin.table("books").select("genre").execute()
        
        genres = list(set([book["genre"] for book in result.data if book["genre"]]))
        genres.sort()
        
        return {"genres": genres}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get genres: {str(e)}")

@router.get("/search/advanced")
async def advanced_search(
    query: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    isbn: Optional[str] = None,
    status: Optional[BookStatus] = None,
    condition: Optional[BookCondition] = None,
    publication_year_from: Optional[int] = None,
    publication_year_to: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Advanced search for books with multiple filters."""
    try:
        offset = (page - 1) * limit
        
        # Build query
        search_query = supabase_admin.table("books").select("*")
        
        # Apply filters
        if query:
            # General search across multiple fields
            search_pattern = f"%{query}%"
            search_query = search_query.or_(f"title.ilike.{search_pattern},author.ilike.{search_pattern},description.ilike.{search_pattern},genre.ilike.{search_pattern}")
        
        if title:
            search_query = search_query.ilike("title", f"%{title}%")
        if author:
            search_query = search_query.ilike("author", f"%{author}%")
        if genre:
            search_query = search_query.ilike("genre", f"%{genre}%")
        if isbn:
            search_query = search_query.eq("isbn", isbn)
        if status:
            search_query = search_query.eq("status", status.value)
        if condition:
            search_query = search_query.eq("condition", condition.value)
        if publication_year_from:
            search_query = search_query.gte("publication_year", publication_year_from)
        if publication_year_to:
            search_query = search_query.lte("publication_year", publication_year_to)
        
        # Get total count
        count_query = supabase_admin.table("books").select("id", count="exact")
        # Apply same filters for count
        if query:
            search_pattern = f"%{query}%"
            count_query = count_query.or_(f"title.ilike.{search_pattern},author.ilike.{search_pattern},description.ilike.{search_pattern},genre.ilike.{search_pattern}")
        if title:
            count_query = count_query.ilike("title", f"%{title}%")
        if author:
            count_query = count_query.ilike("author", f"%{author}%")
        if genre:
            count_query = count_query.ilike("genre", f"%{genre}%")
        if isbn:
            count_query = count_query.eq("isbn", isbn)
        if status:
            count_query = count_query.eq("status", status.value)
        if condition:
            count_query = count_query.eq("condition", condition.value)
        if publication_year_from:
            count_query = count_query.gte("publication_year", publication_year_from)
        if publication_year_to:
            count_query = count_query.lte("publication_year", publication_year_to)
        
        total = count_query.execute().count or 0
        
        # Get paginated results
        result = search_query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        books = [BookResponse(**book) for book in result.data]
        
        return BookListResponse(
            books=books,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search books: {str(e)}")

@router.get("/recommendations/personalized")
async def get_personalized_recommendations(
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered personalized book recommendations."""
    try:
        user_id = current_user["user_id"]
        recommendations = await ai_service.get_personalized_recommendations(user_id, limit)
        
        return {
            "recommendations": recommendations,
            "total": len(recommendations),
            "personalized": len(recommendations) > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@router.get("/recommendations/popular")
async def get_popular_recommendations(
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """Get popular book recommendations."""
    try:
        recommendations = await ai_service.get_popular_recommendations(limit)
        
        return {
            "recommendations": recommendations,
            "total": len(recommendations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get popular recommendations: {str(e)}")

@router.get("/insights/reading")
async def get_reading_insights(
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered reading insights and analytics."""
    try:
        user_id = current_user["user_id"]
        insights = await ai_service.get_reading_insights(user_id)
        
        return insights
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reading insights: {str(e)}")

@router.get("/analytics/library")
async def get_library_analytics(
    current_user: dict = Depends(get_current_user)
):
    """Get library-wide analytics and statistics."""
    try:
        # Total books
        total_books = supabase_admin.table("books").select("id", count="exact").execute().count or 0
        
        # Available books
        available_books = supabase_admin.table("books").select("id", count="exact").eq("status", "available").execute().count or 0
        
        # Checked out books
        checked_out_books = supabase_admin.table("books").select("id", count="exact").eq("status", "checked_out").execute().count or 0
        
        # Most popular genres
        books_result = supabase_admin.table("books").select("genre").execute()
        genre_counts = {}
        for book in books_result.data or []:
            genre = book.get('genre', 'Unknown')
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        popular_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Recent activity (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        recent_checkouts = supabase_admin.table("checkout_history")\
            .select("id", count="exact")\
            .gte("checked_out_at", thirty_days_ago)\
            .execute().count or 0
        
        return {
            "total_books": total_books,
            "available_books": available_books,
            "checked_out_books": checked_out_books,
            "popular_genres": [{"genre": genre, "count": count} for genre, count in popular_genres],
            "recent_checkouts": recent_checkouts,
            "library_utilization": round((checked_out_books / total_books * 100) if total_books > 0 else 0, 1)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get library analytics: {str(e)}")

@router.get("/recommendations/ai-search")
async def get_ai_search_recommendations(
    search_query: str = Query(..., description="The search query that didn't return results"),
    limit: int = Query(5, ge=1, le=10),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered recommendations when a searched book is not available."""
    try:
        user_id = current_user["user_id"]
        recommendations = await ai_service.get_ai_search_recommendations(search_query, user_id, limit)
        
        return {
            "search_query": search_query,
            "recommendations": recommendations,
            "total": len(recommendations),
            "ai_powered": ai_service.openai_enabled,
            "message": f"Since '{search_query}' isn't available, here are some books you might enjoy based on your interests"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get AI search recommendations: {str(e)}")

@router.get("/recommendations/ai-enhanced")
async def get_enhanced_ai_recommendations(
    limit: int = Query(5, ge=1, le=10),
    current_user: dict = Depends(get_current_user)
):
    """Get enhanced AI-powered personalized recommendations."""
    try:
        user_id = current_user["user_id"]
        recommendations = await ai_service.get_enhanced_ai_recommendations(user_id, limit)
        
        return {
            "recommendations": recommendations,
            "total": len(recommendations),
            "ai_powered": ai_service.openai_enabled,
            "message": "AI-curated recommendations based on your reading history"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get enhanced AI recommendations: {str(e)}")

@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific book by ID."""
    try:
        result = supabase_admin.table("books").select("*").eq("id", book_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book_data = result.data[0]
        if not book_data.get("cover_image_url"):
            book_data["cover_image_url"] = get_default_book_cover_url()
        
        return BookResponse(**book_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get book: {str(e)}")

@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: str,
    update_data: BookUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update book information."""
    try:
        user_id = current_user["user_id"]
        
        # Check if book exists and user has permission to update
        existing = supabase_admin.table("books").select("*").eq("id", book_id).eq("added_by", user_id).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Book not found or permission denied")
        
        # Prepare update data (only include non-None fields)
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        # Update book
        result = supabase_admin.table("books").update(update_dict).eq("id", book_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update book")
        
        return BookResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update book: {str(e)}")

@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a book from the library."""
    try:
        user_id = current_user["user_id"]
        
        # Check if book exists and user has permission to delete
        existing = supabase_admin.table("books").select("*").eq("id", book_id).eq("added_by", user_id).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Book not found or permission denied")
        
        book = existing.data[0]
        
        # Check if book is currently checked out
        if book["status"] == BookStatus.CHECKED_OUT.value:
            raise HTTPException(status_code=400, detail="Cannot delete a book that is currently checked out")
        
        # Delete book
        delete_result = supabase_admin.table("books").delete().eq("id", book_id).execute()
        
        if not delete_result.data:
            raise HTTPException(status_code=500, detail="Failed to delete book")
        
        return {"message": "Book deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete book: {str(e)}")

@router.post("/bulk-delete")
async def bulk_delete_books(
    request: BulkDeleteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Delete multiple books."""
    try:
        user_id = current_user["user_id"]
        book_ids = request.book_ids
        
        if not book_ids:
            raise HTTPException(status_code=400, detail="No book IDs provided")
        
        # Get books that belong to the user and are not checked out
        result = supabase_admin.table("books").select("*").eq("added_by", user_id).in_("id", book_ids).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No books found")
        
        # Check for checked out books
        checked_out_books = [book for book in result.data if book["status"] == BookStatus.CHECKED_OUT.value]
        if checked_out_books:
            checked_out_titles = [book["title"] for book in checked_out_books[:3]]
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete checked out books: {', '.join(checked_out_titles)}" + 
                       ("..." if len(checked_out_books) > 3 else "")
            )
        
        found_ids = [book["id"] for book in result.data]
        
        # Delete books
        delete_result = supabase_admin.table("books").delete().in_("id", found_ids).execute()
        
        if not delete_result.data:
            raise HTTPException(status_code=500, detail="Failed to delete books")
        
        return {
            "message": f"Successfully deleted {len(found_ids)} books",
            "deleted_count": len(found_ids),
            "requested_count": len(book_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete books: {str(e)}")

@router.post("/{book_id}/checkout", response_model=CheckoutResponse)
async def checkout_book(
    book_id: str,
    checkout_data: CheckoutRequest,
    current_user: dict = Depends(get_current_user)
):
    """Check out a book to the current user."""
    try:
        user_id = current_user["user_id"]
        
        # Get book details
        book_result = supabase_admin.table("books").select("*").eq("id", book_id).execute()
        
        if not book_result.data:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book = book_result.data[0]
        
        # Check if book is available
        if book["status"] != BookStatus.AVAILABLE.value:
            raise HTTPException(status_code=400, detail="Book is not available for checkout")
        
        # Calculate due date
        checkout_date = datetime.now()
        due_date = (checkout_date + timedelta(days=checkout_data.checkout_days)).date()
        
        # Update book status
        update_data = {
            "status": BookStatus.CHECKED_OUT.value,
            "checked_out_by": user_id,
            "checked_out_at": checkout_date.isoformat(),
            "due_date": due_date.isoformat()
        }
        
        update_result = supabase_admin.table("books").update(update_data).eq("id", book_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to checkout book")
        
        # Add to checkout history
        history_data = {
            "book_id": book_id,
            "user_id": user_id,
            "checked_out_at": checkout_date.isoformat(),
            "due_date": due_date.isoformat()
        }
        
        supabase_admin.table("checkout_history").insert(history_data).execute()
        
        return CheckoutResponse(
            book_id=book_id,
            checked_out_by=user_id,
            checked_out_at=checkout_date,
            due_date=due_date,
            success=True,
            message=f"Book checked out successfully. Due date: {due_date}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to checkout book: {str(e)}")

@router.post("/{book_id}/checkin", response_model=CheckinResponse)
async def checkin_book(
    book_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check in a book (return it)."""
    try:
        user_id = current_user["user_id"]
        
        # Get book details
        book_result = supabase_admin.table("books").select("*").eq("id", book_id).execute()
        
        if not book_result.data:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book = book_result.data[0]
        
        # Check if book is checked out by this user
        if book["status"] != BookStatus.CHECKED_OUT.value or book["checked_out_by"] != user_id:
            raise HTTPException(status_code=400, detail="Book is not checked out by you")
        
        # Calculate if overdue
        due_date = datetime.strptime(book["due_date"], "%Y-%m-%d").date()
        return_date = datetime.now()
        is_overdue = return_date.date() > due_date
        days_overdue = (return_date.date() - due_date).days if is_overdue else None
        
        # Update book status
        update_data = {
            "status": BookStatus.AVAILABLE.value,
            "checked_out_by": None,
            "checked_out_at": None,
            "due_date": None
        }
        
        update_result = supabase_admin.table("books").update(update_data).eq("id", book_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to checkin book")
        
        # Update checkout history
        history_update = {
            "returned_at": return_date.isoformat(),
            "was_overdue": is_overdue
        }
        
        supabase_admin.table("checkout_history").update(history_update).eq("book_id", book_id).eq("user_id", user_id).is_("returned_at", "null").execute()
        
        message = "Book checked in successfully"
        if is_overdue:
            message += f" (was {days_overdue} days overdue)"
        
        return CheckinResponse(
            book_id=book_id,
            returned_at=return_date,
            was_overdue=is_overdue,
            days_overdue=days_overdue,
            success=True,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to checkin book: {str(e)}")

@router.get("/search/advanced")
async def advanced_search(
    query: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    isbn: Optional[str] = None,
    status: Optional[BookStatus] = None,
    condition: Optional[BookCondition] = None,
    publication_year_from: Optional[int] = None,
    publication_year_to: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Advanced search for books with multiple filters."""
    try:
        offset = (page - 1) * limit
        
        # Build query
        search_query = supabase_admin.table("books").select("*")
        
        # Apply filters
        if query:
            # General search across multiple fields
            search_pattern = f"%{query}%"
            search_query = search_query.or_(f"title.ilike.{search_pattern},author.ilike.{search_pattern},description.ilike.{search_pattern},genre.ilike.{search_pattern}")
        
        if title:
            search_query = search_query.ilike("title", f"%{title}%")
        if author:
            search_query = search_query.ilike("author", f"%{author}%")
        if genre:
            search_query = search_query.ilike("genre", f"%{genre}%")
        if isbn:
            search_query = search_query.eq("isbn", isbn)
        if status:
            search_query = search_query.eq("status", status.value)
        if condition:
            search_query = search_query.eq("condition", condition.value)
        if publication_year_from:
            search_query = search_query.gte("publication_year", publication_year_from)
        if publication_year_to:
            search_query = search_query.lte("publication_year", publication_year_to)
        
        # Get total count
        count_query = supabase_admin.table("books").select("id", count="exact")
        # Apply same filters for count
        if query:
            search_pattern = f"%{query}%"
            count_query = count_query.or_(f"title.ilike.{search_pattern},author.ilike.{search_pattern},description.ilike.{search_pattern},genre.ilike.{search_pattern}")
        if title:
            count_query = count_query.ilike("title", f"%{title}%")
        if author:
            count_query = count_query.ilike("author", f"%{author}%")
        if genre:
            count_query = count_query.ilike("genre", f"%{genre}%")
        if isbn:
            count_query = count_query.eq("isbn", isbn)
        if status:
            count_query = count_query.eq("status", status.value)
        if condition:
            count_query = count_query.eq("condition", condition.value)
        if publication_year_from:
            count_query = count_query.gte("publication_year", publication_year_from)
        if publication_year_to:
            count_query = count_query.lte("publication_year", publication_year_to)
        
        total = count_query.execute().count or 0
        
        # Get paginated results
        result = search_query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        books = [BookResponse(**book) for book in result.data]
        
        return BookListResponse(
            books=books,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search books: {str(e)}")

@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific book by ID."""
    try:
        result = supabase_admin.table("books").select("*").eq("id", book_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book_data = result.data[0]
        if not book_data.get("cover_image_url"):
            book_data["cover_image_url"] = get_default_book_cover_url()
        
        return BookResponse(**book_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get book: {str(e)}")

@router.put("/{book_id}", response_model=BookResponse)
async def get_checkout_notifications(
    current_user: dict = Depends(get_current_user)
):
    """Get notification summary for user's loans (overdue and due soon)."""
    try:
        user_id = current_user["user_id"]
        
        # Get all checked out books for this user
        result = supabase_admin.table("books").select("*").eq("checked_out_by", user_id).eq("status", BookStatus.CHECKED_OUT.value).execute()
        
        books = result.data or []
        current_date = date.today()
        
        overdue_books = []
        due_soon_books = []
        
        for book in books:
            if book.get("due_date"):
                due_date = datetime.strptime(book["due_date"], "%Y-%m-%d").date()
                days_diff = (due_date - current_date).days
                
                if days_diff < 0:  # Overdue
                    overdue_books.append({
                        "id": book["id"],
                        "title": book["title"],
                        "author": book["author"],
                        "due_date": book["due_date"],
                        "days_overdue": abs(days_diff)
                    })
                elif days_diff <= 3:  # Due soon (within 3 days)
                    due_soon_books.append({
                        "id": book["id"],
                        "title": book["title"],
                        "author": book["author"],
                        "due_date": book["due_date"],
                        "days_until_due": days_diff
                    })
        
        return {
            "total_checkouts": len(books),
            "overdue_count": len(overdue_books),
            "due_soon_count": len(due_soon_books),
            "overdue_books": overdue_books,
            "due_soon_books": due_soon_books,
            "has_notifications": len(overdue_books) > 0 or len(due_soon_books) > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get checkout notifications: {str(e)}")

@router.post("/{book_id}/extend-checkout")
async def extend_checkout(
    book_id: str,
    extend_days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_user)
):
    """Renew the loan period for a book."""
    try:
        user_id = current_user["user_id"]
        
        # Get book details
        book_result = supabase_admin.table("books").select("*").eq("id", book_id).execute()
        
        if not book_result.data:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book = book_result.data[0]
        
        # Check if book is checked out by this user
        if book["status"] != BookStatus.CHECKED_OUT.value or book["checked_out_by"] != user_id:
            raise HTTPException(status_code=400, detail="Book is not checked out by you")
        
        # Calculate new due date
        current_due_date = datetime.strptime(book["due_date"], "%Y-%m-%d").date()
        new_due_date = current_due_date + timedelta(days=extend_days)
        
        # Update book with new due date
        update_data = {
            "due_date": new_due_date.isoformat()
        }
        
        update_result = supabase_admin.table("books").update(update_data).eq("id", book_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to renew loan")
        
        return {
            "book_id": book_id,
            "old_due_date": current_due_date.isoformat(),
            "new_due_date": new_due_date.isoformat(),
            "extended_days": extend_days,
            "success": True,
            "message": f"Loan renewed for {extend_days} additional days. New due date: {new_due_date.strftime('%B %d, %Y')}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to renew loan: {str(e)}")

@router.get("/recommendations/personalized")
async def get_personalized_recommendations(
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered personalized book recommendations."""
    try:
        user_id = current_user["user_id"]
        recommendations = await ai_service.get_personalized_recommendations(user_id, limit)
        
        return {
            "recommendations": recommendations,
            "total": len(recommendations),
            "personalized": len(recommendations) > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@router.get("/recommendations/popular")
async def get_popular_recommendations(
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """Get popular book recommendations."""
    try:
        recommendations = await ai_service.get_popular_recommendations(limit)
        
        return {
            "recommendations": recommendations,
            "total": len(recommendations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get popular recommendations: {str(e)}")

@router.get("/insights/reading")
async def get_reading_insights(
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered reading insights and analytics."""
    try:
        user_id = current_user["user_id"]
        insights = await ai_service.get_reading_insights(user_id)
        
        return insights
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reading insights: {str(e)}")

@router.get("/analytics/library")
async def get_library_analytics(
    current_user: dict = Depends(get_current_user)
):
    """Get library-wide analytics and statistics."""
    try:
        # Total books
        total_books = supabase_admin.table("books").select("id", count="exact").execute().count or 0
        
        # Available books
        available_books = supabase_admin.table("books").select("id", count="exact").eq("status", "available").execute().count or 0
        
        # Checked out books
        checked_out_books = supabase_admin.table("books").select("id", count="exact").eq("status", "checked_out").execute().count or 0
        
        # Most popular genres
        books_result = supabase_admin.table("books").select("genre").execute()
        genre_counts = {}
        for book in books_result.data or []:
            genre = book.get('genre', 'Unknown')
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        popular_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Recent activity (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        recent_checkouts = supabase_admin.table("checkout_history")\
            .select("id", count="exact")\
            .gte("checked_out_at", thirty_days_ago)\
            .execute().count or 0
        
        return {
            "total_books": total_books,
            "available_books": available_books,
            "checked_out_books": checked_out_books,
            "popular_genres": [{"genre": genre, "count": count} for genre, count in popular_genres],
            "recent_checkouts": recent_checkouts,
            "library_utilization": round((checked_out_books / total_books * 100) if total_books > 0 else 0, 1)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get library analytics: {str(e)}")

@router.get("/recommendations/ai-search")
async def get_ai_search_recommendations(
    search_query: str = Query(..., description="The search query that didn't return results"),
    limit: int = Query(5, ge=1, le=10),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered recommendations when a searched book is not available."""
    try:
        user_id = current_user["user_id"]
        recommendations = await ai_service.get_ai_search_recommendations(search_query, user_id, limit)
        
        return {
            "search_query": search_query,
            "recommendations": recommendations,
            "total": len(recommendations),
            "ai_powered": ai_service.openai_enabled,
            "message": f"Since '{search_query}' isn't available, here are some books you might enjoy based on your interests"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get AI search recommendations: {str(e)}")

@router.get("/recommendations/ai-enhanced")
async def get_enhanced_ai_recommendations(
    limit: int = Query(5, ge=1, le=10),
    current_user: dict = Depends(get_current_user)
):
    """Get enhanced AI-powered personalized recommendations."""
    try:
        user_id = current_user["user_id"]
        recommendations = await ai_service.get_enhanced_ai_recommendations(user_id, limit)
        
        return {
            "recommendations": recommendations,
            "total": len(recommendations),
            "ai_powered": ai_service.openai_enabled,
            "message": "AI-curated recommendations based on your reading history"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get enhanced AI recommendations: {str(e)}")