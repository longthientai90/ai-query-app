/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        heading: ["Space Grotesk", "ui-sans-serif", "sans-serif"],
        body: ["DM Sans", "ui-sans-serif", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#eefcf8",
          100: "#d2f7ec",
          200: "#a9efdc",
          300: "#73e2c9",
          400: "#2fceb0",
          500: "#14b79a",
          600: "#0d947c",
          700: "#0d7665",
          800: "#0e5f52",
          900: "#0f4e45",
        },
      },
      boxShadow: {
        glow: "0 16px 60px rgba(20, 183, 154, 0.28)",
        card: "0 18px 50px rgba(15, 34, 53, 0.12)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        rise: "rise 420ms ease-out",
      },
    },
  },
  plugins: [],
};
