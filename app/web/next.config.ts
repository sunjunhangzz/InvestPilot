import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: {
    root: path.resolve(process.cwd(), "../.."),
    resolveAlias: {
      "@shared": path.resolve(process.cwd(), "../shared"),
    },
  },
};

export default nextConfig;
