/**
 * Standardised API response format.
 *
 * All routes return `{ ok: true, data }` on success or
 * `{ ok: false, error: { code, message } }` on failure.
 */

import { NextResponse } from "next/server";

export interface ApiSuccess<T> {
  ok: true;
  data: T;
}

export interface ApiFailure {
  ok: false;
  error: {
    code: string;
    message: string;
  };
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure;

export function ok<T>(data: T, status = 200): NextResponse<ApiSuccess<T>> {
  return NextResponse.json({ ok: true, data }, { status });
}

export function fail(
  code: string,
  message: string,
  status = 400,
): NextResponse<ApiFailure> {
  return NextResponse.json(
    { ok: false, error: { code, message } },
    { status },
  );
}
