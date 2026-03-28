# Design Quality Standards

Detailed patterns for La-Z-Boy UI polish. Read this when building hero sections, dashboards, marketing pages, or any pixel-polished UI where the execution needs to feel crafted and elevated.

La-Z-Boy's aesthetic direction is **luxury editorial** — clean but warm, confident whitespace, dramatic type scale, rich micro-interactions, and atmospheric depth. Think high-end furniture catalog meets modern SaaS dashboard. Every output should feel intentionally designed, not AI-generated.

---

## Design Thinking (before coding)

Ask three questions before writing a line of UI code:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Does it match the luxury editorial direction, or does it feel generic?
- **Differentiation**: What makes this output memorable?

---

## Motion & Animation

Animation at La-Z-Boy should feel like sinking into a comfortable chair — smooth, unhurried, intentional.

- **Orchestrate page load**: Use staggered `animation-delay` for a cascading reveal effect. One well-orchestrated entrance creates more impact than scattered micro-interactions.
- **Hover states**: Cards and interactive elements should respond with lift (`translateY(-3px)`), shadow deepening, and color transitions. Use `cubic-bezier(0.22, 1, 0.36, 1)` for smooth, spring-like easing.
- **Scroll-triggered reveals**: Use Intersection Observer to animate sections into view as the user scrolls — not all at once on mount.
- **Transitions**: All interactive state changes (hover, focus, active) need `transition` — abrupt jumps break the comfort feeling. 200–300ms is the sweet spot.
- **Restraint**: Match animation complexity to context. Internal tools need subtle polish, not pyrotechnics.

---

## Shadows & Depth

Use brand-colored shadows instead of generic gray — this creates cohesive, branded depth that reinforces the Comfort Blue identity throughout every layer of the UI.

```css
--shadow-card:       0 1px 3px rgba(27, 58, 107, 0.04), 0 1px 2px rgba(27, 58, 107, 0.02);
--shadow-card-hover: 0 20px 40px -12px rgba(27, 58, 107, 0.15), 0 8px 16px -8px rgba(27, 58, 107, 0.08);
--shadow-glow:       0 0 40px -8px rgba(27, 58, 107, 0.12);
```

Shadows use Comfort Blue (`#1B3A6B`) at low opacity, not black or gray. Generic `rgba(0,0,0,0.1)` shadows feel disconnected from the brand.

---

## Backgrounds & Atmosphere

Flat solid colors feel static and cheap. La-Z-Boy's brand warmth comes through texture and depth.

- **Hero/dark sections**: Use gradients within the brand palette — e.g., `from-[#1B3A6B] via-[#152f58] to-[#0f2140]` rather than a flat Comfort Blue
- **Noise/grain textures**: Subtle SVG noise overlays at 2–4% opacity add tactile warmth that echoes the furniture brand
- **Geometric patterns**: Dot grids, circles, or rounded rectangles at very low opacity (3–6%) create visual interest without distraction
- **Glass-morphism**: `backdrop-blur` with semi-transparent brand colors works well for overlays, search bars, and floating elements on dark backgrounds

---

## Spatial Composition & Layout

La-Z-Boy's comfort identity should breathe through layout — generous space reads as quality, not empty.

- **Prefer asymmetric hero layouts**: Split content (text left, visual right) over centered text blocks
- **Generous negative space**: Use `py-16 lg:py-20` or more for sections — cramped `py-8` layouts feel budget
- **Decorative accents**: Thin gradient bars at card tops, angled `clip-path` edges, and gradient dividers add editorial polish without extra weight
- **Grid-breaking moments**: A hero card spanning 2 columns, or offset positioning, breaks strict grid monotony and signals craft

---

## Typography Expressiveness

Helvetica Neue is required, but its range is wide. Maximize contrast within the typeface rather than adding variety.

- **Dramatic scale contrast**: Hero headings at `text-6xl lg:text-7xl` with `tracking-tight leading-[0.95]` feel editorial, not generic
- **Weight contrast**: Bold (700) headings against Light/Regular (300/400) body text creates strong visual hierarchy
- **Letter-spacing variety**: `tracking-tight` for large display text, `tracking-[0.15em] uppercase` for small labels and section headers
- **Fluid scaling**: Use `clamp()` for font size tokens so scale adapts naturally across breakpoints

---

## Anti-Patterns to Avoid

- ❌ Flat, evenly-spaced grids with no visual hierarchy — vary card treatments for featured vs. standard items
- ❌ Generic gray shadows (`rgba(0,0,0,0.1)`) — use brand-colored shadows
- ❌ Abrupt state changes without transitions — every interactive element needs `transition`
- ❌ Cookie-cutter layouts that feel AI-generated — if a layout could be any brand, it's not La-Z-Boy
- ❌ Timid color application — be confident with Comfort Blue; use Burnt Vermilion as a sharp accent, not scattered everywhere equally
- ❌ Cramped spacing — La-Z-Boy is comfort; the layout should feel like it too
