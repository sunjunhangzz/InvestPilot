import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export type FactorWeights = {
  trend: number;
  momentum: number;
  liquidity: number;
  risk: number;
};

export type SharedConfig = {
  databasePath: string;
  reportsPath: string;
  logsPath: string;
  rawDataPath: string;
  cachePath: string;
  recommendationLimit: number;
  minRecommendationLimit: number;
  minTrackingDays: number;
  maxTrackingDays: number;
  factorWeights: FactorWeights;
  filters: {
    minListingDays: number;
    minAverageAmount20d: number;
    minPrice: number;
    maxPrice: number;
  };
  ai: {
    enabled: boolean;
    provider: string;
    model: string;
  };
};

const currentFile = fileURLToPath(import.meta.url);

// Config paths are resolved from the repository root because Next.js routes,
// scripts, and tests may run with different current working directories.
export const PROJECT_ROOT = path.resolve(path.dirname(currentFile), "../..");
export const SHARED_DIR = path.join(PROJECT_ROOT, "app", "shared");
export const CONFIG_PATH = path.join(SHARED_DIR, "config.json");
export const SCHEMA_PATH = path.join(SHARED_DIR, "schema.json");

export function resolveProjectPath(configPath: string): string {
  if (path.isAbsolute(configPath)) {
    return configPath;
  }

  return path.join(PROJECT_ROOT, configPath);
}

export function loadConfig(): SharedConfig {
  const rawConfig = fs.readFileSync(CONFIG_PATH, "utf8");
  return JSON.parse(rawConfig) as SharedConfig;
}

export function loadSchema(): Record<string, string[]> {
  const rawSchema = fs.readFileSync(SCHEMA_PATH, "utf8");
  return JSON.parse(rawSchema) as Record<string, string[]>;
}

export function getConfigPaths(config = loadConfig()): Record<string, string> {
  return {
    databasePath: resolveProjectPath(config.databasePath),
    reportsPath: resolveProjectPath(config.reportsPath),
    logsPath: resolveProjectPath(config.logsPath),
    rawDataPath: resolveProjectPath(config.rawDataPath),
    cachePath: resolveProjectPath(config.cachePath),
  };
}

export function validateFactorWeights(config = loadConfig()): void {
  const totalWeight = Object.values(config.factorWeights).reduce(
    (total, weight) => total + weight,
    0,
  );

  if (Math.abs(totalWeight - 1) > 0.000001) {
    throw new Error(`factorWeights must sum to 1, got ${totalWeight}`);
  }
}
