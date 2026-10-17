const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const gbp = (n) => "£" + Number(n).toFixed(2);
const banner = (cls, html) => `<div class="banner ${cls}">${html}</div>`;
let META = null;

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail ? (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) : `HTTP ${res.status}`);
  return body;
}
const postJSON = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---------- storage: profile and list live on this device only ----------
const KEY_PROFILE = "nostobon.profile.v1", KEY_LIST = "nostobon.list.v1";
const KEY_SAVED = "nostobon.products.v1", KEY_SCAN_STORE = "nostobon.scanstore.v1";
const KEYS = [KEY_PROFILE, KEY_LIST, KEY_SAVED, KEY_SCAN_STORE];
const MEMORY = {};
let STORAGE_OK = true;
function load(key, fallback) {
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; }
  catch { STORAGE_OK = false; return MEMORY[key] ?? fallback; }
}
function save(key, value) {
  MEMORY[key] = value;
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { STORAGE_OK = false; }
}
function forget() {
  try { KEYS.forEach((k) => localStorage.removeItem(k)); } catch { /* nothing stored */ }
  KEYS.forEach((k) => delete MEMORY[k]);
}

const blankProfile = () => ({
  v: 1, created_at: null, updated_at: null,
  name: "", budget: null,
  location: null, mode: "walk", radius_km: 3,
  allergies: [], strict_traces: false, diets: [],
  loyalty: [], discounts: [],
  priority: "balance", max_shops: 2, avoid_chains: [],
});
let PROFILE = load(KEY_PROFILE, null);
let LIST = load(KEY_LIST, []);
const clone = (o) => JSON.parse(JSON.stringify(o));

// ---------- routing ----------
// "prices" is hidden for now: no nav link and not routed. Its code is kept below for later.
const VIEWS = ["setup", "list", "plan", "scan", "profile"];
function route() {
  let view = location.hash.replace(/^#\//, "") || "list";
  if (!VIEWS.includes(view)) view = "list";
  if (!PROFILE && view !== "setup") return (location.hash = "#/setup");
  if (PROFILE && view === "setup") return (location.hash = "#/list");
  if (view === "plan" && !LAST_PLAN) return (location.hash = "#/list");
  $$("[data-view]").forEach((s) => (s.hidden = s.dataset.view !== view));
  $("#top-nav").hidden = view === "setup";
  $$("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === view));
  ({ setup: renderSetup, list: renderList, plan: renderPlan, scan: renderScan, profile: renderProfile }[view])();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);

function renderAvatar() {
  const n = PROFILE?.name?.trim();
  $("#avatar").textContent = n ? n[0].toUpperCase() : "Me";
}

// ---------- profile sections, shared by setup and the profile page ----------
const MODES = { walk: "Walk", cycle: "Cycle", bus: "Bus", car: "Car" };
const RADII = [1.5, 3, 5];
const PRIORITIES = {
  save: ["Save the most", "Happy to visit more shops for a lower bill"],
  balance: ["Balanced", "Extra shops only when the saving is worth it"],
  time: ["Save time", "Fewest, closest shops"],
};
// options: object, or [value, label] pairs when order matters (numeric keys sort first in objects)
const seg = (field, options, current, num = false) => `<div class="seg" role="group">${(Array.isArray(options) ? options : Object.entries(options)).map(([v, label]) =>
  `<button type="button" data-single="${field}" data-value="${esc(v)}" ${num ? "data-num" : ""} aria-pressed="${String(v) === String(current)}">${esc(label)}</button>`).join("")}</div>`;
const chips = (field, options, current) => `<div class="toggles">${Object.entries(options).map(([v, label]) =>
  `<button type="button" class="toggle" data-array="${field}" data-value="${esc(v)}" aria-pressed="${current.includes(v)}">${esc(label)}</button>`).join("")}</div>`;

const SECTIONS = {
  about: {
    title: "About you", sub: "Only your first name, so we know what to call you. Nothing else is needed.",
    html: (d) => `<label>First name <span class="hint">optional</span><input data-field="name" value="${esc(d.name)}" autocomplete="given-name" maxlength="40"></label>
      <label>Weekly food budget <span class="hint">optional, shown against each plan</span>
        <div class="prefix"><span>£</span><input data-field="budget" data-num type="number" min="0" max="1000" step="1" inputmode="decimal" value="${d.budget ?? ""}" placeholder="e.g. 30"></div></label>`,
  },
  location: {
    title: "Where you shop from", sub: "Set once. We measure every trip from here.",
    html: (d) => `<div class="loc-status" id="loc-status">${locStatus(d)}</div>
      <div class="row">
        <label class="grow">Postcode <input id="loc-postcode" placeholder="SO17 1BJ" autocomplete="postal-code"></label>
        <button type="button" class="ghost" id="loc-find">Set</button>
      </div>
      <button type="button" class="ghost full" id="loc-device">Use my current location</button>
      <label>How you get there</label>${seg("mode", MODES, d.mode)}
      <label>How far you will go</label>${seg("radius_km", RADII.map((r) => [r, r + " km"]), d.radius_km, true)}`,
    bind: bindLocation,
    valid: (d) => d.location ? null : "Set your postcode or use your location first.",
  },
  food: {
    title: "Allergies and diet", sub: "Products that clash are left out of every plan.",
    html: (d) => `<label>Allergies and intolerances</label>${chips("allergies", META.allergens, d.allergies)}
      <label class="check"><input type="checkbox" data-bool="strict_traces" ${d.strict_traces ? "checked" : ""}> Also leave out "may contain" products <span class="hint">for severe allergies</span></label>
      <label>Diet</label>${chips("diets", META.diets, d.diets)}
      <p class="note">We filter on typical ingredients for each product type, not the pack in front of you. Always check the label.</p>`,
  },
  cards: {
    title: "Loyalty cards and discounts", sub: "Plans use member prices only for cards you have.",
    html: (d) => `<label>Cards you have</label>${chips("loyalty", Object.fromEntries(Object.entries(META.loyalty_schemes).map(([c, s]) => [s, `${s} · ${c}`])), d.loyalty)}
      <p class="note">We never ask for card numbers. Ticking a card only tells the planner to use its member prices.</p>
      <label>Other discounts <span class="hint">student, staff or membership. You enter them, we do not verify them</span></label>
      <div id="discounts"></div>
      <button type="button" class="ghost small" id="add-discount">Add a discount</button>`,
    bind: bindDiscounts,
  },
  shopping: {
    title: "How you like to shop", sub: "Sets where the price and time slider starts. You can move it on every plan.",
    html: (d) => `<div class="choices">${Object.entries(PRIORITIES).map(([v, [t, s]]) =>
        `<button type="button" class="choice" data-single="priority" data-value="${v}" aria-pressed="${d.priority === v}"><strong>${t}</strong><span>${s}</span></button>`).join("")}</div>
      <label>Most shops in one trip</label>${seg("max_shops", { 1: "1", 2: "2", 3: "3" }, d.max_shops, true)}
      <label>Shops you never want to go to</label>${chips("avoid_chains", Object.fromEntries(META.chains.map((c) => [c, c])), d.avoid_chains)}`,
  },
};

function locStatus(d) {
  if (!d.location) return `<span class="muted">Not set yet.</span>`;
  return `<span class="pin"></span><strong>${esc(d.location.label)}</strong> <span class="muted">set ${esc(d.location.set_at?.slice(0, 10) || "")}</span>
    ${d.location.warning ? banner("warn", esc(d.location.warning)) : ""}`;
}

function bindLocation(root, d, changed) {
  const status = $("#loc-status", root);
  const setLoc = async (params, btn) => {
    const old = btn.textContent; btn.disabled = true; btn.textContent = "Finding...";
    try {
      const r = await api("/api/geocode?" + new URLSearchParams(params));
      d.location = { label: r.label, lat: r.lat, lon: r.lon, warning: r.warning, set_at: new Date().toISOString() };
      status.innerHTML = locStatus(d); changed();
    } catch (err) { status.innerHTML = locStatus(d) + banner("bad", esc(err.message)); }
    finally { btn.disabled = false; btn.textContent = old; }
  };
  $("#loc-find", root).onclick = (e) => {
    const pc = $("#loc-postcode", root).value.trim();
    if (!pc) return (status.innerHTML = locStatus(d) + banner("bad", "Type a postcode first."));
    setLoc({ postcode: pc }, e.target);
  };
  $("#loc-postcode", root).addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); $("#loc-find", root).click(); } });
  $("#loc-device", root).onclick = (e) => {
    if (!navigator.geolocation) return (status.innerHTML = locStatus(d) + banner("bad", "This browser cannot share your location. Type a postcode."));
    const btn = e.target; btn.disabled = true;
    navigator.geolocation.getCurrentPosition(
      (p) => { btn.disabled = false; setLoc({ lat: p.coords.latitude, lon: p.coords.longitude }, btn); },
      (err) => { btn.disabled = false; status.innerHTML = locStatus(d) + banner("bad", `Could not get your location (${esc(err.message)}). Type a postcode.`); },
      { timeout: 10000 });
  };
}

function bindDiscounts(root, d, changed) {
  const box = $("#discounts", root);
  const draw = () => {
    box.innerHTML = d.discounts.length ? d.discounts.map((x, i) => `<div class="discount-row" data-i="${i}">
        <input class="d-label" placeholder="Name, e.g. Co-op member" value="${esc(x.label)}" maxlength="40" aria-label="Discount name">
        <select class="d-chain" aria-label="Shop">${META.chains.map((c) => `<option ${c === x.chain ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
        <div class="suffix"><input class="d-pct" type="number" min="1" max="50" value="${x.pct}" aria-label="Percent off"><span>%</span></div>
        <button type="button" class="icon-btn d-remove" aria-label="Remove discount">×</button></div>`).join("")
      : `<p class="muted small-print">None added.</p>`;
  };
  box.addEventListener("input", (e) => {
    const row = e.target.closest(".discount-row"); if (!row) return;
    const x = d.discounts[row.dataset.i];
    if (e.target.classList.contains("d-label")) x.label = e.target.value;
    if (e.target.classList.contains("d-chain")) x.chain = e.target.value;
    if (e.target.classList.contains("d-pct")) x.pct = Math.max(1, Math.min(50, Number(e.target.value) || 0));
    changed();
  });
  box.addEventListener("click", (e) => {
    if (!e.target.classList.contains("d-remove")) return;
    d.discounts.splice(e.target.closest(".discount-row").dataset.i, 1); draw(); changed();
  });
  $("#add-discount", root).onclick = () => { d.discounts.push({ label: "", chain: META.chains[0], pct: 10 }); draw(); changed(); };
  draw();
}

// generic controls: data-field (text/number), data-bool (checkbox), data-single (segmented), data-array (toggles)
function bindControls(root, d, changed) {
  root.addEventListener("click", (e) => {
    const t = e.target.closest("[data-array],[data-single]");
    if (!t) return;
    if (t.dataset.array) {
      const arr = d[t.dataset.array], v = t.dataset.value, i = arr.indexOf(v);
      if (i >= 0) arr.splice(i, 1); else arr.push(v);
      t.setAttribute("aria-pressed", String(i < 0));
    } else {
      const f = t.dataset.single;
      d[f] = "num" in t.dataset ? Number(t.dataset.value) : t.dataset.value;
      $$(`[data-single="${f}"]`, root).forEach((b) => b.setAttribute("aria-pressed", String(b === t)));
    }
    changed();
  });
  root.addEventListener("input", (e) => {
    const t = e.target;
    if (t.dataset.field) d[t.dataset.field] = "num" in t.dataset ? (t.value === "" ? null : Number(t.value)) : t.value;
    else if (t.dataset.bool) d[t.dataset.bool] = t.checked;
    else return;
    changed();
  });
}

function mountSection(el, key, d, changed) {
  const s = SECTIONS[key];
  el.innerHTML = s.html(d);
  bindControls(el, d, changed);
  s.bind?.(el, d, changed);
}

// ---------- setup: one time, on first visit ----------
const STEPS = ["about", "location", "food", "cards", "shopping"];
let SETUP = { i: 0, draft: blankProfile() };

function renderSetup() {
  const { i, draft } = SETUP, key = STEPS[i], s = SECTIONS[key];
  $("#setup-progress").innerHTML = STEPS.map((_, j) => `<span class="${j <= i ? "on" : ""}"></span>`).join("");
  const box = $("#setup-step");
  box.innerHTML = `${i === 0 ? `<p class="eyebrow">Welcome to Nostobon</p>` : `<p class="eyebrow">Step ${i + 1} of ${STEPS.length}</p>`}
    <h1>${esc(s.title)}</h1><p class="lead">${esc(s.sub)}</p>
    ${i === 0 ? `<p class="note">Set this up once. Your profile stays on this device and is never stored on our server.
      Each plan sends only what it needs: your list, location, cards and food needs. Your list is read by Anthropic's Claude.</p>` : ""}
    <div class="card" id="setup-body"></div>
    <div id="setup-error"></div>
    <div class="steps-nav">
      ${i > 0 ? `<button type="button" class="ghost" id="setup-back">Back</button>` : "<span></span>"}
      <button type="button" class="primary" id="setup-next">${i === STEPS.length - 1 ? "Finish" : "Next"}</button>
    </div>`;
  mountSection($("#setup-body"), key, draft, () => ($("#setup-error").innerHTML = ""));
  $("#setup-back")?.addEventListener("click", () => { SETUP.i--; renderSetup(); });
  $("#setup-next").onclick = () => {
    const problem = s.valid?.(draft);
    if (problem) return ($("#setup-error").innerHTML = banner("bad", esc(problem)));
    if (i < STEPS.length - 1) { SETUP.i++; renderSetup(); window.scrollTo(0, 0); return; }
    draft.created_at = draft.updated_at = new Date().toISOString();
    PROFILE = draft; save(KEY_PROFILE, PROFILE); renderAvatar();
    location.hash = "#/list";
  };
}

// ---------- profile page ----------
function renderProfile() {
  const draft = clone(PROFILE);
  const out = $("#profile-out");
  const initial = draft.name?.trim()?.[0]?.toUpperCase() || "Me";
  out.innerHTML = `<div class="profile-head"><div class="avatar big">${esc(initial)}</div>
      <div><h1>${esc(draft.name || "Your profile")}</h1><p class="muted">Set up ${esc(draft.created_at?.slice(0, 10) || "")}. Stored on this device only.</p></div></div>
    ${STEPS.map((k) => `<div class="card"><h2>${esc(SECTIONS[k].title)}</h2><p class="muted sub">${esc(SECTIONS[k].sub)}</p><div data-section="${k}"></div></div>`).join("")}
    <div class="card"><h2>Your data</h2>
      <p class="muted sub">Your profile, list and saved products are kept in this browser's storage. Our server keeps nothing about you.
        Shelf prices you save are stored with the shop and date only, never with your name or the photo.</p>
      <div class="row"><button type="button" class="ghost" id="export">Download my data</button>
        <button type="button" class="ghost danger" id="wipe">Delete everything</button></div></div>
    <div class="savebar" id="savebar" hidden><span>Unsaved changes</span>
      <button type="button" class="ghost" id="discard">Discard</button><button type="button" class="primary" id="save">Save</button></div>`;
  const bar = $("#savebar");
  const changed = () => (bar.hidden = false);
  $$("[data-section]", out).forEach((el) => mountSection(el, el.dataset.section, draft, changed));
  $("#discard").onclick = renderProfile;
  $("#save").onclick = () => {
    const problem = STEPS.map((k) => SECTIONS[k].valid?.(draft)).find(Boolean);
    if (problem) return alert(problem);
    draft.updated_at = new Date().toISOString();
    PROFILE = draft; save(KEY_PROFILE, PROFILE); renderAvatar(); LAST_PLAN = null;
    bar.hidden = true;
    out.insertAdjacentHTML("afterbegin", banner("ok", "Saved. New plans use these settings."));
    setTimeout(() => out.querySelector(".banner.ok")?.remove(), 2500);
  };
  $("#export").onclick = () => {
    const blob = new Blob([JSON.stringify({ profile: PROFILE, list: LIST, saved_products: load(KEY_SAVED, []) }, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "nostobon-my-data.json" });
    a.click(); URL.revokeObjectURL(a.href);
  };
  $("#wipe").onclick = () => {
    if (!confirm("Delete your profile, list and saved products from this device? You will set up again.")) return;
    forget(); PROFILE = null; LIST = []; LAST_PLAN = null; SETUP = { i: 0, draft: blankProfile() };
    location.hash = "#/setup";
  };
}

// ---------- list: the home screen ----------
function greeting() {
  const h = new Date().getHours();
  const part = h < 5 ? "Evening" : h < 12 ? "Morning" : h < 18 ? "Afternoon" : "Evening";
  return PROFILE?.name?.trim() ? `${part}, ${PROFILE.name.trim()}` : `Good ${part.toLowerCase()}`;
}

function renderList() {
  $("#greeting").textContent = greeting();
  $("#items").innerHTML = LIST.map((t, i) => `<li><span>${esc(t)}</span><button type="button" class="icon-btn" data-remove="${i}" aria-label="Remove ${esc(t)}">×</button></li>`).join("");
  $("#items-empty").hidden = LIST.length > 0;
  $("#list-actions").hidden = LIST.length === 0;
  const p = PROFILE;
  const bits = [`From ${p.location.label}`, MODES[p.mode].toLowerCase(), `within ${p.radius_km} km`];
  if (p.loyalty.length) bits.push(p.loyalty.join(", "));
  if (p.allergies.length + p.diets.length) bits.push(`${p.allergies.length + p.diets.length} food need${p.allergies.length + p.diets.length > 1 ? "s" : ""}`);
  $("#context").textContent = bits.join(" · ") + ".";
}

$("#add-item").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = $("#item-input");
  const parts = input.value.split(/[,\n;]+/).map((s) => s.trim()).filter(Boolean);
  if (!parts.length) return;
  LIST.push(...parts); save(KEY_LIST, LIST);
  input.value = ""; renderList(); input.focus();
});
$("#item-input").addEventListener("paste", (e) => {
  const text = e.clipboardData.getData("text");
  if (!/[\n,;]/.test(text)) return;
  e.preventDefault();
  $("#item-input").value = text; $("#add-item").requestSubmit();
});
$("#items").addEventListener("click", (e) => {
  const i = e.target.dataset.remove; if (i == null) return;
  LIST.splice(Number(i), 1); save(KEY_LIST, LIST); renderList();
});
$("#clear-list").onclick = () => { LIST = []; save(KEY_LIST, LIST); renderList(); };

// ---------- plan ----------
let LAST_PLAN = null;   // { result, index }
let MAP = null, MAP_LAYER = null;

$("#go").addEventListener("click", async (e) => {
  const btn = e.target; btn.disabled = true; btn.textContent = "Reading your list...";
  const p = PROFILE;
  const discounts = {};
  p.discounts.forEach((d) => { if (d.chain && d.pct) discounts[d.chain] = Math.max(discounts[d.chain] || 0, d.pct); });
  try {
    const result = await postJSON("/api/plan", {
      list_text: LIST.join("\n"), lat: p.location.lat, lon: p.location.lon,
      mode: p.mode, radius_km: p.radius_km, max_shops: p.max_shops,
      loyalty: p.loyalty, discounts, allergies: p.allergies, diets: p.diets,
      strict_traces: p.strict_traces, avoid_chains: p.avoid_chains,
    });
    LAST_PLAN = { result, index: defaultIndex(result.plan.options || []) };
    location.hash = "#/plan";
  } catch (err) {
    $$("#list-actions > .banner").forEach((b) => b.remove());
    $("#list-actions").insertAdjacentHTML("afterbegin", banner("bad", esc(err.message)));
  } finally { btn.disabled = false; btn.textContent = "Find my shops"; }
});

// where the slider starts. Options run cheapest first, quickest last.
function defaultIndex(options) {
  if (!options.length) return 0;
  if (PROFILE.priority === "save") return 0;
  if (PROFILE.priority === "time") return options.length - 1;
  const cost = (o) => o.basket + (10 * o.minutes) / 60;   // balanced: an extra £1 saved must cost under 6 minutes
  return options.reduce((best, o, i) => (cost(o) < cost(options[best]) ? i : best), 0);
}

function itemChip(i) {
  const q = i.quantity > 1 ? i.quantity + " x " : "";
  if (i.status === "matched") {
    const brand = i.brand ? ` (${esc(i.brand)} only)` : "";
    const removed = i.diet_removed?.length ? ` <span class="hint">${i.diet_removed.length} option${i.diet_removed.length > 1 ? "s" : ""} left out for your profile</span>` : "";
    return `<span class="chip ok" title="${esc([i.note, ...(i.diet_removed || [])].join("\n"))}">${esc(q + i.input_text)} → ${esc(i.generic)}${brand}${removed}</span>`;
  }
  if (i.status === "ambiguous")
    return `<span class="chip warn" title="${esc(i.note)}">${esc(i.input_text)}: which one? ${esc(i.options.join(", "))}</span>`;
  if (i.status === "blocked")
    return `<span class="chip bad" title="${esc(i.note)}">${esc(i.input_text)}: ${esc(i.diet_removed.map((r) => r.split(": ")[1]).join("; "))}</span>`;
  return `<span class="chip bad" title="${esc(i.note)}">${esc(i.input_text)}: not tracked yet</span>`;
}

function sourceTag(l) {
  const age = l.age_days === 0 ? "today" : l.age_days + "d ago";
  const t = [];
  if (l.source === "online_2024")
    t.push(`<span class="pill off" title="${esc(l.chain_name)}: ${esc(l.chain)} website price on ${esc(l.observed_on)}, from the Kaggle supermarket set. Starting price until a shopper scans it. Prices have risen since and shops can differ from the website.">online price, ${esc(l.observed_on.slice(0, 7))}</span>`);
  else if (l.source === "openfoodfacts")
    t.push(`<span class="pill off" title="Open Food Facts Open Prices, seen at ${esc(l.borrowed_from)}${l.other_format ? ", a different store format" : ""}. Temporary until shoppers scan this shop.">Open Food Facts · ${esc(age)}</span>`);
  else if (l.source === "shopper_other_branch")
    t.push(`<span class="pill borrow" title="Price from ${esc(l.borrowed_from)}. No price from this branch yet.">${l.method === "scan" ? "shelf scan" : "shelf label"}, other branch · ${esc(age)}</span>`);
  else t.push(`<span class="pill seen" title="${l.n_obs} shopper prices for this product here">shelf ${l.method === "scan" ? "scan" : "label"} · ${esc(age)}</span>`);
  if (l.synthetic) t.push(`<span class="pill synth">synthetic</span>`);
  if (l.stale) t.push(`<span class="pill stale">over 30 days old</span>`);
  if (l.valid_until && !l.offer_ended && l.applied.length) t.push(`<span class="pill seen">offer ends ${esc(l.valid_until)}</span>`);
  if (l.offer_ended) t.push(`<span class="pill stale" title="The label said the offer ended ${esc(l.valid_until)}, so the price without it is used.">offer ended ${esc(l.valid_until)}</span>`);
  l.warnings.forEach((w) => t.push(`<span class="pill stale">${esc(w)}</span>`));
  return t.join(" ");
}

function renderPlan() {
  const { result: r } = LAST_PLAN;
  const out = $("#plan-out");
  const p = r.plan;
  const problems = r.items.filter((i) => i.status !== "matched");
  let html = r.warnings.map((w) => banner("warn", esc(w))).join("");
  if (problems.length) html += banner("warn", `${problems.length} item${problems.length > 1 ? "s" : ""} not planned: ${esc(problems.map((i) => i.input_text).join(", "))}. Details below.`);
  if (p.error) {
    out.innerHTML = html + banner("bad", esc(p.error)) + understood(r);
    return;
  }
  const n = p.options.length;
  html += `<div class="card hero">
      <div id="hero-numbers"></div>
      ${n > 1 ? `<div class="slider">
        <input type="range" id="tradeoff" min="0" max="${n - 1}" step="1" value="${LAST_PLAN.index}" aria-label="Trade price against time">
        <div class="ticks">${p.options.map(() => "<span></span>").join("")}</div>
        <div class="ends"><span>Lowest price</span><span>Least time</span></div>
      </div>` : `<p class="muted small-print">Cheapest and quickest are the same route here, so there is nothing to trade off.</p>`}
      <div id="hero-compare" class="compare-line"></div>
    </div>
    <div class="card"><div id="map" class="map"></div><ol id="route" class="route"></ol></div>
    <div id="basket"></div>
    ${understood(r)}
    <p class="small-print">Compared ${p.routes_compared} routes over the ${p.candidates_considered} nearest shops with prices, of ${p.shops_in_radius} in range${p.shops_avoided ? ` (${p.shops_avoided} you avoid)` : ""}.
      Times assume ${p.assumptions.speed_kmh} km/h, street distance ${p.assumptions.road_factor} x straight line and ${p.assumptions.minutes_per_extra_shop} min in each extra shop.
      Shopper prices older than ${p.assumptions.max_price_age_days} days and Open Food Facts prices older than ${p.assumptions.max_reference_age_days} days are ignored.
      Where no shopper has priced a product, the chain's online price from ${esc(META.product_index?.prices_from || "2024")} to ${esc(META.product_index?.prices_to || "")} is used (Kaggle supermarket set). Shops may have changed prices since.</p>`;
  out.innerHTML = html;
  $("#tradeoff")?.addEventListener("input", (e) => { LAST_PLAN.index = Number(e.target.value); renderOption(); });
  initMap();
  renderOption();
}

function understood(r) {
  return `<div class="card"><h2>How we read your list <span class="hint">${r.matcher === "ai" ? "by AI" : "by the baseline matcher, no AI"}</span></h2>
    <div class="chips">${r.items.map(itemChip).join("")}</div></div>`;
}

function renderOption() {
  const p = LAST_PLAN.result.plan, opts = p.options, i = LAST_PLAN.index, o = opts[i];
  const cheapest = opts[0], quickest = opts[opts.length - 1];
  const budget = PROFILE.budget;
  $("#hero-numbers").innerHTML = `<div class="big">${gbp(o.basket)}</div>
    <div class="hero-sub">${o.minutes} min round trip · ${o.shops.length} shop${o.shops.length > 1 ? "s" : ""} · ${o.km} km</div>
    ${budget ? `<div class="budget ${o.basket <= budget ? "under" : "over"}">${o.basket <= budget ? gbp(budget - o.basket) + " under" : gbp(o.basket - budget) + " over"} your ${gbp(budget)} weekly budget</div>` : ""}`;
  let cmp = "";
  if (opts.length > 1) {
    if (i === 0) cmp = `Cheapest route. ${gbp(quickest.basket - o.basket)} less than the quickest, for ${o.minutes - quickest.minutes} more minutes.`;
    else if (i === opts.length - 1) cmp = `Quickest route. ${gbp(o.basket - cheapest.basket)} more than the cheapest, ${cheapest.minutes - o.minutes} minutes saved.`;
    else cmp = `${gbp(o.basket - cheapest.basket)} more than the cheapest, ${cheapest.minutes - o.minutes} min quicker. ${gbp(quickest.basket - o.basket)} less than the quickest.`;
  }
  $("#hero-compare").textContent = cmp;
  $("#route").innerHTML = `<li class="home">Home <span class="muted">${esc(PROFILE.location.label)}</span></li>` +
    o.shops.map((s, k) => `<li><span class="num">${k + 1}</span>${esc(s.name)} <span class="muted">${s.km_from_home} km from home${s.address ? ", " + esc(s.address) : ""}</span></li>`).join("") +
    `<li class="home">Back home</li>`;
  const byShop = o.shops.map((s, k) => {
    const lines = o.lines.filter((l) => l.store_id === s.id);
    const sub = lines.reduce((t, l) => t + l.line_total, 0);
    return `<div class="card shop"><div class="shop-head"><span class="num">${k + 1}</span><h2>${esc(s.name)}</h2><strong>${gbp(sub)}</strong></div>
      <ul class="lines">${lines.map((l) => `<li>
        <div class="line-main"><span>${esc(l.quantity > 1 ? l.quantity + " x " : "")}${esc(l.item)}</span>
          <span class="price">${l.applied.length ? `<s class="muted">${gbp(l.shelf_price * l.quantity)}</s> ` : ""}${gbp(l.line_total)}</span></div>
        <div class="line-sub muted">${esc(l.product_name)}${l.applied.length ? " · " + esc(l.applied.join(", ")) : ""}</div>
        <div class="line-tags">${sourceTag(l)}</div></li>`).join("")}</ul></div>`;
  }).join("");
  $("#basket").innerHTML = (o.missing.length ? banner("warn", "No price nearby for: " + esc(o.missing.join(", "))) : "") + byShop;
  drawMap(o);
}

function initMap() {
  MAP?.remove();
  MAP = null;
  if (!window.L) { $("#map").innerHTML = `<p class="muted small-print">Map unavailable (could not load map library). The route is listed below.</p>`; return; }
  MAP = L.map("map", { zoomControl: false, attributionControl: true, scrollWheelZoom: false });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap contributors" }).addTo(MAP);
  MAP_LAYER = L.layerGroup().addTo(MAP);
}

function drawMap(o) {
  if (!MAP) return;
  MAP_LAYER.clearLayers();
  const home = [PROFILE.location.lat, PROFILE.location.lon];
  const pts = [home, ...o.shops.map((s) => [s.lat, s.lon]), home];
  L.polyline(pts, { className: "route-line", weight: 4, dashArray: "6 8" }).addTo(MAP_LAYER);
  L.marker(home, { icon: L.divIcon({ className: "", html: `<div class="mk home-mk">H</div>`, iconSize: [28, 28], iconAnchor: [14, 14] }) }).addTo(MAP_LAYER);
  o.shops.forEach((s, k) => L.marker([s.lat, s.lon], { icon: L.divIcon({ className: "", html: `<div class="mk">${k + 1}</div>`, iconSize: [28, 28], iconAnchor: [14, 14] }) })
    .bindTooltip(esc(s.name)).addTo(MAP_LAYER));
  MAP.fitBounds(L.latLngBounds(pts).pad(0.25), { animate: false });
}

// ---------- scan: barcode, check the product, shelf price ----------
// Saved products and the last shop live on this device only, like the profile.
const ZXING = { src: "https://unpkg.com/@zxing/library@0.21.3/umd/index.min.js",
  integrity: "sha384-BzBxP10ZE72aitqj5UMmUsbKFliP/DZqA8Wq+BNNhlIJDGoEd1tpkMYXOg9+n6sB" };
const FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e"];
let CAM = null;    // { stream, timer, reader } while the camera is on
let ITEM = null;   // product on the scan card

const kmBetween = (a, b) => {
  const r = Math.PI / 180, dLat = (b.lat - a.lat) * r, dLon = (b.lon - a.lon) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(h));
};
const scanStore = () => META.stores.find((s) => s.id === $("#scan-store").value);

function renderScan() {
  const here = PROFILE.location;
  const stores = META.stores.map((s) => ({ ...s, km: here ? kmBetween(here, s) : null }))
    .sort((a, b) => (a.km ?? 0) - (b.km ?? 0) || a.name.localeCompare(b.name));
  const last = load(KEY_SCAN_STORE, null);
  $("#scan-store").innerHTML = `<option value="">Pick the shop</option>` + stores.map((s) =>
    `<option value="${esc(s.id)}" ${s.id === last ? "selected" : ""}>${esc(s.name)}${s.km != null ? ` · ${s.km.toFixed(1)} km` : ""}${s.address ? " - " + esc(s.address) : ""}</option>`).join("");
  renderSaved();
}
$("#scan-store").addEventListener("change", (e) => {
  save(KEY_SCAN_STORE, e.target.value);
  if (ITEM) renderItem();
  if (LABEL && !LABEL.repeat) $("#scan-out").innerHTML = banner("warn", "Shop changed. Products differ by chain, so take the label photo again.");
  if (LABEL && !LABEL.repeat) LABEL = null;
});

function loadScript({ src, integrity }) {
  return new Promise((ok, fail) => {
    const s = Object.assign(document.createElement("script"), { src, integrity, crossOrigin: "anonymous" });
    s.onload = ok; s.onerror = () => fail(new Error("Could not load the barcode reader. Check the connection, or type the digits."));
    document.head.append(s);
  });
}

async function startCamera() {
  const msg = $("#scan-msg");
  msg.innerHTML = "";
  if (!navigator.mediaDevices?.getUserMedia)
    return (msg.innerHTML = banner("bad", "This browser cannot use the camera. Type the digits under the barcode."));
  const video = $("#scan-video");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
    CAM = { stream };
    video.srcObject = stream;
    await video.play();
    $("#scanner").hidden = false; $("#scan-start").hidden = true;
    const supported = "BarcodeDetector" in window ? await BarcodeDetector.getSupportedFormats() : [];
    const formats = FORMATS.filter((f) => supported.includes(f));
    if (formats.length) {  // built-in reader (Chrome on Android), else ZXing
      const detector = new BarcodeDetector({ formats });
      const tick = async () => {
        if (!CAM) return;
        try { const [hit] = await detector.detect(video); if (hit) return gotCode(hit.rawValue); } catch { /* frame not ready */ }
        CAM.timer = setTimeout(tick, 150);
      };
      tick();
    } else {
      if (!window.ZXing) await loadScript(ZXING);
      const Z = window.ZXing;
      const hints = new Map([[Z.DecodeHintType.POSSIBLE_FORMATS, [Z.BarcodeFormat.EAN_13, Z.BarcodeFormat.EAN_8, Z.BarcodeFormat.UPC_A, Z.BarcodeFormat.UPC_E]]]);
      CAM.reader = new Z.BrowserMultiFormatReader(hints);
      CAM.reader.decodeFromStream(stream, video, (result) => { if (result && CAM) gotCode(result.getText()); });
    }
  } catch (err) {
    stopCamera();
    const why = err.name === "NotAllowedError" ? "Camera access is blocked. Allow it in settings, or type the digits."
      : err.name === "NotFoundError" ? "No camera found. Type the digits under the barcode." : err.message;
    msg.innerHTML = banner("bad", esc(why));
  }
}

function stopCamera() {
  if (!CAM) return;
  clearTimeout(CAM.timer);
  CAM.reader?.reset();
  CAM.stream?.getTracks().forEach((t) => t.stop());
  CAM = null;
  $("#scan-video").srcObject = null;
  $("#scanner").hidden = true; $("#scan-start").hidden = false;
}
$("#scan-start").addEventListener("click", startCamera);
$("#scan-stop").addEventListener("click", stopCamera);
window.addEventListener("hashchange", () => { if (location.hash !== "#/scan") stopCamera(); });

function gotCode(code) {
  stopCamera();
  navigator.vibrate?.(60);
  $("#scan-code").value = code;
  lookUp(code);
}
$("#scan-manual").addEventListener("submit", (e) => { e.preventDefault(); const c = $("#scan-code").value.trim(); if (c) lookUp(c); });

async function lookUp(code) {
  const out = $("#scan-out");
  LABEL = null;
  out.innerHTML = `<div class="card muted">Looking up ${esc(code)}...</div>`;
  try {
    const r = await api("/api/barcode/" + encodeURIComponent(code));
    if (r.status === "invalid") { ITEM = null; return (out.innerHTML = banner("bad", esc(r.note))); }
    const saved = load(KEY_SAVED, []).find((p) => p.code === r.code);
    // A product you confirmed before needs no second check
    ITEM = { ...r, step: saved ? "price" : r.status === "found" ? "confirm" : "name", typed: saved?.typed ?? null,
             name: saved?.typed ? saved.name : r.name };
    renderItem();
  } catch (err) { ITEM = null; out.innerHTML = banner("bad", esc(err.message)); }
}

function itemSource(r) {
  if (!r.source || r.typed) return "";
  const when = r.source.live ? "looked up just now" : `from our copy, fetched ${esc(r.source.fetched_at.slice(0, 10))}`;
  return `<p class="small-print">Name and photo: <a href="${esc(r.source.url)}" target="_blank" rel="noopener">Open Food Facts</a> (ODbL), ${when}.
    ${r.source.note ? esc(r.source.note) : ""}</p>`;
}

function renderItem() {
  const r = ITEM, store = scanStore(), out = $("#scan-out");
  const scheme = store && META.loyalty_schemes[store.chain];
  const pills = [];
  if (r.own_label_of) pills.push(`<span class="pill seen">${esc(r.own_label_of)} own label</span>`);
  const by = { ai: "matched by AI", rules: "matched by simple rules", shopper: "confirmed by a shopper" }[r.match?.by] || "";
  if (r.product_id && r.class_ok !== false) pills.push(`<span class="pill ok-pill" title="${esc(by)}">compared as: ${esc(r.product_name)}</span>`);
  else if (r.match?.status === "new" && r.class_ok !== false) pills.push(`<span class="pill seen" title="${esc(by)}">new to us</span>`);
  else if (r.status === "found") pills.push(`<span class="pill stale">not compared yet</span>`);
  const mismatch = store && r.own_label_of && r.own_label_of !== store.chain
    ? banner("warn", `This is ${esc(r.own_label_of)} own label, but the shop picked is ${esc(store.chain)}. Check the shop.`) : "";
  const head = r.status === "found" && !r.typed ? `<div class="product">
      ${r.image_url ? `<img src="${esc(r.image_url)}" alt="" loading="lazy">` : `<div class="noimg">no photo</div>`}
      <div><strong>${esc(r.name)}</strong>
        <div class="muted">${esc([r.brand, r.quantity].filter(Boolean).join(" · ") || "brand and size unknown")}</div>
        <div class="line-tags">${pills.join(" ")}</div></div></div>`
    : r.step === "name" && r.status !== "found" ? banner("warn", esc(r.note)) : "";
  let body = "";
  if (r.step === "confirm") body = `<p><strong>Is this the product in your hand?</strong></p>
      <div class="row"><button type="button" class="primary" id="item-yes">Yes, that is it</button>
        <button type="button" class="ghost" id="item-no">No, it is wrong</button></div>`;
  else if (r.step === "name") body = `<label>What is it? <span class="hint">name, size and brand from the pack</span>
        <input id="item-name" maxlength="120" value="${esc(r.typed ? r.name : "")}" placeholder="e.g. Tesco fusilli 500g"></label>
      <button type="button" class="primary" id="item-named">Next</button>`;
  else body = `${r.status === "found" && !r.typed ? "" : `<p><strong>${esc(r.name)}</strong> <span class="muted">${esc(r.code)}${r.typed ? ", name typed by you" : ""}</span></p>`}
      <div class="row prices-row">
        <label class="grow">Shelf price <div class="prefix"><span>£</span><input id="item-price" type="number" min="0.01" max="500" step="0.01" inputmode="decimal"></div></label>
        ${scheme ? `<label class="grow">${esc(scheme)} price <span class="hint">if the label shows one</span>
          <div class="prefix"><span>£</span><input id="item-loyalty" type="number" min="0.01" max="500" step="0.01" inputmode="decimal" placeholder="none"></div></label>` : ""}
      </div>
      ${matchNote(r)}
      <button type="button" class="primary full" id="item-save">Save price${store ? " at " + esc(store.name) : ""}</button>`;
  const warn = (r.warnings || []).map((w) => banner("warn", esc(w))).join("");
  out.innerHTML = `<div class="card">${warn}${mismatch}${head}${body}${itemSource(r)}</div>`;
  $("#item-yes")?.addEventListener("click", () => { ITEM.step = "price"; renderItem(); $("#item-price")?.focus(); });
  $("#item-no")?.addEventListener("click", () => { ITEM.step = "name"; renderItem(); $("#item-name").focus(); });
  $("#item-named")?.addEventListener("click", () => {
    const n = $("#item-name").value.trim();
    if (!n) return $("#item-name").focus();
    // The shopper overrules Open Food Facts, so nothing it said about the product holds any more
    Object.assign(ITEM, { name: n, typed: true, product_id: null, product_name: null, own_label_of: null,
      brand: null, quantity: null, image_url: null, step: "price" });
    renderItem(); $("#item-price")?.focus();
  });
  $("#item-save")?.addEventListener("click", saveItem);
  $("#item-class-no")?.addEventListener("click", () => { ITEM.class_ok = false; renderItem(); });
  $("#item-class-undo")?.addEventListener("click", () => { ITEM.class_ok = true; renderItem(); });
}

// Which product class the price joins, who said so, and a way to say no
function matchNote(r) {
  if (r.typed) return `<p class="small-print">Not compared with other shops: the name was typed, so we cannot tell what it matches.</p>`;
  const m = r.match;
  if (!m) return r.product_id ? "" : `<p class="small-print">Not compared with other shops yet. The price is saved, but plans cannot use it.</p>`;
  if (r.class_ok === false) return `<p class="small-print">You said it is not the same, so this price is kept apart.
    <button type="button" class="linkish" id="item-class-undo">Undo</button></p>`;
  const by = { ai: "AI", rules: "simple rules (AI unavailable)", shopper: "a shopper" }[m.by] || m.by;
  const no = ` <button type="button" class="linkish" id="item-class-no">Not the same?</button>`;
  if (r.product_id) return `<p class="small-print">Compared with <strong>${esc(r.product_name)}</strong> at other shops.
    By ${esc(by)}: ${esc(m.reason)}${m.by === "shopper" ? "" : no}</p>`;
  if (m.status === "new") return `<p class="small-print">New to us: saved as <strong>${esc(m.new_name || r.name)}</strong>,
    compared once someone scans the same thing at another chain. By ${esc(by)}: ${esc(m.reason)}${no}</p>`;
  return `<p class="small-print">${esc(r.note || "Not compared yet.")}</p>`;
}

async function saveItem() {
  const r = ITEM, store = scanStore();
  if (!store) return alert("Pick the shop you are in first.");
  const price = Number($("#item-price").value), loy = $("#item-loyalty")?.value;
  if (!(price > 0)) return $("#item-price").focus();
  const btn = $("#item-save"); btn.disabled = true;
  try {
    const res = await postJSON("/api/scans", { store_id: store.id, barcode: r.code, name: r.name, unit_price: price,
      loyalty_price: loy ? Number(loy) : null, shopper_named: !!r.typed, class_ok: r.class_ok !== false });
    Object.assign(r, { product_id: res.product_id, product_name: res.product_id ? (r.product_name || r.match?.new_name || r.name) : null });
    META.stats = res.stats;
    rememberProduct(r, { store_id: store.id, store: store.name, price, loyalty: loy ? Number(loy) : null, on: res.observed_on });
    ITEM = null;
    $("#scan-code").value = "";
    $("#scan-out").innerHTML = res.warnings.map((w) => banner("warn", esc(w))).join("") +
      banner("ok", `Saved ${esc(r.name)} at ${gbp(price)}${loy ? `, ${gbp(loy)} with ${esc(META.loyalty_schemes[store.chain])}` : ""}. Thanks.`);
    renderSaved();
  } catch (err) { btn.disabled = false; $("#scan-out .card").insertAdjacentHTML("afterbegin", banner("bad", esc(err.message))); }
}

function rememberProduct(r, last) {
  const list = load(KEY_SAVED, []).filter((p) => !p.code || p.code !== r.code);
  list.unshift({ code: r.code, name: r.name, brand: r.brand ?? null, quantity: r.quantity ?? null, image_url: r.image_url ?? null,
    own_label_of: r.own_label_of ?? null, product_id: r.product_id ?? null, product_name: r.product_name ?? null,
    typed: !!r.typed, status: r.status, last });
  save(KEY_SAVED, list.slice(0, 200));
}

function renderSaved() {
  const list = load(KEY_SAVED, []);
  const box = $("#saved-products");
  box.innerHTML = list.length ? `<ul class="saved">${list.map((p, i) => `<li data-i="${i}">
      ${p.image_url ? `<img src="${esc(p.image_url)}" alt="" loading="lazy">` : `<div class="noimg">${p.kind === "label" ? "label" : ""}</div>`}
      <div class="grow"><strong>${esc(p.name)}</strong>
        <div class="muted small-print">${p.kind === "label" ? lastLine(p) : p.last ? `${gbp(p.last.price)}${p.last.loyalty != null ? ` (${gbp(p.last.loyalty)} member)` : ""} at ${esc(p.last.store)}, ${esc(p.last.on)}` : ""}</div></div>
      <button type="button" class="ghost small reprice">Price it</button>
      <button type="button" class="icon-btn forget-product" aria-label="Remove ${esc(p.name)}">×</button></li>`).join("")}</ul>`
    : `<p class="muted small-print">Products you save are kept here, so next time you only change the price.</p>`;
}
$("#saved-products").addEventListener("click", (e) => {
  const li = e.target.closest("li");
  if (!li) return;
  const list = load(KEY_SAVED, []), p = list[li.dataset.i];
  if (e.target.closest(".forget-product")) { list.splice(li.dataset.i, 1); save(KEY_SAVED, list); return renderSaved(); }
  if (e.target.closest(".reprice") && p.kind === "label") return repriceLabel(p);
  if (e.target.closest(".reprice")) {
    LABEL = null;
    ITEM = { ...p, step: "price", source: null, note: null };
    renderItem(); window.scrollTo(0, 0); $("#item-price")?.focus();
  }
});

// ---------- shelf label: photo, AI read, pick the product, check, save ----------
// Products saved from labels join "Your products" on this device, so next time you just edit the price.
let LABEL = null;  // label being checked: { label, match, warnings, read_by, store_id, picked, photo, repeat }

const labelKey = (chain, cpid, name) => cpid ? `cp:${cpid}` : `name:${chain}:${(name || "").toLowerCase()}`;
const storeById = (id) => META.stores.find((s) => s.id === id);

// Smaller upload, and photos the browser can open but the AI cannot (HEIC on iPhone) become JPEG
async function shrink(file) {
  try {
    const bmp = await createImageBitmap(file);
    const k = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
    const c = Object.assign(document.createElement("canvas"), { width: Math.round(bmp.width * k), height: Math.round(bmp.height * k) });
    c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
    return await new Promise((ok) => c.toBlob((b) => ok(b || file), "image/jpeg", 0.85));
  } catch { return file; }
}

async function readLabel(form, photo) {
  const store = scanStore(), out = $("#scan-out");
  $("#scan-msg").innerHTML = "";
  if (!store) return ($("#scan-msg").innerHTML = banner("bad", "Pick the shop you are in first."));
  ITEM = null;
  out.innerHTML = `<div class="card muted">Reading the label...</div>`;
  form.append("store_id", store.id);
  try {
    const r = await api("/api/labels/read", { method: "POST", body: form });
    if (r.status === "not_label") { LABEL = null; return (out.innerHTML = banner("bad", esc(r.note))); }
    LABEL = { ...r, store_id: store.id, photo, picked: r.match.picked };
    renderLabel();
  } catch (err) { LABEL = null; out.innerHTML = banner("bad", esc(err.message)); }
}

$("#label-photo").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  e.target.value = "";
  if (!f) return;
  stopCamera();
  const img = await shrink(f), fd = new FormData();
  fd.append("file", img, img === f ? f.name : "label.jpg");
  readLabel(fd, URL.createObjectURL(img));
});
$("#label-typed").addEventListener("submit", (e) => {
  e.preventDefault();
  const t = $("#label-text").value.trim();
  if (!t) return $("#label-text").focus();
  const fd = new FormData();
  fd.append("text", t);
  readLabel(fd, null);
});

function savedFor(key) { return load(KEY_SAVED, []).find((p) => p.key === key); }

function lastLine(p) {
  const l = p.last;
  if (!l) return "";
  const offers = [l.loyalty != null ? `${gbp(l.loyalty)} ${esc(l.scheme || "member")}` : "",
    l.mb_qty ? `${l.mb_qty} for ${gbp(l.mb_price)}` : "", l.valid_until ? `ends ${esc(l.valid_until)}` : ""].filter(Boolean).join(", ");
  return `${gbp(l.price)}${offers ? ` (${offers})` : ""} at ${esc(l.store)}, ${esc(l.on)}`;
}

function renderLabel() {
  const L = LABEL, l = L.label, m = L.match, store = storeById(L.store_id), out = $("#scan-out");
  const scheme = META.loyalty_schemes[store.chain];
  const by = { ai: "AI", baseline: "name match, no AI", search: "word search", device: "you, on this device" }[m.by] || "";
  const opts = m.options.map((o) => `<label class="opt"><input type="radio" name="label-pick" value="${o.id}" ${o.id === L.picked ? "checked" : ""}>
      <span>${esc(o.name)}<span class="muted">${o.price != null ? `${gbp(o.price)} online, ${esc((o.seen_on || "").slice(0, 7))}` : ""}${o.class_name ? ` · compared as ${esc(o.class_name)}` : " · not compared with other shops yet"}</span></span></label>`).join("");
  const none = m.options.length && !L.repeat ? `<label class="opt"><input type="radio" name="label-pick" value="none" ${L.picked === "none" ? "checked" : ""}>
      <span>None of these<span class="muted">saved under the name below, not compared yet</span></span></label>` : "";
  const picked = m.options.find((o) => o.id === L.picked);
  const before = picked && !L.repeat ? savedFor(labelKey(store.chain, picked.id)) : null;
  const showName = !m.options.length || L.picked === "none";
  const offer = l.loyalty_price != null || l.valid_until || l.was_price != null || l.multibuy_qty;
  const num = (id, v, ph = "") => `<input id="${id}" type="number" min="0.01" max="500" step="0.01" inputmode="decimal" value="${v != null ? Number(v).toFixed(2) : ""}" placeholder="${ph}">`;
  const readBy = L.repeat ? `Last saved ${esc(L.saved_on)}. Change what is different today.`
    : L.read_by === "ai" ? "Read by AI from your photo. Check every number against the label." : "Read by simple rules from what you typed, no AI.";
  out.innerHTML = `<div class="card">
    ${L.warnings.map((w) => banner("warn", esc(w))).join("")}
    ${L.photo ? `<img class="label-photo" src="${esc(L.photo)}" alt="Your label photo">` : ""}
    <p class="small-print">${readBy}${l.product_text && !L.repeat ? ` Label says: <strong>${esc(l.product_text)}</strong>${l.size ? ", " + esc(l.size) : ""}.` : ""}</p>
    ${m.options.length ? `<p><strong>${m.status === "exact" || L.repeat ? "Product" : "Which product is it?"}</strong> <span class="pill seen">${esc(by)}</span></p>
      <p class="small-print">${esc(m.note)}</p><div class="pick-list">${opts}${none}</div>` : banner("warn", esc(m.note))}
    ${before ? `<p class="note">You saved this before: ${lastLine(before)}.</p>` : ""}
    <label ${showName ? "" : "hidden"} id="lbl-name-wrap">Product name <span class="hint">name, size and brand from the label</span>
      <input id="lbl-name" maxlength="120" value="${esc([l.product_text, l.size && !(l.product_text || "").includes(l.size) ? l.size : ""].filter(Boolean).join(" "))}"></label>
    <div class="row prices-row">
      <label class="grow">Shelf price <span class="hint">no card</span><div class="prefix"><span>£</span>${num("lbl-price", l.shelf_price)}</div></label>
      ${scheme ? `<label class="grow">${esc(scheme)} price <span class="hint">if shown</span><div class="prefix"><span>£</span>${num("lbl-loyalty", l.loyalty_price, "none")}</div></label>` : ""}
    </div>
    <details class="typed-label" ${offer ? "open" : ""}><summary>Offer details${offer ? "" : " (none read)"}</summary>
      <div class="offer-grid">
        <label>Offer ends <input id="lbl-ends" type="date" value="${esc(l.valid_until || "")}"></label>
        <label>Was price <div class="prefix"><span>£</span>${num("lbl-was", l.was_price, "none")}</div></label>
        <label>Multibuy <div class="multibuy">${`<input id="lbl-mb-qty" type="number" min="2" max="20" step="1" inputmode="numeric" value="${l.multibuy_qty ?? ""}" placeholder="qty">`}
          <span>for £</span>${num("lbl-mb-price", l.multibuy_price, "price")}</div></label>
        ${scheme ? `<label class="check"><input type="checkbox" id="lbl-mb-members" ${l.multibuy_members_only ? "checked" : ""}>Multibuy needs ${esc(scheme)}</label>` : ""}
      </div>
    </details>
    <button type="button" class="primary full" id="lbl-save">Save price at ${esc(store.name)}</button>
    <button type="button" class="ghost full" id="lbl-cancel">Cancel</button>
  </div>`;
  $$('input[name="label-pick"]').forEach((x) => x.addEventListener("change", () => {
    LABEL.picked = x.value === "none" ? "none" : Number(x.value);
    renderLabel();
  }));
  $("#lbl-save").addEventListener("click", saveLabel);
  $("#lbl-cancel").addEventListener("click", () => { LABEL = null; out.innerHTML = ""; });
}

async function saveLabel() {
  const L = LABEL, store = storeById(L.store_id);
  const val = (id) => { const v = $(id)?.value; return v ? Number(v) : null; };
  if (L.match.options.length && L.picked == null) return alert("Pick the product, or None of these.");
  const cpid = typeof L.picked === "number" ? L.picked : null;
  const opt = L.match.options.find((o) => o.id === cpid);
  const name = opt ? opt.name : $("#lbl-name").value.trim();
  if (!name) return $("#lbl-name").focus();
  const price = val("#lbl-price");
  if (!(price > 0)) return $("#lbl-price").focus();
  const body = { store_id: store.id, chain_product_id: cpid, name, unit_price: price,
    identified_by: cpid ? (L.repeat ? "device" : cpid === L.match.picked ? L.match.by : "shopper") : null,
    was_price: val("#lbl-was"), loyalty_price: val("#lbl-loyalty"), valid_until: $("#lbl-ends").value || null,
    multibuy_qty: val("#lbl-mb-qty"), multibuy_price: val("#lbl-mb-price"), multibuy_members_only: !!$("#lbl-mb-members")?.checked };
  const btn = $("#lbl-save"); btn.disabled = true;
  try {
    const res = await postJSON("/api/labels", body);
    META.stats = res.stats;
    const scheme = META.loyalty_schemes[store.chain];
    const list = load(KEY_SAVED, []), key = labelKey(store.chain, cpid, name);
    const kept = list.filter((p) => p.key !== key);
    kept.unshift({ kind: "label", key, chain: store.chain, cpid, name, class_name: opt?.class_name ?? null,
      product_id: res.product_id, online: opt ? { price: opt.price, seen_on: opt.seen_on } : null,
      last: { store_id: store.id, store: store.name, price, loyalty: body.loyalty_price, scheme: body.loyalty_price ? scheme : null,
              valid_until: body.valid_until, was: body.was_price, mb_qty: body.multibuy_qty, mb_price: body.multibuy_price,
              mb_members: body.multibuy_members_only, on: res.observed_on } });
    save(KEY_SAVED, kept.slice(0, 200));
    LABEL = null;
    $("#label-text").value = "";
    $("#scan-out").innerHTML = res.warnings.map((w) => banner("warn", esc(w))).join("") +
      banner("ok", `Saved ${esc(name)} at ${gbp(price)}${body.loyalty_price ? `, ${gbp(body.loyalty_price)} with ${esc(scheme)}` : ""}${body.multibuy_qty ? `, ${body.multibuy_qty} for ${gbp(body.multibuy_price)}` : ""}. Thanks.`);
    renderSaved();
  } catch (err) { btn.disabled = false; $("#scan-out .card").insertAdjacentHTML("afterbegin", banner("bad", esc(err.message))); }
}

// "Price it" on a product saved from a label: same card, filled with what you saved last time
function repriceLabel(p) {
  const here = scanStore();
  const store = here && here.chain === p.chain ? here : storeById(p.last.store_id);
  const l = p.last, ended = l.valid_until && l.valid_until < new Date().toISOString().slice(0, 10);
  LABEL = { repeat: true, saved_on: l.on, store_id: store.id, photo: null, read_by: "saved", picked: p.cpid ?? "none",
    warnings: [here && here.chain !== p.chain ? `This product is from the ${p.chain} list, so it is saved at ${store.name}. Pick a ${p.chain} shop to change that.` : "",
               ended ? `The offer you saved ended on ${l.valid_until}, so it is cleared.` : ""].filter(Boolean),
    label: { product_text: p.name, size: null, shelf_price: l.price, loyalty_price: ended ? null : l.loyalty,
             valid_until: ended ? null : l.valid_until, was_price: ended ? null : l.was,
             multibuy_qty: ended ? null : l.mb_qty, multibuy_price: ended ? null : l.mb_price, multibuy_members_only: !ended && l.mb_members },
    match: p.cpid ? { status: "exact", by: "device", note: "Saved on this device.",
      options: [{ id: p.cpid, name: p.name, price: p.online?.price ?? null, seen_on: p.online?.seen_on ?? "", class_name: p.class_name }], picked: p.cpid }
      : { status: "none", by: null, note: "Not matched to a product we know. Saved under this name.", options: [], picked: null } };
  ITEM = null;
  renderLabel(); window.scrollTo(0, 0); $("#lbl-price")?.focus();
}

// ---------- prices ----------
function renderStats(s) {
  $("#stats").innerHTML = `
    <div><strong>${s.observations}</strong>shopper prices (${s.observations_real} real)</div>
    <div><strong>${s.reference_prices}</strong>Open Food Facts prices, ${s.reference_products} products</div>
    <div><strong>${s.stores_with_prices}</strong>shops with shopper prices</div>
    <div><strong>${s.labels}</strong>shelf labels</div>
    <div><strong>${s.baseline_links}</strong>starting prices, ${s.baseline_classes} products</div>
    <div><strong>${esc(s.latest_observation || "none")}</strong>latest shopper price</div>`;
}

async function loadPrices() {
  renderStats(META.stats);
  const id = $("#product-select").value;
  const { community, reference, baseline } = await api("/api/prices/" + encodeURIComponent(id));
  const comm = community.length ? `<div class="card table-wrap"><h2>From shoppers <span class="hint">shelf labels and scans, main source</span></h2><table>
    <thead><tr><th>Shop</th><th class="num">Price</th><th class="num">Member</th><th>Date</th><th></th></tr></thead><tbody>
    ${community.map((r) => `<tr><td>${esc(r.store)}</td><td class="num">${gbp(r.unit_price)}</td>
      <td class="num">${r.loyalty_price != null ? gbp(r.loyalty_price) + " " + esc(r.loyalty_scheme) : "-"}</td><td>${esc(r.observed_on)}</td>
      <td>${r.synthetic ? '<span class="pill synth">synthetic</span>' : r.method === "scan" ? "shelf scan" : "shelf label"} ${r.outlier ? '<span class="pill stale">outlier, unused</span>' : ""}
        ${r.multibuy_qty ? `<span class="pill seen">${r.multibuy_qty} for ${gbp(r.multibuy_price)}${r.multibuy_scheme ? " " + esc(r.multibuy_scheme) : ""}</span>` : ""}
        ${r.valid_until ? `<span class="pill ${r.valid_until < new Date().toISOString().slice(0, 10) ? "stale" : "seen"}">offer ends ${esc(r.valid_until)}</span>` : ""}</td></tr>`).join("")}
    </tbody></table></div>` : banner("warn", "No shopper prices for this product yet. Scan its shelf label.");
  const ref = reference.length ? `<div class="card table-wrap"><h2>From Open Food Facts <span class="hint">temporary fallback, UK-wide, fetched ${esc(META.reference?.fetched_at?.slice(0, 10) || "")}</span></h2><table>
    <thead><tr><th>Seen at</th><th class="num">Price</th><th class="num">Member</th><th>Date</th><th>Proof</th></tr></thead><tbody>
    ${reference.map((r) => `<tr><td>${esc(r.location)}<div class="muted">${esc(r.city || "")} · ${esc(r.off_name || "")}</div></td><td class="num">${gbp(r.unit_price)}</td>
      <td class="num">${r.loyalty_price != null ? gbp(r.loyalty_price) : "-"}</td><td>${esc(r.observed_on)}</td><td>${esc((r.proof_type || "").toLowerCase().replace("_", " "))}</td></tr>`).join("")}
    </tbody></table></div>` : banner("warn", "No Open Food Facts price for this product.");
  const online = baseline.length ? `<div class="card table-wrap"><h2>Starting prices <span class="hint">chain websites, ${esc(META.product_index?.prices_from || "")} to ${esc(META.product_index?.prices_to || "")}, Kaggle set</span></h2><table>
    <thead><tr><th>Chain</th><th>Product</th><th class="num">Price</th><th>Date</th></tr></thead><tbody>
    ${baseline.map((r) => `<tr><td>${esc(r.chain)}</td><td>${esc(r.chain_name)}<div class="muted">linked by ${r.linked_by === "ai" ? "AI, not yet checked by the team" : r.linked_by === "team" ? "the team" : "simple rules"}</div></td>
      <td class="num">${gbp(r.unit_price)}</td><td>${esc(r.observed_on)}</td></tr>`).join("")}
    </tbody></table><p class="small-print">Used only where no shopper has priced this product at that chain. Prices have risen since.</p></div>`
    : banner("warn", "No starting price for this product: no chain's product list has it linked.");
  $("#prices-out").innerHTML = comm + ref + online;
}
$("#product-select").addEventListener("change", loadPrices);

// ---------- start ----------
async function start() {
  META = await api("/api/meta");
  $("#osm-date").textContent = META.stores_fetched_at?.slice(0, 10) || "unknown";
  $("#off-date").textContent = META.reference?.fetched_at ? "fetched " + META.reference.fetched_at.slice(0, 10) : "not loaded";
  $("#kaggle-dates").textContent = META.product_index ? `${META.product_index.prices_from} to ${META.product_index.prices_to}` : "not loaded";
  // one compact line, so problems stay visible without crowding the list
  const notes = [];
  if (!META.ai_key_set) notes.push(["No AI: no Anthropic API key", "Lists are read by the baseline matcher, which is much less accurate. Shelf label photos cannot be read: type the label instead."]);
  if (!META.stats.baseline_links) notes.push(["No starting prices", "Run scripts/link_classes.py. Plans use shopper prices and Open Food Facts only."]);
  if (!META.reference) notes.push(["No Open Food Facts prices", "Run scripts/fetch_off.py. Plans use shopper prices and starting prices only."]);
  load(KEY_PROFILE, null);
  if (!STORAGE_OK) notes.push(["Profile not saved", "This browser blocks storage. Your profile works for this visit only."]);
  $("#global-banner").innerHTML = notes.length ? `<details class="status"><summary>${notes.map(([t]) => esc(t)).join(" · ")}</summary>
    <ul>${notes.map(([t, d]) => `<li><strong>${esc(t)}.</strong> ${esc(d)}</li>`).join("")}</ul></details>` : "";
  $("#product-select").innerHTML = META.catalogue.map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("");
  renderAvatar();
  route();
}
start().catch((e) => { $("#global-banner").innerHTML = banner("bad", "Could not load Nostobon: " + esc(e.message)); });
