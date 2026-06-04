# LearnSphere-AI Setup Guide

## Prerequisites

- Python 3.9+
- Node.js 16+
- PostgreSQL 12+
- Docker & Docker Compose
- Git

## Backend Setup

### 1. Clone Repository

```bash
git clone https://github.com/Azimullah-6430/LearnSphere-AI.git
cd LearnSphere-AI
```

### 2. Backend Installation

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Setup

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Database Setup

```bash
psql -U postgres
CREATE DATABASE learnsphere_ai;
\q

alembic upgrade head
```

### 5. Run Backend

```bash
python app/main.py
```

Backend runs on `http://localhost:8000`

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env with API endpoint
```

### 3. Run Frontend

```bash
npm start
```

Frontend runs on `http://localhost:3000`

## Docker Setup (Recommended)

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Backend API on port 8000
- Frontend on port 3000

## Default Credentials

**Teacher Portal:**
- Email: `teacher@learnsphere.com`
- Password: `Teacher@123`

**Student Portal:**
- Email: `student@learnsphere.com`
- Password: `Student@123`

## API Documentation

API documentation available at `http://localhost:8000/docs`

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Troubleshooting

See `TROUBLESHOOTING.md` for common issues and solutions.