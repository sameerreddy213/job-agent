# Frontend — job-agent dashboard (Phase 4B)

React 18 + TypeScript + TailwindCSS, built with Vite. Mobile-first, responsive
(mobile / tablet / desktop), dark mode, JWT auth with refresh-token rotation.

## Layout
```
frontend/
├── index.html
├── package.json            # react, react-dom, react-router-dom, axios, recharts
├── vite.config.ts          # dev proxy /api -> localhost:8000
├── tailwind.config.js      # darkMode: 'class'
├── nginx-spa.conf          # SPA fallback (served by the frontend container)
├── Dockerfile              # multi-stage: vite build -> nginx static
└── src/
    ├── main.tsx            # providers: Theme, Toast, Router, Auth
    ├── App.tsx             # routes
    ├── index.css           # tailwind layers
    ├── lib/
    │   ├── api.ts          # axios client + *Api namespaces + token refresh
    │   ├── types.ts        # TS mirrors of backend schemas
    │   └── format.ts       # cn, date/CSV helpers, tone helpers
    ├── context/            # AuthContext, ThemeContext, ToastContext
    ├── components/         # Layout (sidebar+bottom-nav), ProtectedRoute, ui.tsx
    └── pages/              # Login, Dashboard, Queue, JobDetail, Analytics,
                            #   Sources, Settings, ResumeManagement, AuditLogs
```

## Auth flow
- `AuthApi.login` stores access + refresh tokens in localStorage.
- The axios response interceptor catches 401, performs ONE refresh (rotating the
  refresh token), retries the request, and on failure dispatches a `ja:logout`
  event that `AuthContext` uses to clear the session and redirect to `/login`.

## Responsive shell
- **Desktop/tablet:** left sidebar nav.
- **Mobile:** top bar + fixed bottom tab nav.
- Dark mode toggled via the `dark` class on `<html>`, persisted in localStorage.

## API usage rule (Phase 4B constraint)
The UI calls **existing** backend endpoints only — no new backend logic.
Queue **Approve/Reject/Snooze** have no server endpoint yet (Phase 5): Approve
opens the apply URL; Reject/Snooze hide the row locally. Each is marked with
`// Phase 5: replace local-only action with PATCH /jobs/{id}/status`.

## Run
- **Dev:** `cd frontend && npm install && npm run dev` (proxies /api to localhost:8000).
- **Prod:** built by the `frontend` Docker image and served behind nginx at `/`.
