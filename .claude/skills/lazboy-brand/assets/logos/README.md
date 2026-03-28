# La-Z-Boy Logo Assets

Official logo files for agent use. Copy the appropriate variant into your project.

## Available Variants

| File | Size | Use Case |
|------|------|----------|
| `lazboy-logo-navy.png` | 3168x1129 (full res) | Print, high-DPI displays, source file |
| `lazboy-logo-navy-400w.png` | 400w | Standard web header |
| `lazboy-logo-navy-200w.png` | 200w | Compact header, sidebar, footer |
| `lazboy-logo-navy-80w.png` | 80w | Favicon-sized, small badges |

All files: PNG with transparent background, Navy (Comfort Blue #1B3A6B).

## How to Use

### IMPORTANT: Use shell commands to copy — never read/write tools
AI agents (Claude, Cursor) corrupt binary PNG files when using text-based read/write tools.
Always use `curl` or `cp` via a shell command:

```bash
# Download from GitHub (works in any project)
curl -sL "https://raw.githubusercontent.com/lzbtemp/lazboy-agent-skills/main/skills/lazboy-brand/assets/logos/lazboy-logo-navy-400w.png" -o public/lazboy-logo.png

# Or copy locally if the skill repo is cloned
cp /path/to/lazboy-agent-skills/skills/lazboy-brand/assets/logos/lazboy-logo-navy-400w.png public/lazboy-logo.png
```

### HTML
```html
<img src="/lazboy-logo.png" alt="La-Z-Boy" height="40" />
```

### White logo on dark backgrounds (CSS invert)
```css
.logo-white {
  filter: brightness(0) invert(1);
}
```

### React / JSX
```tsx
<img src="/lazboy-logo.png" alt="La-Z-Boy" className="h-10" />
{/* On dark bg: */}
<img src="/lazboy-logo.png" alt="La-Z-Boy" className="h-10 brightness-0 invert" />
```

## Rules
- Never recreate the logo in SVG/CSS/code
- Maintain clearspace equal to the height of the "L" on all sides
- Minimum size: 72px wide (digital)
