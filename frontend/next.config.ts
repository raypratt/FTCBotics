import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  // GitHub Pages serves from /FTCBotics/ in production
  basePath: isProd ? "/FTCBotics" : "",
  env: {
    NEXT_PUBLIC_BASE_PATH: isProd ? "/FTCBotics" : "",
  },
};

export default nextConfig;
