/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const gw = process.env.GATEWAY_URL || "http://gateway:8080";
    return [
      {
        source: "/api/admin/:path*",
        destination: `${gw}/admin/:path*`,
      },
      {
        source: "/api/health",
        destination: `${gw}/health`,
      },
    ];
  },
};

module.exports = nextConfig;
