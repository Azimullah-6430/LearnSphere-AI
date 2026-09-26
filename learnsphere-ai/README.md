# LearnSphere AI

A premium, production-styled frontend for **LearnSphere AI** — a personalized academic intelligence platform with separate teacher and student experiences.

Built with **React 18 + Vite + React Router + Tailwind CSS + Recharts + lucide-react**.

## Getting started

```bash
npm install
npm run dev
```

Then open the printed local URL. Sign in as either **Teacher** or **Student** from the login screen (no real auth — it's a design/demo build) — the app remembers your choice for the session and adapts the sidebar, dashboard, and available pages accordingly.

```bash
npm run build      # production build → dist/
npm run preview    # preview the production build locally
npm run lint        # eslint
```

## What's included

- **Login** — split-screen branding with a Teacher/Student portal switch
- **Dashboards** — distinct teacher (data-dense) and student (personal/motivational) dashboards with live Recharts trend & subject charts
- **Evaluate Answer Script** — a full 5-step flow: question paper → answer script → student details → review → animated processing timeline → question-by-question AI feedback report
- **Evaluation History** — role-aware, searchable table
- **Academic Integrity (Plagiarism)** — similarity matches + side-by-side highlighted comparison
- **Student Analytics / Reports / Students** (teacher)
- **Performance, Personal Trainer (working chat with suggested prompts), Parent Agent, Focus Session (live countdown timer), Academic Memory, Self Evaluation** (student)
- **Notifications & Settings**
- **Light/dark theme** toggle (persisted to `localStorage`), fully responsive with a collapsible mobile sidebar

## Project structure

```
src/
  components/
    ui/Primitives.jsx    reusable Card, Badge, Button, StatCard, RowItem, SearchBox
    charts/Charts.jsx    themed Recharts wrappers (TrendChart, SubjectBarChart)
    Sidebar.jsx          role-aware navigation
    Topbar.jsx           page title, theme toggle, sign out
    AppLayout.jsx         auth-gated shell (sidebar + topbar + routed content)
  context/AppContext.jsx role, theme, and auth state
  data/mockData.js        all demo content in one place — edit this to change names/numbers
  pages/                  one file per route
```

## Design system

All colors, spacing, and radii are defined as CSS variables in `src/index.css` (`:root` for light, `[data-theme="dark"]` for dark) and consumed through Tailwind's arbitrary-value syntax, e.g. `bg-[var(--accent)]`. To re-theme the whole app, edit the variables in one place.

- **Font**: Manrope (body/UI), Source Serif 4 (login headline only)
- **Accent**: deep pine green `#28503F` — deliberately not the purple/gradient palette common in AI-generated UIs
- **Secondary/recognition accent**: muted bronze/gold `#93702F`

## Connecting real data

Everything currently renders from `src/data/mockData.js`. To wire this up to a real backend:

1. Replace the imports in each page with API calls (e.g. via `fetch` or a data-fetching library of your choice).
2. Replace `AppContext`'s mock `login`/`logout` with real authentication.
3. The Evaluate flow's "Start evaluation" step (`src/pages/Evaluate.jsx`) is where you'd trigger an actual evaluation job and poll/stream its status instead of the simulated timeline.
