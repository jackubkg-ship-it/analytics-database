function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.remove("show"), 4200);
}

const STATUS_LABELS = {
  overdue: "Gecikib",
  soon: "Tezliklə",
  ok: "Normal",
  unknown: "Naməlum",
};

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Xəta baş verdi");
  return data;
}

let typesCache = [];

async function loadStatusBoard() {
  try {
    const rows = await api("/api/maintenance/status");
    const body = document.getElementById("status-table-body");
    body.innerHTML = "";
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="8" class="no-data">Hələ heç bir qayda/texnika əlavə edilməyib</td></tr>';
      return;
    }
    for (const r of rows) {
      const tr = document.createElement("tr");
      const dueUsage = r.due_usage != null ? `${r.due_usage} ${r.usage_unit === "km" ? "km" : "saat"}` : "—";
      const currentUsage = r.current_usage != null ? ` (hazırda ${r.current_usage})` : "";
      tr.innerHTML = `
        <td><span class="status-badge ${r.status}">${STATUS_LABELS[r.status]}</span></td>
        <td>${r.dq_number}</td>
        <td>${r.brand}</td>
        <td>${r.maintenance_type}</td>
        <td>${r.last_performed_date ?? "—"}</td>
        <td>${r.due_date ?? "—"}</td>
        <td>${dueUsage}${currentUsage}</td>
        <td>${r.rule_scope === "equipment" ? "Maşına xas" : "Marka üzrə"}</td>`;
      body.appendChild(tr);
    }
  } catch (err) {
    showToast(err.message, true);
  }
}

async function loadEquipmentList() {
  const rows = await api("/api/maintenance/equipment");
  const wrap = document.getElementById("equipment-list");
  wrap.innerHTML = "";
  for (const r of rows) {
    const row = document.createElement("div");
    row.className = "mt-row";
    row.innerHTML = `<span>${r.dq_number}<span class="mt-row-meta">${r.brand}</span></span>`;
    const btn = document.createElement("button");
    btn.className = "delete-btn";
    btn.textContent = "Sil";
    btn.addEventListener("click", async () => {
      await api(`/api/maintenance/equipment/${r.id}`, { method: "DELETE" });
      loadEquipmentList();
      loadStatusBoard();
    });
    row.appendChild(btn);
    wrap.appendChild(row);
  }
}

async function loadTypes() {
  const rows = await api("/api/maintenance/types");
  typesCache = rows;
  const wrap = document.getElementById("types-list");
  wrap.innerHTML = "";
  for (const r of rows) {
    const row = document.createElement("div");
    row.className = "mt-row";
    row.innerHTML = `<span>${r.name}</span>`;
    const btn = document.createElement("button");
    btn.className = "delete-btn";
    btn.textContent = "Sil";
    btn.addEventListener("click", async () => {
      await api(`/api/maintenance/types/${r.id}`, { method: "DELETE" });
      loadTypes();
      loadRules();
      loadStatusBoard();
    });
    row.appendChild(btn);
    wrap.appendChild(row);
  }

  for (const sel of [document.getElementById("rule-type"), document.getElementById("event-type")]) {
    sel.innerHTML = "";
    for (const r of rows) {
      const opt = document.createElement("option");
      opt.value = r.id;
      opt.textContent = r.name;
      sel.appendChild(opt);
    }
  }
}

async function loadRules() {
  const rows = await api("/api/maintenance/rules");
  const wrap = document.getElementById("rules-list");
  wrap.innerHTML = "";
  for (const r of rows) {
    const row = document.createElement("div");
    row.className = "mt-row";
    const parts = [];
    if (r.interval_days) parts.push(`${r.interval_days} gün`);
    if (r.interval_usage) parts.push(`${r.interval_usage} ${r.usage_unit === "km" ? "km" : "saat"}`);
    row.innerHTML = `<span>${r.scope === "brand" ? "Marka" : "Maşın"}: ${r.scope_value} — ${r.maintenance_type}
      <span class="mt-row-meta">${parts.join(" / ")}</span></span>`;
    const btn = document.createElement("button");
    btn.className = "delete-btn";
    btn.textContent = "Sil";
    btn.addEventListener("click", async () => {
      await api(`/api/maintenance/rules/${r.id}`, { method: "DELETE" });
      loadRules();
      loadStatusBoard();
    });
    row.appendChild(btn);
    wrap.appendChild(row);
  }
}

document.getElementById("equipment-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/maintenance/equipment", {
      method: "POST",
      body: JSON.stringify({
        dq_number: document.getElementById("eq-dq").value.trim(),
        brand: document.getElementById("eq-brand").value.trim(),
      }),
    });
    e.target.reset();
    loadEquipmentList();
    loadStatusBoard();
  } catch (err) { showToast(err.message, true); }
});

document.getElementById("type-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/maintenance/types", {
      method: "POST",
      body: JSON.stringify({ name: document.getElementById("type-name").value.trim() }),
    });
    e.target.reset();
    loadTypes();
  } catch (err) { showToast(err.message, true); }
});

document.getElementById("rule-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/maintenance/rules", {
      method: "POST",
      body: JSON.stringify({
        scope: document.getElementById("rule-scope").value,
        scope_value: document.getElementById("rule-scope-value").value.trim(),
        maintenance_type_id: Number(document.getElementById("rule-type").value),
        interval_days: document.getElementById("rule-days").value ? Number(document.getElementById("rule-days").value) : null,
        interval_usage: document.getElementById("rule-usage").value ? Number(document.getElementById("rule-usage").value) : null,
        usage_unit: document.getElementById("rule-unit").value || null,
      }),
    });
    e.target.reset();
    loadRules();
    loadStatusBoard();
    showToast("Qayda yaradıldı");
  } catch (err) { showToast(err.message, true); }
});

document.getElementById("usage-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/maintenance/usage-readings", {
      method: "POST",
      body: JSON.stringify({
        dq_number: document.getElementById("usage-dq").value.trim(),
        unit: document.getElementById("usage-unit").value,
        value: Number(document.getElementById("usage-value").value),
        reading_date: document.getElementById("usage-date").value,
      }),
    });
    e.target.reset();
    loadStatusBoard();
    showToast("Göstərici saxlanıldı");
  } catch (err) { showToast(err.message, true); }
});

document.getElementById("event-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/maintenance/events", {
      method: "POST",
      body: JSON.stringify({
        dq_number: document.getElementById("event-dq").value.trim(),
        maintenance_type_id: Number(document.getElementById("event-type").value),
        performed_date: document.getElementById("event-date").value,
        performed_km: document.getElementById("event-km").value ? Number(document.getElementById("event-km").value) : null,
        performed_hours: document.getElementById("event-hours").value ? Number(document.getElementById("event-hours").value) : null,
        note: document.getElementById("event-note").value || null,
      }),
    });
    e.target.reset();
    loadStatusBoard();
    showToast("ТО qeyd edildi");
  } catch (err) { showToast(err.message, true); }
});

document.getElementById("logout-btn").addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

(async function init() {
  await loadTypes();
  await loadEquipmentList();
  await loadRules();
  await loadStatusBoard();
})();
