/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'pm-primary': '#9b59b6',
        'pm-secondary': '#8e44ad',
        'worker-primary': '#3498db',
        'worker-secondary': '#2980b9',
        'kanban-primary': '#2ecc71',
        'kanban-secondary': '#27ae60',
        'decision-primary': '#f39c12',
        'decision-secondary': '#e67e22',
        'dark-bg': '#0a0a0a',
        'dark-surface': '#1a1a1a',
        'dark-border': '#333333',
      },
      animation: {
        'flow': 'flow 2s ease-in-out infinite',
        'pulse-soft': 'pulse-soft 3s ease-in-out infinite',
      },
      keyframes: {
        flow: {
          '0%': { strokeDashoffset: '24' },
          '100%': { strokeDashoffset: '0' }
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '0.8' },
          '50%': { opacity: '1' }
        }
      }
    },
  },
  plugins: [],
}