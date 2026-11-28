// Salfa Studio: owner control of the daily auto-publish. Lists what goes out next (from the site's publish-queue.json
// plus what the studio already posted) and lets an admin pin an item for the next run or skip it.
// Flags live in public.salfa_queue_flags (service role only); the daily publish task reads them before posting.
// DW-165: «حياتي» tab — the app's own queue (data/hayati-queue.json + data/hayati-posted.json), its own pause switch
// (salfa_settings.hayati_autopublish) and its own flags (item ids «hayati-…»). The daily Hayati routine reads them.
import { createClient } from "jsr:@supabase/supabase-js@2";

const BASE = "https://salfa-studio.vercel.app";
const ORIGINS = ["https://salfa-studio.vercel.app", "https://mjuma11m-sys.github.io"];
const admin = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

// "Log in with TikTok" session (same HMAC token salfa-tiktok issues): valid when it names the bound owner open_id.
const enc = new TextEncoder();
const b64u = (b: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
async function tiktokOwner(token: string): Promise<boolean> {
  const [body, sig, extra] = String(token || "").split(".");
  if (!body || !sig || extra !== undefined) return false;
  const key = await crypto.subtle.importKey("raw", enc.encode("salfa-session:" + (Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "")), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
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
  if (email === (Deno.env.get("OWNER_EMAIL") || "").trim().toLowerCase()) return true;
  const { data: row } = await admin.from("salfa_admin_emails").select("email").eq("email", email).maybeSingle();
  return !!row;
}

const YT_CHANNEL = "UCqVPWALNBj1ceZ8LdbKtQaw";
// Latest YouTube comment threads on the channel's videos, unanswered first (answered = the channel replied).
async function comments() {
  const key = (Deno.env.get("YOUTUBE_API_KEY") || "").trim();
  if (!key) {
    // no key on the server yet: show what the daily task saved (unanswered comments + suggested replies)
    const { data } = await admin.from("salfa_comment_drafts").select("comment_id, draft, status, video, text, author, published_at, url")
      .eq("status", "new").order("published_at", { ascending: false }).limit(50);
    const list = (data || []).map((x) => ({ id: x.comment_id, video: x.video || "", text: x.text || "", author: x.author || "",
      at: x.published_at, likes: 0, replies: 0, answered: false, url: x.url, draft: x.draft }));
    return { comments: list, unanswered: list.length, source: "daily" };
  }
  const yt = (path: string) => fetch(`https://www.googleapis.com/youtube/v3/${path}&key=${key}`).then((r) => r.json());
  const d = await yt(`commentThreads?part=snippet,replies&allThreadsRelatedToChannelId=${YT_CHANNEL}&maxResults=50&order=time&textFormat=plainText`);
  if (d.error) throw new Error(`YouTube: ${d.error.message}`);
  const items = (d.items || []).filter((t: any) => t.snippet.topLevelComment.snippet.authorChannelId?.value !== YT_CHANNEL);
  const ids = [...new Set(items.map((t: any) => t.snippet.videoId))];
  const titles: Record<string, string> = {};
  if (ids.length) for (const v of (await yt(`videos?part=snippet&id=${ids.join(",")}`)).items || []) titles[v.id] = v.snippet.title;
  const out = items.map((t: any) => {
    const c = t.snippet.topLevelComment.snippet;
    const answered = (t.replies?.comments || []).some((r: any) => r.snippet.authorChannelId?.value === YT_CHANNEL);
    return { id: t.id, video: titles[t.snippet.videoId] || t.snippet.videoId, text: String(c.textOriginal || "").slice(0, 400),
      author: String(c.authorDisplayName || "").slice(0, 60), at: c.publishedAt, likes: c.likeCount, replies: t.snippet.totalReplyCount,
      answered, url: `https://www.youtube.com/watch?v=${t.snippet.videoId}&lc=${t.id}` };
  });
  out.sort((a: any, b: any) => Number(a.answered) - Number(b.answered));
  // suggested replies written by the daily task (public.salfa_comment_drafts)
  const { data: drafts } = await admin.from("salfa_comment_drafts").select("comment_id, draft, status").in("comment_id", out.map((x: any) => x.id));
  const dm = new Map((drafts || []).map((x) => [x.comment_id, x]));
  for (const c of out) { const d0 = dm.get(c.id); if (d0 && d0.status === "new") c.draft = d0.draft; }
  return { comments: out, unanswered: out.filter((x: any) => !x.answered).length };
}

// DW-165: the «حياتي» queue for the studio tab
async function hayati() {
  const get = async (f: string, dflt: unknown) => { const r = await fetch(`${BASE}/data/${f}`, { cache: "no-store" }); return r.ok ? r.json() : dflt; };
  const [all, posted] = await Promise.all([
    get("hayati-queue.json", []) as Promise<{ id: string; title?: string; caption: string; media: string | null }[]>,
    get("hayati-posted.json", {}) as Promise<Record<string, string[]>>,
  ]);
  const { data: flags } = await admin.from("salfa_queue_flags").select("item_id, flag").like("item_id", "hayati-%");
  const { data: st } = await admin.from("salfa_settings").select("value").eq("key", "hayati_autopublish").maybeSingle();
  const fl = new Map((flags || []).map((x) => [x.item_id, x.flag]));
  const on = (id: string) => Object.fromEntries(["instagram", "tiktok", "youtube"].map((p) => [p, (posted[p] || []).includes(id)]));
  const pick = (x: typeof all[number]) => ({ id: x.id, title: x.title || "", caption: x.caption, media: x.media, flag: fl.get(x.id) || null, posted: on(x.id) });
  const isDone = (x: typeof all[number]) => Object.values(on(x.id)).some(Boolean);
  const waiting = all.filter((x) => !isDone(x));
  return {
    auto: (st?.value as { on?: boolean } | null)?.on !== false,
    time: "21:13 Asia/Bahrain", perDay: 1,
    next: [...waiting.filter((x) => fl.get(x.id) === "next"), ...waiting.filter((x) => !fl.get(x.id))].map(pick),
    skipped: waiting.filter((x) => fl.get(x.id) === "skip").map(pick),
    done: all.filter(isDone).map(pick),
  };
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
    if (!(await isAdmin(req))) return json({ error: "هالصفحة لصاحب القناة بس" }, 403);
    const body = await req.json().catch(() => ({}));
    if (body.action === "comments") return json(await comments());
    if (body.action === "hayati" || body.action === "hayati_flag" || body.action === "hayati_auto") {
      if (body.action === "hayati_auto") {
        if (typeof body.on !== "boolean") return json({ error: "bad input" }, 400);
        await admin.from("salfa_settings").upsert({ key: "hayati_autopublish", value: { on: body.on }, at: new Date().toISOString() });
      }
      if (body.action === "hayati_flag") {
        const id = String(body.id || "");
        if (!/^hayati-[a-z0-9-]{2,33}$/.test(id)) return json({ error: "bad id" }, 400);
        if (body.flag === "next" || body.flag === "skip") {
          if (body.flag === "next") await admin.from("salfa_queue_flags").delete().eq("flag", "next").like("item_id", "hayati-%");
          await admin.from("salfa_queue_flags").upsert({ item_id: id, flag: body.flag, due: null, at: new Date().toISOString() });
        } else {
          await admin.from("salfa_queue_flags").delete().eq("item_id", id);
        }
      }
      return json(await hayati());
    }
    if (body.action === "manual" || body.action === "manual_set") {
      // numbers typed in from TikTok Studio (until the TikTok stats API is connected)
      if (body.action === "manual_set") {
        const key = String(body.key || ""), value = Math.floor(Number(body.value));
        if (!["tiktok_followers", "tiktok_likes", "yt_watch_hours", "yt_shorts_views_90d"].includes(key) || !Number.isFinite(value) || value < 0 || value >= 1e9) return json({ error: "رقم مو صحيح" }, 400);
        const { error: ue } = await admin.from("salfa_manual_stats").upsert({ key, value, at: new Date().toISOString() });
        if (ue) throw new Error(ue.message); // never report «saved» when the row was refused
        await admin.from("salfa_live").delete().eq("id", 1); // refresh the live card on the next request
      }
      const { data } = await admin.from("salfa_manual_stats").select("key, value, at");
      return json({ manual: data || [] });
    }
    if (body.action === "photo_pick") {
      // the owner picks one of the licensed candidates listed in the site's hold.json; the server fetches it.
      // Only URLs from that list, only Wikimedia Commons / NASA image hosts, only images up to 15 MB (no open fetch).
      const id = String(body.id || ""), i = Number(body.i);
      if (!/^short-[0-9]{3}$/.test(id) || !Number.isInteger(i) || i < 0 || i > 9) return json({ error: "bad input" }, 400);
      const list: { id: string; candidates?: { image: string; credit: string }[] }[] =
        await fetch(`${BASE}/data/hold.json`, { cache: "no-store" }).then((x) => (x.ok ? x.json() : []));
      const c = list.find((h) => h.id === id)?.candidates?.[i];
      if (!c || !/^https:\/\/(upload\.wikimedia\.org\/wikipedia\/commons\/|images-assets\.nasa\.gov\/image\/)[^?#]+$/.test(c.image)) {
        return json({ error: "الصورة مو بالقائمة" }, 400);
      }
      const img = await fetch(c.image, { headers: { "User-Agent": "SalfaStudio/1.0 (salfa-studio.vercel.app)" }, redirect: "error" });
      const type = (img.headers.get("Content-Type") || "").split(";")[0];
      const ext = ({ "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" } as Record<string, string>)[type];
      if (!img.ok || !ext) return json({ error: `ما قدرت أجيب الصورة (${img.status})، جرّب بعد شوي` }, 502);
      const buf = new Uint8Array(await img.arrayBuffer());
      if (buf.byteLength > 15 * 1024 * 1024) return json({ error: "الصورة أكبر من 15 ميقا" }, 400);
      const path = `held/${id}/${crypto.randomUUID().slice(0, 18)}.${ext}`;
      const up = await admin.storage.from("salfa-photos").upload(path, buf, { contentType: type });
      if (up.error) throw new Error(up.error.message);
      const { error } = await admin.from("salfa_photo_uploads").insert({ item_id: id, path, credit: String(c.credit).slice(0, 120) });
      if (error) throw new Error(error.message);
      body.action = "held";
    }
    if (body.action === "held" || body.action === "photo_url" || body.action === "photo_done") {
      // shorts held for want of a real photo: the owner uploads his own (bucket salfa-photos, public read, signed upload only)
      if (body.action === "photo_url" || body.action === "photo_done") {
        const id = String(body.id || "");
        if (!/^short-[0-9]{3}$/.test(id)) return json({ error: "bad id" }, 400);
        if (body.action === "photo_url") {
          const ext = ({ "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" } as Record<string, string>)[String(body.type || "")];
          if (!ext) return json({ error: "الصورة لازم JPG أو PNG أو WEBP" }, 400);
          const path = `held/${id}/${crypto.randomUUID().slice(0, 18)}.${ext}`;
          const { data, error } = await admin.storage.from("salfa-photos").createSignedUploadUrl(path);
          if (error) throw new Error(error.message);
          return json({ path, url: data.signedUrl, token: data.token });
        }
        const path = String(body.path || ""), credit = String(body.credit || "").trim().slice(0, 120);
        if (!new RegExp(`^held/${id}/[a-z0-9-]{8,40}\\.(jpg|png|webp)$`).test(path) || credit.length < 2) return json({ error: "bad input" }, 400);
        const { error } = await admin.from("salfa_photo_uploads").insert({ item_id: id, path, credit });
        if (error) throw new Error(error.message);
      }
      const r0 = await fetch(`${BASE}/data/hold.json`, { cache: "no-store" });
      const held: { id: string; caption: string }[] = r0.ok ? await r0.json() : [];
      const { data: ups } = await admin.from("salfa_photo_uploads").select("item_id, path, credit, status, at").order("at", { ascending: false });
      const pub = (p0: string) => admin.storage.from("salfa-photos").getPublicUrl(p0).data.publicUrl;
      return json({ held: held.map((h) => ({ ...h, uploads: (ups || []).filter((u) => u.item_id === h.id).map((u) => ({ ...u, url: pub(u.path) })) })) });
    }
    if (body.action === "draft_set") {
      const id = String(body.id || ""), st = String(body.status || "");
      if (!/^[\w-]{5,80}$/.test(id) || !["used", "dismissed"].includes(st)) return json({ error: "bad input" }, 400);
      await admin.from("salfa_comment_drafts").update({ status: st }).eq("comment_id", id);
      return json({ ok: true });
    }
    if (body.action === "gen_list" || body.action === "gen_create" || body.action === "gen_cancel") {
      // «التوليد»: the owner requests a video/image; the daily task (Claude) renders it and fills result_url.
      // motion = our own engine (free), voice = the channel ElevenLabs voice; hf_image / hf_video spend the owner's Higgsfield credits (needs confirm).
      const MODELS: Record<string, string[]> = { hf_image: ["gpt_image_2_6", "nano_banana_flash"], hf_video: ["seedance_2_5", "kling3_0_turbo"] };
      if (body.action === "gen_create") {
        const kind = String(body.kind || ""), prompt = String(body.prompt || "").trim(), aspect = String(body.aspect || "9:16");
        if (!["motion", "voice", "hf_image", "hf_video"].includes(kind)) return json({ error: "bad kind" }, 400);
        if (prompt.length < 5 || prompt.length > 1500) return json({ error: "اكتب وصف من 5 لين 1500 حرف" }, 400);
        if (!["9:16", "16:9", "1:1"].includes(aspect)) return json({ error: "bad aspect" }, 400);
        let model: string | null = null;
        if (kind.startsWith("hf_")) {
          model = String(body.model || MODELS[kind][0]);
          if (!MODELS[kind].includes(model)) return json({ error: "bad model" }, 400);
          if (body.confirm !== true) return json({ error: "هالطلب يصرف من رصيد Higgsfield، أكّد أول" }, 400);
        }
        const { count } = await admin.from("salfa_gen_jobs").select("id", { count: "exact", head: true }).in("status", ["new", "running"]);
        if ((count || 0) >= 5) return json({ error: "فيه 5 طلبات تنتظر، استنى لين تخلص" }, 429);
        const { error } = await admin.from("salfa_gen_jobs").insert({ kind, prompt, aspect, model });
        if (error) throw new Error(error.message);
      }
      if (body.action === "gen_cancel") {
        const id = String(body.id || "");
        if (!/^[0-9a-f-]{36}$/.test(id)) return json({ error: "bad id" }, 400);
        await admin.from("salfa_gen_jobs").update({ status: "cancelled" }).eq("id", id).eq("status", "new");
      }
      const { data } = await admin.from("salfa_gen_jobs").select("id, kind, prompt, aspect, model, status, result_url, note, at, done_at").order("at", { ascending: false }).limit(20);
      return json({ jobs: data || [], models: MODELS });
    }
    if (body.action === "auto") {
      // owner switch: pause or resume the daily auto-publish (the daily task reads salfa_settings.autopublish)
      if (typeof body.on !== "boolean") return json({ error: "bad input" }, 400);
      await admin.from("salfa_settings").upsert({ key: "autopublish", value: { on: body.on }, at: new Date().toISOString() });
    }
    if (body.action === "flag") {
      const id = String(body.id || "");
      if (!/^[a-z0-9-]{3,40}$/.test(id)) return json({ error: "bad id" }, 400);
      if (body.flag === "next" || body.flag === "skip") {
        if (body.flag === "next") await admin.from("salfa_queue_flags").delete().eq("flag", "next").not("item_id", "like", "hayati-%"); // one pinned item at a time (the «حياتي» queue keeps its own)
        await admin.from("salfa_queue_flags").upsert({ item_id: id, flag: body.flag, due: null, at: new Date().toISOString() });
      } else if (body.flag === "date") {
        // publish on a chosen day (Asia/Bahrain), tomorrow .. +90 days, one short per day
        const due = String(body.due || "");
        const day = (d: Date) => new Date(d.getTime() + 3 * 3600e3).toISOString().slice(0, 10);
        const now = new Date(), min = day(new Date(now.getTime() + 864e5)), max = day(new Date(now.getTime() + 90 * 864e5));
        if (!/^\d{4}-\d{2}-\d{2}$/.test(due) || due < min || due > max) return json({ error: "اختار يوم من بكرة لين 90 يوم" }, 400);
        const { data: taken } = await admin.from("salfa_queue_flags").select("item_id").eq("flag", "date").eq("due", due).neq("item_id", id);
        if (taken && taken.length) return json({ error: `هاليوم محجوز لـ ${taken[0].item_id}` }, 409);
        await admin.from("salfa_queue_flags").upsert({ item_id: id, flag: "date", due, at: new Date().toISOString() });
      } else {
        await admin.from("salfa_queue_flags").delete().eq("item_id", id);
      }
    }
    const r = await fetch(`${BASE}/data/publish-queue.json`, { cache: "no-store" });
    if (!r.ok) throw new Error("publish queue not found on the site");
    const all: { id: string; caption: string; media: string | null; tiktok: boolean; youtube: boolean }[] = await r.json();
    const [{ data: posted }, { data: flags }] = await Promise.all([
      admin.from("salfa_tiktok_posts").select("item_id").eq("platform", "tiktok"),
      admin.from("salfa_queue_flags").select("item_id, flag, due"),
    ]);
    const { data: st } = await admin.from("salfa_settings").select("value").eq("key", "autopublish").maybeSingle();
    const dues = new Map((flags || []).filter((x) => x.flag === "date").map((x) => [x.item_id, x.due as string]));
    const done = new Set((posted || []).map((x) => x.item_id));
    const fl = new Map((flags || []).map((x) => [x.item_id, x.flag]));
    const waiting = all.filter((x) => !x.tiktok && !done.has(x.id) && x.media);
    const pinned = waiting.filter((x) => fl.get(x.id) === "next");
    const rest = waiting.filter((x) => !fl.get(x.id));
    const skipped = waiting.filter((x) => fl.get(x.id) === "skip");
    const pick = (x: typeof all[number], f: string | null) => ({ id: x.id, caption: x.caption, media: x.media, flag: f, due: dues.get(x.id) || null });
    const scheduled = waiting.filter((x) => fl.get(x.id) === "date").sort((a, b) => (dues.get(a.id)! < dues.get(b.id)! ? -1 : 1));
    return json({
      time: "11:47 + 20:43 Asia/Bahrain",
      perDay: 2,
      total: waiting.length,
      auto: (st?.value as { on?: boolean } | null)?.on !== false,
      scheduled: scheduled.map((x) => pick(x, "date")),
      next: [...pinned.map((x) => pick(x, "next")), ...rest.slice(0, 14 - pinned.length).map((x) => pick(x, null))],
      skipped: skipped.map((x) => pick(x, "skip")),
    });
  } catch (e) {
    return json({ error: (e as Error).message.slice(0, 200) }, 502);
  }
});
