const state = {
  period: "all",
  charts: [],
  yearlyChart: null,
  brandBarChart: null,
  brandLineChart: null,
};

const CONTRACTOR_COLORS = ["--c1", "--c2", "--c3", "--c4", "--c5"];
const BRAND_PALETTE = [
  "#5b8ba0", "#b5651d", "#7a8450", "#9c6b9e", "#4f9d8a",
  "#c9a227", "#8f5a4a", "#5a7fb5", "#8b8b8b",
];

// Рисует количество техники прямо над столбцом (там, где dataset несёт equipmentMonthly) -
// чтобы не приходилось наводить курсор, чтобы увидеть это число.
const barCountLabelsPlugin = {
  id: "barCountLabels",
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    chart.data.datasets.forEach((dataset, dsIndex) => {
      const counts = dataset.equipmentMonthly;
      if (!counts) return;
      const meta = chart.getDatasetMeta(dsIndex);
      if (meta.hidden) return;
      meta.data.forEach((bar, index) => {
        const count = counts[index];
        if (!count) return;
        ctx.save();
        ctx.fillStyle = cssVar("--text-dim");
        ctx.font = "10px 'IBM Plex Mono', monospace";
        ctx.textAlign = "center";
        ctx.fillText(String(count), bar.x, bar.y - 5);
        ctx.restore();
      });
    });
  },
};
Chart.register(barCountLabelsPlugin);

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function money(n) {
  return (n ?? 0).toLocaleString("az-AZ", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.remove("show"), 4200);
}

async function loadPeriods() {
  const res = await fetch("/api/periods");
  const periods = await res.json();
  const select = document.getElementById("period-select");
  select.innerHTML = "";

  const allOpt = document.createElement("option");
  allOpt.value = "all";
  allOpt.textContent = "Bütün dövrlər";
  select.appendChild(allOpt);

  for (const p of periods) {
    const opt = document.createElement("option");
    opt.value = p.value;
    opt.textContent = p.label;
    select.appendChild(opt);
  }

  if (periods.length) {
    select.value = periods[0].value;
    state.period = periods[0].value;
  } else {
    state.period = "all";
  }
}

async function initYearInput() {
  const input = document.getElementById("year-select");
  const res = await fetch("/api/years");
  const years = await res.json();
  const defaultYear = years.length ? years[0] : new Date().getFullYear();
  input.value = defaultYear;
  return defaultYear;
}

function renderYearlySummaryCards(data) {
  const wrap = document.getElementById("yearly-summary-cards");
  wrap.innerHTML = "";
  data.contractors.forEach((c, idx) => {
    const color = cssVar(CONTRACTOR_COLORS[idx % CONTRACTOR_COLORS.length]);
    const monthlySum = c.equipment_monthly.reduce((a, b) => a + b, 0);
    const card = document.createElement("div");
    card.className = "summary-card";
    card.style.borderLeftColor = color;
    card.innerHTML = `
      <span class="summary-card-name">${c.contractor}</span>
      <span class="summary-card-total">${money(c.total)} AZN</span>
      <span class="summary-card-meta">${c.equipment_total} unikal texnika · ${data.year}</span>
      <span class="summary-card-meta-sub">Aylar üzrə cəmi: ${monthlySum} (təkrarla, unikal deyil)</span>`;
    wrap.appendChild(card);
  });
}

async function loadBrandSummary(year) {
  const barCanvas = document.getElementById("brand-bar-chart");
  const lineCanvas = document.getElementById("brand-line-chart");

  if (state.brandBarChart) { state.brandBarChart.destroy(); state.brandBarChart = null; }
  if (state.brandLineChart) { state.brandLineChart.destroy(); state.brandLineChart = null; }
  if (year === null || year === undefined || year === "") return;

  try {
    const res = await fetch(`/api/brand-summary?year=${encodeURIComponent(year)}`);
    if (!res.ok) throw new Error(`Server ${res.status}`);
    const data = await res.json();

    requestAnimationFrame(() => {
      state.brandBarChart = new Chart(barCanvas.getContext("2d"), {
        type: "bar",
        data: {
          labels: data.brands.map((b) => b.brand),
          datasets: [{
            data: data.brands.map((b) => b.total),
            backgroundColor: data.brands.map((_, idx) => BRAND_PALETTE[idx % BRAND_PALETTE.length]),
            borderRadius: 3,
            maxBarThickness: 30,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: cssVar("--text-dim"), font: { size: 10 } }, grid: { display: false } },
            y: { ticks: { color: cssVar("--text-dim"), font: { size: 10 } }, grid: { color: cssVar("--border") } },
          },
        },
      });

      state.brandLineChart = new Chart(lineCanvas.getContext("2d"), {
        type: "line",
        data: {
          labels: data.months,
          datasets: data.brands.map((b, idx) => ({
            label: b.brand,
            data: b.monthly,
            borderColor: BRAND_PALETTE[idx % BRAND_PALETTE.length],
            backgroundColor: BRAND_PALETTE[idx % BRAND_PALETTE.length],
            pointRadius: 3,
            pointHoverRadius: 5,
            tension: 0.25,
            borderWidth: 2,
          })),
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "top",
              labels: { color: cssVar("--text-dim"), font: { size: 10 }, boxWidth: 10 },
            },
          },
          scales: {
            x: { ticks: { color: cssVar("--text-dim"), font: { size: 10 } }, grid: { display: false } },
            y: { ticks: { color: cssVar("--text-dim"), font: { size: 10 } }, grid: { color: cssVar("--border") } },
          },
        },
      });
    });
  } catch (err) {
    console.error("Brand summary chart error:", err);
    showToast("Marka üzrə qrafiklər yüklənmədi", true);
  }
}

async function loadYearlySummary(year) {
  const canvas = document.getElementById("yearly-chart");
  if (state.yearlyChart) {
    state.yearlyChart.destroy();
    state.yearlyChart = null;
  }
  if (year === null || year === undefined || year === "") {
    document.getElementById("yearly-summary-cards").innerHTML = "";
    return;
  }

  try {
    const res = await fetch(`/api/yearly-summary?year=${encodeURIComponent(year)}`);
    if (!res.ok) throw new Error(`Server ${res.status}`);
    const data = await res.json();

    renderYearlySummaryCards(data);

    requestAnimationFrame(() => {
      state.yearlyChart = new Chart(canvas.getContext("2d"), {
        type: "bar",
        data: {
          labels: data.months,
          datasets: data.contractors.map((c, idx) => ({
            label: `${c.contractor} (${c.equipment_total} texnika)`,
            data: c.monthly,
            equipmentMonthly: c.equipment_monthly,
            backgroundColor: cssVar(CONTRACTOR_COLORS[idx % CONTRACTOR_COLORS.length]),
            borderRadius: 3,
            maxBarThickness: 26,
          })),
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "top",
              labels: { color: cssVar("--text-dim"), font: { size: 11 }, boxWidth: 12 },
            },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const count = ctx.dataset.equipmentMonthly?.[ctx.dataIndex] ?? 0;
                  return `${ctx.dataset.label.replace(/\s*\(.*\)$/, "")}: ${money(ctx.parsed.y)} AZN · ${count} texnika`;
                },
              },
            },
          },
          scales: {
            x: { ticks: { color: cssVar("--text-dim"), font: { size: 11 } }, grid: { display: false } },
            y: { ticks: { color: cssVar("--text-dim"), font: { size: 10 } }, grid: { color: cssVar("--border") } },
          },
        },
      });
    });
  } catch (err) {
    console.error("Yearly summary chart error:", err);
    showToast("İllik müqayisə qrafiki yüklənmədi", true);
  }
}

async function loadDashboard() {
  const root = document.getElementById("dashboard-root");
  const res = await fetch(`/api/dashboard?period=${encodeURIComponent(state.period)}`);
  const data = await res.json();

  state.charts.forEach((c) => c.destroy());
  state.charts = [];
  root.innerHTML = "";

  if (!data.length) {
    root.innerHTML = '<p class="empty-state">Hələ heç bir fayl yüklənməyib. Yuxarıdan .xlsx faylı yükləyin.</p>';
    return;
  }

  data.forEach((contractor, idx) => {
    root.appendChild(buildPanel(contractor, CONTRACTOR_COLORS[idx % CONTRACTOR_COLORS.length]));
  });
}

function buildPanel(contractor, colorVarName) {
  const color = cssVar(colorVarName);

  const panel = document.createElement("section");
  panel.className = "panel";

  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<h2>${contractor.contractor}</h2>
    <div class="panel-total">${money(contractor.total)}<span class="unit">AZN</span><span class="panel-total-count">${contractor.equipment_count} texnika</span></div>`;
  panel.appendChild(head);

  const equipBtn = document.createElement("button");
  equipBtn.className = "topbar-icon-btn";
  equipBtn.style.alignSelf = "flex-start";
  equipBtn.textContent = "Servisdə olan texnika";
  equipBtn.addEventListener("click", () => openAllEquipmentModal(contractor.contractor_id, contractor.contractor));
  panel.appendChild(equipBtn);

  const chartWrap = document.createElement("div");
  chartWrap.className = "chart-wrap";
  const canvas = document.createElement("canvas");
  chartWrap.appendChild(canvas);
  panel.appendChild(chartWrap);

  const freqTitle = document.createElement("h3");
  freqTitle.className = "panel-sub-title";
  freqTitle.textContent = "Tez-tez təmir olunan texnika (say)";
  panel.appendChild(freqTitle);
  const freqChartWrap = document.createElement("div");
  freqChartWrap.className = "chart-wrap chart-wrap-freq";
  const freqCanvas = document.createElement("canvas");
  freqChartWrap.appendChild(freqCanvas);
  panel.appendChild(freqChartWrap);

  if (!contractor.by_type.length) {
    const note = document.createElement("p");
    note.className = "no-data";
    note.textContent = "Bu dövr üçün məlumat yoxdur";
    panel.appendChild(note);
  }

  // рисуем графики после вставки в DOM, чтобы canvas получил размеры
  requestAnimationFrame(() => {
    const chart = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: contractor.by_type.map((t) => t.nv_type),
        datasets: [{
          data: contractor.by_type.map((t) => t.total),
          backgroundColor: color,
          borderRadius: 3,
          maxBarThickness: 34,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: cssVar("--text-dim"), font: { size: 10 } }, grid: { display: false } },
          y: { ticks: { color: cssVar("--text-dim"), font: { size: 10 } }, grid: { color: cssVar("--border") } },
        },
      },
    });
    state.charts.push(chart);

    const freqData = contractor.top_equipment_by_frequency || [];
    const freqChart = new Chart(freqCanvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: freqData.map((f) => f.dq_number),
        datasets: [
          {
            label: "Servis sayı (tarixlərə görə)",
            data: freqData.map((f) => f.visit_count),
            backgroundColor: color,
            borderRadius: 3,
            maxBarThickness: 16,
            barPercentage: 0.8,
            categoryPercentage: 0.8,
          },
          {
            label: "Təmir sayı (sətir sayı)",
            data: freqData.map((f) => f.repair_count),
            backgroundColor: cssVar("--amber"),
            borderRadius: 3,
            maxBarThickness: 16,
            barPercentage: 0.8,
            categoryPercentage: 0.8,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: { color: cssVar("--text-dim"), font: { size: 10 }, boxWidth: 10 },
          },
          tooltip: {
            callbacks: {
              afterTitle: (items) => freqData[items[0].dataIndex].nv_type,
            },
          },
        },
        scales: {
          x: { ticks: { color: cssVar("--text-dim"), font: { size: 10 }, precision: 0 }, grid: { color: cssVar("--border") } },
          y: { ticks: { color: cssVar("--text-dim"), font: { size: 10.5, family: "'IBM Plex Mono', monospace" } }, grid: { display: false } },
        },
        onClick: (evt, elements) => {
          if (!elements.length) return;
          loadRepairInfo(freqData[elements[0].index].dq_number, "all");
        },
      },
    });
    state.charts.push(freqChart);
  });

  return panel;
}

function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}
function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

function canViewHistory() {
  const role = window.CURRENT_USER && window.CURRENT_USER.role;
  return role === "admin" || role === "viewer_full";
}

const MONTH_ABBR = {
  "01": "Yan", "02": "Fev", "03": "Mar", "04": "Apr", "05": "May", "06": "İyn",
  "07": "İyl", "08": "Avq", "09": "Sen", "10": "Okt", "11": "Noy", "12": "Dek",
};
function formatPeriod(period) {
  const [year, month] = period.split("-");
  return `${MONTH_ABBR[month] || month} ${year}`;
}

let currentHistory = null;
let activeContractorTab = "all";

function renderHistoryRows(records) {
  const body = document.getElementById("modal-history-body");
  body.innerHTML = "";
  if (!records.length) {
    body.innerHTML = '<tr><td colspan="9" class="no-data">Bu seçim üçün təmir qeydi yoxdur</td></tr>';
    return;
  }
  for (const r of records) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="num">${r.date ?? "—"}</td>
      <td>${r.description ?? "—"}</td>
      <td class="num">${r.qty ?? "—"}</td>
      <td>${r.unit ?? "—"}</td>
      <td class="num">${r.price != null ? money(r.price) : "—"}</td>
      <td class="num">${r.total_price != null ? money(r.total_price) : "—"}</td>
      <td>${r.performer ?? "—"}</td>
      <td>${r.area ?? "—"}</td>
      <td>${r.contractor ?? "—"}</td>`;
    body.appendChild(tr);
  }
}

function selectContractorTab(name) {
  activeContractorTab = name;
  document.querySelectorAll(".contractor-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.contractor === name);
  });
  const filtered = name === "all"
    ? currentHistory.records
    : currentHistory.records.filter((r) => r.contractor === name);
  renderHistoryRows(filtered);
}

function renderContractorTabs(data) {
  const wrap = document.getElementById("contractor-tabs");
  wrap.innerHTML = "";

  const allTab = document.createElement("div");
  allTab.className = "contractor-tab active";
  allTab.dataset.contractor = "all";
  allTab.innerHTML = `<span>Hamısı</span><span class="tab-total">${money(data.total)}</span>`;
  allTab.addEventListener("click", () => selectContractorTab("all"));
  wrap.appendChild(allTab);

  for (const c of data.by_contractor) {
    const tab = document.createElement("div");
    tab.className = "contractor-tab";
    tab.dataset.contractor = c.contractor;
    tab.innerHTML = `<span>${c.contractor}</span><span class="tab-total">${money(c.total)}</span>`;
    tab.addEventListener("click", () => selectContractorTab(c.contractor));
    wrap.appendChild(tab);
  }
}

function renderMonthChips(data) {
  const wrap = document.getElementById("month-chips");
  wrap.innerHTML = "";
  for (const m of data.by_month) {
    const chip = document.createElement("div");
    chip.className = "month-chip";
    chip.innerHTML = `${formatPeriod(m.period)}: <b>${money(m.total)}</b>`;
    wrap.appendChild(chip);
  }
}

let currentDqNumber = null;
let modalPeriodsLoaded = false;

async function ensureModalPeriodOptions() {
  if (modalPeriodsLoaded) return;
  const select = document.getElementById("modal-history-period");
  const periods = await api_getPeriods();
  select.innerHTML = '<option value="all">Bütün dövrlər</option>';
  for (const p of periods) {
    const opt = document.createElement("option");
    opt.value = p.value;
    opt.textContent = p.label;
    select.appendChild(opt);
  }
  modalPeriodsLoaded = true;
}

async function api_getPeriods() {
  const res = await fetch("/api/periods");
  return res.json();
}

async function loadRepairInfo(dqNumber, period = "all") {
  if (!canViewHistory()) {
    showToast("Bu məlumata baxmaq üçün icazəniz yoxdur", true);
    return;
  }
  const res = await fetch(`/api/equipment/${encodeURIComponent(dqNumber)}/history?period=${encodeURIComponent(period)}`);
  if (!res.ok) {
    showToast("Bu texnika üçün məlumat tapılmadı", true);
    return;
  }
  const data = await res.json();
  currentHistory = data;
  currentDqNumber = dqNumber;
  activeContractorTab = "all";

  document.getElementById("modal-history-title").textContent =
    `${data.dq_number} — ${data.nv_type} · Cəmi: ${money(data.total)} AZN`;

  await ensureModalPeriodOptions();
  document.getElementById("modal-history-period").value = period;

  renderContractorTabs(data);
  renderMonthChips(data);
  renderHistoryRows(data.records);

  openModal("modal-history");
}

document.getElementById("modal-history-period")?.addEventListener("change", (e) => {
  if (currentDqNumber) loadRepairInfo(currentDqNumber, e.target.value);
});

// ---------- Bütün texnika: просмотр по марке или по номеру ----------
let allEquipmentCache = [];
let allEquipmentView = "brand";

function renderEquipmentBrandList() {
  document.getElementById("all-equipment-back-btn").classList.add("hidden");
  const brands = {};
  for (const m of allEquipmentCache) {
    brands[m.brand] = (brands[m.brand] || 0) + 1;
  }
  const list = document.getElementById("all-equipment-list");
  list.innerHTML = "";
  for (const [brand, count] of Object.entries(brands).sort((a, b) => b[1] - a[1])) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="dq-block"><span class="dq">${brand}</span></span><span class="total">${count} ədəd ›</span>`;
    li.addEventListener("click", () => renderEquipmentOfBrand(brand));
    list.appendChild(li);
  }
}

function renderEquipmentOfBrand(brand) {
  const backBtn = document.getElementById("all-equipment-back-btn");
  backBtn.classList.remove("hidden");
  backBtn.onclick = renderEquipmentBrandList;

  const list = document.getElementById("all-equipment-list");
  list.innerHTML = "";
  const items = allEquipmentCache.filter((m) => m.brand === brand);
  for (const m of items) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="dq-block"><span class="dq">${m.dq_number}</span><span class="model">${m.nv_type} · ${m.contractors.join(", ")}</span></span><span class="total">›</span>`;
    li.addEventListener("click", () => {
      closeModal("modal-all-equipment");
      loadRepairInfo(m.dq_number, "all");
    });
    list.appendChild(li);
  }
}

function renderEquipmentFlatList() {
  document.getElementById("all-equipment-back-btn").classList.add("hidden");
  const list = document.getElementById("all-equipment-list");
  list.innerHTML = "";
  for (const m of allEquipmentCache) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="dq-block"><span class="dq">${m.dq_number}</span><span class="model">${m.nv_type} · ${m.contractors.join(", ")}</span></span><span class="total">›</span>`;
    li.addEventListener("click", () => {
      closeModal("modal-all-equipment");
      loadRepairInfo(m.dq_number, "all");
    });
    list.appendChild(li);
  }
}

document.querySelectorAll("#all-equipment-view-tabs .contractor-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll("#all-equipment-view-tabs .contractor-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    allEquipmentView = tab.dataset.view;
    if (allEquipmentView === "brand") renderEquipmentBrandList();
    else renderEquipmentFlatList();
  });
});

async function openAllEquipmentModal(contractorId = null, contractorName = null) {
  const list = document.getElementById("all-equipment-list");
  const title = document.getElementById("all-equipment-title");
  if (title) title.textContent = contractorName ? `Servisdə olan texnika — ${contractorName}` : "Bütün texnika";
  list.innerHTML = '<li class="no-data">Yüklənir...</li>';
  document.getElementById("all-equipment-back-btn").classList.add("hidden");
  openModal("modal-all-equipment");
  try {
    const url = contractorId
      ? `/api/equipment/search?q=&contractor_id=${encodeURIComponent(contractorId)}`
      : `/api/equipment/search?q=`;
    const res = await fetch(url);
    allEquipmentCache = await res.json();
    if (!allEquipmentCache.length) {
      list.innerHTML = '<li class="no-data">Hələ heç bir texnika yoxdur</li>';
      return;
    }
    // всегда открываем на виде "по марке" по умолчанию
    document.querySelectorAll("#all-equipment-view-tabs .contractor-tab").forEach((t) =>
      t.classList.toggle("active", t.dataset.view === "brand")
    );
    allEquipmentView = "brand";
    renderEquipmentBrandList();
  } catch (err) {
    list.innerHTML = `<li class="no-data">${err.message}</li>`;
  }
}

document.getElementById("repair-info-btn")?.addEventListener("click", () => {
  if (!canViewHistory()) {
    showToast("Bu məlumata baxmaq üçün icazəniz yoxdur", true);
    return;
  }
  openAllEquipmentModal();
});

async function uploadFile(file) {
  const label = document.getElementById("upload-text");
  const originalText = label.textContent;
  label.textContent = "Yüklənir...";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Yükləmə xətası");

    const rows = data.sheets.reduce((s, x) => s + x.rows_imported, 0);
    showToast(`"${data.filename}" yükləndi: ${rows} sətir, dövr ${data.period}`);
    await loadPeriods();
    document.getElementById("period-select").value = data.period in Object.fromEntries(
      [...document.getElementById("period-select").options].map(o => [o.value, true])
    ) ? data.period : "all";
    state.period = document.getElementById("period-select").value;
    await loadDashboard();
    const year = await initYearInput();
    await loadYearlySummary(year);
    await loadBrandSummary(year);
  } catch (err) {
    showToast(err.message, true);
  } finally {
    label.textContent = originalText;
  }
}

// ---------- Поиск по номеру техники ----------
const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results");
let searchTimer = null;

function hideSearchResults() {
  searchResults.classList.add("hidden");
  searchResults.innerHTML = "";
}

async function runSearch(query) {
  if (!query.trim()) {
    hideSearchResults();
    return;
  }
  const res = await fetch(`/api/equipment/search?q=${encodeURIComponent(query)}`);
  const matches = await res.json();

  searchResults.innerHTML = "";
  if (!matches.length) {
    searchResults.innerHTML = '<div class="search-result-empty">Nəticə tapılmadı</div>';
  } else {
    for (const m of matches) {
      const item = document.createElement("div");
      item.className = "search-result-item";
      item.innerHTML = `<span class="dq">${m.dq_number}</span><span class="meta">${m.nv_type} · ${m.contractors.join(", ")}</span>`;
      item.addEventListener("click", () => {
        hideSearchResults();
        searchInput.value = "";
        loadRepairInfo(m.dq_number, "all");
      });
      searchResults.appendChild(item);
    }
  }
  searchResults.classList.remove("hidden");
}

searchInput.addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  const query = e.target.value;
  searchTimer = setTimeout(() => runSearch(query), 250);
});

searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    hideSearchResults();
    searchInput.blur();
  }
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".search-field")) hideSearchResults();
});

document.getElementById("year-select").addEventListener("change", (e) => {
  loadYearlySummary(e.target.value);
  loadBrandSummary(e.target.value);
});
document.getElementById("year-select").addEventListener("keydown", (e) => {
  if (e.key === "Enter") e.target.blur();
});

document.getElementById("period-select").addEventListener("change", (e) => {
  state.period = e.target.value;
  loadDashboard();
});

document.getElementById("file-input").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) uploadFile(file);
  e.target.value = "";
});

document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.addEventListener("click", () => closeModal(btn.dataset.close));
});
document.querySelectorAll(".modal-overlay").forEach((overlay) => {
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.classList.add("hidden");
  });
});

(async function init() {
  if (!canViewHistory()) {
    const searchField = document.querySelector(".search-field");
    if (searchField) searchField.style.display = "none";
  }

  await loadPeriods();
  await loadDashboard();
  const year = await initYearInput();
  await loadYearlySummary(year);
  await loadBrandSummary(year);
})();

// ---------- Выход / панель администратора ----------
document.getElementById("logout-btn")?.addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

async function loadAdminUsers() {
  const res = await fetch("/api/admin/users");
  if (!res.ok) {
    showToast("İstifadəçilər yüklənmədi", true);
    return;
  }
  const users = await res.json();
  const list = document.getElementById("admin-users-list");
  list.innerHTML = "";
  for (const u of users) {
    const row = document.createElement("div");
    row.className = "admin-user-row";
    row.innerHTML = `<span>${u.username}<span class="role-badge">${u.role_label}</span></span>`;
    if (u.username !== window.CURRENT_USER.username) {
      const btn = document.createElement("button");
      btn.className = "delete-btn";
      btn.textContent = "Sil";
      btn.addEventListener("click", async () => {
        const delRes = await fetch(`/api/admin/users/${u.id}`, { method: "DELETE" });
        const delData = await delRes.json();
        if (!delRes.ok) {
          showToast(delData.detail || "Silinmədi", true);
          return;
        }
        loadAdminUsers();
      });
      row.appendChild(btn);
    }
    list.appendChild(row);
  }
}

document.getElementById("admin-users-btn")?.addEventListener("click", () => {
  loadAdminUsers();
  openModal("modal-admin");
});

document.getElementById("admin-create-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("admin-new-username").value.trim();
  const password = document.getElementById("admin-new-password").value;
  const role = document.getElementById("admin-new-role").value;

  const res = await fetch("/api/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, role }),
  });
  const data = await res.json();
  if (!res.ok) {
    showToast(data.detail || "İstifadəçi yaradıla bilmədi", true);
    return;
  }
  document.getElementById("admin-create-form").reset();
  showToast(`İstifadəçi "${username}" yaradıldı`);
  loadAdminUsers();
});
