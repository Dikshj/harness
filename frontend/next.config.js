/** @type {import('next').NextConfig} */
const apiBaseUrl = process.env.HARNESS_API_URL || 'http://localhost:8000';

const nextConfig = {
  reactStrictMode: true,
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${apiBaseUrl}/:path*` },
    ];
  },
};
module.exports = nextConfig;
