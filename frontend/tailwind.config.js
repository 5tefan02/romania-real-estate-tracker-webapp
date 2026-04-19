// Tailwind config — tells Tailwind which files to scan for class names,
// so it can generate only the CSS we actually use.

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
