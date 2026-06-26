import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        emerald: { DEFAULT: "#00C896", dark: "#00A47C", light: "#E6FAF5" },
        ink: { DEFAULT: "#0A0C0E", 2: "#1A1D21", 3: "#2C3036" },
        muted: "#6B7280",
        surface: "#F7F8FA",
        canvas: "#EEF0F4",
        border: "#E4E6EA",
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      boxShadow: {
        card: "0 4px 24px -4px rgba(10, 12, 14, 0.08)",
        "card-hover": "0 12px 40px -8px rgba(10, 12, 14, 0.15)",
        glow: "0 0 40px -8px rgba(0, 200, 150, 0.45)",
      },
      animation: {
        "fade-up": "fadeUp 0.7s ease-out both",
        "fade-up-delay": "fadeUp 0.7s ease-out 0.15s both",
        float: "float 6s ease-in-out infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
