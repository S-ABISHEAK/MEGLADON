/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0b0f17",
          panel: "#111827",
          border: "#1f2937",
        },
        accent: {
          DEFAULT: "#38bdf8",
          dim: "#0ea5e9",
        },
        status: {
          pending: "#6b7280",
          running: "#38bdf8",
          completed: "#22c55e",
          failed: "#ef4444",
        },
        confidence: {
          high: "#22c55e",
          medium: "#eab308",
          low: "#f97316",
          inferred: "#a855f7",
        },
      },
    },
  },
  plugins: [],
};
