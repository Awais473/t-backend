# Trading Bot

## Prerequisites

- Python 3.10+
- Node.js 18+

---

## Backend Setup (t-backend/)

```bash
cd t-backend

# Virtual environment create karein (pehli baar)
python -m venv venv

# Virtual environment activate karein
.\venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux

# Dependencies install karein
pip install -r requirements.txt

# Server run karein
uvicorn app.main:app --reload --port 8000
```

Backend `http://localhost:8000` par run hoga.

---

## Frontend Setup (t-frontend/)

```bash
cd t-frontend

# Dependencies install karein
npm install

# Dev server run karein
npm run dev
```

Frontend `http://localhost:5173` par run hoga.

---

## Notes

- Frontend ka Vite proxy `/api` aur `/ws` requests ko backend (`localhost:8000`) forward karta hai.
- Backend pehle run karna zaroori hai takay frontend API calls kar sake.
