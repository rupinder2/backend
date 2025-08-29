#!/usr/bin/env python3
"""
Simple test script for the authentication API
This script tests the basic functionality of the API endpoints
"""

import requests
import json
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test@example.com"  # Replace with a real email for testing

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print("✅ Health check passed")
                print(f"   Status: {data.get('status')}")
                print(f"   Supabase configured: {data.get('supabase_configured')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_root_endpoint(self) -> bool:
        """Test the root endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                print("✅ Root endpoint working")
                print(f"   Message: {data.get('message')}")
                return True
            else:
                print(f"❌ Root endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Root endpoint error: {e}")
            return False
    
    def test_auth_endpoints_without_token(self) -> bool:
        """Test auth endpoints without token (should fail)"""
        endpoints = [
            "/api/auth/me",
            "/api/auth/profile",
            "/api/auth/validate-token"
        ]
        
        all_passed = True
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 401:
                    print(f"✅ {endpoint} correctly requires authentication")
                else:
                    print(f"❌ {endpoint} should require authentication but returned {response.status_code}")
                    all_passed = False
            except Exception as e:
                print(f"❌ Error testing {endpoint}: {e}")
                all_passed = False
        
        return all_passed
    
    def test_with_mock_token(self) -> bool:
        """Test endpoints with an invalid token (should fail gracefully)"""
        fake_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.token"
        headers = {"Authorization": fake_token}
        
        endpoints = [
            "/api/auth/me",
            "/api/auth/profile", 
            "/api/auth/validate-token"
        ]
        
        all_passed = True
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", headers=headers)
                if response.status_code == 401:
                    print(f"✅ {endpoint} correctly rejects invalid token")
                else:
                    print(f"❌ {endpoint} should reject invalid token but returned {response.status_code}")
                    all_passed = False
            except Exception as e:
                print(f"❌ Error testing {endpoint} with fake token: {e}")
                all_passed = False
        
        return all_passed
    
    def test_cors_headers(self) -> bool:
        """Test CORS configuration"""
        try:
            # Make an OPTIONS request to check CORS
            response = self.session.options(f"{self.base_url}/api/auth/me")
            headers = response.headers
            
            if "Access-Control-Allow-Origin" in headers:
                print("✅ CORS headers present")
                print(f"   Allow-Origin: {headers.get('Access-Control-Allow-Origin')}")
                return True
            else:
                print("❌ CORS headers missing")
                return False
        except Exception as e:
            print(f"❌ CORS test error: {e}")
            return False
    
    def run_all_tests(self) -> None:
        """Run all tests"""
        print("🚀 Starting API Tests")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Root Endpoint", self.test_root_endpoint),
            ("Auth Without Token", self.test_auth_endpoints_without_token),
            ("Invalid Token Handling", self.test_with_mock_token),
            ("CORS Configuration", self.test_cors_headers)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 Testing: {test_name}")
            if test_func():
                passed += 1
            print("-" * 30)
        
        print(f"\n📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! API is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the configuration and try again.")
        
        print("\n📝 Next Steps:")
        print("1. Ensure your .env file is properly configured")
        print("2. Test the frontend integration at http://localhost:3000")
        print("3. Try the complete OTP flow with a real email address")
        print("4. Check API documentation at http://localhost:8000/docs")

def main():
    """Main function"""
    print("Email OTP Authentication API Tester")
    print("=" * 40)
    
    tester = APITester(API_BASE_URL)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        print(f"✅ API server is running at {API_BASE_URL}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API server at {API_BASE_URL}")
        print("   Make sure the server is running with: python main.py")
        return
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        return
    
    tester.run_all_tests()

if __name__ == "__main__":
    main()
