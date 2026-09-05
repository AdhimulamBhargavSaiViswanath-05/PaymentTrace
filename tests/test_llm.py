"""
Tests for LLM diagnostic service.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock
from backend.services.llm import generate_diagnosis, _build_evidence_payload
from backend.services.reconstruction import reconstruct_journey
from backend.database import initialize_database
from backend.fixtures.data import load_fixtures


# Mock LLM JSON response (structured output from Gemini)
MOCK_LLM_JSON_RESPONSE = {
    "summary": "UPI payment succeeded after initial authentication failure and retry.",
    "what_happened": "The payment journey began with a UPI payment initiation at 10:00:05Z. The first attempt failed at 10:00:12Z with a BAD_REQUEST_ERROR indicating authentication failure. After a 45-second gap, the customer retried the payment at 10:00:50Z. The second attempt was successful, with authorization at 10:00:58Z and capture at 10:00:59Z. The complete journey took 54 seconds.",
    "what_is_known": [
        "Order was created for 50000 INR (₹500.00)",
        "First payment attempt failed due to authentication error",
        "Customer retried after 45 seconds",
        "Second attempt succeeded and payment was captured",
        "Total journey duration was 54 seconds",
        "Final payment status is captured"
    ],
    "what_cannot_be_determined": [
        "Specific reason for authentication failure (e.g., incorrect PIN vs system issue)",
        "Whether the customer intentionally waited 45 seconds or encountered delays",
        "Why there is a terminology mismatch between 'paid' and 'captured' status"
    ],
    "recommended_action": "Review authentication failure patterns to identify if this is a user error or system issue. Consider clarifying status terminology between merchant system and payment gateway."
}


@pytest.fixture
async def setup_with_fixtures():
    """Setup database with fixtures."""
    await initialize_database()
    await load_fixtures()
    yield


@pytest.mark.asyncio
async def test_generate_diagnosis_with_mock_llm(setup_with_fixtures):
    """Test successful diagnosis generation with mocked LLM."""
    # Get real journey
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    # Mock Gemini JSON response
    with patch('backend.services.llm.genai.Client') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock generate_content response with JSON
        mock_response = AsyncMock()
        mock_response.text = json.dumps(MOCK_LLM_JSON_RESPONSE)
        mock_client.aio.models.generate_content.return_value = mock_response
        
        # Generate diagnosis
        diagnosis = await generate_diagnosis(journey, api_key="test_key")
        
        # Verify structure
        assert "summary" in diagnosis
        assert "what_happened" in diagnosis
        assert "what_is_known" in diagnosis
        assert "what_cannot_be_determined" in diagnosis
        assert "recommended_action" in diagnosis
        assert "raw_explanation" in diagnosis
        
        # Verify content is extracted correctly
        assert len(diagnosis["summary"]) > 0
        assert len(diagnosis["what_happened"]) > 0
        assert isinstance(diagnosis["what_is_known"], list)
        assert len(diagnosis["what_is_known"]) > 0
        assert isinstance(diagnosis["what_cannot_be_determined"], list)
        assert len(diagnosis["what_cannot_be_determined"]) > 0
        
        # Verify raw explanation contains the JSON
        assert "summary" in diagnosis["raw_explanation"]


@pytest.mark.asyncio
async def test_generate_diagnosis_missing_api_key(setup_with_fixtures):
    """Test that missing API key raises appropriate error."""
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    # Clear environment variable
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="Gemini API key not configured"):
            await generate_diagnosis(journey)


@pytest.mark.asyncio
async def test_evidence_payload_structure(setup_with_fixtures):
    """Test that evidence payload is properly structured."""
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    payload = _build_evidence_payload(journey)
    
    # Verify structure
    assert "Payment Journey Evidence" in payload
    assert journey.order_id in payload
    assert "PROVEN FACTS" in payload
    assert "DERIVED FACTS" in payload
    assert "CONTEXT" in payload
    
    # Verify context includes key facts
    assert str(journey.order.amount) in payload
    assert journey.order.currency in payload
    assert str(journey.attempt_count) in payload
    assert str(journey.journey_duration_seconds) in payload


@pytest.mark.asyncio
async def test_evidence_payload_includes_all_categories(setup_with_fixtures):
    """Test that all evidence categories are included in payload."""
    # Use scenario B which has inconsistencies
    journey = await reconstruct_journey("order_scenario_b")
    assert journey is not None
    
    payload = _build_evidence_payload(journey)
    
    # Verify all categories present
    assert "PROVEN FACTS" in payload
    assert "DERIVED FACTS" in payload
    assert "INCONSISTENCIES" in payload
    
    # Verify inconsistency is mentioned
    has_inconsistency = any(e.category == "INCONSISTENCY" for e in journey.evidence)
    if has_inconsistency:
        assert "INCONSISTENCIES" in payload


@pytest.mark.asyncio
async def test_llm_receives_only_structured_evidence(setup_with_fixtures):
    """Test that LLM receives only pre-classified evidence, not raw data."""
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    with patch('backend.services.llm.genai.Client') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        mock_response = AsyncMock()
        mock_response.text = json.dumps(MOCK_LLM_JSON_RESPONSE)
        mock_client.aio.models.generate_content.return_value = mock_response
        
        await generate_diagnosis(journey, api_key="test_key")
        
        # Verify LLM was called
        assert mock_client.aio.models.generate_content.called
        
        # Get the actual call arguments
        call_args = mock_client.aio.models.generate_content.call_args
        
        # Verify the prompt contains both system prompt and structured evidence
        full_prompt = call_args[1]["contents"]
        
        # Verify system prompt constraints are included
        assert "CRITICAL CONSTRAINTS" in full_prompt
        assert "Use ONLY the evidence provided" in full_prompt
        assert "Do NOT invent facts" in full_prompt
        
        # Verify structured evidence is included
        assert "PROVEN FACTS" in full_prompt
        assert "DERIVED FACTS" in full_prompt
        
        # Verify JSON response configuration
        config = call_args[1]["config"]
        assert config.response_mime_type == "application/json"
        assert config.response_schema is not None


@pytest.mark.asyncio
async def test_diagnosis_preserves_unknowns(setup_with_fixtures):
    """Test that UNKNOWN evidence is preserved in diagnosis."""
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    # Mock JSON response that includes unknowns
    mock_json_with_unknown = {
        "summary": "Test summary",
        "what_happened": "Test",
        "what_is_known": [
            "Fact 1",
            "Fact 2"
        ],
        "what_cannot_be_determined": [
            "The specific reason for authentication failure",
            "Customer's intent during retry"
        ],
        "recommended_action": "Test"
    }
    
    with patch('backend.services.llm.genai.Client') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        mock_response = AsyncMock()
        mock_response.text = json.dumps(mock_json_with_unknown)
        mock_client.aio.models.generate_content.return_value = mock_response
        
        diagnosis = await generate_diagnosis(journey, api_key="test_key")
        
        # Verify unknowns are extracted
        assert len(diagnosis["what_cannot_be_determined"]) > 0
        
        # Verify they contain appropriate content
        unknowns_text = " ".join(diagnosis["what_cannot_be_determined"])
        assert any(word in unknowns_text.lower() for word in ["cannot", "specific reason", "intent"])


@pytest.mark.asyncio
async def test_malformed_json_handling(setup_with_fixtures):
    """Test that malformed JSON from Gemini is handled gracefully."""
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    with patch('backend.services.llm.genai.Client') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock malformed JSON response
        mock_response = AsyncMock()
        mock_response.text = "{ invalid json without closing brace"
        mock_client.aio.models.generate_content.return_value = mock_response
        
        # Should raise exception with clear error message
        with pytest.raises(Exception, match="Failed to parse JSON response"):
            await generate_diagnosis(journey, api_key="test_key")


@pytest.mark.asyncio
async def test_invalid_json_structure_handling(setup_with_fixtures):
    """Test that JSON with missing required fields is handled gracefully."""
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    with patch('backend.services.llm.genai.Client') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock JSON response missing required fields
        mock_response = AsyncMock()
        incomplete_json = {"summary": "Test only"}
        mock_response.text = json.dumps(incomplete_json)
        mock_client.aio.models.generate_content.return_value = mock_response
        
        # Should raise validation exception
        with pytest.raises(Exception, match="validation failed"):
            await generate_diagnosis(journey, api_key="test_key")
