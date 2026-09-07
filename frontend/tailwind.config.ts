import type { Config } from "tailwindcss";

const config: Config = {
  // Class-based dark mode — toggled by `useThemeStore` adding/removing
  // the `dark` class on <html>. System preference is the initial value
  // when no explicit preference is stored in localStorage.
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#f0f3f9",
          100: "#d9e0f0",
          200: "#b3c1e1",
          300: "#8da2d2",
          400: "#6783c3",
          500: "#4164b4",
          600: "#345090",
          700: "#273c6c",
          800: "#1B3A6B",
          900: "#0d1424",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
export default config;
