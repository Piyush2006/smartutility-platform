import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  agentRules: false, // repo already has a root CLAUDE.md; don't autogenerate a conflicting one here
};

export default nextConfig;
