import { NextRequest } from "next/server";

// Runtime proxy: forwards /api/* to the backend read from BACKEND_URL at REQUEST time.
// (A next.config rewrite bakes the target at build time, which breaks container/Blueprint deploys
// where the backend URL is only known at deploy time.)
export const dynamic = "force-dynamic";

// Accept either a full URL (http://backend:8000) or a bare host (Render `fromService` gives a
// scheme-less hostname) — prepend https:// in the latter case.
const _raw = process.env.BACKEND_URL || "http://localhost:8000";
const BACKEND = /^https?:\/\//.test(_raw) ? _raw : `https://${_raw}`;

async function proxy(req: NextRequest, path: string[]) {
  const target = `${BACKEND}/api/${path.join("/")}${req.nextUrl.search}`;
  const init: RequestInit = {
    method: req.method,
    headers: { "content-type": req.headers.get("content-type") || "application/json" },
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") init.body = await req.text();
  try {
    const res = await fetch(target, init);
    const body = await res.arrayBuffer();
    return new Response(body, {
      status: res.status,
      headers: {
        "content-type": res.headers.get("content-type") || "application/json",
        "content-disposition": res.headers.get("content-disposition") || "",
      },
    });
  } catch {
    return new Response(JSON.stringify({ error: "backend unreachable", backend: BACKEND }), {
      status: 502, headers: { "content-type": "application/json" },
    });
  }
}

type Ctx = { params: { path: string[] } };
export async function GET(req: NextRequest, { params }: Ctx) { return proxy(req, params.path); }
export async function POST(req: NextRequest, { params }: Ctx) { return proxy(req, params.path); }
export async function DELETE(req: NextRequest, { params }: Ctx) { return proxy(req, params.path); }
export async function PUT(req: NextRequest, { params }: Ctx) { return proxy(req, params.path); }
