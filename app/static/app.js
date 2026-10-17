const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const gbp = (n) => "£" + Number(n).toFixed(2);
const banner = (cls, html) => `<div class="banner ${cls}">${html}</div>`;
let META = null;
let DRAFT = null;   // receipt being checked

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail ? (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) : `HTTP ${res.status}`);
  return body;
}
const postJSON = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---------- storage: profile and list live on this device only ----------
const KEY_PROFILE = "nostobon.profile.v1", KEY_LIST = "nostobon.list.v1";
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
  try { localStorage.removeItem(KEY_PROFILE); localStorage.removeItem(KEY_LIST); } catch { /* nothing stored */ }
  delete MEMORY[KEY_PROFILE]; delete MEMORY[KEY_LIST];
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
const VIEWS = ["setup", "list", "plan", "receipt", "prices", "profile"];
function route() {
  let view = location.hash.replace(/^#\//, "") || "list";
  if (!VIEWS.includes(view)) view = "list";
  if (!PROFILE && view !== "setup") return (location.hash = "#/setup");
  if (PROFILE && view === "setup") return (location.hash = "#/list");
  if (view === "plan" && !LAST_PLAN) return (location.hash = "#/list");
  $$("[data-view]").forEach((s) => (s.hidden = s.dataset.view !== view));
  $("#top-nav").hidden = view === "setup";
  $$("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === view));
  ({ setup: renderSetup, list: renderList, plan: renderPlan, prices: loadPrices, profile: renderProfile }[view])();
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
      <p class="muted sub">Your profile and list are kept in this browser's storage. Our server keeps nothing about you.
        Receipts you add are saved without card numbers, loyalty numbers or the photo.</p>
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
    const blob = new Blob([JSON.stringify({ profile: PROFILE, list: LIST }, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "nostobon-my-data.json" });
    a.click(); URL.revokeObjectURL(a.href);
  };
  $("#wipe").onclick = () => {
    if (!confirm("Delete your profile and list from this device? You will set up again.")) return;
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
  if (l.source === "openfoodfacts")
    t.push(`<span class="pill off" title="Open Food Facts Open Prices, seen at ${esc(l.borrowed_from)}${l.other_format ? ", a different store format" : ""}. Temporary until receipts cover this shop.">Open Food Facts · ${esc(age)}</span>`);
  else if (l.source === "receipt_other_branch")
    t.push(`<span class="pill borrow" title="Receipt from ${esc(l.borrowed_from)}. No receipt from this branch yet.">receipt, other branch · ${esc(age)}</span>`);
  else t.push(`<span class="pill rcpt" title="${l.n_obs} receipts for this product here">receipt · ${esc(age)}</span>`);
  if (l.synthetic) t.push(`<span class="pill synth">synthetic</span>`);
  if (l.stale) t.push(`<span class="pill stale">over 30 days old</span>`);
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
      Receipt prices older than ${p.assumptions.max_price_age_days} days and Open Food Facts prices older than ${p.assumptions.max_reference_age_days} days are ignored. Shops may have changed prices since.</p>`;
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
    const sub = lines.reduce((t, l) => t + l.unit_price * l.quantity, 0);
    return `<div class="card shop"><div class="shop-head"><span class="num">${k + 1}</span><h2>${esc(s.name)}</h2><strong>${gbp(sub)}</strong></div>
      <ul class="lines">${lines.map((l) => `<li>
        <div class="line-main"><span>${esc(l.quantity > 1 ? l.quantity + " x " : "")}${esc(l.item)}</span>
          <span class="price">${l.applied.length ? `<s class="muted">${gbp(l.shelf_price)}</s> ` : ""}${gbp(l.unit_price * l.quantity)}</span></div>
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

// ---------- receipt ----------
$$("[data-sample]").forEach((b) => b.addEventListener("click", async () => {
  const res = await fetch("/api/samples/" + b.dataset.sample);
  $("#receipt-text").value = await res.text();
  $("#receipt-file").value = "";
}));

$("#receipt-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Reading...";
  const fd = new FormData();
  const f = $("#receipt-file").files[0];
  if (f) fd.append("file", f); else fd.append("text", $("#receipt-text").value);
  try {
    DRAFT = await api("/api/receipts/parse", { method: "POST", body: fd });
    renderDraft();
  } catch (err) {
    $("#receipt-out").innerHTML = banner("bad", esc(err.message));
  } finally { btn.disabled = false; btn.textContent = "Read receipt"; }
});

function renderDraft() {
  const r = DRAFT.receipt;
  const productOpts = (sel) => `<option value="">Not in catalogue</option>` + META.catalogue.map((p) =>
    `<option value="${esc(p.id)}" ${p.id === sel ? "selected" : ""}>${esc(p.name)}</option>`).join("");
  const stores = META.stores.filter((s) => !r.chain || r.chain === "other" || s.chain === r.chain);
  const storeOpts = `<option value="">Pick the shop</option>` + stores.map((s) =>
    `<option value="${esc(s.id)}" ${s.id === DRAFT.suggested_store_id ? "selected" : ""}>${esc(s.name)}${s.address ? " - " + esc(s.address) : ""}</option>`).join("");
  const rows = r.lines.map((l, i) => `<tr data-i="${i}">
      <td>${esc(l.raw_text)}${l.confidence !== "high" ? ` <span class="pill stale">${esc(l.confidence)} confidence</span>` : ""}</td>
      <td><select class="pid">${productOpts(l.product_id)}</select></td>
      <td class="num"><input class="qty" type="number" step="1" min="1" value="${l.quantity}" style="width:4em"></td>
      <td class="num"><input class="price" type="number" step="0.01" min="0" value="${l.unit_price.toFixed(2)}" style="width:6em"></td>
      <td class="num"><input class="loy" type="number" step="0.01" min="0" value="${l.loyalty_discount ?? ""}" style="width:5em" placeholder="-"></td></tr>`).join("");
  $("#receipt-out").innerHTML = DRAFT.warnings.map((w) => banner("warn", esc(w))).join("") + `
    <div class="card">
      <h2>Check before saving <span class="hint">read by ${DRAFT.parser === "ai" ? "AI" : "baseline regex (no AI)"}</span>
        ${DRAFT.synthetic ? '<span class="pill synth">synthetic sample, saved as synthetic</span>' : ""}</h2>
      <p class="muted">${esc(r.chain || "Unknown shop")}${r.purchase_date ? ", " + esc(r.purchase_date) : ""}${r.total != null ? ", total " + gbp(r.total) : ""}</p>
      <label>Shop <select id="draft-store">${storeOpts}</select></label>
      <div class="table-wrap"><table><thead><tr><th>On receipt</th><th>Product</th><th class="num">Qty</th><th class="num">Unit £</th><th class="num">Loyalty saving £</th></tr></thead>
      <tbody>${rows}</tbody></table></div>
      <p class="small-print">Lines you leave as "Not in catalogue" are saved as unmatched and not used in plans yet.</p>
      <button id="commit" class="primary">Save to community prices</button>
    </div>`;
  $("#commit").onclick = commitDraft;
}

async function commitDraft() {
  const store_id = $("#draft-store").value;
  if (!store_id) return alert("Pick the shop first.");
  const lines = $$("#receipt-out tbody tr").map((tr) => {
    const l = DRAFT.receipt.lines[tr.dataset.i];
    const loy = $(".loy", tr).value;
    return { raw_text: l.raw_text, quantity: Number($(".qty", tr).value), unit_price: Number($(".price", tr).value),
      loyalty_discount: loy ? Number(loy) : null, loyalty_scheme: loy ? (l.loyalty_scheme || "loyalty") : null,
      product_id: $(".pid", tr).value || null, confidence: l.confidence };
  });
  try {
    const res = await postJSON("/api/receipts/commit", { store_id, purchase_date: DRAFT.receipt.purchase_date, source: DRAFT.source,
      parser: DRAFT.parser, content_hash: DRAFT.content_hash, synthetic: DRAFT.synthetic, lines });
    $("#receipt-out").innerHTML = res.warnings.map((w) => banner("warn", esc(w))).join("") + banner("ok", `Saved ${res.saved_lines} prices. Thanks.`);
    META.stats = res.stats;
  } catch (err) { $("#receipt-out").insertAdjacentHTML("afterbegin", banner("bad", esc(err.message))); }
}

// ---------- prices ----------
function renderStats(s) {
  $("#stats").innerHTML = `
    <div><strong>${s.receipts_real}</strong>real receipts</div>
    <div><strong>${s.receipts - s.receipts_real}</strong>synthetic receipts</div>
    <div><strong>${s.observations}</strong>receipt prices (${s.observations_real} real)</div>
    <div><strong>${s.reference_prices}</strong>Open Food Facts prices, ${s.reference_products} products</div>
    <div><strong>${s.stores_with_prices}</strong>shops with receipts</div>
    <div><strong>${esc(s.latest_observation || "none")}</strong>latest receipt price</div>`;
}

async function loadPrices() {
  renderStats(META.stats);
  const id = $("#product-select").value;
  const { community, reference } = await api("/api/prices/" + encodeURIComponent(id));
  const comm = community.length ? `<div class="card table-wrap"><h2>From receipts <span class="hint">main source</span></h2><table>
    <thead><tr><th>Shop</th><th class="num">Price</th><th class="num">Member</th><th>Date</th><th></th></tr></thead><tbody>
    ${community.map((r) => `<tr><td>${esc(r.store)}</td><td class="num">${gbp(r.unit_price)}</td>
      <td class="num">${r.loyalty_price != null ? gbp(r.loyalty_price) + " " + esc(r.loyalty_scheme) : "-"}</td><td>${esc(r.observed_on)}</td>
      <td>${r.synthetic ? '<span class="pill synth">synthetic</span>' : "real receipt"} ${r.outlier ? '<span class="pill stale">outlier, unused</span>' : ""}</td></tr>`).join("")}
    </tbody></table></div>` : banner("warn", "No receipts for this product yet. Add one.");
  const ref = reference.length ? `<div class="card table-wrap"><h2>From Open Food Facts <span class="hint">temporary fallback, UK-wide, fetched ${esc(META.reference?.fetched_at?.slice(0, 10) || "")}</span></h2><table>
    <thead><tr><th>Seen at</th><th class="num">Price</th><th class="num">Member</th><th>Date</th><th>Proof</th></tr></thead><tbody>
    ${reference.map((r) => `<tr><td>${esc(r.location)}<div class="muted">${esc(r.city || "")} · ${esc(r.off_name || "")}</div></td><td class="num">${gbp(r.unit_price)}</td>
      <td class="num">${r.loyalty_price != null ? gbp(r.loyalty_price) : "-"}</td><td>${esc(r.observed_on)}</td><td>${esc((r.proof_type || "").toLowerCase().replace("_", " "))}</td></tr>`).join("")}
    </tbody></table></div>` : banner("warn", "No Open Food Facts price for this product.");
  $("#prices-out").innerHTML = comm + ref;
}
$("#product-select").addEventListener("change", loadPrices);

// ---------- start ----------
async function start() {
  META = await api("/api/meta");
  $("#osm-date").textContent = META.stores_fetched_at?.slice(0, 10) || "unknown";
  $("#off-date").textContent = META.reference?.fetched_at ? "fetched " + META.reference.fetched_at.slice(0, 10) : "not loaded";
  // one compact line, so problems stay visible without crowding the list
  const notes = [];
  if (!META.ai_key_set) notes.push(["No AI: no Anthropic API key", "Lists are read by the baseline matcher and receipts by a regex parser, which are much less accurate. Photos and PDFs cannot be read."]);
  if (!META.reference) notes.push(["No Open Food Facts prices", "Run scripts/fetch_off.py. Plans use receipts only."]);
  load(KEY_PROFILE, null);
  if (!STORAGE_OK) notes.push(["Profile not saved", "This browser blocks storage. Your profile works for this visit only."]);
  $("#global-banner").innerHTML = notes.length ? `<details class="status"><summary>${notes.map(([t]) => esc(t)).join(" · ")}</summary>
    <ul>${notes.map(([t, d]) => `<li><strong>${esc(t)}.</strong> ${esc(d)}</li>`).join("")}</ul></details>` : "";
  $("#product-select").innerHTML = META.catalogue.map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("");
  renderAvatar();
  route();
}
start().catch((e) => { $("#global-banner").innerHTML = banner("bad", "Could not load Nostobon: " + esc(e.message)); });
