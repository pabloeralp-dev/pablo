/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        moss:     '#0A0A0A',
        clay:     '#2563EB',
        cream:    '#EAEAEA',
        charcoal: '#070707',
      },
      fontFamily: {
        sans:  ['Plus Jakarta Sans', 'Outfit', 'sans-serif'],
        serif: ['Cormorant Garamond', 'serif'],
        mono:  ['ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },
    },
  },
  plugins: [],
}
