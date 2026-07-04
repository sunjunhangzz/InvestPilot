/**
 * Convert snake_case keys to camelCase for API responses.
 *
 * SQLite / Python use snake_case; the frontend receives camelCase.
 * All field conversion MUST happen here — page components should never
 * need to reverse-map individual field names.
 */

/** Convert a single snake_case string to camelCase. */
function toCamelCase(key: string): string {
  return key.replace(/_([a-z])/g, (_, char: string) => char.toUpperCase());
}

/** Recursively convert all keys in an object tree from snake_case to camelCase. */
export function mapToCamelCase<T>(value: T): T {
  if (value === null || value === undefined) {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map((item) => mapToCamelCase(item)) as unknown as T;
  }

  if (typeof value === "object" && value.constructor === Object) {
    const result: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(value as Record<string, unknown>)) {
      result[toCamelCase(key)] = mapToCamelCase(val);
    }
    return result as unknown as T;
  }

  return value;
}
