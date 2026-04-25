import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

type CookiesToSet = Array<{
  name: string;
  value: string;
  options?: Parameters<NextResponse["cookies"]["set"]>[2];
}>;

export const createClient = (request: NextRequest) => {
  try {
    if (!supabaseUrl || !supabaseKey) {
      return NextResponse.next({ request: { headers: request.headers } });
    }

    let supabaseResponse = NextResponse.next({
      request: {
        headers: request.headers,
      },
    });

    const supabase = createServerClient(supabaseUrl, supabaseKey, {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: CookiesToSet) {
          // In middleware, treat the request cookies as read-only; only set on the response.
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          );
        },
      },
    });

    // Touch auth to refresh session cookies if needed.
    supabase.auth.getUser().catch(() => {});

    return supabaseResponse;
  } catch {
    // Never block app routing due to session refresh issues.
    return NextResponse.next({ request: { headers: request.headers } });
  }
};

