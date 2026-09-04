"""
Tests for API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import initialize_database
from backend.fixtures.data import load_fixtures


@pytest.fixture
async def client():
    """Create test client."""
    await initialize_database()
    await load_fixtures()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "PaymentTrace"
    assert "phase" in data


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_journey_endpoint_valid_order(client):
    """Test journey endpoint with valid order ID."""
    response = await client.get("/journeys/order_scenario_a")
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify structure
    assert "order_id" in data
    assert "order" in data
    assert "events" in data
    assert "attempts" in data
    assert "evidence" in data
    
    # Verify order details
    assert data["order_id"] == "order_scenario_a"
    assert data["order"]["order_id"] == "order_scenario_a"
    
    # Verify derived facts
    assert "attempt_count" in data
    assert "retry_count" in data
    assert "journey_duration_seconds" in data
    assert "final_status" in data
    
    # Verify data correctness
    assert data["attempt_count"] == 2
    assert data["retry_count"] == 1
    assert data["final_status"] == "captured"


@pytest.mark.asyncio
async def test_journey_endpoint_scenario_b(client):
    """Test journey endpoint with scenario B."""
    response = await client.get("/journeys/order_scenario_b")
    assert response.status_code == 200
    
    data = response.json()
    assert data["order_id"] == "order_scenario_b"
    assert data["attempt_count"] == 1
    assert data["retry_count"] == 0


@pytest.mark.asyncio
async def test_journey_endpoint_invalid_order(client):
    """Test journey endpoint with non-existent order."""
    response = await client.get("/journeys/invalid_order_id")
    assert response.status_code == 404
    
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_journey_events_ordered_chronologically(client):
    """Test that events in API response are chronologically ordered."""
    response = await client.get("/journeys/order_scenario_a")
    assert response.status_code == 200
    
    data = response.json()
    events = data["events"]
    
    # Extract timestamps
    timestamps = [event["timestamp"] for event in events]
    
    # Verify they are in ascending order
    assert timestamps == sorted(timestamps), "Events should be chronologically ordered"


@pytest.mark.asyncio
async def test_journey_no_hardcoded_explanations(client):
    """
    Verify that the API does NOT return hardcoded natural language explanations.
    It should only return structured data and evidence.
    """
    response = await client.get("/journeys/order_scenario_a")
    assert response.status_code == 200
    
    data = response.json()
    
    # Should NOT have fields like "explanation", "summary", "diagnosis", "root_cause"
    assert "explanation" not in data
    assert "summary" not in data
    assert "diagnosis" not in data
    assert "root_cause" not in data
    
    # SHOULD have structured evidence
    assert "evidence" in data
    assert isinstance(data["evidence"], list)
    assert len(data["evidence"]) > 0


@pytest.mark.asyncio
async def test_evidence_structure(client):
    """Test that evidence items have required structure."""
    response = await client.get("/journeys/order_scenario_a")
    assert response.status_code == 200
    
    data = response.json()
    evidence = data["evidence"]
    
    # Each evidence item should have category and statement
    for item in evidence:
        assert "category" in item
        assert "statement" in item
        assert item["category"] in ["PROVEN", "DERIVED", "INCONSISTENCY", "UNKNOWN"]
        assert isinstance(item["statement"], str)
        assert len(item["statement"]) > 0
