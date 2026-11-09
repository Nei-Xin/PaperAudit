/** V3 design tokens — see docs/react-migration.md §5.3. */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "#F4F4F2",
        card: "#FFFFFF",
        line: "#E7E5E1",
        "line-soft": "#F0EFEC",
        hover: "#ECEBE8",
        active: "#E9E8E5",
        ink: { DEFAULT: "#1A1A19", 2: "#3A3835", 3: "#57534E", 4: "#6B6661" },
        accent: { DEFAULT: "#1E4A7A", hover: "#163A61", soft: "#EEF3F8" },
        ok: { DEFAULT: "#3F8A5A", text: "#2F6B45", soft: "#E8F1EA" },
        warn: { DEFAULT: "#B7791F", text: "#8A5A12", soft: "#F7EEDB" },
        bad: { DEFAULT: "#C2410C", text: "#A63D31", soft: "#FDECE4" },
        miss: "#B5473A",
        mute: "#A8A29E",
        review: { text: "#6D4C7D", soft: "#F1EAF4" },
      },
      borderRadius: { card: "14px" },
      fontFamily: {
        sans: ['"Inter"', '"PingFang SC"', '"Hiragino Sans GB"', '"Microsoft YaHei"', '"Noto Sans SC"', "-apple-system", '"Segoe UI"', "sans-serif"],
        serif: ['"Source Serif 4"', '"Songti SC"', '"STSong"', "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 0 0 1px #E7E5E1",
        pop: "0 8px 24px rgba(26,26,25,.12), 0 0 0 1px #E7E5E1",
      },
    },
  },
  plugins: [],
};
