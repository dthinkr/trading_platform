"""
Pytest-based endpoint health tests for the trading platform.
Tests endpoints after RabbitMQ removal to ensure the refactored system works correctly.
"""

import pytest
import pytest_asyncio
import asyncio
import aiohttp
from typing import Dict, Any


class TestEndpointHealth:
    """Test class for endpoint health checking"""
    
    @pytest.fixture
    def base_url(self):
        """Base URL for testing"""
        return "http://localhost:8000"
    
    @pytest_asyncio.fixture
    async def http_session(self):
        """HTTP session for making requests"""
        session = aiohttp.ClientSession()
        yield session
        await session.close()
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, base_url, http_session):
        """Test the root endpoint returns 200"""
        async with http_session.get(f"{base_url}/") as response:
            assert response.status == 200
            data = await response.json()
            assert "message" in data or "status" in data
    
    @pytest.mark.asyncio
    async def test_trader_defaults_endpoint(self, base_url, http_session):
        """Test the trader defaults endpoint returns 200"""
        async with http_session.get(f"{base_url}/traders/defaults") as response:
            assert response.status == 200
            data = await response.json()
            assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_trader_info_endpoint_unauthorized(self, base_url, http_session):
        """Test trader_info endpoint returns 401 when unauthorized (not 500)"""
        trader_id = "HUMAN_testuser"
        async with http_session.get(f"{base_url}/trader_info/{trader_id}") as response:
            # Should return 401 (unauthorized) not 500 (internal server error)
            assert response.status in [401, 403, 404], f"Expected 401/403/404, got {response.status}"
            assert response.status != 500, "Should not return 500 Internal Server Error"
    
    @pytest.mark.asyncio
    async def test_trader_info_endpoint_specific_user(self, base_url, http_session):
        """Test trader_info endpoint for specific user that was causing 500 errors"""
        trader_id = "HUMAN_venvoooo"
        async with http_session.get(f"{base_url}/trader_info/{trader_id}") as response:
            # Should return 401 (unauthorized) not 500 (internal server error)
            assert response.status in [401, 403, 404], f"Expected 401/403/404, got {response.status}"
            assert response.status != 500, "Should not return 500 Internal Server Error"
    
    @pytest.mark.asyncio
    async def test_all_endpoints_no_500_errors(self, base_url, http_session):
        """Comprehensive test to ensure no endpoints return 500 errors"""
        endpoints_to_test = [
            "/",
            "/traders/defaults",
            "/trader_info/HUMAN_testuser",
            "/trader_info/HUMAN_venvoooo"
        ]
        
        results = {}
        for endpoint in endpoints_to_test:
            try:
                async with http_session.get(f"{base_url}{endpoint}") as response:
                    results[endpoint] = response.status
                    # Most important: no 500 errors
                    assert response.status != 500, f"Endpoint {endpoint} returned 500 Internal Server Error"
            except Exception as e:
                pytest.fail(f"Endpoint {endpoint} raised exception: {e}")
        
        # Print results for debugging
        print("\nEndpoint test results:")
        for endpoint, status in results.items():
            print(f"  {endpoint}: {status}")
    
    @pytest.mark.asyncio
    async def test_server_responsiveness(self, base_url, http_session):
        """Test that server responds to requests in reasonable time"""
        import time
        
        start_time = time.time()
        async with http_session.get(f"{base_url}/") as response:
            response_time = time.time() - start_time
            
        assert response.status == 200
        assert response_time < 5.0, f"Server took too long to respond: {response_time:.2f}s"


@pytest.mark.integration
class TestEndpointIntegration:
    """Integration tests for endpoint functionality"""
    
    @pytest.mark.asyncio
    async def test_endpoint_error_handling(self):
        """Test that endpoints handle errors gracefully after RabbitMQ removal"""
        # This test ensures that removing RabbitMQ didn't break error handling
        async with aiohttp.ClientSession() as session:
            # Test with invalid endpoint
            async with session.get("http://localhost:8000/nonexistent") as response:
                assert response.status == 404
                
            # Test with malformed trader ID
            async with session.get("http://localhost:8000/trader_info/invalid-id") as response:
                assert response.status in [400, 401, 403, 404]
                assert response.status != 500


# Utility functions for manual testing
async def run_quick_health_check():
    """Manual health check function (can be called outside pytest)"""
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        endpoints = [
            ("/", "Root endpoint"),
            ("/traders/defaults", "Trader defaults"),
            ("/trader_info/HUMAN_testuser", "Trader info (test user)"),
            ("/trader_info/HUMAN_venvoooo", "Trader info (specific user)")
        ]
        
        print("🚀 Running health check...")
        all_passed = True
        
        for endpoint, description in endpoints:
            try:
                async with session.get(f"{base_url}{endpoint}") as response:
                    status = response.status
                    success = status != 500
                    emoji = "✅" if success else "❌"
                    print(f"  {emoji} {description}: {status}")
                    
                    if not success:
                        all_passed = False
                        
            except Exception as e:
                print(f"  ❌ {description}: ERROR - {e}")
                all_passed = False
        
        print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed'}")
        return all_passed


if __name__ == "__main__":
    # Allow running as standalone script for quick testing
    print("For pytest: run 'pytest back/tests/test_endpoints_health.py -v'")
    print("For quick check:")
    asyncio.run(run_quick_health_check()) 