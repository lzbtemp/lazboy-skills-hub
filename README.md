# La-Z-Boy AI Hub

Internal portal for discovering and installing AI skills, MCP servers, and tools across La-Z-Boy engineering teams.

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React | 19 |
| Language | TypeScript | 5.9 |
| Build tool | Vite | 7 |
| Styling | Tailwind CSS | 4.2 |
| Data fetching | TanStack React Query | 5 |
| HTTP client | Axios | 1.13 |
| Routing | React Router DOM | 7 |
| Animations | Framer Motion / Motion | 12 |
| 3D graphics | Spline React | 4.1 |
| Markdown | react-markdown + rehype-highlight | 10 / 7 |
| Icons | Lucide React | 0.577 |
| Deployment | Vercel | — |

**No backend** — all data comes from the GitHub API (live) and static TypeScript data files (bundled).

## Features

- **Skills Catalog** — Browse 29+ AI agent skills with search, category filters, and detail pages. Skills are fetched live from the `LZBRetail/lazboy-agent-skills` GitHub repo.
- **MCP Servers** — 21 curated MCP server entries with config JSON copy, tool listings, and detail pages.
- **Tools Directory** — 186+ searchable tools across all MCP servers with category filtering.
- **Marketplace** — Discover and install community skills from external providers (Anthropic, Vercel Labs).
- **Role-based Discovery** — Filter resources by role (Frontend, Backend, Full Stack, DevOps, Data/AI, Designer, QA, Security).
- **Glass-morphism UI** — Frosted glass cards, scroll-triggered animations, 3D Spline robot, responsive grid layout.

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

### Preview Production Build

```bash
cd frontend
npm run preview
```

### Lint

```bash
cd frontend
npm run lint
```

## Project Structure

```
lazboy-ai-hub/
├── frontend/
│   └── src/
│       ├── api/
│       │   └── github.ts          # GitHub API client (skills, marketplace, file tree)
│       ├── components/
│       │   ├── common/            # LoadingSpinner, Pagination, ScrollReveal
│       │   ├── layout/            # Header, Footer
│       │   ├── mcp/               # McpCard, McpGrid
│       │   ├── search/            # SearchBar, FilterPanel, SortDropdown
│       │   ├── skills/            # SkillCard, SkillGrid, SkillContentViewer,
│       │   │                      #   InstallInstructions, FileExplorer
│       │   ├── tools/             # ToolCard, ToolGrid
│       │   └── ui/                # Spline 3D, Typewriter, TextRotate, Spotlight
│       ├── data/
│       │   ├── mcp-servers.ts     # 21 curated MCP server definitions
│       │   └── tools.ts           # 186+ tools derived from MCP servers
│       ├── hooks/
│       │   ├── useSkills.ts       # Paginated skill listing with filters
│       │   ├── useCategories.ts   # Category aggregation (30-min cache)
│       │   └── useSearch.ts       # Full-text search with pagination
│       ├── lib/
│       │   ├── logger.ts          # Structured logging utility
│       │   └── utils.ts           # Tailwind merge helper
│       ├── pages/
│       │   ├── HomePage.tsx       # Hero, role selector, featured content
│       │   ├── BrowsePage.tsx     # Tabbed browse (Skills, MCP, Tools)
│       │   ├── SkillDetailPage.tsx
│       │   ├── McpDetailPage.tsx
│       │   ├── MarketplacePage.tsx
│       │   ├── MarketplaceDetailPage.tsx
│       │   └── NotFoundPage.tsx
│       ├── types/
│       │   └── index.ts           # Shared TypeScript interfaces
│       ├── App.tsx                # Router + React Query provider
│       └── main.tsx               # Entry point
├── .claude/skills/                # Agent skills (SKILL.md files)
├── vercel.json                    # Vercel deployment config (SPA rewrites)
└── README.md
```

## Data Architecture

```
┌─────────────┐       ┌──────────────────┐
│  GitHub API  │──────▶│  api/github.ts   │──▶ React Query cache (5-min stale)
│  (live)      │       │  fetchAllSkills  │
└─────────────┘       │  searchSkills    │
                      │  fetchFileTree   │
                      │  marketplace     │
                      └──────────────────┘

┌─────────────┐       ┌──────────────────┐
│  Static TS   │──────▶│  data/           │──▶ Imported at build time
│  (bundled)   │       │  mcp-servers.ts  │
└─────────────┘       │  tools.ts        │
                      └──────────────────┘
```

- **Skills** are fetched live from `LZBRetail/lazboy-agent-skills` on GitHub, parsed from SKILL.md frontmatter, and cached in-memory + React Query.
- **MCP Servers & Tools** are curated static data bundled into the build.
- **Marketplace** fetches skills from external GitHub repos (Anthropic, Vercel Labs).

## Logging

The app uses a lightweight structured logger (`src/lib/logger.ts`) with the following design:

- **Log levels:** `debug`, `info`, `warn`, `error`
- **Dev mode:** human-readable console output with module prefix
- **Production:** JSON-structured output for log aggregation
- **Modules instrumented:**
  - `api:github` — all GitHub API requests with timing, cache hits, errors
  - `hook:useSkills` / `hook:useSearch` / `hook:useCategories` — query lifecycle
  - `app` — global React Query error handler (catches all failed queries/mutations)

Open browser DevTools Console to see log output during development.

## Routes

| Path | Page | Data Source |
|------|------|-------------|
| `/` | Home | GitHub API + static |
| `/browse` | Browse (tabs: Skills, MCP, Tools) | GitHub API + static |
| `/skills/:slug` | Skill detail | GitHub API |
| `/mcp/:slug` | MCP Server detail | Static data |
| `/marketplace` | External marketplace | GitHub API |
| `/marketplace/:org/:repo/:slug` | Marketplace skill detail | GitHub API |

## Build Optimization

Vite is configured with manual chunk splitting:
- `vendor` — React, React DOM, React Router
- `query` — TanStack React Query
- `markdown` — react-markdown, rehype-highlight

## Deployment

Deployed to **Vercel** with SPA routing (all paths rewrite to `/index.html`).

```bash
# vercel.json handles:
# - Build: cd frontend && npm run build
# - Output: frontend/dist
# - SPA rewrites: /(.*) → /index.html
```

## License

Internal use only — La-Z-Boy Incorporated
