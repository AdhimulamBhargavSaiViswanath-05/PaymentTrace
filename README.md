# PaymentTrace

**Developer diagnostic tool for investigating payment journeys**

---

## Problem Statement

When payments fail or behave unexpectedly, developers and payment operations teams need to:
1. Retrieve scattered payment/event records for a specific order
2. Reconstruct the complete payment journey deterministically
3. Identify what actually happened vs. what was expected
4. Communicate findings clearly to stakeholders

Current approaches often involve manual log analysis, educated guessing, and fragmented data sources. PaymentTrace provides a systematic, evidence-based diagnostic workflow.

## Primary User

**Developer / Payment Operations Investigator**

Someone who needs to:
- Debug a specific payment issue
- Understand retry/fallback behavior
- Identify inconsistencies in payment state
- Generate clear explanations for support teams

## Secondary Beneficiary

**Support Personnel**

Who need to communicate diagnostic results to customers in clear, non-technical language.

## MVP Scope

PaymentTrace MVP follows this flow:

```
Order ID
  ↓
Retrieve available payment/event records
  ↓
Deterministically reconstruct payment journey
  ↓
Order events by timestamp
  ↓
Derive basic facts (attempts, retries, duration)
  ↓
Compare relevant states
  ↓
Classify evidence as:
  • Proven (directly from logs)
  • Derived (inferred from patterns)
  • Inconsistency (conflicting data)
  • Unknown (gaps in data)
  ↓
Send structured evidence to LLM
  ↓
Generate constrained natural-language explanation
```

### MVP Features
- Order ID-based search
- Event timeline reconstruction
- Basic fact derivation (retry count, duration, etc.)
- Evidence classification
- LLM-based explanation generation
- Simple web interface

### Technology Stack
- **Backend:** FastAPI (Python)
- **Database:** SQLite
- **Frontend:** Static HTML/CSS/JS
- **AI:** LLM API integration (structured prompts)

## Explicit Non-Goals

PaymentTrace is **NOT**:

❌ A customer-facing payment application  
❌ A payment gateway  
❌ A payment router  
❌ A replacement for Razorpay or similar platforms  
❌ An XAI/SHAP/LIME explainability system  
❌ A predictive ML system  
❌ A real-time monitoring dashboard  
❌ A production payment processor

## Architecture

PaymentTrace uses a layered architecture where the deterministic reconstruction engine is the source of truth, and the LLM serves only as a language synthesis layer:

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

### System Components

```
┌─────────────────┐
│   Frontend      │  Static HTML interface (Phase 0 placeholder)
│   (Minimal)     │  Order ID input + results display
└────────┬────────┘
         │
         │ HTTP/REST
         ↓
┌─────────────────┐
│   FastAPI       │  Phase 1: /journeys/{order_id}
│   Backend       │  Phase 2: /journeys/{order_id}/diagnosis
└────────┬────────┘
         │
         ├─────────────┐
         ↓             ↓
┌─────────────┐  ┌──────────────┐
│  SQLite DB  │  │ Gemini API   │
│  Events     │  │ (External)   │
│  Orders     │  │              │
│  Attempts   │  │              │
└─────────────┘  └──────────────┘
```

### Critical Architectural Constraints

The LLM (Gemini) does **NOT**:
- Determine payment facts or journey state
- Calculate attempt counts, retry gaps, or durations
- Classify evidence as PROVEN/DERIVED/INCONSISTENCY/UNKNOWN
- Access raw database records

The LLM **ONLY**:
- Receives pre-classified structured evidence
- Converts evidence into natural language explanations
- Operates under 13 strict anti-hallucination constraints

All facts are established by the deterministic Phase 1 reconstruction engine.

## Local Setup

### Prerequisites
- Python 3.9+
- pip
- (Optional) Google Gemini API key for diagnosis endpoint

### Installation

1. **Clone repository:**
   ```bash
   git clone <repository-url>
   cd PaymentTrace
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Gemini API (Optional):**
   
   To use the diagnosis endpoint (`/journeys/{order_id}/diagnosis`), you need a Gemini API key:
   
   ```bash
   # Create .env file (NEVER commit this file)
   cp .env.example .env
   
   # Edit .env and add your key:
   # GEMINI_API_KEY=your_actual_api_key_here
   ```
   
   **IMPORTANT:** The `.env` file is gitignored and must **NEVER** be committed to version control.
   
   Without a Gemini API key:
   - Phase 1 endpoints (`/journeys/{order_id}`) work normally
   - Phase 2 diagnosis endpoint returns 503 error
   - All tests still pass (tests use mocked LLM responses)

5. **Run backend:**
   ```bash
   python -m uvicorn backend.main:app --reload
   ```

6. **Access API:**
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs
   - Frontend: Open `frontend/index.html` in browser (Phase 0 placeholder)

### Verify Installation

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "PaymentTrace",
  "version": "0.3.0",
  "phase": "2 - LLM Diagnostic Integration",
  "llm_configured": true
}
```

## Project Status

**Current Phase:** Phase 2 - LLM Diagnostic Integration ✅ **COMPLETE**

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed phase breakdown.

### What Works Now

**Phase 1 - Deterministic Payment Journey Reconstruction:**
✅ SQLite database with payment events, attempts, and orders  
✅ Deterministic journey reconstruction from database records  
✅ Evidence classification (PROVEN/DERIVED/INCONSISTENCY/UNKNOWN)  
✅ Chronological event ordering by timestamp  
✅ Derived fact calculations (attempts, retries, duration, gaps)  
✅ API endpoint: `GET /journeys/{order_id}`  

**Phase 2 - Evidence-Grounded AI Diagnostic Explanations:**
✅ Google Gemini LLM integration (`gemini-3.7-flash`)  
✅ Structured evidence payload generation  
✅ Constrained system prompt with 13 anti-hallucination rules  
✅ Structured JSON diagnosis output with Pydantic validation  
✅ API endpoint: `GET /journeys/{order_id}/diagnosis`  
✅ Graceful error handling for missing API keys and malformed responses  
✅ 34/34 tests passing (all LLM calls mocked in tests)  

### What Doesn't Exist Yet
❌ Functional frontend interface (current UI is Phase 0 placeholder)  
❌ Production database configuration  
❌ Real-time event ingestion  
❌ Authentication or authorization  
❌ Monitoring and logging  
❌ Deployment configuration

## API Endpoints

### Phase 1 Endpoints

#### `GET /health`
Health check with LLM configuration status.

#### `GET /`
API information and endpoint list.

#### `GET /journeys/{order_id}`
Deterministic payment journey reconstruction (no LLM required).

Returns structured journey data with:
- Order details
- Chronologically ordered events
- Payment attempts
- Derived facts (attempts, retries, duration)
- Evidence classification (PROVEN/DERIVED/INCONSISTENCY/UNKNOWN)

**Example:**
```bash
curl http://localhost:8000/journeys/order_scenario_a
```

### Phase 2 Endpoints

#### `GET /journeys/{order_id}/diagnosis`
Complete diagnostic report with AI-generated explanation.

Combines Phase 1 reconstruction with Gemini-generated natural language explanation.

**Requires:** `GEMINI_API_KEY` environment variable

**Example:**
```bash
curl http://localhost:8000/journeys/order_scenario_a/diagnosis
```

**Response structure:**
```json
{
  "order_id": "order_scenario_a",
  "journey": {
    "order": {...},
    "events": [...],
    "attempts": [...],
    "evidence": [...]
  },
  "diagnosis": {
    "summary": "Brief overview of what happened",
    "what_happened": "Chronological explanation...",
    "what_is_known": ["fact 1", "fact 2"],
    "what_cannot_be_determined": ["unknown 1"],
    "recommended_action": "Suggested next steps...",
    "raw_explanation": "Full JSON response from Gemini"
  },
  "llm_model": "gemini-3.7-flash",
  "evidence_based": true
}
```

**Note:** The diagnosis endpoint depends on external Gemini API availability. During high demand, Gemini may return 503 errors. This is an external provider issue, not an application error.

## Development Guidelines

### Principles
1. **Evidence-based:** Every conclusion must trace to source data
2. **Deterministic:** Same input → same reconstruction (Phase 1)
3. **Minimal dependencies:** Only add what's necessary
4. **Clear separation:** Proven facts ≠ Derived insights
5. **Constrained AI:** LLM receives structured evidence, not raw logs
6. **Architectural boundary:** Deterministic engine is source of truth, LLM is language layer

### Code Structure
```
backend/
  main.py                   # FastAPI app + routes
  models.py                 # Pydantic models
  database.py               # SQLite connection and schema
  services/
    reconstruction.py       # Phase 1: Deterministic journey reconstruction
    evidence.py             # Phase 1: Evidence classification
    llm.py                  # Phase 2: Gemini integration
  fixtures/
    data.py                 # Test scenarios

frontend/
  index.html                # Phase 0 placeholder

tests/
  test_reconstruction.py    # Phase 1 tests
  test_api.py               # Phase 1 API tests
  test_llm.py               # Phase 2 LLM service tests (mocked)
  test_diagnosis_api.py     # Phase 2 diagnosis endpoint tests (mocked)
```

### Testing

Run the complete test suite:
```bash
pytest -v
```

**All 34 tests use mocked Gemini responses.** Tests do **NOT** require a real `GEMINI_API_KEY` and will not make external API calls.

Test breakdown:
- **10 tests:** Phase 1 reconstruction logic
- **8 tests:** Phase 1 API endpoints
- **8 tests:** Phase 2 LLM service (mocked)
- **8 tests:** Phase 2 diagnosis endpoint (mocked)

## Limitations and Disclaimers

**This is an MVP for development and demonstration purposes.**

PaymentTrace is **NOT**:
- Production-ready for real payment processing
- Guaranteed to prevent LLM hallucinations (constrained, not perfect)
- Validated for accuracy on real-world payment data
- Suitable for compliance-critical or financial reporting use cases
- A replacement for proper payment gateway investigation tools

**Known Limitations:**
- Fixture data only (no real Razorpay production data)
- Frontend is Phase 0 placeholder (not functional)
- Diagnosis endpoint depends on external Gemini API availability
- No authentication, rate limiting, or production safeguards
- SQLite database (not suitable for production scale)

## Contributing

This is an MVP under active development. Current implementation status:
- ✅ Phase 0: Project Setup
- ✅ Phase 1: Deterministic Reconstruction
- ✅ Phase 2: LLM Diagnostic Integration
- ⏳ Phase 3: Frontend Interface (next)

## License

See [LICENSE](LICENSE) file.

---

**Version:** 0.3.0  
**Last Updated:** September 5, 2026  
**Current Branch:** `feature/phase2-llm-integration`  
**Current Commit:** `418e790`