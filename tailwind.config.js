// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'media', // This enables dark mode based on user preference
  theme: {
    extend: {
      colors: {
        mint: {
          50: '#f0fdf9',
          100: '#d0f7ed',
          200: '#a1ecd6',
          300: '#6ddbb8',
          400: '#38c496',
          500: '#1ca77a',
          600: '#138764',
          700: '#126c51',
          800: '#105543',
          900: '#0e4638',
          950: '#042721',
        },
      },
    },
  },
  plugins: [],
}