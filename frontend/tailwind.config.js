/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Pure black/white theme
        background: '#000000',
        card: '#0A0A0A',
        'card-hover': '#111111',
        border: '#1A1A1A',
        'border-light': '#222222',
        primary: '#FFFFFF',
        secondary: '#888888',
        muted: '#555555',
        // Only colors: profit/loss
        profit: '#22C55E',
        'profit-dark': '#16A34A',
        'profit-light': '#4ADE80',
        loss: '#EF4444',
        'loss-dark': '#DC2626',
        'loss-light': '#F87171',
        warning: '#FFFFFF',
        'warning-light': '#CCCCCC',
        call: '#22C55E',
        put: '#EF4444',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(255, 255, 255, 0.1)' },
          '50%': { boxShadow: '0 0 40px rgba(255, 255, 255, 0.2)' },
        },
      },
    },
  },
  plugins: [],
}
