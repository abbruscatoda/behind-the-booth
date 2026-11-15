import type { NextConfig } from "next";
const config: NextConfig = { cacheComponents: true, htmlLimitedBots: /.*/, partialPrefetching: true, turbopack: { root: process.cwd() } };
export default config;
