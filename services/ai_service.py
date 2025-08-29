"""
AI-powered features for the library management system.
This module provides intelligent recommendations and insights.
"""

import random
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from supabase_client import supabase_admin
from config import settings
import openai

class AILibraryService:
    """AI-powered library management features."""
    
    def __init__(self):
        # Initialize OpenAI client
        if settings.OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )
            self.openai_enabled = True
        else:
            self.openai_client = None
            self.openai_enabled = False
        
        self.genre_similarities = {
            'Science Fiction': ['Fantasy', 'Dystopian Fiction', 'Technology'],
            'Fantasy': ['Science Fiction', 'Adventure', 'Young Adult'],
            'Mystery': ['Thriller', 'Crime', 'Psychological Thriller'],
            'Thriller': ['Mystery', 'Crime', 'Horror', 'Psychological Thriller'],
            'Romance': ['Drama', 'Contemporary Fiction', 'Young Adult'],
            'Non-fiction': ['Biography', 'History', 'Science', 'Philosophy', 'Self-help'],
            'Biography': ['History', 'Non-fiction', 'Memoir'],
            'History': ['Biography', 'Non-fiction', 'Politics'],
            'Classic Literature': ['Fiction', 'Drama', 'Philosophy'],
            'Young Adult': ['Fantasy', 'Romance', 'Coming-of-age', 'Adventure'],
            'Horror': ['Thriller', 'Mystery', 'Psychological Thriller'],
            'Business': ['Self-help', 'Non-fiction', 'Technology'],
            'Science': ['Non-fiction', 'Technology', 'Philosophy'],
            'Philosophy': ['Non-fiction', 'Science', 'Psychology'],
            'Psychology': ['Self-help', 'Philosophy', 'Non-fiction'],
            'Self-help': ['Psychology', 'Business', 'Non-fiction'],
            'Technology': ['Science', 'Non-fiction', 'Science Fiction'],
            'Crime': ['Mystery', 'Thriller', 'Psychological Thriller'],
            'Adventure': ['Fantasy', 'Young Adult', 'Action'],
            'Drama': ['Classic Literature', 'Romance', 'Fiction'],
            'Memoir': ['Biography', 'Non-fiction', 'History'],
            'Coming-of-age': ['Young Adult', 'Fiction', 'Drama'],
            'Dystopian Fiction': ['Science Fiction', 'Thriller', 'Philosophy'],
            'Psychological Thriller': ['Thriller', 'Mystery', 'Horror', 'Crime']
        }
    
    async def get_personalized_recommendations(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get personalized book recommendations based on user's reading history."""
        try:
            # Get user's checkout history
            checkout_history = supabase_admin.table("checkout_history")\
                .select("*, books!inner(*)")\
                .eq("user_id", user_id)\
                .execute()
            
            if not checkout_history.data:
                # New user - get popular books
                return await self.get_popular_recommendations(limit)
            
            # Analyze reading patterns
            user_preferences = self._analyze_user_preferences(checkout_history.data)
            
            # Get recommendations based on preferences
            recommendations = await self._get_recommendations_by_preferences(
                user_preferences, user_id, limit
            )
            
            return recommendations
            
        except Exception as e:
            print(f"Error getting personalized recommendations: {e}")
            return await self.get_popular_recommendations(limit)
    
    def _analyze_user_preferences(self, checkout_history: List[Dict]) -> Dict[str, Any]:
        """Analyze user reading patterns from checkout history."""
        genres = {}
        authors = {}
        total_books = len(checkout_history)
        
        for record in checkout_history:
            book = record.get('books', {})
            
            # Count genres
            genre = book.get('genre', 'Unknown')
            genres[genre] = genres.get(genre, 0) + 1
            
            # Count authors
            author = book.get('author', 'Unknown')
            authors[author] = authors.get(author, 0) + 1
        
        # Get preferred genres (sorted by frequency)
        preferred_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
        preferred_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'preferred_genres': [genre for genre, count in preferred_genres[:3]],
            'preferred_authors': [author for author, count in preferred_authors[:3]],
            'total_books_read': total_books,
            'genre_diversity': len(genres),
            'reading_pattern': self._determine_reading_pattern(genres, total_books)
        }
    
    def _determine_reading_pattern(self, genres: Dict[str, int], total_books: int) -> str:
        """Determine user's reading pattern based on genre distribution."""
        if total_books < 3:
            return "new_reader"
        
        max_genre_count = max(genres.values()) if genres else 0
        genre_concentration = max_genre_count / total_books if total_books > 0 else 0
        
        if genre_concentration > 0.7:
            return "genre_focused"
        elif len(genres) >= 5:
            return "diverse_reader"
        else:
            return "moderate_explorer"
    
    async def _get_recommendations_by_preferences(
        self, preferences: Dict[str, Any], user_id: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Get book recommendations based on user preferences."""
        recommendations = []
        
        # Get books user hasn't checked out
        user_books = supabase_admin.table("checkout_history")\
            .select("book_id")\
            .eq("user_id", user_id)\
            .execute()
        
        checked_out_book_ids = [record['book_id'] for record in user_books.data] if user_books.data else []
        
        # Strategy 1: Similar genres
        for genre in preferences['preferred_genres']:
            similar_genres = self.genre_similarities.get(genre, [genre])
            for similar_genre in similar_genres:
                books = await self._get_books_by_genre(similar_genre, checked_out_book_ids, limit // 2)
                for book in books:
                    if len(recommendations) < limit:
                        recommendations.append({
                            'book': book,
                            'score': 0.8,
                            'reason': f"Similar to your interest in {genre}"
                        })
        
        # Strategy 2: Same authors
        for author in preferences['preferred_authors']:
            books = await self._get_books_by_author(author, checked_out_book_ids, 2)
            for book in books:
                if len(recommendations) < limit:
                    recommendations.append({
                        'book': book,
                        'score': 0.9,
                        'reason': f"Another book by {author}"
                    })
        
        # Strategy 3: Highly rated books in preferred genres
        for genre in preferences['preferred_genres']:
            books = await self._get_highly_rated_books_by_genre(genre, checked_out_book_ids, 2)
            for book in books:
                if len(recommendations) < limit:
                    recommendations.append({
                        'book': book,
                        'score': 0.7,
                        'reason': f"Highly rated {genre} book"
                    })
        
        # If we don't have enough recommendations, fill with popular books
        if len(recommendations) < limit:
            popular_books = await self.get_popular_recommendations(limit - len(recommendations))
            recommendations.extend(popular_books)
        
        # Remove duplicates and sort by score
        seen_books = set()
        unique_recommendations = []
        for rec in recommendations:
            book_id = rec['book']['id']
            if book_id not in seen_books:
                seen_books.add(book_id)
                unique_recommendations.append(rec)
        
        return sorted(unique_recommendations, key=lambda x: x['score'], reverse=True)[:limit]
    
    async def _get_books_by_genre(self, genre: str, exclude_ids: List[str], limit: int) -> List[Dict]:
        """Get available books by genre."""
        query = supabase_admin.table("books").select("*").eq("genre", genre).eq("status", "available")
        
        if exclude_ids:
            query = query.not_.in_("id", exclude_ids)
        
        result = query.limit(limit).execute()
        return result.data or []
    
    async def _get_books_by_author(self, author: str, exclude_ids: List[str], limit: int) -> List[Dict]:
        """Get available books by author."""
        query = supabase_admin.table("books").select("*").eq("author", author).eq("status", "available")
        
        if exclude_ids:
            query = query.not_.in_("id", exclude_ids)
        
        result = query.limit(limit).execute()
        return result.data or []
    
    async def _get_highly_rated_books_by_genre(self, genre: str, exclude_ids: List[str], limit: int) -> List[Dict]:
        """Get highly rated books by genre (simulated for now)."""
        books = await self._get_books_by_genre(genre, exclude_ids, limit * 2)
        
        # Simulate rating by using publication year and random factor
        for book in books:
            # Newer books and classic books get higher "ratings"
            year = book.get('publication_year', 1900)
            if year > 2010 or year < 1960:
                book['simulated_rating'] = random.uniform(4.0, 5.0)
            else:
                book['simulated_rating'] = random.uniform(3.0, 4.5)
        
        # Sort by simulated rating and return top books
        books.sort(key=lambda x: x.get('simulated_rating', 0), reverse=True)
        return books[:limit]
    
    async def get_popular_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get popular book recommendations (most checked out books)."""
        try:
            # Get books with checkout counts
            checkout_counts = supabase_admin.table("checkout_history")\
                .select("book_id, books!inner(*)")\
                .execute()
            
            if not checkout_counts.data:
                # No checkout history - return random available books
                available_books = supabase_admin.table("books")\
                    .select("*")\
                    .eq("status", "available")\
                    .limit(limit)\
                    .execute()
                
                return [{
                    'book': book,
                    'score': 0.5,
                    'reason': "Popular in our library"
                } for book in (available_books.data or [])]
            
            # Count checkouts per book
            book_counts = {}
            for record in checkout_counts.data:
                book_id = record['book_id']
                book_data = record.get('books', {})
                
                if book_data.get('status') == 'available':  # Only recommend available books
                    if book_id not in book_counts:
                        book_counts[book_id] = {
                            'book': book_data,
                            'count': 0
                        }
                    book_counts[book_id]['count'] += 1
            
            # Sort by popularity and create recommendations
            popular_books = sorted(book_counts.values(), key=lambda x: x['count'], reverse=True)
            
            recommendations = []
            for book_data in popular_books[:limit]:
                recommendations.append({
                    'book': book_data['book'],
                    'score': min(1.0, book_data['count'] / 10),  # Normalize score
                    'reason': f"Popular book ({book_data['count']} checkouts)"
                })
            
            return recommendations
            
        except Exception as e:
            print(f"Error getting popular recommendations: {e}")
            return []
    
    async def get_reading_insights(self, user_id: str) -> Dict[str, Any]:
        """Get reading insights and analytics for a user."""
        try:
            # Get user's checkout history
            checkout_history = supabase_admin.table("checkout_history")\
                .select("*, books!inner(*)")\
                .eq("user_id", user_id)\
                .execute()
            
            if not checkout_history.data:
                return {
                    'total_books_read': 0,
                    'favorite_genre': None,
                    'favorite_author': None,
                    'reading_streak': 0,
                    'insights': ["Start your reading journey by checking out your first book!"]
                }
            
            # Analyze reading patterns
            preferences = self._analyze_user_preferences(checkout_history.data)
            
            # Calculate reading streak
            reading_streak = self._calculate_reading_streak(checkout_history.data)
            
            # Generate insights
            insights = self._generate_reading_insights(preferences, checkout_history.data)
            
            return {
                'total_books_read': preferences['total_books_read'],
                'favorite_genre': preferences['preferred_genres'][0] if preferences['preferred_genres'] else None,
                'favorite_author': preferences['preferred_authors'][0] if preferences['preferred_authors'] else None,
                'reading_streak': reading_streak,
                'genre_diversity': preferences['genre_diversity'],
                'reading_pattern': preferences['reading_pattern'],
                'insights': insights
            }
            
        except Exception as e:
            print(f"Error getting reading insights: {e}")
            return {
                'total_books_read': 0,
                'insights': ["Unable to generate insights at this time."]
            }
    
    def _calculate_reading_streak(self, checkout_history: List[Dict]) -> int:
        """Calculate the user's current reading streak in days."""
        if not checkout_history:
            return 0
        
        # Sort by checkout date
        sorted_history = sorted(
            checkout_history,
            key=lambda x: x.get('checked_out_at', ''),
            reverse=True
        )
        
        today = datetime.now().date()
        streak = 0
        
        for record in sorted_history:
            checkout_date_str = record.get('checked_out_at')
            if checkout_date_str:
                checkout_date = datetime.fromisoformat(checkout_date_str.replace('Z', '+00:00')).date()
                days_diff = (today - checkout_date).days
                
                if days_diff <= 7:  # Checked out within the last week
                    streak += 1
                else:
                    break
        
        return min(streak * 7, 365)  # Cap at 365 days
    
    def _generate_reading_insights(self, preferences: Dict, checkout_history: List[Dict]) -> List[str]:
        """Generate personalized reading insights."""
        insights = []
        
        # Pattern-based insights
        pattern = preferences['reading_pattern']
        if pattern == "genre_focused":
            insights.append(f"You're a focused reader who loves {preferences['preferred_genres'][0]}!")
        elif pattern == "diverse_reader":
            insights.append("You're an adventurous reader who explores many genres!")
        elif pattern == "moderate_explorer":
            insights.append("You enjoy variety in your reading while having some favorite genres.")
        
        # Volume insights
        total_books = preferences['total_books_read']
        if total_books >= 20:
            insights.append("Impressive! You're a prolific reader.")
        elif total_books >= 10:
            insights.append("Great reading habit! Keep it up.")
        elif total_books >= 5:
            insights.append("You're building a nice reading routine.")
        
        # Genre diversity insights
        if preferences['genre_diversity'] >= 5:
            insights.append("Your diverse reading helps you see the world from many perspectives.")
        elif preferences['genre_diversity'] >= 3:
            insights.append("You enjoy exploring different types of stories and ideas.")
        
        # Recent reading insights
        recent_books = [
            record for record in checkout_history
            if record.get('checked_out_at') and 
            (datetime.now() - datetime.fromisoformat(record['checked_out_at'].replace('Z', '+00:00'))).days <= 30
        ]
        
        if len(recent_books) >= 3:
            insights.append("You've been very active lately! Great reading momentum.")
        elif len(recent_books) == 0:
            insights.append("It's been a while since your last book. Ready for your next adventure?")
        
        return insights[:3]  # Return top 3 insights
    
    async def get_ai_search_recommendations(self, search_query: str, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get AI recommendations when a searched book is not available.
        Uses LLM to suggest similar books based on the search query and user's reading history.
        """
        try:
            if not self.openai_enabled:
                # Fallback to traditional recommendations if OpenAI is not available
                return await self.get_personalized_recommendations(user_id, limit)
            
            # Get user's reading history
            checkout_history = supabase_admin.table("checkout_history")\
                .select("*, books!inner(*)")\
                .eq("user_id", user_id)\
                .execute()
            
            # Get all available books
            available_books = supabase_admin.table("books")\
                .select("*")\
                .eq("status", "available")\
                .execute()
            
            if not available_books.data:
                return []
            
            # Prepare data for LLM
            user_books = []
            if checkout_history.data:
                user_books = [
                    f"{record['books']['title']} by {record['books']['author']} ({record['books']['genre']})"
                    for record in checkout_history.data
                ]
            
            available_titles = [
                {
                    "id": book["id"],
                    "title": book["title"],
                    "author": book["author"],
                    "genre": book["genre"],
                    "description": book.get("description", "")
                }
                for book in available_books.data
            ]
            
            # Create prompt for LLM
            prompt = self._create_search_recommendation_prompt(
                search_query, user_books, available_titles, limit
            )
            
            # Call OpenAI API
            response = await self._call_openai(prompt)
            
            if response:
                return self._parse_search_recommendations(response, available_books.data)
            else:
                # Fallback to traditional search if AI fails
                return await self._fallback_search_recommendations(search_query, user_id, limit)
                
        except Exception as e:
            print(f"Error in AI search recommendations: {e}")
            # Fallback to traditional recommendations
            return await self._fallback_search_recommendations(search_query, user_id, limit)
    
    async def get_enhanced_ai_recommendations(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get enhanced AI recommendations based on user's reading history.
        Uses LLM to provide more sophisticated recommendations with detailed reasoning.
        """
        try:
            if not self.openai_enabled:
                # Fallback to existing recommendations if OpenAI is not available
                return await self.get_personalized_recommendations(user_id, limit)
            
            # Get user's reading history
            checkout_history = supabase_admin.table("checkout_history")\
                .select("*, books!inner(*)")\
                .eq("user_id", user_id)\
                .execute()
            
            # Get all available books
            available_books = supabase_admin.table("books")\
                .select("*")\
                .eq("status", "available")\
                .execute()
            
            if not available_books.data:
                return []
            
            # Get books user hasn't read
            user_book_ids = []
            user_books = []
            if checkout_history.data:
                user_book_ids = [record['book_id'] for record in checkout_history.data]
                user_books = [
                    {
                        "title": record['books']['title'],
                        "author": record['books']['author'],
                        "genre": record['books']['genre'],
                        "description": record['books'].get('description', ''),
                        "publication_year": record['books'].get('publication_year', 'Unknown')
                    }
                    for record in checkout_history.data
                ]
            
            # Filter available books (exclude already read)
            unread_books = [
                book for book in available_books.data 
                if book["id"] not in user_book_ids
            ]
            
            if not unread_books:
                return []
            
            # Create prompt for LLM
            prompt = self._create_ai_recommendation_prompt(user_books, unread_books, limit)
            
            # Call OpenAI API
            response = await self._call_openai(prompt)
            
            if response:
                return self._parse_ai_recommendations(response, unread_books)
            else:
                # Fallback to existing personalized recommendations
                return await self.get_personalized_recommendations(user_id, limit)
                
        except Exception as e:
            print(f"Error in enhanced AI recommendations: {e}")
            # Fallback to existing recommendations
            return await self.get_personalized_recommendations(user_id, limit)
    
    def _create_search_recommendation_prompt(self, search_query: str, user_books: List[str], available_books: List[Dict], limit: int) -> str:
        """Create a prompt for search-based recommendations."""
        user_history = "None" if not user_books else "\n".join(f"- {book}" for book in user_books[-10:])  # Last 10 books
        
        available_list = "\n".join([
            f"ID: {book['id']}, Title: {book['title']}, Author: {book['author']}, Genre: {book['genre']}, Description: {book['description'][:100]}..."
            for book in available_books[:20]  # Limit to avoid token limits
        ])
        
        return f"""You are a librarian AI assistant helping users find books. 

The user searched for: "{search_query}"

The book they searched for is not available, but I want to recommend similar books from our library.

User's Reading History:
{user_history}

Available Books in Library:
{available_list}

Please recommend {limit} books that would interest someone searching for "{search_query}". Consider:
1. The user's reading history and preferences
2. Books similar to what they searched for
3. Books they haven't read yet

Respond with ONLY a JSON array of recommendations in this exact format:
[
  {{
    "book_id": "book_id_here",
    "reason": "Detailed explanation of why this book matches their search and interests",
    "score": 0.9
  }}
]

Ensure the book_id matches exactly from the available books list. Provide thoughtful, personalized reasons."""
    
    def _create_ai_recommendation_prompt(self, user_books: List[Dict], available_books: List[Dict], limit: int) -> str:
        """Create a prompt for AI-powered recommendations."""
        if user_books:
            user_history = "\n".join([
                f"- {book['title']} by {book['author']} ({book['genre']}) - {book['description'][:100]}..."
                for book in user_books[-10:]  # Last 10 books
            ])
        else:
            user_history = "No reading history available"
        
        available_list = "\n".join([
            f"ID: {book['id']}, Title: {book['title']}, Author: {book['author']}, Genre: {book['genre']}, Description: {book.get('description', 'No description')[:100]}..."
            for book in available_books[:25]  # Limit to avoid token limits
        ])
        
        return f"""You are an expert librarian AI with deep knowledge of literature and reader preferences.

User's Reading History:
{user_history}

Available Books to Recommend:
{available_list}

Based on the user's reading history, please recommend {limit} books they would enjoy. Consider:
1. Genre preferences and patterns
2. Author styles they seem to enjoy
3. Themes and subjects they're drawn to
4. Reading level and complexity
5. Variety to help them discover new interests

Respond with ONLY a JSON array of recommendations in this exact format:
[
  {{
    "book_id": "book_id_here", 
    "reason": "Detailed explanation of why this book matches their preferences based on their reading history",
    "score": 0.9
  }}
]

Ensure book_id matches exactly from the available books. Provide thoughtful, personalized reasons that reference their reading history."""
    
    async def _call_openai(self, prompt: str) -> Optional[str]:
        """Call OpenAI API with error handling."""
        try:
            if not self.openai_client:
                return None
                
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful librarian AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None
    
    def _parse_search_recommendations(self, response: str, available_books: List[Dict]) -> List[Dict[str, Any]]:
        """Parse OpenAI response for search recommendations."""
        try:
            # Try to extract JSON from the response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:-3]
            elif response.startswith("```"):
                response = response[3:-3]
            
            recommendations_data = json.loads(response)
            
            # Create book lookup
            book_lookup = {book["id"]: book for book in available_books}
            
            recommendations = []
            for rec in recommendations_data[:5]:  # Limit to 5
                book_id = rec.get("book_id")
                if book_id in book_lookup:
                    recommendations.append({
                        "book": book_lookup[book_id],
                        "score": rec.get("score", 0.8),
                        "reason": rec.get("reason", "AI recommendation based on your search")
                    })
            
            return recommendations
            
        except Exception as e:
            print(f"Error parsing AI recommendations: {e}")
            return []
    
    def _parse_ai_recommendations(self, response: str, available_books: List[Dict]) -> List[Dict[str, Any]]:
        """Parse OpenAI response for AI recommendations."""
        try:
            # Try to extract JSON from the response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:-3]
            elif response.startswith("```"):
                response = response[3:-3]
            
            recommendations_data = json.loads(response)
            
            # Create book lookup
            book_lookup = {book["id"]: book for book in available_books}
            
            recommendations = []
            for rec in recommendations_data[:5]:  # Limit to 5
                book_id = rec.get("book_id")
                if book_id in book_lookup:
                    recommendations.append({
                        "book": book_lookup[book_id],
                        "score": rec.get("score", 0.8),
                        "reason": rec.get("reason", "AI recommendation based on your reading history")
                    })
            
            return recommendations
            
        except Exception as e:
            print(f"Error parsing AI recommendations: {e}")
            return []
    
    async def _fallback_search_recommendations(self, search_query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback recommendations when AI is not available."""
        try:
            # Simple text search across available books
            search_pattern = f"%{search_query}%"
            books = supabase_admin.table("books")\
                .select("*")\
                .eq("status", "available")\
                .or_(f"title.ilike.{search_pattern},author.ilike.{search_pattern},genre.ilike.{search_pattern},description.ilike.{search_pattern}")\
                .limit(limit)\
                .execute()
            
            recommendations = []
            for book in books.data or []:
                recommendations.append({
                    "book": book,
                    "score": 0.7,
                    "reason": f"Found based on your search for '{search_query}'"
                })
            
            # Fill with personalized recommendations if not enough found
            if len(recommendations) < limit:
                personal_recs = await self.get_personalized_recommendations(user_id, limit - len(recommendations))
                recommendations.extend(personal_recs)
            
            return recommendations[:limit]
            
        except Exception as e:
            print(f"Error in fallback search recommendations: {e}")
            return []

# Global instance
ai_service = AILibraryService()
