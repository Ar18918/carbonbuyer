/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // /api/* is proxied to BACKEND_URL at runtime by app/api/[...path]/route.ts (deploy-friendly).
};

export default nextConfig;
