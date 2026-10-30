# CareerPilot AI — Frontend Web Client

## Overview
Single-Page Application (SPA) built with React 18+, TypeScript, and Vite. Implements an accessible, responsive, evidence-grounded placement preparation UI.

---

## 1. Prerequisites
- **Node.js**: v22.16.0 (or v20+)
- **npm**: 10.9.2+

---

## 2. Installation & Scripts

Navigate to the `frontend/` directory:
```powershell
cd frontend

# Install pinned dependencies
npm install

# Run Vite local development server (defaults to http://localhost:5173)
npm run dev

# Run TypeScript compilation check
npm run build -- --noEmit

# Build production bundle
npm run build

# Preview production build locally
npm run preview
```

---

## 3. Environment & Backend Connection
The frontend communicates with the FastAPI backend over REST APIs.
- Default local API proxy / URL: `http://localhost:8000/api/v1`
- Secrets policy: Never place JWT signing secrets, database credentials, or AI provider keys in frontend `.env` files.
