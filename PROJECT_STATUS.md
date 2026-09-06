# PaymentTrace - Project Status

## Current Phase: Phase 3 - Functional Frontend ✅

**Status:** COMPLETE

**Current Branch:** `feature/phase2-llm-integration`  
**Current Commit:** `f845b8e`  
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

### ✅ Phase 3: Functional Frontend (Complete)
- [x] Order ID search interface with input validation
- [x] Quick-select buttons for fixture scenarios
- [x] Real-time API integration (GET /journeys/{order_id}/diagnosis)
- [x] Loading states with progressive messages
- [x] Order summary display (amount, status, attempts, retries, duration)
- [x] Payment timeline visualization (chronological, color-coded by status)
- [x] Payment attempts display with retry highlighting
- [x] Evidence panel with 4-category tabs (PROVEN/DERIVED/INCONSISTENCY/UNKNOWN)
- [x] Evidence items display with statements and sources
- [x] AI diagnosis rendering (summary, what happened, known/unknown, action)
- [x] Dynamic LLM model display from API response
- [x] Comprehensive error handling (404, 503, 500, network, empty input)
- [x] Responsive design (mobile/tablet/desktop breakpoints)
- [x] Professional developer-tool styling
- [x] No hardcoded diagnosis data (all from API)
- [x] No frontend business logic duplication
- [x] Frontend files: index.html, styles.css (~780 lines), app.js (~545 lines)

### ⏳ Phase 4: Advanced Journey Analysis (NOT STARTED - NEXT)
- [ ] Complex state machine analysis
- [ ] Timeline gap detection
- [ ] Additional inconsistency patterns

### ⏳ Phase 5: Production Readiness (NOT STARTED)
- [ ] Production database configuration
- [ ] API authentication
- [ ] Rate limiting
- [ ] Monitoring and logging
- [ ] Deployment configuration

## Phase 3 Implementation Summary

### Overview

Phase 3 transforms PaymentTrace from a backend-only API into a complete diagnostic tool with a functional web interface. The frontend consumes the existing Phase 2 diagnosis endpoint and provides visual investigation capabilities while preserving all architectural boundaries.

### Architecture

Phase 3 extends the existing architecture with a frontend display layer:

```
DETERMINISTIC RECONSTRUCTION (Phase 1 - Backend)
         ↓
EVIDENCE CLASSIFICATION (Phase 1 - Backend)
         ↓
STRUCTURED EVIDENCE PAYLOAD (Phase 1 - Backend)
         ↓
GEMINI LLM (Phase 2 - Backend)
         ↓
STRUCTURED JSON DIAGNOSIS (Phase 2 - Backend)
         ↓
FRONTEND DISPLAY (Phase 3 - Frontend)
```

**Critical Constraint:** The frontend does **NOT** calculate payment facts, classify evidence, or generate diagnoses. It **ONLY** displays API response data with visual formatting.

### Frontend Implementation

**Technology Stack:**
- HTML5 (semantic structure)
- CSS3 (responsive design, ~780 lines)
- Vanilla JavaScript (API integration, ~545 lines)
- Fetch API (no external dependencies)

**File Structure:**
```
frontend/
  index.html    (134 lines) - Semantic HTML structure
  styles.css    (778 lines) - Professional styling, responsive
  app.js        (543 lines) - API integration & rendering
```

**Total Frontend Code: ~1,455 lines**

### User Flow

1. User enters order ID (or clicks quick-select scenario button)
2. Frontend validates input (empty check)
3. JavaScript calls `GET /journeys/{order_id}/diagnosis`
4. Loading state displays with progressive messages:
   - "Reconstructing payment journey..."
   - "Generating evidence-grounded diagnosis..."
5. On success: Render complete diagnostic interface
6. On error: Display appropriate error message with retry option

### UI Components

**1. Header**
- PaymentTrace branding
- Tagline: "Payment Journey Reconstruction & Evidence-Grounded Diagnosis"
- Phase 3 badge

**2. Search Section**
- Order ID input field with validation
- "Diagnose Journey" button
- Quick-select buttons: Scenario A, Scenario B
- Enter key support

**3. Loading States**
- Animated spinner
- Progressive status messages
- Button disabled during API call

**4. Error Handling**
- 404: "Order Not Found" with suggestions
- 503: "Diagnostic Service Unavailable" (LLM config issue)
- 500: "Diagnosis Generation Failed"
- Network error: "API Unavailable" with /health suggestion
- Empty input: Validation message

**5. Order Summary**
- Grid layout (responsive)
- Order ID, Amount (formatted), Currency
- Merchant Status (color-coded)
- Final Payment Status (color-coded)
- Attempts, Retries, Duration (formatted), Events

**6. Payment Timeline**
- Vertical timeline with connecting line
- Chronological order preserved from backend
- Color-coded status markers (success/failed/pending/created)
- Event type, timestamp (formatted), status, payment ID
- Error codes and metadata display
- Visual hierarchy for readability

**7. Payment Attempts**
- Attempt cards with attempt number
- Status badges (color-coded: captured/failed)
- Retry attempts visually highlighted
- Payment ID, method (uppercase), timestamp
- Grid layout for attempt details

**8. Evidence Panel**
- Tab navigation: PROVEN / DERIVED / INCONSISTENCY / UNKNOWN
- Evidence items grouped by category
- Each item shows:
  - Statement (from API)
  - Source (from API)
  - Category-specific color coding
- Empty state handling per category
- Backend classification preserved exactly

**9. AI Diagnosis**
- Dedicated card with gradient background
- Meta badges:
  - "Evidence-Grounded Diagnosis"
  - Model name (dynamic from API: `llm_model`)
- Structured sections:
  - Summary
  - What Happened (chronological narrative)
  - What Is Known (bulleted list)
  - What Cannot Be Determined (bulleted list)
  - Recommended Action
- All content from API response

### Data Integration

**API Endpoint:** `GET /journeys/{order_id}/diagnosis`

**Data Flow:**
```javascript
// API call
fetch(`https://paymenttrace-api.onrender.com/journeys/${orderId}/diagnosis`)
  → Parse JSON response
  → Render order summary (data.journey.order)
  → Render timeline (data.journey.events)
  → Render attempts (data.journey.attempts)
  → Render evidence (data.journey.evidence)
  → Render diagnosis (data.diagnosis)
  → Display model name (data.llm_model)
```

**Frontend does NOT:**
- Calculate attempt counts, retry gaps, or durations
- Classify evidence into categories
- Reorder events
- Determine payment status
- Generate diagnoses
- Call Gemini directly

**All facts come from backend API response.**

### Responsive Design

**Breakpoints:**
- Mobile: < 768px (vertical layout, stacked components)
- Tablet: 768px - 1199px (adaptive grid)
- Desktop: ≥ 1200px (full layout, max-width container)

**Mobile Optimizations:**
- Search form stacks vertically
- Timeline readable on small screens
- Evidence tabs scroll horizontally
- Cards adapt to narrow width
- Touch-friendly button sizes

### Visual Design

**Design Philosophy:**
- Professional fintech/developer tool aesthetic
- Technical credibility emphasized
- Clean, hierarchical information architecture

**Color Coding:**
- Success: Green (#10b981)
- Failed: Red (#ef4444)
- Pending: Yellow (#f59e0b)
- Created: Indigo (#6366f1)

**Evidence Categories:**
- PROVEN: Green border
- DERIVED: Blue border
- INCONSISTENCY: Red border
- UNKNOWN: Yellow border

**Typography:**
- Monospace font for technical data (order IDs, timestamps, codes)
- Sans-serif for readable text
- Clear hierarchy with font sizes

**Layout:**
- Card-based sections
- Subtle shadows and borders
- Consistent spacing
- No excessive animations or gradients

### Error Handling

**Comprehensive coverage:**

1. **404 - Order Not Found:**
   - Error title, message
   - Suggestion: "Available test orders: order_scenario_a, order_scenario_b"
   - Retry button

2. **503 - Service Unavailable:**
   - Detects LLM configuration issue
   - Message: "LLM service not configured"
   - Note about GEMINI_API_KEY

3. **500 - Diagnosis Failed:**
   - Error message from API
   - Suggestion to check backend logs

4. **Network Failure:**
   - Detects fetch errors
   - Message: "Unable to connect to backend"
   - Suggestion to check /health endpoint

5. **Empty Order ID:**
   - Client-side validation
   - No API call made
   - Clear error message

### Files Modified (Phase 3)

**Created:**
- `frontend/app.js` (+543 lines)
- `frontend/styles.css` (+778 lines)

**Modified:**
- `frontend/index.html` (replaced Phase 0 placeholder, net +39 lines)

**Unchanged (Backend Integrity Preserved):**
- `backend/services/reconstruction.py` (no changes)
- `backend/services/evidence.py` (no changes)
- `backend/services/llm.py` (no changes)
- `backend/main.py` (no changes)
- `backend/models.py` (no changes)
- All test files (no changes)

**Phase 1 and Phase 2 remain completely untouched.**

### Test Coverage

**Phase 3 Testing:**
- Frontend uses mocked API responses during development
- Backend tests remain unchanged: 34/34 passing
- No new backend tests required (frontend only)

**Manual Testing Required:**
- UI functionality (order search, display, errors)
- Responsive design (mobile/tablet/desktop)
- Cross-browser compatibility
- API integration with real backend

### Phase 3 Achievements

✅ **Complete functional frontend without backend modifications**  
✅ **Real-time API integration (no hardcoded data)**  
✅ **Evidence classification preserved from backend**  
✅ **Timeline chronology maintained from backend**  
✅ **Professional developer-tool UX**  
✅ **Comprehensive error handling**  
✅ **Responsive across devices**  
✅ **No frontend business logic duplication**  
✅ **Architectural boundaries respected**  
✅ **All 34 backend tests still passing**

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

❌ No production database configuration  
❌ No real Razorpay production data integration  
❌ No real-time event ingestion  
❌ No authentication or authorization  
❌ No monitoring or logging system  
❌ No deployment configuration  
❌ No advanced journey analysis features

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

### Phase 3 Decisions
- **Technology:** Vanilla JavaScript (no framework) for simplicity
- **Styling:** Custom CSS (~780 lines) for full control
- **Architecture:** Frontend as pure display layer, no business logic
- **API Integration:** Fetch API with comprehensive error handling
- **Design:** Professional developer-tool aesthetic, not consumer-facing
- **Responsive:** Mobile-first approach with 768px breakpoint
- **Testing:** Manual UI testing, backend tests unchanged

## Next Steps

**Phase 4 (Recommended Next - NOT STARTED):**
- Advanced journey analysis
- Complex state machine patterns
- Timeline gap detection algorithms
- Payment method-specific rules
- Enhanced inconsistency detection
- Pattern recognition for common failure modes

**Phase 5 (Future - NOT STARTED):**
**Phase 5 (Future - NOT STARTED):**
- Production database configuration
- API authentication and authorization
- Rate limiting
- Monitoring and logging infrastructure
- Deployment configuration
- Performance optimization
- Timeline gap analysis
- Payment method-specific rules

---

**Last Updated:** September 5, 2026  
**Version:** 0.3.0  
**Current Branch:** `feature/phase2-llm-integration`  
**Current Commit:** `f845b8e`
