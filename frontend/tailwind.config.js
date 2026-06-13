/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B0B0B",
        surface: "#111214",
        surface2: "#181A1D",
        accent: "#6B56FF",
        accent2: "#4BB9FF",
        border: "rgba(255,255,255,0.08)",
        text: "#F7F7FB",
        muted: "#ADB2C6",
      },
      boxShadow: {
        glow: "0 20px 70px rgba(107, 86, 255, 0.16)",
      },
      backgroundImage: {
        glass: "linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04))",
        radialGlow: "radial-gradient(circle at top left, rgba(107,86,255,0.20), transparent 28%), radial-gradient(circle at bottom right, rgba(75,185,255,0.16), transparent 24%)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
