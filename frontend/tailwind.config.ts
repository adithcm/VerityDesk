import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        paper: "#f7f4ef",
        signal: "#28666e",
        positive: "#2f7d57",
        caution: "#b87514",
        danger: "#b42318",
      },
    },
  },
  plugins: [],
};

export default config;
