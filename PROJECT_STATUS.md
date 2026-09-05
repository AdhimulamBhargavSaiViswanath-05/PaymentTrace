# PaymentTrace - Project Status

## Current Phase: Phase 2 - LLM Diagnostic Integration ✅

**Status:** COMPLETE

**Current Branch:** `feature/phase2-llm-integration`  
**Current Commit:** `418e790`  
**Tests Passing:** 34/34

## Phase Breakdown

### ✅ Phase 0: Project Setup (Complete)
- [x] Repository structure created
- [x] Backend framework initialized (FastAPI)
- [x] Health check endpoint implemented
- [x] Development environment documentation
- [x] Minimal frontend placeholder
- [x] Virtual environment tested
- [x] Backend startup verified

### ✅ Phase 1: Data Model & Deterministic Reconstruction (Complete)
- [x] SQLite database schema (orders, payment_attempts, payment_events)
- [x] Database initialization mechanism
- [x] Fixture data with controlled scenarios
- [x] Deterministic event ordering (timestamp-based)
- [x] Journey reconstruction service
- [x] Derived fact calculations (attempt count, duration, retry gaps)
- [x] Evidence classification system (PROVEN/DERIVED/INCONSISTENCY/UNKNOWN)
- [x] API endpoint: GET /journeys/{order_id}
- [x] Comprehensive test suite (18 tests passing)
- [x] Backend verified with actual API responses

### ✅ Phase 2: LLM Diagnostic Integration (Complete)
- [x] Google Gemini SDK integration (google-genai==2.22.0)
- [x] Environment variable configuration (GEMINI_API_KEY via python-dotenv)
- [x] Structured evidence payload builder
- [x] System prompt with 13 strict anti-hallucination constraints
- [x] Structured JSON output from Gemini with Pydantic validation
- [x] DiagnosisSchema for response validation
- [x] API endpoint: GET /journeys/{order_id}/diagnosis
- [x] Graceful error handling (missing API key, missing order, malformed JSON)
- [x] Response model combining journey + diagnosis
- [x] LLM service tests (8 tests, mocked)
- [x] Diagnosis API tests (8 tests, mocked)
- [x] Phase 1 backward compatibility verified
- [x] Total test suite: 34 tests passing

### ⏳ Phase 3: Frontend Interface (NOT STARTED - NEXT)
- [ ] Order ID search interface
- [ ] Journey timeline visualization
- [ ] Evidence categorization display
- [ ] Diagnosis explanation rendering
- [ ] Error state handling (404, 503)

### ⏳ Phase 4: Advanced Journey Analysis (NOT STARTED)
- [ ] Complex state machine analysis
- [ ] Timeline gap detection
- [ ] Additional inconsistency patterns

### ⏳ Phase 5: Production Readiness (NOT STARTED)
- [ ] Production database configuration
- [ ] API authentication
- [ ] Rate limiting
- [ ] Monitoring and logging
- [ ] Deployment configuration

## Phase 2 Implementation Summary

### Architecture

Phase 2 maintains strict architectural boundaries:

```
DETERMINISTIC RECONSTRUCTION (Phase 1)
         ↓
EVIDENCE CLASSIFICATION
(PROVEN / DERIVED / INCONSISTENCY / UNKNOWN)
         ↓
STRUCTURED EVIDENCE PAYLOAD
         ↓
GEMINI LLM (Phase 2)
         ↓
STRUCTURED JSON DIAGNOSIS
         ↓
NATURAL LANGUAGE EXPLANATION
```

**Critical Constraint:** The LLM does **NOT** determine facts, calculate metrics, or classify evidence. It **ONLY** converts pre-classified structured evidence into natural language.

### LLM Integration

**Provider:** Google Gemini  
**Model:** `gemini-3.7-flash` (cost-effective workhorse model)  
**SDK:** `google-genai==2.22.0`  
**Configuration:** `GEMINI_API_KEY` environment variable (via `.env` file, gitignored)

**System Prompt Constraints (13 rules):**
1. Use ONLY the evidence provided in the user message
2. Do NOT invent facts, causes, or explanations not present in evidence
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

### Structured JSON Output

Phase 2 uses Gemini's structured JSON mode with Pydantic schema validation:

```python
class DiagnosisSchema(BaseModel):
    summary: str
    what_happened: str
    what_is_known: List[str]
    what_cannot_be_determined: List[str]
    recommended_action: str
```

**Benefits:**
- Reliable parsing (no markdown extraction)
- Type validation
- Consistent response structure
- Graceful error handling for malformed JSON

### API Endpoint

**`GET /journeys/{order_id}/diagnosis`**

**Workflow:**
1. Call Phase 1 `reconstruct_journey(order_id)`
2. Check `GEMINI_API_KEY` environment variable
3. Build structured evidence payload from Phase 1 evidence
4. Send to Gemini with system prompt + evidence
5. Parse and validate JSON response
6. Return combined journey + diagnosis

**Error Handling:**
- 404: Order not found
- 503: `GEMINI_API_KEY` not configured
- 500: LLM generation failed (with context)
- Malformed JSON: Graceful error with truncated raw response

### Files Modified (Phase 2)

**New Files:**
- `backend/services/llm.py` (+195 lines)
- `tests/test_llm.py` (+254 lines)
- `tests/test_diagnosis_api.py` (+203 lines)
- `.env.example` (Gemini API key template)

**Modified Files:**
- `backend/main.py` (+99 lines) - Added diagnosis endpoint
- `backend/models.py` (+21 lines) - Added Diagnosis, DiagnosticResponse
- `requirements.txt` - Added google-genai, python-dotenv
- `.gitignore` - Added `.env`

**Unchanged (Phase 1 integrity preserved):**
- `backend/services/reconstruction.py` (no changes)
- `backend/services/evidence.py` (no changes)
- `backend/database.py` (no changes)
- All Phase 1 tests (no changes)

### Test Coverage

**Phase 2 Tests: 16 new tests**

**LLM Service Tests (8):**
- ✅ Mock Gemini response handling
- ✅ Evidence payload structure
- ✅ Evidence payload includes all categories
- ✅ LLM receives only structured evidence (not raw DB records)
- ✅ UNKNOWN preservation (no speculation)
- ✅ Malformed JSON handling
- ✅ Invalid JSON structure handling
- ✅ Missing API key error

**Diagnosis API Tests (8):**
- ✅ Health endpoint shows LLM configuration status
- ✅ Root endpoint includes diagnosis endpoint
- ✅ Diagnosis endpoint with mock LLM
- ✅ Phase 1 reconstruction used by diagnosis endpoint
- ✅ Response includes both journey and diagnosis
- ✅ Missing API key returns 503
- ✅ Missing order returns 404
- ✅ Phase 1 tests still pass (backward compatibility)

**All tests use mocked Gemini responses. No real API calls during testing.**

### Verification Results

**Real API Testing:**
- ✅ `/health` endpoint shows `llm_configured: true`
- ✅ `/journeys/order_scenario_a` returns Phase 1 deterministic journey
- ✅ `/journeys/order_scenario_a/diagnosis` reaches Gemini API
- ⚠️ Some requests returned 503 UNAVAILABLE due to external provider high demand (not an application error)

### Phase 2 Achievements

✅ **LLM integration without compromising deterministic architecture**  
✅ **Structured JSON output eliminates fragile markdown parsing**  
✅ **Comprehensive anti-hallucination constraints**  
✅ **Evidence-grounding: LLM cannot invent facts**  
✅ **Graceful degradation when API unavailable**  
✅ **Full test coverage with mocked responses**  
✅ **Phase 1 backward compatibility maintained**  
✅ **Security: API key in environment, .env gitignored**

### Database Schema
**3 tables created:**

1. **orders** - Core order information
   - order_id (PK)
   - created_at
   - amount, currency
   - merchant_status

2. **payment_attempts** - Individual payment attempts
   - attempt_id (PK)
   - order_id (FK)
   - payment_id
   - method, attempt_number
   - status, created_at

3. **payment_events** - Granular event timeline
   - event_id (PK)
   - order_id (FK), payment_id
   - event_type, status
   - timestamp
   - error_code, metadata_json

### Fixture Scenarios
**Two controlled scenarios implemented:**

1. **Scenario A** - UPI retry after authentication error
   - 2 payment attempts
   - 5 events total
   - 45-second retry gap
   - Final status: captured

2. **Scenario B** - Late authorization with state inconsistency
   - 1 payment attempt
   - 4 events including webhook
   - Demonstrates state mismatch detection
   - Final status: captured (but order status = created)

### Deterministic Reconstruction Engine

**Key Features:**
- ✅ Events ordered by timestamp (not insertion order)
- ✅ Deterministic derived facts (no randomness)
- ✅ Retry detection and gap calculation
- ✅ Journey duration calculation
- ✅ State inconsistency detection

**Derived Facts Calculated:**
- attempt_count
- event_count
- journey_start, journey_end
- journey_duration_seconds
- retry_count
- retry_gaps_seconds
- final_status

### Evidence Classification

**Four categories implemented:**

1. **PROVEN** - Facts directly from database records
   - Order details (amount, currency, created_at)
   - Event occurrences with timestamps
   - Payment attempt outcomes
   - Error codes and metadata

2. **DERIVED** - Facts calculated from available data
   - Total attempt count
   - Total event count
   - Retry count (attempts - 1)
   - Time gaps between attempts
   - Journey duration
   - Final payment status

3. **INCONSISTENCY** - Detected conflicting states
   - Order status vs. payment status mismatches
   - Event status vs. attempt status conflicts
   - State progression anomalies

4. **UNKNOWN** - Identified data gaps
   - Missing event records
   - Missing attempt records
   - Error codes without detailed metadata

### API Endpoints

**Implemented:**
- `GET /health` - Health check
- `GET /` - API information
- `GET /journeys/{order_id}` - Journey reconstruction

**Response Structure:**
```json
{
  "order_id": "...",
  "order": {...},
  "events": [...],
  "attempts": [...],
  "attempt_count": N,
  "event_count": N,
  "journey_start": "ISO timestamp",
  "journey_end": "ISO timestamp",
  "journey_duration_seconds": N.N,
  "retry_count": N,
  "retry_gaps_seconds": [...],
  "final_status": "...",
  "evidence": [
    {
      "category": "PROVEN|DERIVED|INCONSISTENCY|UNKNOWN",
      "statement": "...",
      "source": "..."
    }
  ]
}
```

### Test Coverage

**18 tests implemented and passing:**

**Reconstruction Tests:**
- ✅ Event chronological ordering (deterministic)
- ✅ Attempt count calculation
- ✅ Retry count and gap calculations
- ✅ Duration calculations
- ✅ Unknown order handling
- ✅ Scenario A full reconstruction
- ✅ Scenario B full reconstruction
- ✅ Evidence classification presence
- ✅ Inconsistency detection

**API Tests:**
- ✅ Health endpoint
- ✅ Root endpoint
- ✅ Valid order journey retrieval
- ✅ Invalid order 404 response
- ✅ Event chronological ordering in API response
- ✅ No hardcoded explanations in response
- ✅ Evidence structure validation

### Verification Results

**Backend startup:** ✅ Successfully running on port 8002

**Example API Responses:**

**Scenario A (UPI Retry):**
- 2 attempts, 5 events
- 54 second journey duration
- 45 second retry gap
- 20 evidence items (PROVEN/DERIVED/INCONSISTENCY)
- Detects "paid" vs "captured" status inconsistency

**Scenario B (Late Authorization):**
- 1 attempt, 4 events
- 55 second journey duration
- 0 retries
- 15 evidence items
- Detects "created" vs "captured" status inconsistency

**Invalid Order:**
- Returns 404 with clear error message

## What Does NOT Exist Yet

❌ No functional frontend interface (current UI is Phase 0 placeholder)  
❌ No frontend timeline visualization  
❌ No frontend evidence display  
❌ No frontend diagnosis rendering  
❌ No production database  
❌ No real Razorpay production data  
❌ No real-time event ingestion  
❌ No authentication or authorization  
❌ No monitoring or logging system  
❌ No deployment configuration

## Critical Design Principles Maintained

✅ **Deterministic reconstruction** - Same input always produces same output  
✅ **Evidence-based** - All facts traceable to source data  
✅ **No hardcoded explanations** - Only structured data returned  
✅ **Clear separation** - PROVEN facts ≠ DERIVED insights  
✅ **Timestamp-ordered events** - Not dependent on insertion order  
✅ **Explicit unknowns** - System acknowledges data gaps  
✅ **Inconsistency detection** - Conflicting states are identified  

## Architecture Decision Log

### Phase 0 Decisions
- **Backend:** FastAPI (lightweight, async-ready, automatic OpenAPI docs)
- **Database:** SQLite (simple, file-based, sufficient for MVP)
- **Frontend:** Static HTML (minimal complexity for Phase 0)
- **Dependencies:** Minimal set only (FastAPI, uvicorn, aiosqlite)

### Phase 1 Decisions
- **Database Schema:** Minimal 3-table design (orders, attempts, events)
- **Event Ordering:** Deterministic timestamp-based sorting
- **Evidence Model:** 4-category classification (PROVEN/DERIVED/INCONSISTENCY/UNKNOWN)
- **Reconstruction:** Pure Python logic (no ML, no LLM in this phase)
- **Testing:** pytest with asyncio support
- **Fixtures:** Generic/simulated data (not Razorpay-specific)

### Phase 2 Decisions
- **LLM Provider:** Google Gemini (cost-effective, structured JSON support)
- **Model:** gemini-3.7-flash (workhorse model for MVP)
- **Structured Output:** JSON mode with Pydantic validation (no markdown parsing)
- **Architecture:** Strict boundary - LLM is language layer only, not reasoning layer
- **System Prompt:** 13 explicit anti-hallucination constraints
- **Testing:** Mocked LLM responses, no real API calls in tests
- **Configuration:** Environment variable (GEMINI_API_KEY via .env file)

## Next Steps

**Phase 3 (Recommended Next - NOT STARTED):**
- Minimal functional frontend for PaymentTrace
- Single-page application (vanilla JS, no framework)
- Order ID input and "Diagnose" button
- Journey timeline visualization
- Evidence display by category
- Diagnosis explanation rendering
- Error handling (404, 503)

**Phase 4 Options (Future):**
- Advanced journey analysis (complex state patterns)
- Additional inconsistency detection rules
- Timeline gap analysis
- Payment method-specific rules

---

**Last Updated:** September 5, 2026  
**Version:** 0.3.0  
**Current Branch:** `feature/phase2-llm-integration`  
**Current Commit:** `418e790`
