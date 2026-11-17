import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Hide the floating "N" route indicator in dev; compile and runtime errors still show.
  devIndicators: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
