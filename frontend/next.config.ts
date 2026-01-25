import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
      {
        source: '/download/:path*',
        destination: 'http://localhost:8000/download/:path*',
      },
    ];
  },
};

export default nextConfig;
