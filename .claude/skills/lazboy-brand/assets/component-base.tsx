/**
 * La-Z-Boy Base Component
 * =======================
 * Starting point for any React component in a La-Z-Boy project.
 * All brand colors, fonts, and spacing are pre-applied via CSS custom properties.
 *
 * Usage: Copy this file and replace the example UI with your component content.
 * Never hardcode brand colors or fonts — always use the CSS variables below.
 */

import React from "react";

// ── Brand CSS variables (inject once at app root or in your global CSS) ──────
const brandStyles = `
  :root {
    --color-primary:      #1B3A6B;
    --color-accent:       #C0392B;
    --color-green:        #8FAF8A;
    --color-bg:           #FAF8F5;
    --color-text:         #2C2C2C;
    --color-text-light:   rgba(44, 44, 44, 0.6);
    --color-white:        #FFFFFF;

    --font-stack:         'Helvetica Neue', Helvetica, Arial, sans-serif;
    --font-size-h1:       clamp(32px, 5vw, 48px);
    --font-size-h2:       clamp(24px, 4vw, 32px);
    --font-size-h3:       20px;
    --font-size-body:     15px;
    --font-size-caption:  12px;
    --font-weight-bold:   700;
    --font-weight-semi:   600;
    --font-weight-body:   400;

    --radius-sm:          4px;
    --radius-md:          8px;
    --radius-lg:          16px;
    --radius-full:        9999px;

    --spacing-xs:  4px;
    --spacing-sm:  8px;
    --spacing-md:  16px;
    --spacing-lg:  24px;
    --spacing-xl:  32px;
    --spacing-2xl: 48px;
  }

  * { box-sizing: border-box; }

  body {
    font-family:      var(--font-stack);
    font-size:        var(--font-size-body);
    color:            var(--color-text);
    background-color: var(--color-bg);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    line-height: 1.6;
  }

  h1 { font-size: var(--font-size-h1); font-weight: var(--font-weight-bold); color: var(--color-primary); }
  h2 { font-size: var(--font-size-h2); font-weight: var(--font-weight-bold); color: var(--color-primary); }
  h3 { font-size: var(--font-size-h3); font-weight: var(--font-weight-semi); color: var(--color-text); }
`;

// ── Reusable brand-styled sub-components ─────────────────────────────────────
export const BrandButton = ({ children, variant = "primary", onClick }) => {
  const styles = {
    primary: {
      backgroundColor: "var(--color-accent)",
      color: "var(--color-white)",
    },
    secondary: {
      backgroundColor: "transparent",
      color: "var(--color-primary)",
      border: "2px solid var(--color-primary)",
    },
    ghost: {
      backgroundColor: "transparent",
      color: "var(--color-accent)",
      border: "none",
      textDecoration: "underline",
    },
  };

  return (
    <button
      onClick={onClick}
      style={{
        ...styles[variant],
        fontFamily: "var(--font-stack)",
        fontSize: "var(--font-size-body)",
        fontWeight: "var(--font-weight-semi)",
        padding: "var(--spacing-sm) var(--spacing-lg)",
        borderRadius: "var(--radius-md)",
        cursor: "pointer",
        border: styles[variant].border || "none",
        transition: "opacity 0.15s ease",
      }}
      onMouseOver={(e) => (e.currentTarget.style.opacity = "0.85")}
      onMouseOut={(e) => (e.currentTarget.style.opacity = "1")}
    >
      {children}
    </button>
  );
};

export const BrandCard = ({ title, children }) => (
  <div
    style={{
      backgroundColor: "var(--color-white)",
      borderRadius: "var(--radius-lg)",
      padding: "var(--spacing-xl)",
      boxShadow: "0 2px 12px rgba(27, 58, 107, 0.08)",
    }}
  >
    {title && (
      <h3 style={{ marginTop: 0, marginBottom: "var(--spacing-md)" }}>{title}</h3>
    )}
    {children}
  </div>
);

export const BrandBadge = ({ label, color = "primary" }) => {
  const colors = {
    primary: { bg: "var(--color-primary)", text: "var(--color-white)" },
    accent:  { bg: "var(--color-accent)",  text: "var(--color-white)" },
    green:   { bg: "var(--color-green)",   text: "var(--color-text)"  },
  };
  return (
    <span
      style={{
        backgroundColor: colors[color].bg,
        color: colors[color].text,
        fontFamily: "var(--font-stack)",
        fontSize: "var(--font-size-caption)",
        fontWeight: "var(--font-weight-semi)",
        padding: "2px var(--spacing-sm)",
        borderRadius: "var(--radius-full)",
        display: "inline-block",
      }}
    >
      {label}
    </span>
  );
};

// ── Example component (replace with your own) ─────────────────────────────────
export default function LaZBoyBaseComponent() {
  return (
    <>
      <style>{brandStyles}</style>
      <div style={{ padding: "var(--spacing-2xl)", maxWidth: "800px", margin: "0 auto" }}>
        <h1>La-Z-Boy Component</h1>
        <p style={{ color: "var(--color-text-light)", marginBottom: "var(--spacing-xl)" }}>
          Replace this content with your component. Brand variables are pre-applied.
        </p>

        <BrandCard title="Example Card">
          <p>Card content goes here. Body text uses Charcoal on Warm White.</p>
          <div style={{ display: "flex", gap: "var(--spacing-sm)", marginTop: "var(--spacing-md)" }}>
            <BrandBadge label="Active" color="green" />
            <BrandBadge label="Featured" color="primary" />
          </div>
        </BrandCard>

        <div style={{ display: "flex", gap: "var(--spacing-md)", marginTop: "var(--spacing-xl)" }}>
          <BrandButton variant="primary">Primary CTA</BrandButton>
          <BrandButton variant="secondary">Secondary</BrandButton>
          <BrandButton variant="ghost">Learn more</BrandButton>
        </div>
      </div>
    </>
  );
}
