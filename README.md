# La-Z-Boy AI Hub

Internal portal for discovering and installing AI skills, MCP servers, and tools across La-Z-Boy engineering teams.

## Tech Stack

- **Frontend**: React 19 / TypeScript / Vite / Tailwind CSS 4.2
- **Data**: GitHub API (skills), static JSON (MCP servers & tools)
- **UI**: Framer Motion, Lucide icons, glass-morphism design system
- **Deployment**: Vercel

## Features

- **Skills Catalog** — Browse 29+ AI agent skills with search, category filters, and detail pages. Skills are fetched live from GitHub.
- **MCP Servers** — 21 curated MCP server entries with config JSON copy, tool listings, and detail pages.
- **Tools Directory** — 186+ searchable tools across all MCP servers with category filtering.
- **Role-based Discovery** — Filter resources by role (Frontend, Backend, Full Stack, DevOps, Data/AI, Designer, QA, Security).
- **Glass-morphism UI** — Frosted glass cards, scroll-triggered animations, responsive 3-column grid layout.

## Quick Start

### Prerequisites

- Node.js 20+

### Install & Run

```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:5173

### Build

```bash
cd frontend
npm run build
```

### Lint

```bash
cd frontend
npm run lint
```

## Project Structure

```
lazboy-ai-hub/
├── .github/workflows/   # CI pipeline (lint + build)
├── frontend/
│   └── src/
│       ├── api/         # GitHub API client
│       ├── components/
│       │   ├── common/  # ScrollReveal, shared components
│       │   ├── layout/  # Header, Footer
│       │   ├── mcp/     # McpCard, McpGrid
│       │   ├── search/  # SearchBar
│       │   ├── skills/  # SkillCard, SkillGrid, SkillContentViewer
│       │   ├── tools/   # ToolCard, ToolGrid
│       │   └── ui/      # Spline 3D, Typewriter, TextRotate, Spotlight
│       ├── data/        # Static MCP servers & tools data
│       ├── hooks/       # useSkills, custom hooks
│       ├── pages/       # HomePage, BrowsePage, SkillDetailPage, McpDetailPage
│       └── types/       # TypeScript interfaces
├── .claude/skills/      # Agent skills (SKILL.md files)
└── README.md
```

## License

Internal use only — La-Z-Boy Incorporated
