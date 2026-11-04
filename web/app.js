"use strict";

// Die Kalender- und Bahnwerte stammen ausschließlich aus dem lokalen Python-Kern.
// Browserrechnungen betreffen Darstellung, Kameraprojektion und die Wahl eines q-Zeitpunkts.
const $ = (id) => document.getElementById(id);
const app = {
  meta: null, state: null, series: null, planets: null, tab: "overview",
  group: 4, level: "year", stateSeq: 0, seriesSeq: 0, planetSeq: 0,
  pending: false, sliderBounds: null, sliderTimer: null,
  playing: false, animationBusy: false, animationStart: 0, animationQ: 0n,
  camera: {yaw: -0.45, pitch: 0.80, zoom: 1},
  selectedPlanet: "earth", planetHits: [], drag: null, lastPointerMoved: false,
};
const fmt = new Intl.NumberFormat("de-DE");
const fnum = (n, digits = 3) => Number(n).toLocaleString("de-DE", {maximumFractionDigits: digits});
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const qfmt = (s) => {try {return fmt.format(BigInt(s));} catch {return String(s);}};
const prettyUTC = (s) => String(s).replace("T", " · ").replace(/Z$/, " UTC");
function showError(error) {$("error-box").textContent = error?.message || String(error); $("error-box").hidden = false;}
function clearError() {$("error-box").hidden = true;}
function notice(text) {$("notice-box").textContent = text; $("notice-box").hidden = !text;}

async function api(path, params = {}) {
  const url = new URL(path, window.location.origin);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, String(value));
  const response = await fetch(url, {cache: "no-store"});
  let data;
  try {data = await response.json();} catch {throw new Error("Der lokale Rechenkern hat keine gültige JSON-Antwort geliefert.");}
  if (!response.ok || data.error) throw new Error(data.error || `Lokale Anfrage fehlgeschlagen (${response.status}).`);
  return data;
}

async function setState(path = "/api/state", params = {}, options = {}) {
  const seq = ++app.stateSeq;
  app.pending = true;
  try {
    const data = await api(path, {...params, group: app.group});
    if (seq !== app.stateSeq) return false;
    app.state = data;
    clearError();
    if (!options.keepNotice) notice("");
    renderState();
    if (app.tab === "residuals" && $("series-mode").value === "cycle") loadSeries();
    if (app.tab === "space") loadPlanets();
    return true;
  } catch (error) {
    if (seq === app.stateSeq) {showError(error); if (app.playing) stopPlayback();}
    return false;
  } finally {if (seq === app.stateSeq) app.pending = false;}
}

function manualState(path, params) {stopPlayback(); return setState(path, params);}

function renderMeta() {
  const m = app.meta;
  $("version").textContent = `Demonstrator ${m.version}`;
  $("footer-version").textContent = m.version;
  $("quantum-value").textContent = `q = ${m.q_seconds.exact} s`;
  $("definition-quantum").textContent = `q = ${m.q_seconds.exact} s ≈ ${fnum(m.q_seconds.value, 8)} s`;
  $("definition-epoch").textContent = prettyUTC(m.epoch_utc);
  $("horizon-label").textContent = `Ab jj bis vor ${String(m.horizon.end_utc).slice(0, 10)} · ${m.horizon.years} Jahre`;
  $("anchor-formula").textContent = `τ(x) = ${m.math.Y} x + (${m.math.b} x ${Number(m.math.g) < 0 ? "−" : "+"} ${Math.abs(Number(m.math.g))} x²) / ${m.math.d} q`;
  $("credits").innerHTML = m.credits.map((c) => `<div><strong>${esc(c.name)}</strong><span>${esc(c.role)}</span></div>`).join("");
  $("presets").innerHTML = m.presets.map((p, i) => `<button type="button" data-preset="${i}">${esc(p.label)}</button>`).join("");
  $("presets").addEventListener("click", (event) => {
    const button = event.target.closest("[data-preset]");
    if (button) manualState("/api/state", {q: m.presets[Number(button.dataset.preset)].q});
  });
  if (!m.group_options.includes(app.group)) app.group = m.group_options[0];
  $("group-select").value = String(app.group);
}

function renderState() {
  const s = app.state, c = s.calendar;
  $("utc-display").textContent = prettyUTC(s.utc);
  $("q-display").textContent = qfmt(s.q);
  $("q-input").value = s.q;
  $("utc-input").value = s.utc;
  $("coordinate-display").textContent = s.coordinate_text;
  $("stat-year").textContent = `${c.chart} / ${c.year}`;
  $("stat-year-detail").textContent = `Jahresindex ${c.year_index} · ${c.day_of_year === 364 ? "Nulltag" : `Monat ${c.month}, Tag ${c.day}`}`;
  $("stat-group").textContent = `${s.group.phase} / ${s.group.size - 1}`;
  $("stat-group-detail").textContent = `Gruppe ${s.group.index} · Jahre ${s.group.start_year}–${s.group.end_year - 1}`;
  $("stat-cycle").innerHTML = `${qfmt(s.cycle.length_q)} <span>q</span>`;
  $("stat-cycle-detail").textContent = `66 Ticks + ${s.cycle.zero_length_q} q Nulldurchgang`;
  $("stat-residual").innerHTML = `${fnum(s.residual.cycle.q, 5)} <span>q</span>`;
  $("stat-residual-detail").textContent = `${s.residual.cycle.exact_q} q ≈ ${fnum(s.residual.cycle.seconds * 1000, 3)} ms`;
  $("zero-badge").textContent = s.cycle.is_zero ? `Nulldurchgang ${c.countdown}` : "normal";
  $("zero-badge").classList.toggle("zero", s.cycle.is_zero);
  $("tick-quant").textContent = s.cycle.is_zero ? `${c.countdown} (Übergang)` : `${c.tick} / ${c.quant}`;
  $("cycle-offset").textContent = `${qfmt(s.cycle.offset_q)} q`;
  $("cycle-next").textContent = `${qfmt(s.cycle.next_q)} q`;
  $("moon-phase").textContent = `${fnum(s.moon.phase_degrees, 3)}°`;
  $("moon-detail").textContent = `Lunation ${s.moon.lunation} · Phase ${qfmt(s.moon.phase)} joe`;
  $("rotation-phase").textContent = `${s.rotation.cycle} / ${s.rotation.tick} / ${s.rotation.quant}`;
  $("rotation-detail").textContent = `Greenwich · Umlauf ${qfmt(s.rotation.turn)}`;
  renderMoon(s.moon.phase_degrees);
  renderLevels();
  drawCycle();
}

function renderLevels() {
  const levels = app.state.levels;
  if (!levels.some((l) => l.key === app.level)) app.level = levels.find((l) => /year|jahr/i.test(l.key))?.key || levels[0].key;
  $("levels-list").innerHTML = levels.map((l, i) => `<button type="button" class="level-row${l.key === app.level ? " selected" : ""}" data-level="${i}" aria-pressed="${l.key === app.level}"><span class="level-name">${esc(l.label)}<span class="level-index">Index ${esc(l.index)}</span></span><span class="level-track"><span class="level-fill" style="width:${clamp(l.progress, 0, 1) * 100}%"></span></span><span class="level-value">${fnum(l.progress * 100, 2)} %</span></button>`).join("");
  const level = levels.find((l) => l.key === app.level);
  let lo = BigInt(level.start_q), hi = BigInt(level.end_q) - 1n;
  const max = BigInt(app.meta.horizon.end_q) - 1n;
  if (lo < 0n) lo = 0n;
  if (hi > max) hi = max;
  app.sliderBounds = {lo, hi};
  const q = BigInt(app.state.q);
  const fraction = hi > lo ? Number((q - lo) * 10000n / (hi - lo)) : 0;
  $("time-slider").value = String(clamp(fraction, 0, 10000));
  $("scrub-title").textContent = `${level.label} · Index ${level.index}`;
  $("scrub-percent").textContent = `${fnum(level.progress * 100, 4)} %`;
  $("scrub-start").textContent = `${qfmt(lo)} q`;
  $("scrub-end").textContent = `${qfmt(hi)} q`;
}

function renderMoon(degrees) {
  const phase = ((degrees % 360) + 360) % 360, side = phase <= 180 ? 1 : -1;
  const cos = Math.cos(phase * Math.PI / 180), points = [];
  for (let i = 0; i <= 40; i++) {const y = -28 + 56 * i / 40; points.push([32 + side * Math.sqrt(Math.max(0, 784 - y * y)), 32 + y]);}
  for (let i = 40; i >= 0; i--) {const y = -28 + 56 * i / 40; points.push([32 + side * cos * Math.sqrt(Math.max(0, 784 - y * y)), 32 + y]);}
  $("moon-light").setAttribute("d", `M${points.map((p) => p.join(",")).join("L")}Z`);
}

function canvasContext(id) {
  const canvas = $(id), rect = canvas.getBoundingClientRect();
  if (rect.width < 1 || rect.height < 1) return null;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.round(rect.width), height = Math.round(rect.height);
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);}
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  return {canvas, ctx, width, height};
}

function drawCycle() {
  if (!app.state) return;
  const setup = canvasContext("cycle-canvas"); if (!setup) return;
  const {ctx, width: w, height: h} = setup, c = app.state.calendar;
  const cx = Math.min(95, w * .24), cy = h * .49, radius = Math.min(54, h * .34);
  ctx.lineWidth = 7; ctx.lineCap = "round";
  for (let i = 0; i < 66; i++) {
    const a = -Math.PI / 2 + i / 66 * Math.PI * 2, b = a + Math.PI * 2 / 66 * .57;
    ctx.beginPath(); ctx.strokeStyle = i === c.tick ? "#087f83" : i < (c.tick ?? 66) ? "#b8dcd4" : "#e5edf1"; ctx.arc(cx, cy, radius, a, b); ctx.stroke();
  }
  ctx.textAlign = "center"; ctx.fillStyle = app.state.cycle.is_zero ? "#b86d32" : "#102b46"; ctx.font = "600 23px system-ui";
  ctx.fillText(app.state.cycle.is_zero ? String(c.countdown) : String(c.tick), cx, cy + 5);
  ctx.fillStyle = "#637485"; ctx.font = "9px system-ui"; ctx.fillText(app.state.cycle.is_zero ? "Nulldurchgang" : "Tick von 0 bis 65", cx, cy + 22);
  const left = cx + radius + 28, available = Math.max(50, w - left - 8), cols = Math.min(12, Math.floor(available / 16)), step = Math.min(23, available / Math.max(1, cols)), box = Math.max(5, step - 4);
  ctx.textAlign = "left"; ctx.fillStyle = "#637485"; ctx.font = "10px system-ui"; ctx.fillText(app.state.cycle.is_zero ? "Übergang zum nächsten Zyklus" : "23 Quanten im aktuellen Tick", left, cy - 35);
  if (!app.state.cycle.is_zero) {
    for (let i = 0; i < 23; i++) {
      ctx.fillStyle = i === c.quant ? "#087f83" : i < c.quant ? "#b8dcd4" : "#e5edf1";
      ctx.beginPath(); const x = left + (i % cols) * step, y = cy - 20 + Math.floor(i / cols) * (box + 6);
      ctx.roundRect ? ctx.roundRect(x, y, box, box, 2) : ctx.rect(x, y, box, box); ctx.fill();
    }
  } else {
    const zero = Number(app.state.cycle.zero_length_q);
    for (let i = 0; i < zero; i++) {ctx.fillStyle = c.countdown === i - zero ? "#b86d32" : "#f5dfc4"; ctx.fillRect(left + i * 43, cy - 19, 35, 28); ctx.fillStyle = c.countdown === i - zero ? "#fff" : "#9b632f"; ctx.textAlign = "center"; ctx.font = "600 12px system-ui"; ctx.fillText(String(i - zero), left + i * 43 + 17, cy - 1);}
  }
}

function selectTab(name) {
  app.tab = name;
  document.querySelectorAll(".tab").forEach((el) => {const active = el.dataset.tab === name; el.classList.toggle("active", active); el.setAttribute("aria-selected", String(active)); el.tabIndex = active ? 0 : -1;});
  for (const id of ["overview", "residuals", "space", "definitions"]) $(`view-${id}`).hidden = id !== name;
  history.replaceState(null, "", `#${name}`);
  if (name === "residuals") loadSeries();
  if (name === "space") {loadPlanets(); drawPlanets();}
  if (name === "overview") drawCycle();
}

async function loadSeries() {
  if (!app.state) return;
  const mode = $("series-mode").value, seq = ++app.seriesSeq;
  let start = 0, count = mode === "year" ? 529 : 23;
  if (mode === "cycle") {
    start = Number(app.state.calendar.cycle_index);
    const end = app.meta.math.Z * app.meta.horizon.years;
    count = Math.min(768, end - start + 1);
  }
  try {
    const data = await api("/api/series", {mode, start, count});
    if (seq !== app.seriesSeq) return;
    app.series = data; clearError(); renderSeries();
  } catch (error) {if (seq === app.seriesSeq) showError(error);}
}

function renderSeries() {
  const s = app.series;
  $("series-mean").textContent = `${s.summary.mean_exact_q} q`;
  $("series-max").textContent = `${fnum(s.summary.max_abs_q, 6)} q`;
  $("series-range").textContent = `${fnum(s.summary.min_q, 4)} / ${fnum(s.summary.max_q, 4)} q`;
  $("series-count").textContent = fmt.format(s.summary.count);
  $("series-x-title").textContent = s.xlabel;
  $("series-table").innerHTML = s.points.slice(0, 100).map((p) => `<tr><td>${esc(p.x)}</td><td>${esc(p.exact_q)}</td><td>${fnum(p.q, 8)}</td><td>${fnum(p.seconds, 9)}</td><td>${p.extra_q === null ? "—" : qfmt(p.extra_q)}</td></tr>`).join("");
  drawResiduals();
}

function drawResiduals() {
  if (!app.series) return;
  const setup = canvasContext("residual-canvas"); if (!setup) return;
  const {ctx, width: w, height: h} = setup, pts = app.series.points, pad = {l:48, r:18, t:25, b:43};
  const pw = w - pad.l - pad.r, ph = h - pad.t - pad.b;
  const x = (i) => pad.l + i / Math.max(1, pts.length - 1) * pw;
  const y = (v) => pad.t + (.55 - v) / 1.1 * ph;
  ctx.font = "10px system-ui"; ctx.textAlign = "right";
  for (const tick of [-.5, -.25, 0, .25, .5]) {
    ctx.strokeStyle = tick === 0 ? "#aebec8" : "#e0e8ed"; ctx.lineWidth = 1; ctx.setLineDash(Math.abs(tick) === .5 ? [5, 4] : []); ctx.beginPath(); ctx.moveTo(pad.l, y(tick)); ctx.lineTo(w - pad.r, y(tick)); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "#738797"; ctx.fillText(fnum(tick, 2), pad.l - 10, y(tick) + 3);
  }
  ctx.fillStyle = "#738797"; ctx.textAlign = "left"; ctx.fillText("Rest in q", pad.l, 11);
  ctx.textAlign = "center";
  for (let i = 0; i <= 5; i++) {const j = Math.round(i / 5 * (pts.length - 1)); ctx.fillText(fmt.format(pts[j].x), x(j), h - 22);}
  ctx.fillText(app.series.xlabel, pad.l + pw / 2, h - 3);
  ctx.strokeStyle = pts.length > 100 ? "#68a9ab" : "#087f83"; ctx.lineWidth = pts.length > 100 ? .8 : 1.5;
  ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(x(i), y(p.q)) : ctx.moveTo(x(i), y(p.q))); ctx.stroke();
  if (pts.length <= 800) {ctx.fillStyle = "#087f83"; for (let i = 0; i < pts.length; i++) {ctx.beginPath(); ctx.arc(x(i), y(pts[i].q), pts.length > 100 ? 1.7 : 3.2, 0, 2 * Math.PI); ctx.fill();}}
  ctx.strokeStyle = "#ba8045"; ctx.setLineDash([5, 4]); ctx.beginPath(); ctx.moveTo(pad.l, y(app.series.summary.mean_q)); ctx.lineTo(w - pad.r, y(app.series.summary.mean_q)); ctx.stroke(); ctx.setLineDash([]);
  app.plotGeometry = {pad, pw, ph, width:w, height:h};
}

function download(name, content, mime) {
  const blob = new Blob([content], {type:mime}), url = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function loadPlanets() {
  if (!app.state) return;
  const q = app.state.q, seq = ++app.planetSeq;
  try {
    const data = await api("/api/planets", {q});
    if (seq !== app.planetSeq || q !== app.state.q) return;
    app.planets = data; renderPlanetUI(); drawPlanets();
  } catch (error) {if (seq === app.planetSeq) showError(error);}
}

function renderPlanetUI() {
  const p = app.planets;
  $("planet-date").textContent = prettyUTC(p.utc);
  $("planet-list").innerHTML = p.bodies.map((b) => `<button type="button" class="planet-item${b.id === app.selectedPlanet ? " selected" : ""}" data-planet="${esc(b.id)}" aria-pressed="${b.id === app.selectedPlanet}"><i class="planet-dot" style="background:${esc(b.color)}"></i><span>${esc(b.name)}</span><span class="distance">${fnum(b.distance_au, 2)} AU</span></button>`).join("");
  const b = p.bodies.find((b) => b.id === app.selectedPlanet) || p.bodies[0];
  $("planet-detail").innerHTML = `<h3>${esc(b.name)}</h3><p>${b.id === "earth" ? "Erdnäherung: Erde-Mond-Baryzentrum" : b.id === "sun" ? "Ursprung der heliozentrischen Darstellung" : "Heliozentrische Bahnnäherung"}</p><dl><dt>Sonnenabstand</dt><dd>${fnum(b.distance_au, 5)} AU</dd><dt>Große Halbachse</dt><dd>${fnum(b.a_au, 5)} AU</dd><dt>Exzentrizität</dt><dd>${fnum(b.eccentricity, 6)}</dd><dt>Bahnneigung</dt><dd>${fnum(b.inclination_deg, 4)}°</dd><dt>Umlaufnäherung</dt><dd>${b.period_days === null ? "—" : `${fnum(b.period_days, 2)} Tage`}</dd></dl><p class="position">x ${fnum(b.position_au[0], 6)}<br>y ${fnum(b.position_au[1], 6)}<br>z ${fnum(b.position_au[2], 6)} AU</p>`;
  $("planet-model-notes").textContent = `${p.model} · ${p.frame}. ${p.notes.join(" ")}`;
}

function transformedPosition(p) {
  if ($("distance-mode").value === "proportional") return p;
  const r = Math.hypot(...p);
  if (r < 1e-12) return [0,0,0];
  const scale = Math.log1p(r * 2.6) / r;
  return p.map((v) => v * scale);
}

function projection(p, w, h, maxR) {
  const [x,y,z] = transformedPosition(p), {yaw, pitch, zoom} = app.camera;
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
  const rx = x * cy - y * sy, ry = x * sy + y * cy;
  const py = ry * cp - z * sp, depth = ry * sp + z * cp;
  const perspective = 1 / Math.max(.3, 1 + depth / (maxR * 5));
  const scale = Math.min(w, h) * .39 / maxR * zoom;
  return {x:w * .5 + rx * scale * perspective, y:h * .51 + py * scale * perspective, z:depth, perspective};
}

function drawPlanets() {
  const setup = canvasContext("planet-canvas"); if (!setup) return;
  const {ctx,width:w,height:h} = setup;
  const gradient = ctx.createRadialGradient(w*.48,h*.45,0,w*.5,h*.5,Math.max(w,h)*.7); gradient.addColorStop(0,"#102a3d");gradient.addColorStop(1,"#05111c");ctx.fillStyle=gradient;ctx.fillRect(0,0,w,h);
  // Sterne sind nur ein deterministischer Hintergrund, keine Sternkarte.
  for (let i=0;i<105;i++) {const sx=((i*7919+233)%10007)/10007*w,sy=((i*3571+941)%9967)/9967*h;ctx.fillStyle=i%7===0?"#7492a755":"#8da9ba28";ctx.fillRect(sx,sy,i%7===0?1.5:1,i%7===0?1.5:1);}
  if (!app.planets) {ctx.fillStyle="#a8c1d1";ctx.textAlign="center";ctx.font="13px system-ui";ctx.fillText("Planetenbahnen werden geladen …",w/2,h/2);return;}
  const compressed=$("distance-mode").value==="compressed";
  const maxR=compressed?Math.log1p(32*2.6):32;
  const project=(p)=>projection(p,w,h,maxR);
  // Ekliptische Referenzachsen, räumlich durch dieselbe Kamera projiziert.
  for (const [axis,label,color] of [[[maxR*.30,0,0],"x", "#4a7888"],[[0,maxR*.30,0],"y","#4a7888"],[[0,0,maxR*.22],"z","#647ea3"]]) {
    const actual=compressed?axis.map(v=>v*3):axis,a=project([0,0,0]),b=project(actual);
    ctx.strokeStyle=color+"55";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();ctx.font="9px system-ui";ctx.fillStyle=color;ctx.textAlign="center";ctx.fillText(label,b.x+6,b.y-3);
  }
  for (const b of app.planets.bodies) {
    if (!b.orbit_au.length) continue;
    const selected=b.id===app.selectedPlanet;
    ctx.strokeStyle=selected?b.color+"ae":"#708fa44a";ctx.lineWidth=selected?1.4:.8;ctx.beginPath();
    b.orbit_au.forEach((point,i)=>{const p=project(point);i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y);});ctx.stroke();
  }
  const bodies=app.planets.bodies.map((b)=>({...b,projected:project(b.position_au)})).sort((a,b)=>b.projected.z-a.projected.z);
  app.planetHits=[];
  for (const b of bodies) {
    const p=b.projected, radius=clamp(Number(b.symbol_size)||5,3.5,16)*Math.sqrt(p.perspective);
    if (p.x<-70||p.x>w+70||p.y<-70||p.y>h+70)continue;
    if (b.id==="sun") {const glow=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,55);glow.addColorStop(0,"#ffca7088");glow.addColorStop(.3,"#ffbd4b22");glow.addColorStop(1,"#ffbd4b00");ctx.fillStyle=glow;ctx.fillRect(p.x-55,p.y-55,110,110);}
    if (b.id==="saturn") {ctx.save();ctx.translate(p.x,p.y);ctx.rotate(-.3);ctx.strokeStyle="#c4af8c99";ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(0,0,radius*1.85,radius*.60,0,0,Math.PI*2);ctx.stroke();ctx.restore();}
    const sphere=ctx.createRadialGradient(p.x-radius*.35,p.y-radius*.35,1,p.x,p.y,radius);sphere.addColorStop(0,b.color);sphere.addColorStop(.65,b.color);sphere.addColorStop(1,"#142431");ctx.fillStyle=sphere;ctx.beginPath();ctx.arc(p.x,p.y,radius,0,2*Math.PI);ctx.fill();
    if (b.id===app.selectedPlanet) {ctx.strokeStyle="#e4fff3";ctx.lineWidth=1;ctx.beginPath();ctx.arc(p.x,p.y,radius+5,0,2*Math.PI);ctx.stroke();}
    const label=b.id==="earth"?"Erde*":b.name;
    ctx.font="10px system-ui";ctx.fillStyle=b.id===app.selectedPlanet?"#e1fff5":"#c1d4e1";
    const labelWidth=ctx.measureText(label).width;
    const labelLeft=p.x+radius+7;
    ctx.textAlign=labelLeft+labelWidth>w-8?"right":"left";
    const labelX=ctx.textAlign==="right"?Math.max(labelWidth+8,p.x-radius-7):Math.max(8,labelLeft);
    ctx.fillText(label,labelX,clamp(p.y-5,12,h-9));
    app.planetHits.push({id:b.id,x:p.x,y:p.y,radius:Math.max(radius+9,13)});
  }
  $("space-scale").textContent=`Abstände ${compressed?"komprimiert":"proportional"} · Kugelgrößen symbolisch`;
}

function resetCamera(top=false) {app.camera={yaw:-.45,pitch:top?0:.80,zoom:1};drawPlanets();}
function zoomCamera(factor) {app.camera.zoom=clamp(app.camera.zoom*factor,.35,15);drawPlanets();}

function stopPlayback() {
  clearTimeout(app.sliderTimer);
  app.playing=false;
  $("play-button").textContent="▶ Zeit abspielen";
  $("play-button").setAttribute("aria-pressed","false");
}
function startPlayback() {
  clearTimeout(app.sliderTimer);
  if(!app.state||!app.meta)return;
  app.playing=true;app.animationStart=performance.now();app.animationQ=BigInt(app.state.q);
  $("play-button").textContent="Ⅱ Pause";$("play-button").setAttribute("aria-pressed","true");
}
async function animationTick() {
  if(!app.playing||app.animationBusy||document.hidden)return;
  const speed=Number($("speed-select").value),elapsed=(performance.now()-app.animationStart)/1000;
  let target=app.animationQ+BigInt(Math.floor(elapsed*speed*86400/app.meta.q_seconds.value));
  const max=BigInt(app.meta.horizon.end_q)-1n;
  const reached=target>=max;if(reached)target=max;
  app.animationBusy=true;
  await setState("/api/state",{q:target.toString()});
  app.animationBusy=false;
  if(reached){stopPlayback();notice("Ende des vereinbarten 966-Jahres-Horizonts erreicht.");}
}

function bindEvents() {
  $("date-form").addEventListener("submit",(e)=>{e.preventDefault();manualState("/api/date",{utc:$("utc-input").value.trim()});});
  $("q-form").addEventListener("submit",(e)=>{e.preventDefault();const q=$("q-input").value.trim();if(!/^\d+$/.test(q)){showError("Bitte eine nichtnegative ganze Zahl in q eingeben.");return;}manualState("/api/state",{q});});
  $("group-select").addEventListener("change",()=>{stopPlayback();app.group=Number($("group-select").value);if(app.state)setState("/api/state",{q:app.state.q});});
  document.querySelectorAll("[data-jump]").forEach((el)=>el.addEventListener("click",()=>{if(app.state)manualState("/api/jump",{q:app.state.q,unit:el.dataset.jump,delta:el.dataset.delta});}));
  document.querySelectorAll(".tab").forEach((el)=>el.addEventListener("click",()=>selectTab(el.dataset.tab)));
  document.querySelector(".tabs").addEventListener("keydown",(event)=>{if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;const tabs=Array.from(document.querySelectorAll(".tab")),idx=tabs.indexOf(document.activeElement);let next=event.key==="Home"?0:event.key==="End"?tabs.length-1:(idx+(event.key==="ArrowRight"?1:tabs.length-1))%tabs.length;event.preventDefault();tabs[next].focus();selectTab(tabs[next].dataset.tab);});
  $("levels-list").addEventListener("click",(event)=>{const row=event.target.closest("[data-level]");if(row){app.level=app.state.levels[Number(row.dataset.level)].key;renderLevels();}});
  $("time-slider").addEventListener("input",()=>{stopPlayback();clearTimeout(app.sliderTimer);const value=BigInt($("time-slider").value),bounds=app.sliderBounds;const q=bounds.lo+(bounds.hi-bounds.lo)*value/10000n;app.sliderTimer=setTimeout(()=>setState("/api/state",{q:q.toString()}),60);});
  $("series-mode").addEventListener("change",loadSeries);
  $("export-state").addEventListener("click",()=>{if(app.state)download(`zyklus23_q_${app.state.q}.json`,JSON.stringify({version:app.meta.version,...app.state},null,2),"application/json");});
  $("export-csv").addEventListener("click",()=>{if(!app.series)return;const rows=["index;rest_exact_q;rest_q;rest_seconds;extra_q",...app.series.points.map(p=>[p.x,p.exact_q,p.q,p.seconds,p.extra_q??""].join(";"))];download(`zyklus23_reste_${app.series.mode}.csv`,"\ufeff"+rows.join("\r\n"),"text/csv;charset=utf-8");});
  $("run-checks").addEventListener("click",async()=>{const button=$("run-checks");button.disabled=true;$("checks-output").textContent="Die Prüfungen laufen …";try{const result=await api("/api/checks");$("checks-output").innerHTML=result.checks.map(c=>`<div class="check-item"><span class="check-icon${c.passed?"":" fail"}">${c.passed?"✓":"×"}</span><strong>${esc(c.name)}</strong><small>${esc(c.detail)}</small></div>`).join("");}catch(e){showError(e);$("checks-output").textContent="Prüfung konnte nicht abgeschlossen werden.";}finally{button.disabled=false;}});
  $("play-button").addEventListener("click",()=>app.playing?stopPlayback():startPlayback());
  $("speed-select").addEventListener("change",()=>{if(app.playing)startPlayback();});
  $("planet-list").addEventListener("click",(event)=>{const button=event.target.closest("[data-planet]");if(button){app.selectedPlanet=button.dataset.planet;renderPlanetUI();drawPlanets();}});
  $("distance-mode").addEventListener("change",()=>{app.camera.zoom=1;drawPlanets();});
  $("camera-reset").addEventListener("click",()=>resetCamera());$("camera-top").addEventListener("click",()=>resetCamera(true));$("zoom-in").addEventListener("click",()=>zoomCamera(1.25));$("zoom-out").addEventListener("click",()=>zoomCamera(.8));
  const space=$("planet-canvas");
  space.addEventListener("wheel",(e)=>{e.preventDefault();zoomCamera(Math.exp(-e.deltaY*.001));},{passive:false});
  space.addEventListener("pointerdown",(e)=>{space.focus({preventScroll:true});space.setPointerCapture(e.pointerId);app.drag={x:e.clientX,y:e.clientY,yaw:app.camera.yaw,pitch:app.camera.pitch};app.lastPointerMoved=false;});
  space.addEventListener("pointermove",(e)=>{if(!app.drag)return;const dx=e.clientX-app.drag.x,dy=e.clientY-app.drag.y;if(Math.abs(dx)+Math.abs(dy)>4)app.lastPointerMoved=true;app.camera.yaw=app.drag.yaw+dx*.007;app.camera.pitch=clamp(app.drag.pitch+dy*.007,-Math.PI/2+.02,Math.PI/2-.02);drawPlanets();});
  space.addEventListener("pointerup",(e)=>{if(!app.lastPointerMoved){const r=space.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;const hit=[...app.planetHits].reverse().find(p=>Math.hypot(p.x-x,p.y-y)<=p.radius);if(hit){app.selectedPlanet=hit.id;renderPlanetUI();drawPlanets();}}app.drag=null;});
  space.addEventListener("pointercancel",()=>{app.drag=null;});
  space.addEventListener("keydown",(e)=>{if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","+","=","-","0"].includes(e.key))return;e.preventDefault();if(e.key==="ArrowLeft")app.camera.yaw-=.1;if(e.key==="ArrowRight")app.camera.yaw+=.1;if(e.key==="ArrowUp")app.camera.pitch=clamp(app.camera.pitch-.1,-1.55,1.55);if(e.key==="ArrowDown")app.camera.pitch=clamp(app.camera.pitch+.1,-1.55,1.55);if(e.key==="+"||e.key==="=")zoomCamera(1.2);if(e.key==="-")zoomCamera(1/1.2);if(e.key==="0")resetCamera();drawPlanets();});
  $("residual-canvas").addEventListener("pointermove",(e)=>{if(!app.series||!app.plotGeometry)return;const r=e.currentTarget.getBoundingClientRect(),g=app.plotGeometry;const i=clamp(Math.round((e.clientX-r.left-g.pad.l)/g.pw*(app.series.points.length-1)),0,app.series.points.length-1),p=app.series.points[i],tip=$("plot-tooltip");tip.innerHTML=`${esc(app.series.xlabel)} ${esc(p.x)}<br>ρ = ${esc(p.exact_q)} q<br>${fnum(p.seconds*1000,6)} ms`;tip.hidden=false;tip.style.left=`${clamp(e.clientX-r.left+12,0,r.width-165)}px`;tip.style.top=`${clamp(e.clientY-r.top-45,5,r.height-65)}px`;});
  $("residual-canvas").addEventListener("pointerleave",()=>{$("plot-tooltip").hidden=true;});
  const resize=new ResizeObserver(()=>{drawCycle();drawResiduals();drawPlanets();});for(const id of ["cycle-canvas","residual-canvas","planet-canvas"])resize.observe($(id));
  document.addEventListener("visibilitychange",()=>{if(document.hidden&&app.playing)stopPlayback();});
  setInterval(animationTick,220);
}

async function init() {
  bindEvents();
  try {
    app.meta=await api("/api/overview");app.group=app.meta.default_group;renderMeta();
    await setState("/api/state",{q:"0"});
    const requested=location.hash.slice(1);if(["overview","residuals","space","definitions"].includes(requested))selectTab(requested);
  } catch(error){showError(error);$("utc-display").textContent="Lokaler Rechenkern nicht erreichbar";$("coordinate-display").textContent="Bitte den Viewer mit python START.py starten und die angezeigte lokale Adresse öffnen.";}
}
init();
