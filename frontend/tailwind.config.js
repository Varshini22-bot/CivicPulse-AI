/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        civic: {
          navy: {
            DEFAULT: '#0f172a',
            dark: '#090d16',
            light: '#1e293b',
            muted: '#334155'
          },
          teal: {
            DEFAULT: '#0d9488',
            hover: '#0f766e',
            light: '#ccfbf1'
          },
          cyan: {
            DEFAULT: '#0284c7',
            light: '#e0f2fe'
          },
          priority: {
            critical: '#ef4444',
            high: '#f97316',
            medium: '#eab308',
            low: '#22c55e'
          }
        }
      }
    },
  },
  plugins: [],
}
