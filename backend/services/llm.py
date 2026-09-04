"""
LLM service for generating evidence-grounded diagnostic explanations.

This service converts pre-classified evidence into natural language.
The LLM does NOT perform payment reasoning or determine truth.
All facts are established by the deterministic reconstruction engine.
"""

import os
from typing import List, Optional
from openai import AsyncOpenAI
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

Your task: Generate a structured diagnostic explanation containing:
1. Summary: Brief overview of what happened
2. What Happened: Chronological explanation of the payment journey
3. What Is Known: List of confirmed facts from evidence
4. What Cannot Be Determined: List of unknowns or uncertainties
5. Recommended Action: Suggested next steps for investigation (if applicable)

Be factual, precise, and acknowledge limitations of the available data."""


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
        api_key: OpenAI API key (optional, defaults to environment variable)
        
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
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "OpenAI API key not configured. Set OPENAI_API_KEY environment variable "
            "or pass api_key parameter."
        )
    
    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=api_key)
    
    # Build evidence payload
    evidence_payload = _build_evidence_payload(journey)
    
    try:
        # Call LLM with strict system prompt
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective for MVP
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": evidence_payload}
            ],
            temperature=0.3,  # Low temperature for consistency
            max_tokens=1000
        )
        
        # Extract response
        explanation = response.choices[0].message.content
        
        # Parse structured response
        # In production, use structured output or JSON mode
        # For MVP, return as sections
        diagnosis = {
            "summary": _extract_section(explanation, "Summary", "What Happened"),
            "what_happened": _extract_section(explanation, "What Happened", "What Is Known"),
            "what_is_known": _extract_list(explanation, "What Is Known", "What Cannot Be Determined"),
            "what_cannot_be_determined": _extract_list(explanation, "What Cannot Be Determined", "Recommended Action"),
            "recommended_action": _extract_section(explanation, "Recommended Action", None),
            "raw_explanation": explanation  # Include full response for transparency
        }
        
        return diagnosis
        
    except Exception as e:
        raise Exception(f"Failed to generate diagnosis: {str(e)}")


def _extract_section(text: str, start_marker: str, end_marker: Optional[str]) -> str:
    """Extract section between markers."""
    try:
        start_idx = text.find(start_marker)
        if start_idx == -1:
            return ""
        
        start_idx = text.find(":", start_idx) + 1
        
        if end_marker:
            end_idx = text.find(end_marker, start_idx)
            if end_idx == -1:
                content = text[start_idx:]
            else:
                content = text[start_idx:end_idx]
        else:
            content = text[start_idx:]
        
        return content.strip()
    except:
        return ""


def _extract_list(text: str, start_marker: str, end_marker: Optional[str]) -> List[str]:
    """Extract bulleted list between markers."""
    try:
        section = _extract_section(text, start_marker, end_marker)
        
        # Split by lines and extract list items
        lines = section.split('\n')
        items = []
        for line in lines:
            line = line.strip()
            # Remove bullet points/numbers
            if line and (line.startswith('-') or line.startswith('•') or 
                        (len(line) > 2 and line[0].isdigit() and line[1] == '.')):
                item = line.lstrip('-•0123456789. ').strip()
                if item:
                    items.append(item)
        
        return items
    except:
        return []
