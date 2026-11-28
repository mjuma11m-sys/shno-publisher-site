// DW-166: «حياتي» → Instagram (@hayati.bh) direct publish through the Instagram API with Instagram Login (no Buffer).
// Reads the same queue the «📱 حياتي» studio tab manages: data/hayati-queue.json, the pause switch
// salfa_settings.hayati_autopublish, and the «hayati-…» flags in salfa_queue_flags (skip / next).
// One reel a day at 21:13 Bahrain time. pg_cron calls {action:"run"} every 10 minutes with the cron key;
// a reel container is created when due, then published once Instagram finishes processing it.
// The token never leaves the server: the owner pastes it once in the studio (action "connect"); it is refreshed weekly.
import { createClient } from "jsr:@supabase/supabase-js@2";

const BASE = "https://salfa-studio.vercel.app";
const G = "https://graph.instagram.com/v21.0";
const ORIGINS = ["https://salfa-studio.vercel.app", "https://mjuma11m-sys.github.io"];
const SLOT_MIN = 21 * 60 + 13; // Bahrain local minutes
const admin = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
const env = (k: string) => (Deno.env.get(k) || "").trim();

const enc = new TextEncoder();
const b64u = (b: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
async function tiktokOwner(token: string): Promise<boolean> {
  const [body, sig, extra] = String(token || "").split(".");
  if (!body || !sig || extra !== undefined) return false;
  const key = await crypto.subtle.importKey("raw", enc.encode("salfa-session:" + env("SUPABASE_SERVICE_ROLE_KEY")), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  if (b64u(await crypto.subtle.sign("HMAC", key, enc.encode(body))) !== sig) return false;
  let p: { sub?: string; exp?: number } = {};
  try { p = JSON.parse(atob(body.replace(/-/g, "+").replace(/_/g, "/"))); } catch { return false; }
  if (typeof p.sub !== "string" || !(Number(p.exp) > Date.now() / 1000)) return false;
  const { data } = await admin.from("salfa_tiktok_token").select("owner_open_id").eq("id", 1).maybeSingle();
  return !!data?.owner_open_id && data.owner_open_id === p.sub;
}
async function isAdmin(req: Request): Promise<boolean> {
  const tts = req.headers.get("X-Salfa-Session");
  if (tts && (await tiktokOwner(tts))) return true;
  const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!jwt) return false;
  const { data } = await admin.auth.getUser(jwt);
  const email = data.user?.email?.toLowerCase() || "";
  if (!email || !data.user?.email_confirmed_at) return false;
  if (email === env("OWNER_EMAIL").toLowerCase()) return true;
  const { data: row } = await admin.from("salfa_admin_emails").select("email").eq("email", email).maybeSingle();
  return !!row;
}
async function isCron(req: Request): Promise<boolean> {
  const k = req.headers.get("X-Salfa-Cron") || "";
  if (k.length < 32) return false;
  const { data } = await admin.from("salfa_cron_key").select("key").eq("id", 1).maybeSingle();
  return !!data?.key && data.key === k;
}

// content gate (CLAUDE.md «حياتي» rules): the app is on the App Store; no launch date or countdown for any update,
// no «يقرر» (we say «تقدير»), and screenshots carry «* لقطات ببيانات تجريبية».
const BANNED = /يوم الإطلاق|موعد الإطلاق|تاريخ الإطلاق|عد تنازلي|ينزل يوم|قيد التطوير|نسخة تجريبية|باقي\s*\d+\s*(يوم|أيام|ساع)|يقرر|\d+\s*(يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر)|\b20\d\d\b/;
function gate(caption: string): string | null {
  if (!caption || caption.length > 2200) return "الكابشن فاضي أو أطول من 2200 حرف";
  const m = caption.match(BANNED);
  if (m) return `الكابشن فيه «${m[0]}» (ممنوع: تاريخ، عد تنازلي، «يقرر»، و«قيد التطوير» لأن التطبيق على App Store)`;
  if (!caption.includes("* لقطات ببيانات تجريبية")) return "الكابشن ناقصه «* لقطات ببيانات تجريبية»";
  return null;
}

type Item = { id: string; title?: string; caption: string; asset?: string; media?: string | null; cover?: string | null };
const bhNow = () => { const d = new Date(Date.now() + 3 * 3600e3); return { day: d.toISOString().slice(0, 10), min: d.getUTCHours() * 60 + d.getUTCMinutes() }; };

async function token() {
  const { data } = await admin.from("salfa_ig_token").select("*").eq("id", 1).maybeSingle();
  return { t: data?.access_token || env("IG_ACCESS_TOKEN"), uid: data?.ig_user_id || env("IG_USER_ID"), row: data };
}
async function ig(path: string, params: Record<string, string>, method = "GET") {
  const u = new URL(G + path);
  const body = new URLSearchParams(params);
  const r = method === "GET" ? await fetch(u + "?" + body) : await fetch(u, { method, body });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) throw new Error((j.error?.message || `Instagram ${r.status}`).slice(0, 300));
  return j;
}

async function connect(raw: string) {
  const t = String(raw || "").trim();
  if (!/^[A-Za-z0-9_\-|.]{40,600}$/.test(t)) throw new Error("الرمز مو بالشكل الصحيح");
  const me = await ig("/me", { fields: "user_id,username", access_token: t });
  await admin.from("salfa_ig_token").upsert({ id: 1, access_token: t, ig_user_id: String(me.user_id), username: me.username,
    expires_at: new Date(Date.now() + 59 * 864e5).toISOString(), refreshed_at: new Date().toISOString() });
  return me.username as string;
}
async function refresh(row: { access_token?: string; refreshed_at?: string } | null) {
  if (!row?.access_token || (row.refreshed_at && Date.now() - Date.parse(row.refreshed_at) < 6 * 864e5)) return;
  try {
    const j = await ig("/refresh_access_token", { grant_type: "ig_refresh_token", access_token: row.access_token }).catch(() => null);
    if (!j?.access_token) return;
    await admin.from("salfa_ig_token").update({ access_token: j.access_token, refreshed_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + Number(j.expires_in || 5184000) * 1000).toISOString() }).eq("id", 1);
  } catch { /* keep the current token */ }
}

async function queueState() {
  const q: Item[] = await fetch(`${BASE}/data/hayati-queue.json`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : [])).catch(() => []);
  const { data: flags } = await admin.from("salfa_queue_flags").select("item_id, flag").like("item_id", "hayati-%");
  const { data: st } = await admin.from("salfa_settings").select("value").eq("key", "hayati_autopublish").maybeSingle();
  const { data: posts } = await admin.from("hayati_ig_posts").select("item_id, status, permalink, error, published_at, created_at").order("created_at", { ascending: false }).limit(50);
  const done = new Set((posts || []).filter((p) => p.status !== "failed").map((p) => p.item_id));
  const skip = new Set((flags || []).filter((f) => f.flag === "skip").map((f) => f.item_id));
  const nextId = (flags || []).find((f) => f.flag === "next")?.item_id;
  const left = q.filter((i) => !done.has(i.id) && !skip.has(i.id));
  left.sort((a, b) => (a.id === nextId ? -1 : b.id === nextId ? 1 : 0));
  return { q, left, posts: posts || [], on: st?.value?.on !== false };
}

async function run() {
  const { t, uid, row } = await token();
  if (!t || !uid) return { ok: false, connected: false, note: "إنستغرام مو مربوط" };
  await refresh(row);
  const log: string[] = [];
  // 1) finish what Instagram is still processing
  const { data: proc } = await admin.from("hayati_ig_posts").select("*").eq("status", "processing");
  for (const p of proc || []) {
    try {
      const s = await ig(`/${p.container_id}`, { fields: "status_code,status", access_token: t });
      if (s.status_code === "FINISHED") {
        const pub = await ig(`/${uid}/media_publish`, { creation_id: p.container_id, access_token: t }, "POST");
        const m = await ig(`/${pub.id}`, { fields: "permalink", access_token: t }).catch(() => ({}));
        await admin.from("hayati_ig_posts").update({ status: "published", ig_media_id: pub.id, permalink: m.permalink || null, published_at: new Date().toISOString() }).eq("id", p.id);
        log.push(`published ${p.item_id}`);
      } else if (s.status_code === "ERROR" || s.status_code === "EXPIRED" || p.tries >= 18) {
        await admin.from("hayati_ig_posts").update({ status: "failed", error: String(s.status || s.status_code).slice(0, 300) }).eq("id", p.id);
        log.push(`failed ${p.item_id}`);
      } else await admin.from("hayati_ig_posts").update({ tries: p.tries + 1 }).eq("id", p.id);
    } catch (e) {
      await admin.from("hayati_ig_posts").update({ tries: p.tries + 1, error: String((e as Error).message).slice(0, 300), status: p.tries >= 18 ? "failed" : "processing" }).eq("id", p.id);
    }
  }
  // 2) start today's reel when due (one a day, after 21:13 Bahrain, only while the «حياتي» switch is on)
  const st = await queueState();
  const now = bhNow();
  const today = st.posts.some((p) => ((p.published_at || p.created_at) as string) && // one attempt a day, failed ones too (no retry loop)
    new Date(Date.parse((p.published_at || p.created_at) as string) + 3 * 3600e3).toISOString().slice(0, 10) === now.day);
  if (!st.on) log.push("paused");
  else if (today) log.push("already posted today");
  else if (now.min < SLOT_MIN) log.push("not yet 21:13");
  else {
    // first item that passes the content gate; failing ones stay in the queue (not skipped) until their caption is fixed
    for (const x of st.left) { const b = gate(x.caption); if (b) log.push(`held ${x.id}: ${b}`); }
    const it = st.left.find((x) => !gate(x.caption) && (x.asset || x.media));
    if (!it) log.push("nothing publishable");
    else {
      const url = (it.asset ? `${BASE}/media/${it.asset}` : it.media) as string;
      {
        const params: Record<string, string> = { media_type: "REELS", video_url: url, caption: it.caption, share_to_feed: "true", access_token: t };
        if (it.cover) params.cover_url = it.cover.startsWith("http") ? it.cover : `${BASE}/media/${it.cover}`;
        try {
          const c = await ig(`/${uid}/media`, params, "POST");
          await admin.from("hayati_ig_posts").insert({ item_id: it.id, kind: "reel", media_path: url, caption: it.caption, status: "processing", container_id: c.id });
          await admin.from("salfa_queue_flags").delete().eq("item_id", it.id).eq("flag", "next");
          log.push(`container ${it.id}`);
        } catch (e) {
          await admin.from("hayati_ig_posts").insert({ item_id: it.id, kind: "reel", media_path: url, caption: it.caption, status: "failed", error: String((e as Error).message).slice(0, 300) });
          log.push(`error ${it.id}: ${(e as Error).message}`);
        }
      }
    }
  }
  return { ok: true, log };
}

async function status() {
  const { t, uid, row } = await token();
  const st = await queueState();
  return { connected: !!(t && uid), username: row?.username || null, expires_at: row?.expires_at || null, on: st.on,
    next: st.left.find((x) => !gate(x.caption))?.id || null, left: st.left.length,
    held: st.left.filter((x) => gate(x.caption)).map((x) => ({ id: x.id, why: gate(x.caption) })), posts: st.posts.slice(0, 15), slot: "21:13" };
}

Deno.serve(async (req) => {
  const origin = req.headers.get("Origin");
  const h = {
    "Access-Control-Allow-Origin": origin && ORIGINS.includes(origin) ? origin : ORIGINS[0],
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info, x-salfa-session",
    "Access-Control-Allow-Methods": "POST, OPTIONS", "Vary": "Origin",
    "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store",
  };
  const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: h });
  if (req.method === "OPTIONS") return new Response("ok", { headers: h });
  if (req.method !== "POST") return json({ error: "POST only" }, 405);
  try {
    const body = await req.json().catch(() => ({}));
    if (await isCron(req)) return json(await run());
    if (!(await isAdmin(req))) return json({ error: "هالصفحة لصاحب القناة بس" }, 403);
    if (body.action === "connect") return json({ ok: true, username: await connect(body.token) });
    if (body.action === "disconnect") { await admin.from("salfa_ig_token").delete().eq("id", 1); return json({ ok: true }); }
    if (body.action === "run") return json(await run());
    if (body.action === "retry") {
      const id = String(body.id || "");
      if (!/^hayati-[a-z0-9-]{2,33}$/.test(id)) return json({ error: "bad id" }, 400);
      await admin.from("hayati_ig_posts").delete().eq("item_id", id).eq("status", "failed");
      return json(await status());
    }
    return json(await status());
  } catch (e) {
    return json({ error: String((e as Error).message || e).slice(0, 300) }, 500);
  }
});
