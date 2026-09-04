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

## Planned Architecture

```
┌─────────────────┐
│   Frontend      │  Static HTML interface
│   (Minimal)     │  Order ID input + results display
└────────┬────────┘
         │
         │ HTTP/REST
         ↓
┌─────────────────┐
│   FastAPI       │  /health, /search, /diagnose
│   Backend       │  Journey reconstruction logic
└────────┬────────┘
         │
         ├─────────────┐
         ↓             ↓
┌─────────────┐  ┌──────────────┐
│  SQLite DB  │  │  LLM API     │
│  Events     │  │  (External)  │
│  Orders     │  │              │
└─────────────┘  └──────────────┘
```

### Data Flow
1. User enters Order ID
2. Backend queries SQLite for related events
3. Events sorted by timestamp
4. Journey reconstruction algorithm runs
5. Evidence classified (Proven/Derived/Inconsistency/Unknown)
6. Structured evidence sent to LLM
7. LLM returns constrained explanation
8. Frontend displays timeline + explanation

## Local Setup

### Prerequisites
- Python 3.9+
- pip

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

4. **Run backend:**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

5. **Access API:**
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs
   - Frontend: Open `frontend/index.html` in browser

### Verify Installation

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "PaymentTrace",
  "version": "0.1.0",
  "phase": "0 - Setup"
}
```

## Project Status

**Current Phase:** Phase 0 - Setup (IN PROGRESS)

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed phase breakdown.

### What Works Now
✅ Backend starts successfully  
✅ Health check endpoint  
✅ API documentation

### What Doesn't Exist Yet
❌ Database schema  
❌ Payment/event ingestion  
❌ Journey reconstruction logic  
❌ Evidence classification  
❌ AI integration  
❌ Functional diagnostic features

## Development Guidelines

### Principles
1. **Evidence-based:** Every conclusion must trace to source data
2. **Deterministic:** Same input → same reconstruction
3. **Minimal dependencies:** Only add what's necessary
4. **Clear separation:** Proven facts ≠ Derived insights
5. **Constrained AI:** LLM receives structured evidence, not raw logs

### Code Structure
```
backend/
  main.py           # FastAPI app + routes
  models/           # Database models (future)
  services/         # Business logic (future)
  utils/            # Helper functions (future)

frontend/
  index.html        # Main interface

tests/              # Test suite (future)
```

## Contributing

This is an MVP under active development. Focus areas:
- Database schema design
- Journey reconstruction algorithm
- Evidence classification logic
- LLM prompt engineering

## License

See [LICENSE](LICENSE) file.

---

**Version:** 0.1.0  
**Last Updated:** September 4, 2026