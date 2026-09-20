# Sonexial Automation - Agentic GEO Scanner

Full-stack application for automated Generative Engine Optimization (GEO) audits and AI pitch generation.

## Project Structure

```
sonexial-automation/
├── backend/          # FastAPI scanner and agentic outreach service
│   ├── main.py
│   └── requirements.txt
└── frontend/         # Next.js UI interface
    ├── app/
    ├── package.json
    └── ...
```

## Getting Started

### Backend (FastAPI)

1. Navigate to `backend`:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the API:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### Frontend (Next.js)

1. Navigate to `frontend`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.
