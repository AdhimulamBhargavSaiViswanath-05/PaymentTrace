# PaymentTrace - Project Status

## Current Phase: Phase 1 - Data Model & Reconstruction ✅

**Status:** COMPLETE

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

### ⏳ Phase 2: Advanced Journey Analysis (Not Started)
- [ ] Complex state machine analysis
- [ ] Timeline gap detection
- [ ] Additional inconsistency patterns

### ⏳ Phase 3: LLM Integration (Not Started)
- [ ] LLM API client setup
- [ ] Structured evidence formatting for LLM
- [ ] Constrained natural-language explanation generation
- [ ] Explanation validation

### ⏳ Phase 4: Frontend Interface (Not Started)
- [ ] Order ID search interface
- [ ] Journey timeline visualization
- [ ] Evidence categorization display
- [ ] Explanation rendering

### ⏳ Phase 5: Production Readiness (Not Started)
- [ ] Production database configuration
- [ ] API authentication
- [ ] Rate limiting
- [ ] Monitoring and logging
- [ ] Deployment configuration

## Phase 1 Implementation Summary

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

❌ No AI/LLM integration  
❌ No natural-language explanations  
❌ No frontend interface (beyond Phase 0 placeholder)  
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

## Next Steps

**Phase 2 Options:**
- Advanced journey analysis (complex state patterns)
- Additional inconsistency detection rules
- Timeline gap analysis

**Phase 3 (Recommended Next):**
- LLM integration for natural-language explanations
- Structured evidence → constrained prompt design
- Explanation generation from evidence only

---

**Last Updated:** September 4, 2026  
**Version:** 0.2.0  
**Current Branch:** feature/project-setup
