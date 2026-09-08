(function () {
  const LS_CASES = "netsage_custom_cases";   // localStorage key: array of user-added case objects
  const LS_REVIEWS = "netsage_reviews";      // localStorage key: { case_id: {status, note, ts, ...} }
  const LS_DELETED = "netsage_deleted_ids";  // localStorage key: array of base-case ids the user deleted

  let baseCases = {};      // from data/cases.json — case_id -> case object
  let baseOrder = [];      // ordered ids from data/cases.json
  let customCases = {};    // from localStorage — case_id -> case object
  let customOrder = [];
  let deletedBaseIds = new Set();
  let aiResults = {};      // from data/ai_results.json — case_id -> diagnosis object
  let ruleFindings = {};   // from data/rule_checker_report.json — case_id -> findings
  let reviews = {};        // from localStorage
  let activeCaseId = null;
  let editingCaseId = null;
  let searchTerm = "";

  function allOrder() {
    return [...baseOrder.filter((id) => !deletedBaseIds.has(id)), ...customOrder];
  }
  function getCase(id) {
    return customCases[id] || baseCases[id];
  }

  function loadLocal() {
    try {
      const raw = localStorage.getItem(LS_CASES);
      if (raw) {
        const arr = JSON.parse(raw);
        arr.forEach((c) => {
          customCases[c.case_id] = c;
          if (!customOrder.includes(c.case_id)) customOrder.push(c.case_id);
        });
      }
    } catch (e) {}
    try {
      const raw = localStorage.getItem(LS_REVIEWS);
      if (raw) reviews = JSON.parse(raw);
    } catch (e) {}
    try {
      const raw = localStorage.getItem(LS_DELETED);
      if (raw) deletedBaseIds = new Set(JSON.parse(raw));
    } catch (e) {}
  }

  function persistCustomCases() {
    localStorage.setItem(LS_CASES, JSON.stringify(customOrder.map((id) => customCases[id])));
  }
  function persistReviews() {
    localStorage.setItem(LS_REVIEWS, JSON.stringify(reviews));
  }
  function persistDeleted() {
    localStorage.setItem(LS_DELETED, JSON.stringify([...deletedBaseIds]));
  }

  async function fetchJson(path, fallback) {
    try {
      const res = await fetch(path);
      if (!res.ok) return fallback;
      return await res.json();
    } catch (e) {
      return fallback;
    }
  }

  async function init() {
    loadLocal();
    const casesArr = await fetchJson("data/cases.json", []);
    casesArr.forEach((c) => {
  const normalizedCase = {
    case_id: c["Case ID"],
    case_name: c["Case Name"],
    symptom: c["Symptom"],
    topology_note: c["Topology"],
    show_output: c["Evidence"],
    expected_fault: c["Expected Fault"],
    osi_layer: c["OSI Layer"],
    concept_tag: c["Concept"],
    category: c["Concept"],
    severity: c["Severity"]
  };

  baseCases[normalizedCase.case_id] = normalizedCase;
  baseOrder.push(normalizedCase.case_id);
});
    aiResults = await fetchJson("data/ai_results.json", {});
    const ruleReport = await fetchJson("data/rule_checker_report.json", []);
    ruleReport.forEach((r) => {
      ruleFindings[r.case_id] = r.rule_checker_findings || {};
    });

    const order = allOrder();
    if (order.length) activeCaseId = order[0];
    render();
  }

  function escapeHtml(s) {
    return String(s || "").replace(
      /[&<>"']/g,
      (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m])
    );
  }

  function matchesSearch(c) {
    if (!searchTerm) return true;
    const hay = (c.case_id + " " + c.category + " " + c.symptom).toLowerCase();
    return hay.includes(searchTerm.toLowerCase());
  }

  function renderCaseList() {
    const el = document.getElementById("ns-case-list");
    const order = allOrder().filter((id) => matchesSearch(getCase(id)));
    if (!order.length) {
      el.innerHTML = '<div class="ns-empty">No cases match.<br>Click "+ Add case" to add one.</div>';
      return;
    }
    el.innerHTML = order
      .map((id) => {
        const c = getCase(id);
        const rev = reviews[id];
        const pill = rev ? `<span class="ns-pill ns-pill-status-${rev.status}">${rev.status}</span>` : "";
        return `<div class="ns-case-item ${id === activeCaseId ? "active" : ""}" data-case="${id}">
        <div class="ns-case-id">${id}</div>
        <div class="ns-case-symptom">${escapeHtml(c.symptom)}</div>
        <span class="ns-pill ns-pill-cat">${escapeHtml(c.category)}</span> ${pill}
      </div>`;
      })
      .join("");
    el.querySelectorAll(".ns-case-item").forEach((item) => {
      item.addEventListener("click", () => {
        activeCaseId = item.getAttribute("data-case");
        render();
      });
    });
  }

  function renderDetail() {
    const el = document.getElementById("ns-detail");
    const c = getCase(activeCaseId);
    if (!c) {
      el.innerHTML = '<div class="ns-empty">Select a case, or add your first one.</div>';
      return;
    }
    const diag = aiResults[c.case_id];
    const rev = reviews[c.case_id];
    const findings = ruleFindings[c.case_id];

    let ruleBlock = "";
    if (findings && Object.keys(findings).length) {
      ruleBlock = `<div class="ns-section-label">Deterministic rule checker</div>
        <div class="ns-evidence ns-mono">${Object.entries(findings)
          .map(([k, v]) => `${k}: ${v.map(escapeHtml).join("; ")}`)
          .join("\n")}</div>`;
    }

    let diagBlock = "";
    if (diag && diag.error) {
      diagBlock = `<div class="ns-err">AI diagnosis not available: ${escapeHtml(diag.error)}</div>`;
    } else if (diag) {
      diagBlock = `<div class="ns-diag-card">
        <div class="ns-diag-row"><strong>Root cause</strong></div>
        <div class="ns-body">${escapeHtml(diag.root_cause)}</div>
        <div class="ns-diag-row" style="margin-top:10px;">
          <span>Confidence: <span class="ns-conf ns-conf-${diag.confidence || "low"}">${diag.confidence || "-"}</span></span>
          <span class="ns-mono" style="color:var(--ns-text-mute);">${escapeHtml(diag.osi_layer)}</span>
        </div>
        <div class="ns-section-label">Evidence cited</div>
        <div class="ns-body" style="color:var(--ns-text-dim);">${escapeHtml(diag.evidence)}</div>
        <div class="ns-section-label">Next command</div>
        <div class="ns-evidence ns-mono">${escapeHtml(diag.next_command)}</div>
        <div class="ns-section-label">Fix steps (draft — not yet applied)</div>
        <ul class="ns-fix-list">${(diag.fix_steps || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>
      </div>
      <div class="ns-review-row">
        <button class="ns-btn ns-btn-primary" data-action="accept">Accept</button>
        <button class="ns-btn" data-action="edit">Mark edited</button>
        <button class="ns-btn" data-action="reject">Reject</button>
      </div>
      <textarea class="ns-note" id="ns-note" placeholder="Reviewer note — why accepted / what you changed / why rejected...">${rev ? escapeHtml(rev.note) : ""}</textarea>
      ${rev ? `<div class="ns-body" style="margin-top:8px;color:var(--ns-text-mute);font-size:11px;">Logged as <strong style="color:var(--ns-text);">${rev.status}</strong> on ${new Date(rev.ts).toLocaleString()}</div>` : ""}`;
    } else {
      diagBlock = `<div class="ns-empty" style="padding:20px 0;">
        No AI diagnosis yet for this case.<br><br>
        Run this in a terminal (with your Anthropic API key set):<br>
        <code class="ns-mono">python3 scripts/run_diagnosis.py ${c.case_id}</code><br><br>
        Then refresh this page.
      </div>`;
    }

    el.innerHTML = `
      <div class="ns-case-actions">
        <button class="ns-btn" id="ns-edit-case">Edit case</button>
        <button class="ns-btn" id="ns-del-case" style="color:var(--ns-red);">Delete case</button>
      </div>
      <div class="ns-section-label">Case ${c.case_id} &middot; ${escapeHtml(c.category)} &middot; ${escapeHtml(c.severity)} severity</div>
      <div class="ns-body"><strong>Symptom:</strong> ${escapeHtml(c.symptom)}</div>
      <div class="ns-body" style="margin-top:4px;color:var(--ns-text-dim);">${escapeHtml(c.topology_note)}</div>
      <div class="ns-section-label">Show-command evidence</div>
      <div class="ns-evidence ns-mono">${escapeHtml(c.show_output)}</div>
      <div class="ns-section-label">Your expected fault (answer key)</div>
      <div class="ns-body" style="color:var(--ns-text-dim);">${escapeHtml(c.expected_fault)}</div>
      ${ruleBlock}
      <div class="ns-section-label">AI diagnosis</div>
      ${diagBlock}
    `;

    document.getElementById("ns-edit-case").addEventListener("click", () => openModal(c.case_id));
    document.getElementById("ns-del-case").addEventListener("click", () => {
      if (!confirm("Delete case " + c.case_id + "? This cannot be undone.")) return;
      if (customCases[c.case_id]) {
        delete customCases[c.case_id];
        customOrder = customOrder.filter((x) => x !== c.case_id);
        persistCustomCases();
      } else {
        deletedBaseIds.add(c.case_id);
        persistDeleted();
      }
      delete reviews[c.case_id];
      persistReviews();
      const order = allOrder();
      activeCaseId = order[0] || null;
      render();
    });

    el.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const note = document.getElementById("ns-note").value;
        const status =
          btn.getAttribute("data-action") === "accept"
            ? "accepted"
            : btn.getAttribute("data-action") === "edit"
            ? "edited"
            : "rejected";
        reviews[c.case_id] = {
          status,
          note,
          ts: Date.now(),
          root_cause: diag ? diag.root_cause : "",
          expected_fault: c.expected_fault,
          category: c.category,
        };
        persistReviews();
        render();
      });
    });
  }

  function renderDashboard() {
    const grid = document.getElementById("ns-dash-grid");
    const order = allOrder();
    const total = order.length;
    const reviewedIds = Object.keys(reviews).filter((id) => order.includes(id));
    const reviewed = reviewedIds.length;
    const accepted = reviewedIds.filter((id) => reviews[id].status === "accepted").length;
    const corrected = reviewedIds.filter(
      (id) => reviews[id].status === "edited" || reviews[id].status === "rejected"
    ).length;
    const agreementRate = reviewed ? Math.round((accepted / reviewed) * 100) : 0;

    grid.innerHTML = `
      <div class="ns-metric"><div class="ns-metric-label">TOTAL CASES</div><div class="ns-metric-value">${total}</div></div>
      <div class="ns-metric"><div class="ns-metric-label">REVIEWED</div><div class="ns-metric-value">${reviewed}</div></div>
      <div class="ns-metric"><div class="ns-metric-label">AI/HUMAN AGREEMENT</div><div class="ns-metric-value">${agreementRate}%</div></div>
      <div class="ns-metric"><div class="ns-metric-label">CORRECTED CASES</div><div class="ns-metric-value">${corrected}</div></div>
    `;

    const byCat = {};
    order.forEach((id) => {
      const c = getCase(id);
      if (c) byCat[c.category] = (byCat[c.category] || 0) + 1;
    });
    const entries = Object.entries(byCat);
    const max = entries.length ? Math.max(...entries.map((e) => e[1])) : 1;
    const chart = document.getElementById("ns-bar-chart");
    chart.innerHTML = entries.length
      ? entries
          .map(
            ([cat, count]) => `
      <div class="ns-bar-row">
        <span class="ns-mono" style="color:var(--ns-text-dim);">${cat}</span>
        <div class="ns-bar-track"><div class="ns-bar-fill" style="width:${(count / max) * 100}%;"></div></div>
        <span class="ns-mono">${count}</span>
      </div>`
          )
          .join("")
      : '<div class="ns-empty">Add cases to see the breakdown.</div>';

    const bySev = { High: 0, Medium: 0, Low: 0 };
    order.forEach((id) => {
      const c = getCase(id);
      if (c && c.severity) bySev[c.severity] = (bySev[c.severity] || 0) + 1;
    });
    const sevEntries = Object.entries(bySev).filter(([, count]) => count > 0);
    const sevMax = sevEntries.length ? Math.max(...sevEntries.map((e) => e[1])) : 1;
    const sevChart = document.getElementById("ns-severity-chart");
    sevChart.innerHTML = sevEntries.length
      ? sevEntries
          .map(
            ([sev, count]) => `
      <div class="ns-bar-row">
        <span class="ns-mono" style="color:var(--ns-text-dim);">${sev}</span>
        <div class="ns-bar-track"><div class="ns-bar-fill" style="width:${(count / sevMax) * 100}%;"></div></div>
        <span class="ns-mono">${count}</span>
      </div>`
          )
          .join("")
      : '<div class="ns-empty">Add cases to see the breakdown.</div>';
  }

  function renderLog() {
    const el = document.getElementById("ns-log-list");
    const order = allOrder();
    const entries = Object.entries(reviews).filter(([id, r]) => order.includes(id) && r.status !== "accepted");
    if (!entries.length) {
      el.innerHTML =
        '<div class="ns-empty">No corrected cases logged yet. Reject or mark a diagnosis "edited" to log it here — the assignment requires at least 5.</div>';
      return;
    }
    el.innerHTML = entries
      .map(
        ([id, r]) => `
      <div class="ns-log-item">
        <div class="ns-log-head"><span>${id} &middot; ${escapeHtml(r.category)}</span><span class="ns-pill ns-pill-status-${r.status}">${r.status}</span></div>
        <div class="ns-body"><strong>Expected fault:</strong> ${escapeHtml(r.expected_fault)}</div>
        <div class="ns-body" style="color:var(--ns-text-dim);"><strong>AI said:</strong> ${escapeHtml(r.root_cause || "(no diagnosis run)")}</div>
        <div class="ns-body" style="margin-top:4px;"><strong>Reviewer note:</strong> ${escapeHtml(r.note || "(none)")}</div>
      </div>`
      )
      .join("");
  }

  function render() {
    renderCaseList();
    renderDetail();
    renderDashboard();
    renderLog();
  }

  // --- Modal (add/edit case) ---
  function openModal(existingId) {
    editingCaseId = existingId || null;
    const c = existingId ? getCase(existingId) : null;
    document.getElementById("ns-modal-title").textContent = existingId ? "Edit case " + existingId : "Add a case";
    document.getElementById("f-case_id").value = c ? c.case_id : nextCaseId();
    document.getElementById("f-case_id").disabled = !!existingId;
    document.getElementById("f-category").value = c ? c.category : "VLAN";
    document.getElementById("f-severity").value = c ? c.severity : "Medium";
    document.getElementById("f-osi_layer").value = c ? c.osi_layer : "";
    document.getElementById("f-concept_tag").value = c ? c.concept_tag : "";
    document.getElementById("f-symptom").value = c ? c.symptom : "";
    document.getElementById("f-topology_note").value = c ? c.topology_note : "";
    document.getElementById("f-show_output").value = c ? c.show_output : "";
    document.getElementById("f-expected_fault").value = c ? c.expected_fault : "";
    document.getElementById("ns-delete-case").style.display = existingId ? "inline-block" : "none";
    document.getElementById("ns-modal-overlay").style.display = "flex";
  }
  function closeModal() {
    document.getElementById("ns-modal-overlay").style.display = "none";
    editingCaseId = null;
  }
  function nextCaseId() {
    const order = allOrder();
    let n = order.length + 1;
    let id = "C" + String(n).padStart(3, "0");
    while (getCase(id)) {
      n++;
      id = "C" + String(n).padStart(3, "0");
    }
    return id;
  }

  document.getElementById("ns-add-case-btn").addEventListener("click", () => openModal(null));
  document.getElementById("ns-modal-close").addEventListener("click", closeModal);
  document.getElementById("ns-modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "ns-modal-overlay") closeModal();
  });
  document.getElementById("ns-search").addEventListener("input", (e) => {
    searchTerm = e.target.value;
    renderCaseList();
  });

  document.getElementById("ns-save-case").addEventListener("click", () => {
    const id = document.getElementById("f-case_id").value.trim();
    if (!id) {
      alert("Case ID is required.");
      return;
    }
    const c = {
      case_id: id,
      category: document.getElementById("f-category").value,
      severity: document.getElementById("f-severity").value,
      osi_layer: document.getElementById("f-osi_layer").value.trim(),
      concept_tag: document.getElementById("f-concept_tag").value.trim(),
      symptom: document.getElementById("f-symptom").value.trim(),
      topology_note: document.getElementById("f-topology_note").value.trim(),
      show_output: document.getElementById("f-show_output").value,
      expected_fault: document.getElementById("f-expected_fault").value.trim(),
    };
    customCases[id] = c;
    if (!customOrder.includes(id)) customOrder.push(id);
    persistCustomCases();
    activeCaseId = id;
    closeModal();
    render();
  });

  document.getElementById("ns-delete-case").addEventListener("click", () => {
    if (!editingCaseId) return;
    if (!confirm("Delete case " + editingCaseId + "? This cannot be undone.")) return;
    if (customCases[editingCaseId]) {
      delete customCases[editingCaseId];
      customOrder = customOrder.filter((x) => x !== editingCaseId);
      persistCustomCases();
    } else {
      deletedBaseIds.add(editingCaseId);
      persistDeleted();
    }
    delete reviews[editingCaseId];
    persistReviews();
    const order = allOrder();
    activeCaseId = order[0] || null;
    closeModal();
    render();
  });

  document.querySelectorAll(".ns-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".ns-tab").forEach((t) => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });
      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      document.querySelectorAll(".ns-view").forEach((v) => (v.style.display = "none"));
      document.getElementById("ns-view-" + tab.getAttribute("data-tab")).style.display = "block";
    });
  });

  // --- Export helpers ---
  function downloadFile(filename, content, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function csvEscape(v) {
    const s = String(v == null ? "" : v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }

  document.getElementById("ns-export-cases").addEventListener("click", () => {
    const order = allOrder();
    const fields = [
      "case_id", "category", "severity", "symptom", "topology_note",
      "show_output", "expected_fault", "osi_layer", "concept_tag",
    ];
    const rows = [fields.join(",")];
    order.forEach((id) => {
      const c = getCase(id);
      rows.push(fields.map((f) => csvEscape(c[f])).join(","));
    });
    downloadFile("cases.csv", rows.join("\n"), "text/csv");
  });

  document.getElementById("ns-export-reviews").addEventListener("click", () => {
    downloadFile("reviews.json", JSON.stringify(reviews, null, 2), "application/json");
  });

  document.getElementById("ns-export-log").addEventListener("click", () => {
    const order = allOrder();
    const entries = Object.entries(reviews).filter(([id, r]) => order.includes(id) && r.status !== "accepted");
    let md = "# Responsible AI Log\n\n";
    md += "| Case ID | Category | AI root cause | Expected fault | Status | Reviewer note |\n";
    md += "|---|---|---|---|---|---|\n";
    entries.forEach(([id, r]) => {
      md += `| ${id} | ${r.category || ""} | ${(r.root_cause || "").replace(/\|/g, "/")} | ${(r.expected_fault || "").replace(/\|/g, "/")} | ${r.status} | ${(r.note || "").replace(/\|/g, "/")} |\n`;
    });
    downloadFile("responsible_ai_log.md", md, "text/markdown");
  });

  init();
})();
