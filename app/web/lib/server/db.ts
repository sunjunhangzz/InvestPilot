/**
 * Shared SQLite read helpers for Next.js API Routes.
 *
 * All functions open a fresh connection per call — suitable for the single-user
 * local MVP where concurrent reads are rare and short-lived.
 */
import Database from "better-sqlite3";
import { getConfigPaths } from "@shared/paths";

let _dbPath: string | null = null;

function dbPath(): string {
  if (_dbPath === null) {
    _dbPath = getConfigPaths().databasePath;
  }
  return _dbPath;
}

/**
 * Open a read-only SQLite connection.
 *
 * Read-only mode avoids accidental writes from API code and prevents
 * SQLITE_BUSY conflicts with the worker's write transactions.
 */
export function openDatabase(): Database.Database {
  return new Database(dbPath(), { readonly: true });
}

/**
 * Run a query and return all rows as plain objects.
 */
export function queryAll<T = Record<string, unknown>>(
  sql: string,
  params: unknown[] = [],
): T[] {
  const db = openDatabase();
  try {
    return db.prepare(sql).all(...params) as T[];
  } finally {
    db.close();
  }
}

/**
 * Run a query and return the first row, or null.
 */
export function queryOne<T = Record<string, unknown>>(
  sql: string,
  params: unknown[] = [],
): T | null {
  const db = openDatabase();
  try {
    return (db.prepare(sql).get(...params) as T) ?? null;
  } finally {
    db.close();
  }
}
