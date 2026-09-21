const state = {
  period: "all",
  dashboardCache: null,
  historyData: null,
  currentDqNumber: null,
  navStack: ["tab-search"],
  charts: {}, // именованные инстансы Chart.js, чтобы можно было destroy() перед перерисовкой
};

const PALETTE = ["#5b8ba0", "#b5651d", "#7a8450", "#9c6b9e", "#4f9d8a", "#c9a227", "#8f5a4a", "#5a7fb5", "#8b8b8b"];
const TEXT_DIM = "#8b939b";
const BORDER = "#2b3137";
const AMBER = "#f2a93b";

function destroyChart(name) {
  if (state.charts[name]) {
    state.charts[name].destroy();
    state.charts[name] = null;
  }
}

function showToast(message, isError = false) {
  const toast = document.getElementById("m-toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.remove("show"), 3800);
}

function money(n) {
  return (n ?? 0).toLocaleString("az-AZ", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function canViewHistory() {
  const role = window.CURRENT_USER && window.CURRENT_USER.role;
  return role === "admin" || role === "viewer_full";
}
function isAdmin() {
  return window.CURRENT_USER && window.CURRENT_USER.role === "admin";
}

async function api(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Xəta baş verdi");
  return data;
}

// ---------- Навигация по вкладкам ----------
function showTab(id) {
  document.querySelectorAll(".m-tab").forEach((el) => el.classList.toggle("active", el.id === id));
  document.querySelectorAll(".m-tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === id);
  });
}

document.querySelectorAll(".m-tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.navStack = [btn.dataset.tab];
    showTab(btn.dataset.tab);
  });
});

document.querySelectorAll("[data-back]").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.navStack.pop();
    showTab(state.navStack[state.navStack.length - 1] || "tab-summary");
  });
});

function pushTab(id) {
  state.navStack.push(id);
  showTab(id);
}

// ---------- Setup by role ----------
(function setupTabsForRole() {
  const tabbar = document.getElementById("m-tabbar");
  if (!canViewHistory()) {
    tabbar.querySelector('[data-tab="tab-search"]').remove();
  }
  if (!isAdmin()) {
    tabbar.querySelector('[data-tab="tab-maintenance"]')?.remove();
  }
})();

// ================= AXTAR =================
let searchTimer = null;
document.getElementById("m-search-input")?.addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => runSearch(e.target.value.trim()), 250);
});

let searchViewMode = "brand";
let searchCache = [];

async function runSearch(q) {
  const empty = document.getElementById("m-search-empty");
  const results = document.getElementById("m-search-results");
  const backBtn = document.getElementById("m-search-back-btn");
  results.innerHTML = '<p class="m-hint">Yüklənir...</p>';
  backBtn.classList.add("hidden");
  try {
    const matches = await api(`/api/equipment/search?q=${encodeURIComponent(q)}`);
    searchCache = matches;
    empty.classList.toggle("hidden", matches.length > 0);

    if (q) {
      renderSearchFlatList(matches);
    } else if (searchViewMode === "brand") {
      renderSearchBrandList();
    } else {
      renderSearchFlatList(matches);
    }
  } catch (err) {
    results.innerHTML = "";
    showToast(err.message, true);
  }
}

function renderSearchFlatList(matches) {
  const results = document.getElementById("m-search-results");
  results.innerHTML = "";
  for (const m of matches) {
    const card = document.createElement("div");
    card.className = "m-card";
    card.innerHTML = `
      <div class="m-card-main">
        <span class="m-card-title">${m.dq_number}</span>
        <span class="m-card-sub">${m.nv_type} · ${m.contractors.join(", ")}</span>
      </div>
      <span class="m-card-value">›</span>`;
    card.addEventListener("click", () => openHistory(m.dq_number));
    results.appendChild(card);
  }
}

function renderSearchBrandList() {
  document.getElementById("m-search-back-btn").classList.add("hidden");
  const brands = {};
  for (const m of searchCache) {
    brands[m.brand] = (brands[m.brand] || 0) + 1;
  }
  const results = document.getElementById("m-search-results");
  results.innerHTML = "";
  for (const [brand, count] of Object.entries(brands).sort((a, b) => b[1] - a[1])) {
    const card = document.createElement("div");
    card.className = "m-card";
    card.innerHTML = `
      <div class="m-card-main"><span class="m-card-title">${brand}</span></div>
      <span class="m-card-value">${count} ədəd ›</span>`;
    card.addEventListener("click", () => renderSearchBrandEquipment(brand));
    results.appendChild(card);
  }
}

function renderSearchBrandEquipment(brand) {
  const backBtn = document.getElementById("m-search-back-btn");
  backBtn.classList.remove("hidden");
  backBtn.onclick = renderSearchBrandList;
  renderSearchFlatList(searchCache.filter((m) => m.brand === brand));
}

document.querySelectorAll('#tab-search .m-chip[data-view]').forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll('#tab-search .m-chip[data-view]').forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    searchViewMode = chip.dataset.view;
    document.getElementById("m-search-input").value = "";
    runSearch("");
  });
});

// ================= XÜLASƏ =================
async function loadPeriods() {
  const periods = await api("/api/periods");
  const select = document.getElementById("m-period-select");
  select.innerHTML = '<option value="all">Bütün dövrlər</option>';
  for (const p of periods) {
    const opt = document.createElement("option");
    opt.value = p.value;
    opt.textContent = p.label;
    select.appendChild(opt);
  }
  if (periods.length) select.value = periods[0].value;
  state.period = select.value;
  return periods;
}

document.getElementById("m-period-select")?.addEventListener("change", (e) => {
  state.period = e.target.value;
  loadSummary();
});

async function loadSummary() {
  const list = document.getElementById("m-summary-list");
  list.innerHTML = '<p class="m-hint">Yüklənir...</p>';
  try {
    const data = await api(`/api/dashboard?period=${encodeURIComponent(state.period)}`);
    state.dashboardCache = data;
    list.innerHTML = "";
    for (const c of data) {
      const eqCount = c.equipment_count;
      const card = document.createElement("div");
      card.className = "m-card";
      card.innerHTML = `
        <div class="m-card-main">
          <span class="m-card-title">${c.contractor}</span>
          <span class="m-card-sub">${eqCount} texnika</span>
        </div>
        <span class="m-card-value">${money(c.total)}<span class="unit">AZN</span></span>`;
      card.addEventListener("click", () => openBrandList(c));
      list.appendChild(card);
    }
  } catch (err) {
    showToast(err.message, true);
  }
}

function openBrandList(contractor) {
  state.currentContractor = contractor;
  document.getElementById("m-brand-title").textContent = contractor.contractor;
  const list = document.getElementById("m-brand-list");
  list.innerHTML = "";
  if (!contractor.by_type.length) {
    list.innerHTML = '<p class="m-hint">Bu dövr üçün məlumat yoxdur</p>';
  }
  for (const t of contractor.by_type) {
    const card = document.createElement("div");
    card.className = "m-card";
    card.innerHTML = `
      <div class="m-card-main">
        <span class="m-card-title">${t.nv_type}</span>
        <span class="m-card-sub">${t.equipment.length} ədəd</span>
      </div>
      <span class="m-card-value">${money(t.total)}<span class="unit">AZN</span></span>`;
    card.addEventListener("click", () => openEquipmentList(t));
    list.appendChild(card);
  }

  destroyChart("brand");
  const canvas = document.getElementById("m-brand-chart");
  requestAnimationFrame(() => {
    state.charts.brand = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: contractor.by_type.map((t) => t.nv_type),
        datasets: [{
          data: contractor.by_type.map((t) => t.total),
          backgroundColor: contractor.by_type.map((_, i) => PALETTE[i % PALETTE.length]),
          borderRadius: 4,
          maxBarThickness: 26,
        }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: TEXT_DIM, font: { size: 10 } }, grid: { color: BORDER } },
          y: { ticks: { color: TEXT_DIM, font: { size: 10.5 } }, grid: { display: false } },
        },
      },
    });
  });

  pushTab("tab-brand");
}

function openEquipmentList(typeData) {
  document.getElementById("m-brand-title").textContent = typeData.nv_type;
  const list = document.getElementById("m-brand-list");
  list.innerHTML = "";
  for (const eq of typeData.equipment) {
    const card = document.createElement("div");
    card.className = "m-card";
    card.innerHTML = `
      <div class="m-card-main">
        <span class="m-card-title">${eq.dq_number}</span>
        <span class="m-card-sub">${eq.nv_type ?? ""}</span>
      </div>
      <span class="m-card-value">${money(eq.total)}<span class="unit">AZN</span></span>`;
    card.addEventListener("click", () => {
      if (!canViewHistory()) {
        showToast("Bu məlumata baxmaq üçün icazəniz yoxdur", true);
        return;
      }
      openHistory(eq.dq_number);
    });
    list.appendChild(card);
  }
  // остаёмся на том же экране (tab-brand), просто перерисовали список - обратно ведёт та же кнопка "Geri"
}

// ================= Служебная техника подрядчика (полный список) =================
document.getElementById("m-view-fleet-btn")?.addEventListener("click", async () => {
  if (!canViewHistory()) {
    showToast("Bu məlumata baxmaq üçün icazəniz yoxdur", true);
    return;
  }
  const contractor = state.currentContractor;
  if (!contractor) return;
  const list = document.getElementById("m-brand-list");
  list.innerHTML = '<p class="m-hint">Yüklənir...</p>';
  try {
    const matches = await api(`/api/equipment/search?q=&contractor_id=${encodeURIComponent(contractor.contractor_id)}`);
    document.getElementById("m-brand-title").textContent = `Servisdə olan texnika — ${contractor.contractor}`;
    list.innerHTML = "";
    if (!matches.length) {
      list.innerHTML = '<p class="m-hint">Heç bir texnika tapılmadı</p>';
      return;
    }
    for (const m of matches) {
      const card = document.createElement("div");
      card.className = "m-card";
      card.innerHTML = `
        <div class="m-card-main">
          <span class="m-card-title">${m.dq_number}</span>
          <span class="m-card-sub">${m.nv_type}</span>
        </div>
        <span class="m-card-value">›</span>`;
      card.addEventListener("click", () => openHistory(m.dq_number));
      list.appendChild(card);
    }
  } catch (err) {
    showToast(err.message, true);
  }
});

// ================= ИСТОРИЯ ТЕХНИКИ =================
document.getElementById("m-history-back")?.addEventListener("click", () => {
  state.navStack.pop();
  showTab(state.navStack[state.navStack.length - 1] || "tab-summary");
});

let historyPeriodsLoaded = false;
async function ensureHistoryPeriodOptions() {
  if (historyPeriodsLoaded) return;
  const select = document.getElementById("m-history-period");
  const periods = await api("/api/periods");
  select.innerHTML = '<option value="all">Bütün dövrlər</option>';
  for (const p of periods) {
    const opt = document.createElement("option");
    opt.value = p.value;
    opt.textContent = p.label;
    select.appendChild(opt);
  }
  historyPeriodsLoaded = true;
}

document.getElementById("m-history-period")?.addEventListener("change", (e) => {
  if (state.currentDqNumber) openHistory(state.currentDqNumber, e.target.value);
});

async function openHistory(dqNumber, period = "all") {
  try {
    const data = await api(`/api/equipment/${encodeURIComponent(dqNumber)}/history?period=${encodeURIComponent(period)}`);
    state.historyData = data;
    state.currentDqNumber = dqNumber;
    document.getElementById("m-history-title").textContent = `${data.dq_number} — ${data.nv_type} · ${money(data.total)} AZN`;

    await ensureHistoryPeriodOptions();
    document.getElementById("m-history-period").value = period;

    renderHistoryChips(data);
    renderHistoryEntries(data.records);
    pushTab("tab-history");
  } catch (err) {
    showToast(err.message, true);
  }
}

function renderHistoryChips(data) {
  const wrap = document.getElementById("m-history-tabs");
  wrap.innerHTML = "";
  const allChip = document.createElement("div");
  allChip.className = "m-chip active";
  allChip.textContent = `Hamısı (${money(data.total)})`;
  allChip.addEventListener("click", () => {
    document.querySelectorAll("#m-history-tabs .m-chip").forEach((c) => c.classList.remove("active"));
    allChip.classList.add("active");
    renderHistoryEntries(data.records);
  });
  wrap.appendChild(allChip);

  for (const c of data.by_contractor) {
    const chip = document.createElement("div");
    chip.className = "m-chip";
    chip.textContent = `${c.contractor} (${money(c.total)})`;
    chip.addEventListener("click", () => {
      document.querySelectorAll("#m-history-tabs .m-chip").forEach((el) => el.classList.remove("active"));
      chip.classList.add("active");
      renderHistoryEntries(data.records.filter((r) => r.contractor === c.contractor));
    });
    wrap.appendChild(chip);
  }
}

function renderHistoryEntries(records) {
  const list = document.getElementById("m-history-list");
  list.innerHTML = "";
  if (!records.length) {
    list.innerHTML = '<p class="m-hint">Qeyd tapılmadı</p>';
    return;
  }
  for (const r of records) {
    const card = document.createElement("div");
    card.className = "m-entry-card";
    card.innerHTML = `
      <div class="m-entry-head">
        <span class="m-entry-date">${r.date ?? "—"}</span>
        <span class="m-entry-total">${r.total_price != null ? money(r.total_price) : "—"}</span>
      </div>
      <div class="m-entry-desc">${r.description ?? "—"}</div>
      <div class="m-entry-meta">
        <span>${r.qty ?? "—"} ${r.unit ?? ""}</span>
        <span>${r.performer ?? "—"}</span>
        <span>${r.area ?? "—"}</span>
        <span>${r.contractor}</span>
      </div>`;
    list.appendChild(card);
  }
}

// ================= İLLİK =================
async function loadYearlyTab(year) {
  const yearInput = document.getElementById("m-year-input");
  if (year === undefined) year = yearInput.value;

  try {
    const [summary, brand] = await Promise.all([
      api(`/api/yearly-summary?year=${encodeURIComponent(year)}`),
      api(`/api/brand-summary?year=${encodeURIComponent(year)}`),
    ]);

    yearInput.value = summary.year ?? year;

    // карточки-итоги
    const cardsWrap = document.getElementById("m-yearly-cards");
    cardsWrap.innerHTML = "";
    summary.contractors.forEach((c, idx) => {
      const monthlySum = c.equipment_monthly.reduce((a, b) => a + b, 0);
      const card = document.createElement("div");
      card.className = "m-card static";
      card.style.borderLeft = `3px solid ${PALETTE[idx % PALETTE.length]}`;
      card.innerHTML = `
        <div class="m-card-main">
          <span class="m-card-title">${c.contractor}</span>
          <span class="m-card-sub">${c.equipment_total} unikal texnika · aylar üzrə cəmi ${monthlySum}</span>
        </div>
        <span class="m-card-value">${money(c.total)}<span class="unit">AZN</span></span>`;
      cardsWrap.appendChild(card);
    });

    // график 1: подрядчики по месяцам
    destroyChart("yearly");
    requestAnimationFrame(() => {
      state.charts.yearly = new Chart(document.getElementById("m-yearly-chart").getContext("2d"), {
        type: "bar",
        data: {
          labels: summary.months,
          datasets: summary.contractors.map((c, idx) => ({
            label: c.contractor,
            data: c.monthly,
            backgroundColor: PALETTE[idx % PALETTE.length],
            borderRadius: 3,
          })),
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "top", labels: { color: TEXT_DIM, font: { size: 9 }, boxWidth: 8 } } },
          scales: {
            x: { ticks: { color: TEXT_DIM, font: { size: 9 } }, grid: { display: false } },
            y: { ticks: { color: TEXT_DIM, font: { size: 9 } }, grid: { color: BORDER } },
          },
        },
      });
    });

    // график 2: марки за год (столбцы)
    destroyChart("brandBar");
    requestAnimationFrame(() => {
      state.charts.brandBar = new Chart(document.getElementById("m-brand-bar-chart").getContext("2d"), {
        type: "bar",
        data: {
          labels: brand.brands.map((b) => b.brand),
          datasets: [{
            data: brand.brands.map((b) => b.total),
            backgroundColor: brand.brands.map((_, i) => PALETTE[i % PALETTE.length]),
            borderRadius: 3,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: TEXT_DIM, font: { size: 9 } }, grid: { display: false } },
            y: { ticks: { color: TEXT_DIM, font: { size: 9 } }, grid: { color: BORDER } },
          },
        },
      });
    });

    // график 3: марки по месяцам (линии)
    destroyChart("brandLine");
    requestAnimationFrame(() => {
      state.charts.brandLine = new Chart(document.getElementById("m-brand-line-chart").getContext("2d"), {
        type: "line",
        data: {
          labels: brand.months,
          datasets: brand.brands.map((b, idx) => ({
            label: b.brand,
            data: b.monthly,
            borderColor: PALETTE[idx % PALETTE.length],
            backgroundColor: PALETTE[idx % PALETTE.length],
            pointRadius: 2,
            borderWidth: 2,
            tension: 0.25,
          })),
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "top", labels: { color: TEXT_DIM, font: { size: 9 }, boxWidth: 8 } } },
          scales: {
            x: { ticks: { color: TEXT_DIM, font: { size: 9 } }, grid: { display: false } },
            y: { ticks: { color: TEXT_DIM, font: { size: 9 } }, grid: { color: BORDER } },
          },
        },
      });
    });
  } catch (err) {
    showToast(err.message, true);
  }
}

document.getElementById("m-year-input")?.addEventListener("change", (e) => {
  loadYearlyTab(e.target.value);
});

// ================= ТО =================
async function loadStatusBoard() {
  const list = document.getElementById("m-status-list");
  if (!list) return;
  try {
    const rows = await api("/api/maintenance/status");
    list.innerHTML = "";
    if (!rows.length) {
      list.innerHTML = '<p class="m-hint">Hələ heç bir qayda/texnika əlavə edilməyib</p>';
      return;
    }
    const labels = { overdue: "Gecikib", soon: "Tezliklə", ok: "Normal", unknown: "Naməlum" };
    for (const r of rows) {
      const card = document.createElement("div");
      card.className = "m-card static";
      card.innerHTML = `
        <div class="m-card-main">
          <span class="m-card-title"><span class="m-status-dot ${r.status}" style="display:inline-block;margin-right:7px;"></span>${r.dq_number} — ${r.maintenance_type}</span>
          <span class="m-card-sub">${r.last_performed_date ? "Son: " + r.last_performed_date : "Heç vaxt qeyd edilməyib"}</span>
        </div>
        <span class="m-card-value" style="color:var(--text-dim); font-size:11.5px;">${labels[r.status]}</span>`;
      list.appendChild(card);
    }
  } catch (err) {
    showToast(err.message, true);
  }
}

async function loadMaintenanceTypes() {
  const sel = document.getElementById("m-event-type");
  if (!sel) return;
  try {
    const rows = await api("/api/maintenance/types");
    sel.innerHTML = "";
    for (const t of rows) {
      const opt = document.createElement("option");
      opt.value = t.id;
      opt.textContent = t.name;
      sel.appendChild(opt);
    }
  } catch (err) {
    showToast(err.message, true);
  }
}

document.getElementById("m-usage-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/maintenance/usage-readings", {
      method: "POST",
      body: JSON.stringify({
        dq_number: document.getElementById("m-usage-dq").value.trim(),
        unit: document.getElementById("m-usage-unit").value,
        value: Number(document.getElementById("m-usage-value").value),
        reading_date: document.getElementById("m-usage-date").value,
      }),
    });
    e.target.reset();
    showToast("Göstərici saxlanıldı");
    loadStatusBoard();
  } catch (err) {
    showToast(err.message, true);
  }
});

document.getElementById("m-event-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/maintenance/events", {
      method: "POST",
      body: JSON.stringify({
        dq_number: document.getElementById("m-event-dq").value.trim(),
        maintenance_type_id: Number(document.getElementById("m-event-type").value),
        performed_date: document.getElementById("m-event-date").value,
        performed_km: document.getElementById("m-event-km").value ? Number(document.getElementById("m-event-km").value) : null,
        performed_hours: document.getElementById("m-event-hours").value ? Number(document.getElementById("m-event-hours").value) : null,
        note: document.getElementById("m-event-note").value || null,
      }),
    });
    e.target.reset();
    showToast("ТО qeyd edildi");
    loadStatusBoard();
  } catch (err) {
    showToast(err.message, true);
  }
});

// ================= Fayl yüklə (admin) =================
document.getElementById("m-file-input")?.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);
  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Yükləmə xətası");
    const rows = data.sheets.reduce((s, x) => s + (x.rows_imported || 0), 0);
    showToast(`"${data.filename}" yükləndi: ${rows} sətir`);
    await loadPeriods();
    await loadSummary();
    await loadYearlyTab(document.getElementById("m-year-input").value);
  } catch (err) {
    showToast(err.message, true);
  } finally {
    e.target.value = "";
  }
});

// ================= Logout =================
document.getElementById("m-logout-btn").addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

// ================= Init =================
async function initYearInput() {
  const input = document.getElementById("m-year-input");
  try {
    const years = await api("/api/years");
    input.value = years.length ? years[0] : new Date().getFullYear();
  } catch {
    input.value = new Date().getFullYear();
  }
}

(async function init() {
  const firstTab = canViewHistory() ? "tab-search" : "tab-summary";
  state.navStack = [firstTab];
  showTab(firstTab);

  await loadPeriods();
  await loadSummary();
  await initYearInput();
  await loadYearlyTab();

  if (canViewHistory()) {
    runSearch("");
  }

  if (isAdmin()) {
    await loadMaintenanceTypes();
    await loadStatusBoard();
  }
})();
