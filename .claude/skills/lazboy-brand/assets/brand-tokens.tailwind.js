// La-Z-Boy Brand Tokens — Tailwind config extension
// Usage: merge this into your tailwind.config.js theme.extend

module.exports = {
  theme: {
    extend: {
      colors: {
        'lazboy': {
          'primary': '#1B3A6B',
          'accent': '#C0392B',
          'green': '#8FAF8A',
          'bg': '#FAF8F5',
          'text': '#2C2C2C',
          'text-light': 'rgba(44,44,44,0.6)',
          'white': '#FFFFFF',
          'black': '#000000',
          'legacy-red': '#CC0000',
        },
      },
      borderRadius: {
        'lzb-sm': '4px',
        'lzb-md': '8px',
        'lzb-lg': '16px',
        'lzb-full': '9999px',
      },
      fontSize: {
        'lzb-h1': 'clamp(32px, 5vw, 48px)',
        'lzb-h2': 'clamp(24px, 4vw, 32px)',
        'lzb-h3': '20px',
        'lzb-body': '15px',
        'lzb-caption': '12px',
      },
    },
  },
};