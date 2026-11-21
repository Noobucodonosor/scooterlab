import { WorkshopViewer } from "/workshop_viewer.js";

const state = {
  overview: null,
  activeProcId: "service_30k",
  activeStepIdx: 0,
  activePart: "underseat_tub",
  currentSession: null,
  token: sessionStorage.getItem("scooterlab_token") || "",
};

const esc = (s) =>
  String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("is-show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => el.classList.remove("is-show"), 2800);
}

async function apiFetch(url, opts = {}) {
  const headers = new Headers(opts.headers || {});
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
  const resp = await fetch(url, { ...opts, headers });
  if (resp.status === 401) {
    document.getElementById("auth-banner").style.display = "block";
    throw new Error("Autenticazione Bearer richiesta");
  }
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
  document.getElementById("auth-banner").style.display = "none";
  return data;
}

// --- Workshop Atlas & GLB Viewer Setup ---
const viewer = new WorkshopViewer({
  atlasViewport: document.getElementById("atlas-viewport"),
  atlasImg: document.getElementById("atlas-img"),
  glbCanvas: document.getElementById("glb-canvas"),
  onSelectPart: (partId) => {
    state.activePart = partId;
    renderOemParts();
  },
  onSelectPlate: (plate) => {
    document.getElementById("active-part-label").textContent = `${plate.source_tag} ${plate.source_pdf} · p.${plate.page}`;
    document.getElementById("plate-meta").textContent = plate.description;
    document.getElementById("atlas-missing").style.display = plate.available ? "none" : "block";
    document.getElementById("atlas-img").style.display = plate.available ? "block" : "none";
    highlightPlateChips(plate.id);
  },
});

function highlightPlateChips(plateId) {
  document.querySelectorAll("#part-chips .chip").forEach((el) => {
    el.classList.toggle("is-active", el.dataset.plate === plateId);
  });
}

function renderPlateChips() {
  const plates = state.overview?.atlas_plates || [];
  const wrap = document.getElementById("part-chips");
  wrap.innerHTML = plates
    .map(
      (p) =>
        `<button class="chip ${viewer.activePlate?.id === p.id ? "is-active" : ""}" data-plate="${esc(p.id)}" type="button">${esc(p.title)}</button>`
    )
    .join("");
  wrap.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchViewerMode("atlas");
      viewer.selectPlateById(btn.dataset.plate);
    });
  });
}

function renderOemParts() {
  const catalog = state.overview?.oem_parts || [];
  const showAll = document.getElementById("oem-all-toggle").checked;
  const query = (document.getElementById("oem-search").value || "").trim().toLowerCase();

  const filtered = catalog.filter((item) => {
    if (!showAll && !query && item.focus_part !== state.activePart) return false;
    if (query) {
      const hay = `${item.code} ${item.name} ${item.equivalent} ${item.spec}`.toLowerCase();
      return hay.includes(query);
    }
    return true;
  });

  const list = document.getElementById("oem-list");
  if (!filtered.length) {
    list.innerHTML = `<div class="muted">Nessun ricambio specifico per questa vista. Spunta <strong>Mostra tutti</strong> per l'intero catalogo SYM.</div>`;
    return;
  }

  list.innerHTML = filtered
    .map(
      (item) => `
      <div class="oem-item">
        <div style="flex:1 1 260px;">
          <div><code class="badge mono">${esc(item.code)}</code> <strong>${esc(item.name)}</strong> <span class="badge mono">${esc(item.source)}</span></div>
          <div class="muted" style="margin-top:4px;">Equiv: ${esc(item.equivalent)} · ${esc(item.spec)}</div>
        </div>
        <div class="control-group">
          <button class="btn btn--sm js-copy-code" data-code="${esc(item.code)}" type="button">Copia codice</button>
          <a class="btn btn--sm btn--primary" href="${esc(item.microfiche_url)}" target="_blank" rel="noopener">Esploso Microfiche</a>
        </div>
      </div>`
    )
    .join("");

  list.querySelectorAll(".js-copy-code").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.code);
        showToast(`Copiato codice OEM: ${btn.dataset.code}`);
      } catch {
        showToast(`Codice: ${btn.dataset.code}`);
      }
    });
  });
}

function switchViewerMode(mode) {
  const isGlb = mode === "glb";
  document.getElementById("mode-atlas").classList.toggle("btn--primary", !isGlb);
  document.getElementById("mode-glb").classList.toggle("btn--primary", isGlb);

  const atlasVp = document.getElementById("atlas-viewport");
  const glbCanvas = document.getElementById("glb-canvas");
  const glbEmpty = document.getElementById("glb-empty");

  if (!isGlb) {
    atlasVp.style.display = "flex";
    glbCanvas.style.display = "none";
    glbEmpty.style.display = "none";
    viewer.setMode("atlas");
  } else {
    atlasVp.style.display = "none";
    const hasGlb = Boolean(state.overview?.has_custom_glb);
    glbCanvas.style.display = hasGlb ? "block" : "none";
    glbEmpty.style.display = hasGlb ? "none" : "block";
    viewer.setMode("glb");
  }
}

// --- Tabs Navigation ---
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach((b) => b.setAttribute("aria-selected", String(b === btn)));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("is-active", p.id === `tab-${tab}`));
  });
});

// --- Procedures & Guided Atlas Sync ---
function renderProcedures() {
  if (!state.overview) return;
  const procs = state.overview.procedures || [];
  const progressMap = state.overview.procedure_progress || {};
  const tabsEl = document.getElementById("proc-tabs");
  const stepsEl = document.getElementById("proc-steps");

  const activeProc = procs.find((p) => p.id === state.activeProcId) || procs[0];
  if (!activeProc) return;
  state.activeProcId = activeProc.id;

  tabsEl.innerHTML = procs
    .map(
      (p) =>
        `<button class="chip ${p.id === activeProc.id ? "is-active" : ""}" data-proc="${esc(p.id)}" type="button">${esc(p.title)}</button>`
    )
    .join("");
  tabsEl.querySelectorAll("button").forEach((b) => {
    b.addEventListener("click", () => {
      state.activeProcId = b.dataset.proc;
      state.activeStepIdx = 0;
      renderProcedures();
    });
  });

  const doneSet = new Set(progressMap[activeProc.id] || []);
  document.getElementById("proc-meta").textContent = `${activeProc.category} · ${activeProc.duration} — ${activeProc.summary}`;
  document.getElementById("proc-progress-badge").textContent = `${doneSet.size} / ${activeProc.steps.length} completati`;

  const selectedStep = activeProc.steps[state.activeStepIdx] || activeProc.steps[0];
  if (selectedStep && selectedStep.focus_part) {
    viewer.focusPart(selectedStep.focus_part);
  }

  stepsEl.innerHTML = activeProc.steps
    .map((st, idx) => {
      const isSel = idx === state.activeStepIdx;
      const isDone = doneSet.has(idx);
      return `
        <div class="step-item ${isSel ? "is-selected" : ""} ${isDone ? "is-done" : ""}" data-idx="${idx}">
          <div class="step-item__head">
            <span>${esc(st.title)}</span>
            <span class="badge ${isDone ? "badge--ok" : ""}">${isDone ? "FATTO" : "DA FARE"}</span>
          </div>
          ${
            isSel
              ? `<div class="step-detail">
                  <div class="control-group" style="margin-bottom:8px;">
                    <span class="badge">Attrezzi: ${esc(st.tools)}</span>
                    <span class="badge mono">${esc(st.torque_spec)}</span>
                  </div>
                  <p style="margin:6px 0;">${esc(st.detail)}</p>
                  <div class="alert-box"><strong>Attenzione:</strong> ${esc(st.warning)}</div>
                  <div class="control-group" style="margin-top:8px;">
                    <button class="btn btn--primary btn--sm js-toggle-step" data-done="${isDone ? "0" : "1"}" type="button">
                      ${isDone ? "Segna da fare" : "Segna Fatto ✓ & Avanti"}
                    </button>
                  </div>
                </div>`
              : ""
          }
        </div>
      `;
    })
    .join("");

  stepsEl.querySelectorAll(".step-item").forEach((el) => {
    el.addEventListener("click", (e) => {
      if (e.target.closest(".js-toggle-step")) return;
      state.activeStepIdx = Number(el.dataset.idx);
      renderProcedures();
    });
  });

  const toggleBtn = stepsEl.querySelector(".js-toggle-step");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", async () => {
      const done = toggleBtn.dataset.done === "1";
      try {
        const res = await apiFetch("/api/garage/procedure", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ proc_id: activeProc.id, step_idx: state.activeStepIdx, done }),
        });
        state.overview.procedure_progress = res.procedure_progress;
        if (done && state.activeStepIdx < activeProc.steps.length - 1) {
          state.activeStepIdx += 1;
        }
        renderProcedures();
        showToast(done ? "Step salvato come completato" : "Step ripristinato");
      } catch (err) {
        showToast(err.message);
      }
    });
  }
}

// --- Telemetry & Charts ---
function renderSessionSelectors() {
  if (!state.overview) return;
  const sessions = (state.overview.sessions || []).filter((s) => !s.corrupt);
  const sessSel = document.getElementById("sess-select");
  const baseSel = document.getElementById("base-select");

  if (!sessions.length) {
    sessSel.innerHTML = `<option value="">Nessuna sessione (.slab)</option>`;
    baseSel.innerHTML = `<option value="">Nessuna baseline</option>`;
    renderEmptyTelemetry();
    return;
  }

  const prevSess = state.currentSession || sessions[0].name;
  const prevBase = state.overview.baseline_session || "";
  sessSel.innerHTML = sessions
    .map((s) => `<option value="${esc(s.name)}" ${s.name === prevSess ? "selected" : ""}>${esc(s.name)} (${s.distance_km} km)</option>`)
    .join("");
  baseSel.innerHTML =
    `<option value="">Nessuna baseline A/B</option>` +
    sessions
      .map((s) => `<option value="${esc(s.name)}" ${s.name === prevBase ? "selected" : ""}>${esc(s.name)}</option>`)
      .join("");

  state.currentSession = sessSel.value;
  loadSessionDetail();
}

function renderEmptyTelemetry() {
  document.getElementById("kpi-grid").innerHTML = `
    <div class="kpi-card" style="grid-column:1/-1;">
      <div class="kpi-card__k">Nessun file .slab presente</div>
      <p class="muted" style="margin:6px 0 0;">Premi <strong>"Genera Demo A/B da Casa"</strong> per provare subito telemetria, confronto rulli, FFT e mappa offline, oppure carica un file <code>.slab</code>.</p>
    </div>`;
  ["svg-speed", "svg-fft", "svg-track"].forEach((id) => {
    document.getElementById(id).innerHTML = `<text x="20" y="110" fill="#9e9d99" font-size="13">In attesa di una sessione .slab...</text>`;
  });
}

async function loadSessionDetail() {
  const name = document.getElementById("sess-select").value;
  if (!name) return;
  state.currentSession = name;
  const base = document.getElementById("base-select").value;
  const priv = document.getElementById("privacy-toggle").checked ? "1" : "0";
  const rec = document.getElementById("recover-toggle").checked ? "1" : "0";

  const q = new URLSearchParams({ privacy: priv, recover: rec });
  if (base && base !== name) q.set("baseline", base);

  try {
    const data = await apiFetch(`/api/sessions/${encodeURIComponent(name)}?${q.toString()}`);
    renderTelemetryData(data);
  } catch (err) {
    showToast(err.message);
  }
}

function fmtDelta(val, unit, invert = false) {
  if (val === null || val === undefined) return "";
  const sign = val > 0 ? "+" : "";
  const good = invert ? val < 0 : val > 0;
  return `<span class="${good ? "delta-pos" : "delta-neg"}">(${sign}${val}${unit})</span>`;
}

function renderTelemetryData(d) {
  const k = d.kpi;
  const dl = d.deltas || {};
  const hs = d.health_summary || {};
  const regStr = hs.vbat_min_v ? `${hs.vbat_min_v}–${hs.vbat_max_v} V (${hs.regulator_ok ? "OK" : "CHECK"})` : "—";

  document.getElementById("kpi-grid").innerHTML = `
    <div class="kpi-card"><div class="kpi-card__k">0–50 km/h</div><div class="kpi-card__v">${k.zero_to_50_s !== null ? `${k.zero_to_50_s} s` : "—"} ${fmtDelta(dl.zero_to_50_s, "s", true)}</div></div>
    <div class="kpi-card"><div class="kpi-card__k">Velocità Max</div><div class="kpi-card__v">${k.max_speed_kmh} km/h ${fmtDelta(dl.max_speed_kmh, " km/h")}</div></div>
    <div class="kpi-card"><div class="kpi-card__k">Distanza / Durata</div><div class="kpi-card__v">${k.distance_km} km · ${k.duration_s}s</div></div>
    <div class="kpi-card"><div class="kpi-card__k">Piega Max SX / DX</div><div class="kpi-card__v">${k.max_lean_left_deg}° / ${k.max_lean_right_deg}°</div></div>
    <div class="kpi-card"><div class="kpi-card__k">Comfort RMS</div><div class="kpi-card__v">${k.comfort_rms_g} g ${fmtDelta(dl.comfort_rms_g, "g", true)}</div></div>
    <div class="kpi-card"><div class="kpi-card__k">Vibrazione / Regolatore</div><div class="kpi-card__v">${k.dominant_vib_hz} Hz · ${esc(regStr)}</div></div>
  `;

  const sp = d.speed_series || [];
  const sSvg = document.getElementById("svg-speed");
  if (sp.length >= 2) {
    const tMax = Math.max(...sp.map((p) => p.t_s), 1);
    const vMax = Math.max(...sp.map((p) => p.kmh), 60);
    const pts = sp.map((p) => `${(30 + (p.t_s / tMax) * 550).toFixed(1)},${(195 - (p.kmh / vMax) * 165).toFixed(1)}`).join(" ");
    sSvg.innerHTML = `
      <line x1="30" y1="195" x2="580" y2="195" stroke="#5a5850" />
      <polyline fill="none" stroke="#60a5fa" stroke-width="2.4" points="${pts}" />
      <text x="32" y="20" fill="#dfdedb" font-size="11">Max ${k.max_speed_kmh} km/h · Media ${k.avg_speed_kmh} km/h</text>`;
    document.getElementById("speed-meta").textContent = `${sp.length} campioni`;
  } else {
    sSvg.innerHTML = `<text x="20" y="110" fill="#9e9d99" font-size="13">Dati GPS insufficienti (fix >= 2 richiesto).</text>`;
  }

  const fft = d.spectrum_series || [];
  const fSvg = document.getElementById("svg-fft");
  if (fft.length >= 2) {
    const fMax = d.nyquist_hz || 50;
    const pMax = Math.max(...fft.map((p) => p.power), 1e-6);
    const pts = fft.map((p) => `${(30 + (p.hz / fMax) * 550).toFixed(1)},${(195 - (p.power / pMax) * 165).toFixed(1)}`).join(" ");
    fSvg.innerHTML = `
      <line x1="30" y1="195" x2="580" y2="195" stroke="#5a5850" />
      <polyline fill="none" stroke="#f59e0b" stroke-width="2.2" points="${pts}" />
      <text x="32" y="20" fill="#dfdedb" font-size="11">Picco ${k.dominant_vib_hz} Hz (Nyquist ${fMax} Hz)</text>`;
    document.getElementById("fft-meta").textContent = `0–${fMax} Hz`;
  } else {
    fSvg.innerHTML = `<text x="20" y="110" fill="#9e9d99" font-size="13">Dati IMU insufficienti per FFT.</text>`;
  }

  const tr = d.gps_track || [];
  const tSvg = document.getElementById("svg-track");
  if (tr.length >= 2) {
    const xs = tr.map((p) => p.x);
    const ys = tr.map((p) => p.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const span = Math.max(maxX - minX, maxY - minY, 10);
    const pts = tr
      .map((p) => `${(60 + ((p.x - minX) / span) * 480).toFixed(1)},${(195 - ((p.y - minY) / span) * 165).toFixed(1)}`)
      .join(" ");
    tSvg.innerHTML = `
      <polyline fill="none" stroke="#34d399" stroke-width="2.8" points="${pts}" />
      <text x="24" y="20" fill="#dfdedb" font-size="11">Traccia locale offline (coordinate relative m)</text>`;
    document.getElementById("track-meta").textContent = d.privacy_trim_m > 0 ? `Privacy ${d.privacy_trim_m}m attiva` : "Traccia completa";
  } else {
    tSvg.innerHTML = `<text x="20" y="110" fill="#9e9d99" font-size="13">Traccia GPS troppo breve per Privacy Zone.</text>`;
  }
}

// --- Check-Up Fabbrica & Tagliandi ---
function renderCheckupAndMaintenance() {
  if (!state.overview) return;
  const specs = state.overview.factory_specs || [];
  const checks = state.overview.factory_checks || {};

  document.getElementById("specs-list").innerHTML = specs
    .map((s) => {
      const saved = checks[s.id];
      const badgeCls = saved ? (saved.status === "OK" ? "badge--ok" : saved.status === "WARNING" ? "badge--warn" : "badge--err") : "";
      return `
        <div class="spec-row" data-spec="${esc(s.id)}">
          <div>
            <strong>${esc(s.label)}</strong> <span class="badge mono">${esc(s.source)}</span>
            <div class="muted mono">Specifica: ${esc(s.nominal)} ${esc(s.unit)}</div>
          </div>
          <input type="number" step="0.01" placeholder="${esc(s.unit)}" value="${saved ? esc(saved.value) : ""}" />
          <button class="btn btn--sm btn--primary js-check-btn" type="button">Verifica</button>
          <div class="spec-row__res">${saved ? `<span class="badge ${badgeCls}">${esc(saved.status)}</span> ${esc(saved.message)}` : `<span class="muted">${esc(s.hint)}</span>`}</div>
        </div>`;
    })
    .join("");

  document.querySelectorAll(".js-check-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const row = btn.closest(".spec-row");
      const val = parseFloat(row.querySelector("input").value);
      if (Number.isNaN(val)) {
        showToast("Inserisci un valore numerico valido");
        return;
      }
      try {
        const res = await apiFetch("/api/garage/check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ spec_id: row.dataset.spec, value: val }),
        });
        state.overview.factory_checks[row.dataset.spec] = res.result;
        renderCheckupAndMaintenance();
        showToast(`Check ${res.result.status}: ${res.result.spec_id}`);
      } catch (err) {
        showToast(err.message);
      }
    });
  });

  const MAINT_LABELS = {
    olio_motore: "Olio Motore (0,70 L SAE 10W-30)",
    olio_trasmissione: "Olio Trasmissione (170 cc 85W-140)",
    filtro_aria: "Filtro Aria (17211-ADB-000)",
    filtro_pompa_benzina: "Filtro Pompa Benzina",
    cinghia_rulli_candela: "Cinghia, Rulli 18×14 & Candela CR7HSA",
  };
  const sched = state.overview.maintenance_schedule || [];
  document.getElementById("maint-schedule").innerHTML = sched
    .map((m) => {
      const pct = Math.max(0, Math.min(100, 100 - (m.remaining_km / m.interval_km) * 100));
      const cls = m.status === "OK" ? "badge--ok" : m.status === "DUE_SOON" ? "badge--warn" : "badge--err";
      const title = MAINT_LABELS[m.item] || m.item;
      return `
        <div style="margin-bottom:10px;">
          <div class="toolbar-row">
            <strong>${esc(title)}</strong>
            <span class="badge ${cls} mono">${esc(m.status)} · ${m.remaining_km} km</span>
          </div>
          <div class="progress-bar"><div class="progress-bar__fill" style="width:${pct.toFixed(0)}%"></div></div>
          <div class="muted mono">Prossima scadenza: ${m.next_due_km} km (ogni ${m.interval_km} km)</div>
        </div>`;
    })
    .join("");

  const log = state.overview.maintenance_log || [];
  document.getElementById("maint-log").innerHTML = log.length
    ? log.map((e) => `<div style="padding:6px 0;border-bottom:1px solid var(--line);"><strong>${esc(e.item)}</strong> · <span class="mono">${e.km} km</span> <span class="muted">(${esc(e.notes || "—")})</span></div>`).join("")
    : "Nessun intervento registrato.";
}

function renderDeviceInfo() {
  if (!state.overview) return;
  const info = state.overview.server_info || {};
  const sessions = state.overview.sessions || [];
  const platesAvail = (state.overview.atlas_plates || []).filter((p) => p.available).length;
  const platesTotal = (state.overview.atlas_plates || []).length;
  document.getElementById("device-status").innerHTML = `
    <div><span class="badge ${info.tls_enabled ? "badge--ok" : "badge--warn"}">HTTPS TLS: ${info.tls_enabled ? "ATTIVO" : "Locale HTTP (usa gen_local_tls.sh)"}</span></div>
    <div><span class="badge ${info.mqtt_enabled ? "badge--ok" : ""}">MQTT / Mini-UNS: ${info.mqtt_enabled ? "ATTIVO" : "Opzionale (off)"}</span></div>
    <div><span class="badge ${platesAvail === platesTotal ? "badge--ok" : "badge--warn"}">Tavole Esplose SYM: ${platesAvail} / ${platesTotal} estratte</span></div>
    <div class="mono muted">Sessioni archiviate: ${sessions.length} · Odometro corrente: ${state.overview.odometer_km} km</div>
  `;
}

// --- Load Overview & Wire Events ---
async function refreshOverview() {
  try {
    state.overview = await apiFetch("/api/overview");
    document.getElementById("odom-input").value = state.overview.odometer_km;
    document.getElementById("maint-km").value = state.overview.odometer_km;
    viewer.setCatalog(state.overview.atlas_plates || [], state.overview.has_custom_glb);
    renderPlateChips();
    renderProcedures();
    renderOemParts();
    renderSessionSelectors();
    renderCheckupAndMaintenance();
    renderDeviceInfo();
  } catch (err) {
    showToast(err.message);
  }
}

document.getElementById("token-save").addEventListener("click", () => {
  state.token = document.getElementById("token-input").value.trim();
  sessionStorage.setItem("scooterlab_token", state.token);
  refreshOverview();
});

document.getElementById("odom-save").addEventListener("click", async () => {
  const val = parseFloat(document.getElementById("odom-input").value);
  if (Number.isNaN(val)) return;
  try {
    await apiFetch("/api/garage/odometer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ odometer_km: val }),
    });
    showToast("Odometro aggiornato");
    refreshOverview();
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("maint-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiFetch("/api/garage/maintenance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        item: document.getElementById("maint-item").value,
        km: parseFloat(document.getElementById("maint-km").value),
        notes: document.getElementById("maint-notes").value,
      }),
    });
    document.getElementById("maint-item").value = "";
    document.getElementById("maint-notes").value = "";
    showToast("Intervento registrato");
    refreshOverview();
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("mode-atlas").addEventListener("click", () => switchViewerMode("atlas"));
document.getElementById("mode-glb").addEventListener("click", () => switchViewerMode("glb"));
document.getElementById("btn-zoom-in").addEventListener("click", () => viewer.zoomBy(0.35));
document.getElementById("btn-zoom-out").addEventListener("click", () => viewer.zoomBy(-0.35));
document.getElementById("btn-reset3d").addEventListener("click", () => viewer.resetView());

document.getElementById("oem-search").addEventListener("input", renderOemParts);
document.getElementById("oem-all-toggle").addEventListener("change", renderOemParts);

document.getElementById("glb-file-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const headers = { "Content-Type": "application/octet-stream" };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const resp = await fetch("/api/models/upload", { method: "POST", headers, body: file });
  const data = await resp.json();
  if (!resp.ok) {
    showToast(`Errore .glb: ${data.error}`);
    return;
  }
  showToast("Modello 3D .glb caricato in locale");
  await refreshOverview();
  switchViewerMode("glb");
});

document.getElementById("sess-select").addEventListener("change", loadSessionDetail);
document.getElementById("base-select").addEventListener("change", async (e) => {
  const b = e.target.value || null;
  await apiFetch("/api/garage/baseline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session: b }),
  });
  loadSessionDetail();
});
document.getElementById("privacy-toggle").addEventListener("change", loadSessionDetail);
document.getElementById("recover-toggle").addEventListener("change", loadSessionDetail);

document.getElementById("btn-demo").addEventListener("click", async () => {
  try {
    await apiFetch("/api/sessions/demo", { method: "POST" });
    showToast("Create 2 sessioni demo A/B (Pre-Tagliando vs Rulli Nuovi)");
    await refreshOverview();
    const post = (state.overview.sessions || []).find((s) => s.name === "demo_post_rulli.slab");
    if (post) {
      document.getElementById("sess-select").value = post.name;
      loadSessionDetail();
    }
  } catch (err) {
    showToast(err.message);
  }
});

async function uploadBrowserFile(file) {
  if (!file) return;
  const rec = document.getElementById("recover-toggle").checked ? "1" : "0";
  const headers = {
    "X-Session-Name": file.name.endsWith(".slab") ? file.name : `${file.name}.slab`,
    "X-Recover": rec,
    "Content-Type": "application/octet-stream",
  };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const resp = await fetch("/api/sessions/upload", { method: "POST", headers, body: file });
  const data = await resp.json();
  if (!resp.ok) {
    showToast(`Errore upload: ${data.error}`);
    return;
  }
  state.currentSession = data.session;
  showToast(`Caricata sessione ${data.session}`);
  refreshOverview();
}

const dz = document.getElementById("dropzone");
dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("is-drag"); });
dz.addEventListener("dragleave", () => dz.classList.remove("is-drag"));
dz.addEventListener("drop", (e) => {
  e.preventDefault();
  dz.classList.remove("is-drag");
  uploadBrowserFile(e.dataTransfer.files[0]);
});
document.getElementById("file-input").addEventListener("change", (e) => uploadBrowserFile(e.target.files[0]));

refreshOverview();
