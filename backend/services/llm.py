"""
LLM service for generating evidence-grounded diagnostic explanations.

This service converts pre-classified evidence into natural language.
The LLM does NOT perform payment reasoning or determine truth.
All facts are established by the deterministic reconstruction engine.
"""

import os
import json
from typing import List, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from ..models import PaymentJourney, Evidence


# System prompt with strict constraints
SYSTEM_PROMPT = """You are a payment diagnostic system that explains payment journeys based on pre-classified evidence.

CRITICAL CONSTRAINTS:
1. Use ONLY the evidence provided in the user message
2. Do NOT invent facts, causes, or explanations not present in the evidence
3. Do NOT infer network problems unless explicitly stated in evidence
4. Do NOT infer bank problems unless explicitly stated in evidence
5. Do NOT infer customer intent or actions beyond what evidence shows
6. Do NOT claim a payment failed if later evidence shows success
7. Do NOT claim a payment succeeded unless PROVEN evidence supports it
8. Treat UNKNOWN items as genuinely unknown - do not speculate
9. Never convert DERIVED facts into PROVEN facts
10. Never convert INCONSISTENCY into a root cause without evidence
11. If the root cause cannot be determined from evidence, explicitly state this
12. Explain the timeline in chronological order
13. Keep explanations concise and useful for developers/payment operations

EVIDENCE CATEGORIES:
- PROVEN: Facts directly from database records (timestamps, statuses, error codes)
- DERIVED: Facts calculated from available data (counts, durations, gaps)
- INCONSISTENCY: Detected conflicts between data points
- UNKNOWN: Gaps in available data where information is missing

Return your analysis as a structured JSON object with these exact fields:
- summary: Brief overview of what happened
- what_happened: Chronological explanation of the payment journey
- what_is_known: Array of confirmed facts from evidence
- what_cannot_be_determined: Array of unknowns or uncertainties
- recommended_action: Suggested next steps for investigation (if applicable)

Be factual, precise, and acknowledge limitations of the available data."""


# Pydantic model for structured JSON response from Gemini
class DiagnosisSchema(BaseModel):
    """Schema for LLM-generated diagnostic explanation."""
    summary: str
    what_happened: str
    what_is_known: List[str]
    what_cannot_be_determined: List[str]
    recommended_action: str


def _build_evidence_payload(journey: PaymentJourney) -> str:
    """
    Build structured evidence payload for LLM.
    
    Organizes evidence by category for clear presentation.
    """
    # Organize evidence by category
    proven = [e for e in journey.evidence if e.category == "PROVEN"]
    derived = [e for e in journey.evidence if e.category == "DERIVED"]
    inconsistencies = [e for e in journey.evidence if e.category == "INCONSISTENCY"]
    unknown = [e for e in journey.evidence if e.category == "UNKNOWN"]
    
    # Build structured payload
    payload = f"""Payment Journey Evidence for Order: {journey.order_id}

CONTEXT:
- Amount: {journey.order.amount} {journey.order.currency}
- Payment Method: {journey.attempts[0].method if journey.attempts else 'Unknown'}
- Total Attempts: {journey.attempt_count}
- Journey Duration: {journey.journey_duration_seconds:.1f} seconds
- Final Status: {journey.final_status}

PROVEN FACTS (from database records):
"""
    
    for i, evidence in enumerate(proven, 1):
        payload += f"{i}. {evidence.statement}\n   Source: {evidence.source}\n"
    
    payload += "\nDERIVED FACTS (calculated from data):\n"
    for i, evidence in enumerate(derived, 1):
        payload += f"{i}. {evidence.statement}\n   Source: {evidence.source}\n"
    
    if inconsistencies:
        payload += "\nINCONSISTENCIES (detected conflicts):\n"
        for i, evidence in enumerate(inconsistencies, 1):
            payload += f"{i}. {evidence.statement}\n   Source: {evidence.source}\n"
    
    if unknown:
        payload += "\nUNKNOWN (gaps in data):\n"
        for i, evidence in enumerate(unknown, 1):
            payload += f"{i}. {evidence.statement}\n   Source: {evidence.source}\n"
    
    payload += "\nGenerate a diagnostic explanation based ONLY on the above evidence."
    
    return payload


async def generate_diagnosis(
    journey: PaymentJourney,
    api_key: Optional[str] = None
) -> dict:
    """
    Generate diagnostic explanation from structured evidence.
    
    Args:
        journey: Complete payment journey with pre-classified evidence
        api_key: Gemini API key (optional, defaults to environment variable)
        
    Returns:
        Dictionary containing:
        - summary: Brief overview
        - what_happened: Chronological explanation
        - what_is_known: List of confirmed facts
        - what_cannot_be_determined: List of unknowns
        - recommended_action: Suggested next steps
        
    Raises:
        ValueError: If API key is not available
        Exception: If LLM call fails
    """
    # Get API key from parameter or environment
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "Gemini API key not configured. Set GEMINI_API_KEY environment variable "
            "or pass api_key parameter."
        )
    
    # Initialize Gemini client
    client = genai.Client(api_key=api_key)
    
    # Build evidence payload
    evidence_payload = _build_evidence_payload(journey)
    
    try:
        # Call LLM with strict system prompt and structured JSON output
        # Combine system prompt and user message for Gemini
        full_prompt = f"{SYSTEM_PROMPT}\n\n{evidence_payload}"
        
        response = await client.aio.models.generate_content(
            model="gemini-3.7-flash",  # Cost-effective workhorse model for MVP
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,  # Low temperature for consistency
                max_output_tokens=2000,  # Increased for complete JSON response
                response_mime_type="application/json",
                response_schema=DiagnosisSchema
            )
        )
        
        # Extract raw response for transparency
        raw_response = response.text
        
        # Parse and validate JSON response
        try:
            # Gemini returns JSON as a string, parse it
            parsed_json = json.loads(raw_response)
            
            # Validate against schema
            validated_diagnosis = DiagnosisSchema(**parsed_json)
            
            # Convert to dict and add raw response
            diagnosis = validated_diagnosis.model_dump()
            diagnosis["raw_explanation"] = raw_response  # Include full response for transparency
            
            return diagnosis
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response from Gemini: {str(e)}. Raw response: {raw_response[:200]}")
        except ValidationError as e:
            raise Exception(f"Gemini response validation failed: {str(e)}. Raw response: {raw_response[:200]}")
        
    except Exception as e:
        # Re-raise with context if it's already our exception
        if "Failed to parse JSON" in str(e) or "validation failed" in str(e):
            raise
        # Otherwise wrap it
        raise Exception(f"Failed to generate diagnosis: {str(e)}")


# Note: Removed _extract_section and _extract_list functions
# Now using structured JSON output from Gemini instead of string parsing
