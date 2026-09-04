# Development Setup

## Python Virtual Environment

### Prerequisites
- Python 3.9 or higher
- pip

### Setup Steps

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```

2. **Activate virtual environment:**
   
   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```
   
   On Windows:
   ```bash
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation:**
   ```bash
   pip list
   ```

### Deactivate Virtual Environment

When finished working:
```bash
deactivate
```

## Running the Backend

With the virtual environment activated:

```bash
cd backend
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

Health check: `http://localhost:8000/health`

API documentation: `http://localhost:8000/docs`
