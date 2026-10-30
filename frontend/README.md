# CareerPilot AI — Frontend Web Client

## Overview
Single-Page Application (SPA) built with React 18+, TypeScript, and Vite. Implements an accessible, evidence-first placement intelligence dashboard.

## Directory Layout
- `src/components/`: Reusable UI elements (buttons, inputs, cards, modal dialogs, alerts).
- `src/pages/`: Page views corresponding to core workflows (Login, Onboarding, Resume Workspace, Matching, Practice Room, Mock Interview, Progress).
- `src/services/`: Typed API client matching backend Pydantic contracts.
- `src/types/`: TypeScript data models and response types.

## Setup & Execution Commands
```bash
# Install dependencies
npm install

# Run TypeScript type check
npm run build -- --noEmit

# Launch Vite development server (defaults to http://localhost:5173)
npm run dev

# Run unit tests
npm test
```

