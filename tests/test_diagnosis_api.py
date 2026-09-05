"""
Tests for diagnosis API endpoint.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import initialize_database
from backend.fixtures.data import load_fixtures


# Mock LLM response (structured diagnosis dict, not JSON string)
MOCK_DIAGNOSIS = {
    "summary": "UPI payment succeeded after retry",
    "what_happened": "Payment failed initially, then succeeded on retry",
    "what_is_known": [
        "Order amount was 50000 INR",
        "First attempt failed",
        "Second attempt succeeded"
    ],
    "what_cannot_be_determined": [
        "Specific reason for initial failure"
    ],
    "recommended_action": "Review authentication patterns",
    "raw_explanation": json.dumps({
        "summary": "UPI payment succeeded after retry",
        "what_happened": "Payment failed initially, then succeeded on retry",
        "what_is_known": ["Order amount was 50000 INR", "First attempt failed", "Second attempt succeeded"],
        "what_cannot_be_determined": ["Specific reason for initial failure"],
        "recommended_action": "Review authentication patterns"
    })
}


@pytest.fixture
async def client():
    """Create test client."""
    await initialize_database()
    await load_fixtures()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint_shows_llm_status(client):
    """Test health endpoint includes LLM configuration status."""
    response = await client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "llm_configured" in data
    assert isinstance(data["llm_configured"], bool)
    assert data["phase"] == "2 - LLM Diagnostic Integration"


@pytest.mark.asyncio
async def test_root_endpoint_includes_diagnosis(client):
    """Test root endpoint lists diagnosis endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "endpoints" in data
    assert "diagnosis" in data["endpoints"]


@pytest.mark.asyncio
async def test_diagnosis_endpoint_with_mock_llm(client):
    """Test diagnosis endpoint with mocked LLM."""
    # Mock LLM service
    with patch('backend.main.generate_diagnosis') as mock_gen:
        mock_gen.return_value = MOCK_DIAGNOSIS
        
        # Mock environment variable
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            response = await client.get("/journeys/order_scenario_a/diagnosis")
            assert response.status_code == 200
            
            data = response.json()
            
            # Verify structure
            assert "order_id" in data
            assert "journey" in data
            assert "diagnosis" in data
            assert "llm_model" in data
            assert "evidence_based" in data
            
            # Verify order_id matches
            assert data["order_id"] == "order_scenario_a"
            
            # Verify evidence_based is always True
            assert data["evidence_based"] is True
            
            # Verify journey is included (Phase 1 data)
            assert "order" in data["journey"]
            assert "events" in data["journey"]
            assert "attempts" in data["journey"]
            assert "evidence" in data["journey"]
            
            # Verify diagnosis structure
            diagnosis = data["diagnosis"]
            assert "summary" in diagnosis
            assert "what_happened" in diagnosis
            assert "what_is_known" in diagnosis
            assert "what_cannot_be_determined" in diagnosis
            assert "recommended_action" in diagnosis


@pytest.mark.asyncio
async def test_diagnosis_endpoint_missing_api_key(client):
    """Test diagnosis endpoint fails gracefully without API key."""
    # Clear API key
    with patch.dict('os.environ', {}, clear=True):
        response = await client.get("/journeys/order_scenario_a/diagnosis")
        assert response.status_code == 503
        
        data = response.json()
        assert "detail" in data
        assert "not configured" in data["detail"].lower()


@pytest.mark.asyncio
async def test_diagnosis_endpoint_missing_order(client):
    """Test diagnosis endpoint returns 404 for missing order."""
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
        response = await client.get("/journeys/invalid_order_123/diagnosis")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_diagnosis_uses_existing_phase1_reconstruction(client):
    """Test that diagnosis endpoint uses existing Phase 1 reconstruction."""
    # Mock generate_diagnosis to verify it receives correct journey
    with patch('backend.main.generate_diagnosis') as mock_gen:
        mock_gen.return_value = MOCK_DIAGNOSIS
        
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            response = await client.get("/journeys/order_scenario_a/diagnosis")
            assert response.status_code == 200
            
            # Verify generate_diagnosis was called
            assert mock_gen.called
            
            # Get the journey that was passed
            call_args = mock_gen.call_args
            journey = call_args[0][0]
            
            # Verify it's a proper PaymentJourney with evidence
            assert journey.order_id == "order_scenario_a"
            assert len(journey.evidence) > 0
            assert journey.attempt_count == 2
            assert journey.retry_count == 1


@pytest.mark.asyncio
async def test_diagnosis_response_includes_both_journey_and_explanation(client):
    """Test that response includes both deterministic journey and LLM explanation."""
    with patch('backend.main.generate_diagnosis') as mock_gen:
        mock_gen.return_value = MOCK_DIAGNOSIS
        
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            response = await client.get("/journeys/order_scenario_a/diagnosis")
            assert response.status_code == 200
            
            data = response.json()
            
            # Verify journey (Phase 1 deterministic data) is included
            journey = data["journey"]
            assert journey["attempt_count"] == 2
            assert journey["retry_count"] == 1
            assert len(journey["evidence"]) > 0
            
            # Verify diagnosis (Phase 2 LLM explanation) is included
            diagnosis = data["diagnosis"]
            assert len(diagnosis["summary"]) > 0
            assert len(diagnosis["what_is_known"]) > 0


@pytest.mark.asyncio
async def test_existing_phase1_tests_still_work(client):
    """Test that existing Phase 1 /journeys endpoint still works."""
    # This ensures Phase 2 didn't break Phase 1
    response = await client.get("/journeys/order_scenario_a")
    assert response.status_code == 200
    
    data = response.json()
    
    # Phase 1 structure should be unchanged
    assert "order_id" in data
    assert "order" in data
    assert "events" in data
    assert "attempts" in data
    assert "evidence" in data
    assert data["attempt_count"] == 2
    assert data["retry_count"] == 1
