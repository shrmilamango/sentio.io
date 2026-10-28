/** Sentio design tokens.
 *  Palette from Indian block-print + spice: indigo ink, haldi yellow, chilli, leaf. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FBFAF7",      // page background
        ink: "#1C1A17",        // text
        muted: "#5E5A53",      // secondary text
        line: "#E4E0D6",       // borders, rules
        indigo: { DEFAULT: "#1F2A5C", soft: "#E9EBF4", deep: "#161E44" },
        haldi: { DEFAULT: "#F2B632", soft: "#FCF1D2", deep: "#C98F0E" },
        chilli: { DEFAULT: "#C8412E", soft: "#F8E3DF", ink: "#A3321F" }, // negative
        leaf: { DEFAULT: "#2F7D4F", soft: "#E1F0E6", ink: "#256640" }, // positive
        slate: { DEFAULT: "#8A8F98", soft: "#ECEDEF", ink: "#5A5F68" },  // neutral
      },
      fontFamily: {
        serif: ['"Tiro Devanagari Hindi"', "Georgia", "serif"],
        sans: ['"Mukta"', "system-ui", "sans-serif"],
      },
      maxWidth: { prose: "62ch" },
    },
  },
  plugins: [],
};
