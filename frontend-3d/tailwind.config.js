/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Cyberpunk Industrial palette (matching existing theme.css)
        'rig-bg': '#0a0a0a',
        'rig-surface': '#111111',
        'rig-border': '#1a1a1a',
        'rig-cyan': '#00ffff',
        'rig-green': '#00ff41',
        'rig-yellow': '#ffd700',
        'rig-red': '#ff1744',
        'rig-orange': '#ff6600',
        'rig-purple': '#9945FF',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Inter', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px #00ffff, 0 0 10px #00ffff' },
          '100%': { boxShadow: '0 0 10px #00ffff, 0 0 20px #00ffff, 0 0 30px #00ffff' },
        }
      }
    },
  },
  plugins: [],
}
