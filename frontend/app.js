/**
 * SHOEBOX — Local Receipt Photo to Clean Spreadsheet
 * Pure Vanilla JavaScript (Zero external libraries, 100% offline)
 */

(function () {
  "use strict";

  // Application State
  const state = {
    receipts: [],
    selectedReceiptId: null,
    searchQuery: "",
    filterCategory: "ALL",
    filterStatus: "ALL",
    health: {
      ollama_running: false,
      model_available: false,
      model_name: "gemma3:4b",
      endpoint: "localhost:11434",
    },
    eventSource: null,
    activeEditingCell: null,
  };

  const CATEGORY_COLORS = {
    Food: "#F59E0B",
    Travel: "#3B82F6",
    Supplies: "#10B981",
    Utilities: "#8B5CF6",
    Rent: "#EC4899",
    Software: "#6366F1",
    Equipment: "#14B8A6",
    Services: "#F97316",
    Other: "#6B7280",
  };

  // DOM Elements Cache
  const elements = {
    // Health & Privacy
    setupHelperModal: document.getElementById("setupHelperModal"),
    setupPullCmd: document.getElementById("setupPullCmd"),
    retryHealthBtn: document.getElementById("retryHealthBtn"),
    bypassDemoBtn: document.getElementById("bypassDemoBtn"),
    privacyBadgeBtn: document.getElementById("privacyBadgeBtn"),
    privacyPanel: document.getElementById("privacyPanel"),
    closePrivacyPanel: document.getElementById("closePrivacyPanel"),
    proofModel: document.getElementById("proofModel"),
    proofEndpoint: document.getElementById("proofEndpoint"),
    proofCount: document.getElementById("proofCount"),
    proofTimeSaved: document.getElementById("proofTimeSaved"),

    // Stats
    statTotalSpend: document.getElementById("statTotalSpend"),
    statTotalTax: document.getElementById("statTotalTax"),
    statReceiptCount: document.getElementById("statReceiptCount"),
    statAttentionSub: document.getElementById("statAttentionSub"),
    categorySvgChart: document.getElementById("categorySvgChart"),
    categoryLegend: document.getElementById("categoryLegend"),
    categoryCountTag: document.getElementById("categoryCountTag"),

    // Upload & Dropzone
    dropzone: document.getElementById("dropzone"),
    fileInput: document.getElementById("fileInput"),
    browseFilesBtn: document.getElementById("browseFilesBtn"),
    loadSamplesBtn: document.getElementById("loadSamplesBtn"),
    emptyLoadSamplesBtn: document.getElementById("emptyLoadSamplesBtn"),
    queueThumbnailBar: document.getElementById("queueThumbnailBar"),
    queueThumbnailGrid: document.getElementById("queueThumbnailGrid"),
    queueProgressBadge: document.getElementById("queueProgressBadge"),

    // Table & Controls
    receiptsTable: document.getElementById("receiptsTable"),
    receiptsTableBody: document.getElementById("receiptsTableBody"),
    tableEmptyState: document.getElementById("tableEmptyState"),
    tableCountBadge: document.getElementById("tableCountBadge"),
    searchInput: document.getElementById("searchInput"),
    filterCategory: document.getElementById("filterCategory"),
    filterStatus: document.getElementById("filterStatus"),
    clearDataBtn: document.getElementById("clearDataBtn"),

    // Export Dropdown
    exportMenuBtn: document.getElementById("exportMenuBtn"),
    exportMenu: document.getElementById("exportMenu"),
    exportReceiptsCsv: document.getElementById("exportReceiptsCsv"),
    exportLineItemsCsv: document.getElementById("exportLineItemsCsv"),

    // Side Drawer
    sideDrawer: document.getElementById("sideDrawer"),
    drawerBackdrop: document.getElementById("drawerBackdrop"),
    closeDrawerBtn: document.getElementById("closeDrawerBtn"),
    cancelDrawerBtn: document.getElementById("cancelDrawerBtn"),
    saveDrawerBtn: document.getElementById("saveDrawerBtn"),
    drawerDeleteBtn: document.getElementById("drawerDeleteBtn"),
    drawerReprocessBtn: document.getElementById("drawerReprocessBtn"),
    drawerStatusBadge: document.getElementById("drawerStatusBadge"),
    drawerVendorTitle: document.getElementById("drawerVendorTitle"),
    drawerImage: document.getElementById("drawerImage"),
    drawerFilename: document.getElementById("drawerFilename"),
    imagePreviewContainer: document.getElementById("imagePreviewContainer"),
    drawerWarningsBox: document.getElementById("drawerWarningsBox"),
    drawerWarningsList: document.getElementById("drawerWarningsList"),
    drawerConfidenceVal: document.getElementById("drawerConfidenceVal"),
    drawerConfidenceFill: document.getElementById("drawerConfidenceFill"),
    drawerVendorInput: document.getElementById("drawerVendorInput"),
    drawerDateInput: document.getElementById("drawerDateInput"),
    drawerCategorySelect: document.getElementById("drawerCategorySelect"),
    drawerCurrencyInput: document.getElementById("drawerCurrencyInput"),
    drawerPaymentInput: document.getElementById("drawerPaymentInput"),
    drawerSubtotalInput: document.getElementById("drawerSubtotalInput"),
    drawerTaxInput: document.getElementById("drawerTaxInput"),
    drawerTotalInput: document.getElementById("drawerTotalInput"),
    drawerNotesInput: document.getElementById("drawerNotesInput"),
    drawerLineItemsBody: document.getElementById("drawerLineItemsBody"),
    addLineItemBtn: document.getElementById("addLineItemBtn"),
    drawerRawOutput: document.getElementById("drawerRawOutput"),

    // Zoom Modal
    imageZoomModal: document.getElementById("imageZoomModal"),
    zoomedImage: document.getElementById("zoomedImage"),
    closeZoomBackdrop: document.getElementById("closeZoomBackdrop"),
    closeZoomBtn: document.getElementById("closeZoomBtn"),

    // Toasts
    toastContainer: document.getElementById("toastContainer"),
  };

  /* ==========================================================================
     UTILITIES & HELPERS
     ========================================================================== */
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let iconSvg = "";
    if (type === "success") {
      iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (type === "error") {
      iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
    } else {
      iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      setTimeout(() => toast.remove(), 250);
    }, 3800);
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatCurrency(amount, currency = "INR") {
    if (amount === null || amount === undefined || isNaN(amount)) return "—";
    const num = Number(amount);
    const sym = currency === "INR" ? "₹" : currency === "USD" ? "$" : currency === "EUR" ? "€" : currency + " ";
    return `${sym}${num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function formatTimeSaved(receiptCount) {
    const totalSecs = receiptCount * 90; // 90 seconds manual entry per receipt
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    if (mins === 0 && secs === 0) return "0m 00s";
    return `${mins}m ${secs.toString().padStart(2, "0")}s`;
  }

  function getAvatarColor(name) {
    const colors = [
      "#6366F1", "#14B8A6", "#EC4899", "#F59E0B",
      "#10B981", "#8B5CF6", "#06B6D4", "#F43F5E",
    ];
    let hash = 0;
    const str = name || "Unknown";
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  }

  // Smooth Count-Up Animation for Numbers
  function animateCount(elem, start, end, prefix = "", suffix = "", isFloat = true) {
    const duration = 650;
    const startTime = performance.now();

    function update(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // easeOutExpo
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = start + (end - start) * ease;

      if (isFloat) {
        elem.textContent = `${prefix}${current.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${suffix}`;
      } else {
        elem.textContent = `${prefix}${Math.round(current)}${suffix}`;
      }

      if (progress < 1) {
        requestAnimationFrame(update);
      }
    }
    requestAnimationFrame(update);
  }

  /* ==========================================================================
     API & SERVER-SENT EVENTS
     ========================================================================== */
  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        state.health = data;

        elements.proofModel.textContent = data.model_name || "gemma3:4b";
        elements.proofEndpoint.textContent = data.endpoint || "localhost:11434";
        if (elements.setupPullCmd) {
          elements.setupPullCmd.textContent = `ollama pull ${data.model_name || "gemma3:4b"}`;
        }

        if (!data.ollama_running || !data.model_available) {
          elements.setupHelperModal.style.display = "flex";
        } else {
          elements.setupHelperModal.style.display = "none";
        }
      }
    } catch (err) {
      console.warn("Health check unreachable:", err);
      elements.setupHelperModal.style.display = "flex";
    }
  }

  async function loadReceipts() {
    try {
      const res = await fetch("/api/receipts");
      if (res.ok) {
        const data = await res.json();
        state.receipts = data;
        renderAll();
      }
    } catch (err) {
      console.error("Failed to load receipts:", err);
      showToast("Failed to load receipts from local database", "error");
    }
  }

  function initSSE() {
    if (state.eventSource) {
      state.eventSource.close();
    }

    state.eventSource = new EventSource("/api/events");

    state.eventSource.onopen = () => {
      console.log("SSE connected to local Shoebox server");
    };

    state.eventSource.addEventListener("receipt_queued", (e) => {
      try {
        const payload = JSON.parse(e.data);
        const receipt = payload.data.receipt;
        const exists = state.receipts.find((r) => r.id === receipt.id);
        if (!exists) {
          state.receipts.unshift(receipt);
        }
        renderAll();
      } catch (err) {
        console.error("SSE receipt_queued error:", err);
      }
    });

    state.eventSource.addEventListener("status_update", (e) => {
      try {
        const payload = JSON.parse(e.data);
        const { id, status } = payload.data;
        const item = state.receipts.find((r) => r.id === id);
        if (item) {
          item.status = status;
          renderAll();
        }
      } catch (err) {
        console.error("SSE status_update error:", err);
      }
    });

    state.eventSource.addEventListener("receipt_completed", (e) => {
      try {
        const payload = JSON.parse(e.data);
        const completed = payload.data.receipt;
        const idx = state.receipts.findIndex((r) => r.id === completed.id);
        if (idx !== -1) {
          state.receipts[idx] = completed;
        } else {
          state.receipts.unshift(completed);
        }

        // If drawer is currently open for this receipt, refresh drawer data
        if (state.selectedReceiptId === completed.id) {
          populateDrawer(completed);
        }

        renderAll();
        showToast(`Scanned: ${completed.vendor || "Receipt"} (${formatCurrency(completed.total, completed.currency)})`, "success");
      } catch (err) {
        console.error("SSE receipt_completed error:", err);
      }
    });

    state.eventSource.addEventListener("receipt_updated", (e) => {
      try {
        const payload = JSON.parse(e.data);
        const updated = payload.data.receipt;
        const idx = state.receipts.findIndex((r) => r.id === updated.id);
        if (idx !== -1) {
          state.receipts[idx] = updated;
          renderAll();
        }
      } catch (err) {
        console.error("SSE receipt_updated error:", err);
      }
    });

    state.eventSource.addEventListener("receipt_deleted", (e) => {
      try {
        const payload = JSON.parse(e.data);
        const id = payload.data.id;
        state.receipts = state.receipts.filter((r) => r.id !== id);
        if (state.selectedReceiptId === id) {
          closeDrawer();
        }
        renderAll();
      } catch (err) {
        console.error("SSE receipt_deleted error:", err);
      }
    });

    state.eventSource.addEventListener("receipts_cleared", () => {
      state.receipts = [];
      closeDrawer();
      renderAll();
      showToast("All receipts cleared", "info");
    });

    state.eventSource.onerror = (err) => {
      console.warn("SSE connection interrupted, retrying in 3s...", err);
      state.eventSource.close();
      setTimeout(initSSE, 3000);
    };
  }

  /* ==========================================================================
     UPLOAD & SAMPLE DEMO LOGIC
     ========================================================================== */
  async function handleFilesUpload(files) {
    if (!files || files.length === 0) return;
    const formData = new FormData();
    for (const f of files) {
      formData.append("files", f);
    }

    showToast(`Uploading ${files.length} receipt${files.length > 1 ? "s" : ""}...`, "info");

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        showToast(`Queued ${data.uploaded} file${data.uploaded > 1 ? "s" : ""} for scanning`, "info");
        await loadReceipts();
      } else {
        const err = await res.json();
        showToast(err.detail || "Upload failed", "error");
      }
    } catch (err) {
      console.error("Upload error:", err);
      showToast("Network error uploading files", "error");
    }
  }

  async function loadSyntheticSamples() {
    showToast("Generating 3 synthetic benchmark receipts...", "info");
    try {
      const res = await fetch("/api/demo/samples", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        showToast("Loaded 3 demo receipts. Processing sequentially...", "success");
        await loadReceipts();
      } else {
        showToast("Failed to load sample receipts", "error");
      }
    } catch (err) {
      console.error("Demo load error:", err);
      showToast("Error loading demo samples", "error");
    }
  }

  /* ==========================================================================
     RENDERING: SUMMARY, QUEUE, TABLE, CHARTS
     ========================================================================== */
  function renderAll() {
    renderSummary();
    renderQueueThumbnails();
    renderTable();
    renderCategoryChart();
  }

  function renderSummary() {
    let totalSpend = 0;
    let totalTax = 0;
    let reviewCount = 0;

    for (const r of state.receipts) {
      if (r.status === "done" || r.status === "needs review") {
        totalSpend += Number(r.total || 0);
        totalTax += Number(r.tax || 0);
      }
      if (r.status === "needs review" || (r.warnings && r.warnings.length > 0)) {
        reviewCount++;
      }
    }

    elements.statTotalSpend.textContent = formatCurrency(totalSpend, "INR");
    elements.statTotalTax.textContent = formatCurrency(totalTax, "INR");
    elements.statReceiptCount.textContent = state.receipts.length;
    elements.statAttentionSub.textContent = `${reviewCount} need review`;

    // Proof panel counters
    elements.proofCount.textContent = state.receipts.length;
    elements.proofTimeSaved.textContent = formatTimeSaved(state.receipts.length);
  }

  function renderQueueThumbnails() {
    const activeQueue = state.receipts.filter(
      (r) => r.status === "queued" || r.status === "scanning"
    );

    if (activeQueue.length === 0) {
      elements.queueThumbnailBar.style.display = "none";
      return;
    }

    elements.queueThumbnailBar.style.display = "flex";
    const scanningCount = activeQueue.filter((r) => r.status === "scanning").length;
    elements.queueProgressBadge.textContent = `${scanningCount} scanning · ${activeQueue.length - scanningCount} queued`;

    elements.queueThumbnailGrid.innerHTML = activeQueue
      .map(
        (r) => `
        <div class="queue-thumb-item ${r.status === "scanning" ? "scanning" : ""}">
          <img src="${r.image_path}" alt="${escapeHtml(r.filename)}" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'80\\' height=\\'80\\' fill=\\'%234B5563\\'><rect width=\\'80\\' height=\\'80\\'/></svg>'">
          <div class="queue-thumb-meta">
            ${r.status === "scanning" ? "Scanning..." : "Queued"}
          </div>
        </div>
      `
      )
      .join("");
  }

  function renderCategoryChart() {
    const categoryTotals = {};
    let grandTotal = 0;

    for (const r of state.receipts) {
      if (r.status === "done" || r.status === "needs review") {
        const cat = r.category || "Other";
        const amt = Number(r.total || 0);
        categoryTotals[cat] = (categoryTotals[cat] || 0) + amt;
        grandTotal += amt;
      }
    }

    const categories = Object.keys(categoryTotals).sort(
      (a, b) => categoryTotals[b] - categoryTotals[a]
    );

    elements.categoryCountTag.textContent = `${categories.length} categories`;

    if (grandTotal === 0 || categories.length === 0) {
      elements.categorySvgChart.innerHTML = `
        <rect x="0" y="4" width="280" height="20" rx="6" fill="rgba(255,255,255,0.08)"/>
      `;
      elements.categoryLegend.innerHTML = `<span class="stat-subtext">No processed receipts yet</span>`;
      return;
    }

    // Build SVG Segments
    let currentX = 0;
    const chartWidth = 280;
    const barHeight = 20;
    let svgHtml = "";
    let legendHtml = "";

    categories.forEach((cat, index) => {
      const amt = categoryTotals[cat];
      const pct = (amt / grandTotal) * 100;
      const width = Math.max(3, (amt / grandTotal) * chartWidth);
      const color = CATEGORY_COLORS[cat] || "#6B7280";

      svgHtml += `
        <rect x="${currentX}" y="4" width="${width}" height="${barHeight}" fill="${color}" rx="${index === 0 ? 6 : 0}">
          <title>${escapeHtml(cat)}: ${pct.toFixed(1)}% (${formatCurrency(amt)})</title>
        </rect>
      `;
      currentX += width;

      legendHtml += `
        <div class="legend-chip">
          <span class="legend-dot" style="background-color: ${color};"></span>
          <span>${escapeHtml(cat)}</span>
          <span class="legend-pct">${pct.toFixed(0)}%</span>
        </div>
      `;
    });

    elements.categorySvgChart.innerHTML = svgHtml;
    elements.categoryLegend.innerHTML = legendHtml;
  }

  function getFilteredReceipts() {
    return state.receipts.filter((r) => {
      // Category filter
      if (state.filterCategory !== "ALL" && (r.category || "Other") !== state.filterCategory) {
        return false;
      }
      // Status filter
      if (state.filterStatus !== "ALL" && r.status !== state.filterStatus) {
        return false;
      }
      // Text search
      if (state.searchQuery) {
        const q = state.searchQuery.toLowerCase();
        const vendor = (r.vendor || "").toLowerCase();
        const notes = (r.notes || "").toLowerCase();
        const cat = (r.category || "").toLowerCase();
        const filename = (r.filename || "").toLowerCase();
        if (!vendor.includes(q) && !notes.includes(q) && !cat.includes(q) && !filename.includes(q)) {
          return false;
        }
      }
      return true;
    });
  }

  function renderTable() {
    const filtered = getFilteredReceipts();
    elements.tableCountBadge.textContent = `${filtered.length} of ${state.receipts.length} items`;

    if (filtered.length === 0) {
      elements.receiptsTableBody.innerHTML = "";
      elements.tableEmptyState.style.display = "flex";
      elements.receiptsTable.style.display = "none";
      return;
    }

    elements.tableEmptyState.style.display = "none";
    elements.receiptsTable.style.display = "table";

    elements.receiptsTableBody.innerHTML = filtered
      .map((r) => {
        const isNeedsReview = r.status === "needs review" || (r.warnings && r.warnings.length > 0);
        const rowClass = isNeedsReview ? "row-needs-review" : "";
        const avatarColor = getAvatarColor(r.vendor);
        const initial = (r.vendor && r.vendor !== "Unknown Vendor" ? r.vendor.charAt(0) : "R").toUpperCase();

        // Status badge markup
        let statusBadge = "";
        if (r.status === "done") {
          statusBadge = `<span class="badge badge-done">Done</span>`;
        } else if (r.status === "needs review") {
          statusBadge = `<span class="badge badge-review">Review</span>`;
        } else if (r.status === "scanning") {
          statusBadge = `<span class="badge badge-scanning">Scanning...</span>`;
        } else if (r.status === "queued") {
          statusBadge = `<span class="badge badge-queued">Queued</span>`;
        } else {
          statusBadge = `<span class="badge badge-error">Error</span>`;
        }

        // Warnings chips markup
        let warningsChips = "";
        if (r.warnings && r.warnings.length > 0) {
          warningsChips = r.warnings
            .map(
              (w) => `
              <span class="warning-chip" title="${escapeHtml(w)}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                ${escapeHtml(w.split(":")[0])}
              </span>
            `
            )
            .join("");
        }

        const notesText = r.notes ? `<div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(r.notes.slice(0, 45))}</div>` : "";

        return `
          <tr class="${rowClass}" data-id="${r.id}">
            <td class="td-status">${statusBadge}</td>
            <td class="td-date">
              <span class="editable-cell" data-field="date" data-id="${r.id}" title="Click to edit date">
                ${escapeHtml(r.date || "—")}
              </span>
            </td>
            <td class="td-vendor">
              <div class="vendor-cell">
                <div class="vendor-avatar" style="background-color: ${avatarColor};">${initial}</div>
                <div>
                  <div class="vendor-name editable-cell" data-field="vendor" data-id="${r.id}" title="Click to edit vendor">
                    ${escapeHtml(r.vendor || "Processing...")}
                  </div>
                  <div class="vendor-filename-sub">${escapeHtml(r.filename)}</div>
                </div>
              </div>
            </td>
            <td class="td-category">
              <span class="editable-cell" data-field="category" data-id="${r.id}" title="Click to edit category">
                ${escapeHtml(r.category || "Other")}
              </span>
            </td>
            <td class="td-curr">
              <span class="editable-cell font-mono" data-field="currency" data-id="${r.id}">
                ${escapeHtml(r.currency || "INR")}
              </span>
            </td>
            <td class="td-num">
              <span class="editable-cell" data-field="subtotal" data-id="${r.id}">
                ${r.subtotal !== null && r.subtotal !== undefined ? Number(r.subtotal).toFixed(2) : "—"}
              </span>
            </td>
            <td class="td-num">
              <span class="editable-cell" data-field="tax" data-id="${r.id}">
                ${r.tax !== null && r.tax !== undefined ? Number(r.tax).toFixed(2) : "0.00"}
              </span>
            </td>
            <td class="td-num font-bold">
              <span class="editable-cell" data-field="total" data-id="${r.id}">
                ${Number(r.total || 0).toFixed(2)}
              </span>
            </td>
            <td class="td-confidence">
              <span class="font-mono" style="font-size: 12px; color: ${r.confidence >= 0.8 ? "var(--emerald-400)" : r.confidence >= 0.6 ? "var(--amber-400)" : "var(--rose-500)"};">
                ${Math.round((r.confidence || 0) * 100)}%
              </span>
            </td>
            <td class="td-notes">
              ${warningsChips}
              ${notesText}
            </td>
            <td class="td-actions" onclick="event.stopPropagation();">
              <div class="table-actions-cell">
                <button class="btn-icon inspect-row-btn" data-id="${r.id}" title="Inspect receipt in side drawer">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
                <button class="btn-icon delete-row-btn" data-id="${r.id}" title="Delete receipt">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  /* ==========================================================================
     INLINE CELL EDITING (PERSISTS TO SQLITE ON BLUR / ENTER)
     ========================================================================== */
  function setupTableEvents() {
    elements.receiptsTableBody.addEventListener("click", (e) => {
      const target = e.target;
      const cell = target.closest(".editable-cell");

      // Check if clicked directly on an editable cell
      if (cell) {
        e.stopPropagation();
        activateCellEdit(cell);
        return;
      }

      // Check inspect button
      const inspectBtn = target.closest(".inspect-row-btn");
      if (inspectBtn) {
        e.stopPropagation();
        openDrawer(inspectBtn.getAttribute("data-id"));
        return;
      }

      // Check delete button
      const delBtn = target.closest(".delete-row-btn");
      if (delBtn) {
        e.stopPropagation();
        deleteReceipt(delBtn.getAttribute("data-id"));
        return;
      }

      // Otherwise click anywhere on the row opens the drawer
      const row = target.closest("tr");
      if (row && row.getAttribute("data-id")) {
        openDrawer(row.getAttribute("data-id"));
      }
    });
  }

  function activateCellEdit(cell) {
    if (state.activeEditingCell) {
      finishCellEdit(state.activeEditingCell, false);
    }

    const field = cell.getAttribute("data-field");
    const id = cell.getAttribute("data-id");
    const receipt = state.receipts.find((r) => r.id === id);
    if (!receipt) return;

    state.activeEditingCell = cell;
    const originalText = cell.textContent.trim();
    const currentVal = receipt[field] !== null && receipt[field] !== undefined ? receipt[field] : "";

    const input = document.createElement("input");
    input.type = ["subtotal", "tax", "total"].includes(field) ? "number" : "text";
    if (input.type === "number") input.step = "0.01";
    input.className = "cell-input-active";
    input.value = currentVal;

    cell.textContent = "";
    cell.appendChild(input);
    input.focus();
    input.select();

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        finishCellEdit(cell, true);
      } else if (e.key === "Escape") {
        e.preventDefault();
        finishCellEdit(cell, false, originalText);
      }
    });

    input.addEventListener("blur", () => {
      finishCellEdit(cell, true);
    });
  }

  async function finishCellEdit(cell, shouldSave, fallbackText = null) {
    if (!cell) return;
    state.activeEditingCell = null;

    const input = cell.querySelector("input");
    if (!input) return;

    const field = cell.getAttribute("data-field");
    const id = cell.getAttribute("data-id");
    const newVal = input.value.trim();

    if (!shouldSave) {
      cell.textContent = fallbackText || "—";
      return;
    }

    // Call PATCH API
    try {
      const payload = {};
      if (["subtotal", "tax", "total"].includes(field)) {
        payload[field] = newVal ? parseFloat(newVal) : null;
      } else {
        payload[field] = newVal;
      }

      const res = await fetch(`/api/receipts/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const updated = await res.json();
        const idx = state.receipts.findIndex((r) => r.id === id);
        if (idx !== -1) {
          state.receipts[idx] = updated;
        }
        renderAll();
        showToast(`Updated ${field}`, "success");
      } else {
        renderAll();
        showToast("Failed to save edit", "error");
      }
    } catch (err) {
      console.error("Cell edit error:", err);
      renderAll();
      showToast("Error saving cell", "error");
    }
  }

  /* ==========================================================================
     SIDE DRAWER (INSPECTION, FORM EDITING, LINE ITEMS)
     ========================================================================== */
  function openDrawer(id) {
    const receipt = state.receipts.find((r) => r.id === id);
    if (!receipt) return;

    state.selectedReceiptId = id;
    populateDrawer(receipt);

    elements.sideDrawer.classList.add("open");
    elements.sideDrawer.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    state.selectedReceiptId = null;
    elements.sideDrawer.classList.remove("open");
    elements.sideDrawer.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  function populateDrawer(r) {
    elements.drawerVendorTitle.textContent = r.vendor || "Receipt Details";
    elements.drawerFilename.textContent = r.filename;
    elements.drawerImage.src = r.image_path;

    // Status badge
    elements.drawerStatusBadge.className = `badge badge-${r.status === "needs review" ? "review" : r.status}`;
    elements.drawerStatusBadge.textContent = r.status.toUpperCase();

    // Warnings Box
    if (r.warnings && r.warnings.length > 0) {
      elements.drawerWarningsBox.style.display = "flex";
      elements.drawerWarningsList.innerHTML = r.warnings
        .map((w) => `<div>• ${escapeHtml(w)}</div>`)
        .join("");
    } else {
      elements.drawerWarningsBox.style.display = "none";
    }

    // Confidence
    const confPct = Math.round((r.confidence || 0) * 100);
    elements.drawerConfidenceVal.textContent = `${confPct}%`;
    elements.drawerConfidenceFill.style.width = `${confPct}%`;

    // Form inputs
    elements.drawerVendorInput.value = r.vendor || "";
    elements.drawerDateInput.value = r.date || "";
    elements.drawerCategorySelect.value = r.category || "Other";
    elements.drawerCurrencyInput.value = r.currency || "INR";
    elements.drawerPaymentInput.value = r.payment_method || "";
    elements.drawerSubtotalInput.value = r.subtotal !== null && r.subtotal !== undefined ? r.subtotal : "";
    elements.drawerTaxInput.value = r.tax !== null && r.tax !== undefined ? r.tax : "";
    elements.drawerTotalInput.value = r.total !== null && r.total !== undefined ? r.total : "";
    elements.drawerNotesInput.value = r.notes || "";

    // Line items
    renderDrawerLineItems(r.line_items || []);

    // Raw model output
    elements.drawerRawOutput.textContent = r.raw_model_output || "No raw model output recorded.";
  }

  function renderDrawerLineItems(items) {
    if (!items || items.length === 0) {
      elements.drawerLineItemsBody.innerHTML = `
        <tr class="empty-line-items-row">
          <td colspan="4" style="text-align: center; color: var(--text-muted); font-size: 11px; padding: 12px;">
            No individual line items parsed. Click "+ Add Item" to specify them.
          </td>
        </tr>
      `;
      return;
    }

    elements.drawerLineItemsBody.innerHTML = items
      .map(
        (it, idx) => `
        <tr data-index="${idx}">
          <td>
            <input type="text" class="line-item-desc" value="${escapeHtml(it.description || "")}" placeholder="Description">
          </td>
          <td>
            <input type="number" class="line-item-qty tabular-nums" value="${it.qty || 1}" step="1" style="text-align: right;">
          </td>
          <td>
            <input type="number" class="line-item-price tabular-nums" value="${it.price || 0}" step="0.01" style="text-align: right;">
          </td>
          <td style="text-align: center;">
            <button type="button" class="item-del-btn" data-index="${idx}" title="Remove item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </td>
        </tr>
      `
      )
      .join("");
  }

  function addEmptyLineItem() {
    const existing = elements.drawerLineItemsBody.querySelectorAll("tr:not(.empty-line-items-row)");
    const newIdx = existing.length;

    const tr = document.createElement("tr");
    tr.setAttribute("data-index", newIdx);
    tr.innerHTML = `
      <td><input type="text" class="line-item-desc" placeholder="New Item Description"></td>
      <td><input type="number" class="line-item-qty tabular-nums" value="1" step="1" style="text-align: right;"></td>
      <td><input type="number" class="line-item-price tabular-nums" value="0.00" step="0.01" style="text-align: right;"></td>
      <td style="text-align: center;">
        <button type="button" class="item-del-btn" data-index="${newIdx}" title="Remove item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </td>
    `;

    const emptyRow = elements.drawerLineItemsBody.querySelector(".empty-line-items-row");
    if (emptyRow) emptyRow.remove();

    elements.drawerLineItemsBody.appendChild(tr);
    tr.querySelector(".line-item-desc").focus();
  }

  async function saveDrawerChanges() {
    if (!state.selectedReceiptId) return;

    // Collect line items
    const rows = elements.drawerLineItemsBody.querySelectorAll("tr:not(.empty-line-items-row)");
    const lineItems = [];
    rows.forEach((row) => {
      const desc = row.querySelector(".line-item-desc")?.value.trim();
      const qty = parseFloat(row.querySelector(".line-item-qty")?.value) || 1.0;
      const price = parseFloat(row.querySelector(".line-item-price")?.value) || 0.0;
      if (desc) {
        lineItems.push({ description: desc, qty, price });
      }
    });

    const payload = {
      vendor: elements.drawerVendorInput.value.trim() || "Unknown Vendor",
      date: elements.drawerDateInput.value.trim() || null,
      category: elements.drawerCategorySelect.value,
      currency: elements.drawerCurrencyInput.value.trim().toUpperCase() || "INR",
      payment_method: elements.drawerPaymentInput.value.trim() || null,
      subtotal: elements.drawerSubtotalInput.value ? parseFloat(elements.drawerSubtotalInput.value) : null,
      tax: elements.drawerTaxInput.value ? parseFloat(elements.drawerTaxInput.value) : null,
      total: parseFloat(elements.drawerTotalInput.value) || 0.0,
      notes: elements.drawerNotesInput.value.trim() || null,
      line_items: lineItems,
    };

    try {
      const res = await fetch(`/api/receipts/${state.selectedReceiptId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const updated = await res.json();
        const idx = state.receipts.findIndex((r) => r.id === state.selectedReceiptId);
        if (idx !== -1) {
          state.receipts[idx] = updated;
        }
        populateDrawer(updated);
        renderAll();
        showToast("Changes saved successfully", "success");
        closeDrawer();
      } else {
        showToast("Error updating receipt", "error");
      }
    } catch (err) {
      console.error("Save drawer error:", err);
      showToast("Network error saving changes", "error");
    }
  }

  async function deleteReceipt(id) {
    if (!confirm("Are you sure you want to delete this receipt?")) return;
    try {
      const res = await fetch(`/api/receipts/${id}`, { method: "DELETE" });
      if (res.ok) {
        state.receipts = state.receipts.filter((r) => r.id !== id);
        if (state.selectedReceiptId === id) {
          closeDrawer();
        }
        renderAll();
        showToast("Receipt deleted", "info");
      } else {
        showToast("Failed to delete receipt", "error");
      }
    } catch (err) {
      console.error("Delete receipt error:", err);
      showToast("Error deleting receipt", "error");
    }
  }

  async function reprocessCurrentReceipt() {
    if (!state.selectedReceiptId) return;
    try {
      const res = await fetch(`/api/receipts/${state.selectedReceiptId}/reprocess`, {
        method: "POST",
      });
      if (res.ok) {
        showToast("Re-queued receipt for vision extraction", "info");
      } else {
        showToast("Failed to reprocess receipt", "error");
      }
    } catch (err) {
      console.error("Reprocess error:", err);
      showToast("Error re-queuing receipt", "error");
    }
  }

  /* ==========================================================================
     IMAGE ZOOM MODAL
     ========================================================================== */
  function openZoomModal() {
    if (!state.selectedReceiptId) return;
    const r = state.receipts.find((rec) => rec.id === state.selectedReceiptId);
    if (!r) return;

    elements.zoomedImage.src = r.image_path;
    elements.imageZoomModal.classList.add("open");
    elements.imageZoomModal.setAttribute("aria-hidden", "false");
  }

  function closeZoomModal() {
    elements.imageZoomModal.classList.remove("open");
    elements.imageZoomModal.setAttribute("aria-hidden", "true");
  }

  /* ==========================================================================
     CSV EXPORT TRIGGERS
     ========================================================================== */
  function downloadCsv(url) {
    const a = document.createElement("a");
    a.href = url;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast("Spreadsheet downloaded", "success");
  }

  /* ==========================================================================
     EVENT LISTENERS & BINDINGS
     ========================================================================== */
  function bindEvents() {
    // Dropzone Events
    const dropzone = elements.dropzone;
    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("drag-over");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length > 0) {
        handleFilesUpload(dt.files);
      }
    });

    elements.browseFilesBtn.addEventListener("click", () => {
      elements.fileInput.click();
    });

    elements.fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFilesUpload(e.target.files);
        elements.fileInput.value = "";
      }
    });

    elements.loadSamplesBtn.addEventListener("click", loadSyntheticSamples);
    elements.emptyLoadSamplesBtn.addEventListener("click", loadSyntheticSamples);

    // Filter & Search
    elements.searchInput.addEventListener("input", (e) => {
      state.searchQuery = e.target.value.trim();
      renderTable();
    });

    elements.filterCategory.addEventListener("change", (e) => {
      state.filterCategory = e.target.value;
      renderTable();
    });

    elements.filterStatus.addEventListener("change", (e) => {
      state.filterStatus = e.target.value;
      renderTable();
    });

    // Clear Session
    elements.clearDataBtn.addEventListener("click", async () => {
      if (!confirm("Clear all receipts from local database? This cannot be undone.")) return;
      try {
        await fetch("/api/receipts/clear", { method: "POST" });
      } catch (err) {
        console.error("Clear error:", err);
      }
    });

    // Privacy Proof Panel Toggle
    elements.privacyBadgeBtn.addEventListener("click", () => {
      const isCollapsed = elements.privacyPanel.classList.toggle("collapsed");
      elements.privacyPanel.setAttribute("aria-expanded", !isCollapsed);
    });

    elements.closePrivacyPanel.addEventListener("click", () => {
      elements.privacyPanel.classList.add("collapsed");
      elements.privacyPanel.setAttribute("aria-expanded", "false");
    });

    // Export Dropdown
    elements.exportMenuBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      elements.exportMenu.classList.toggle("show");
    });

    document.addEventListener("click", (e) => {
      if (!elements.exportDropdown?.contains(e.target)) {
        elements.exportMenu.classList.remove("show");
      }
    });

    elements.exportReceiptsCsv.addEventListener("click", () => {
      elements.exportMenu.classList.remove("show");
      downloadCsv("/api/export/csv");
    });

    elements.exportLineItemsCsv.addEventListener("click", () => {
      elements.exportMenu.classList.remove("show");
      downloadCsv("/api/export/line-items-csv");
    });

    // Drawer Controls
    elements.closeDrawerBtn.addEventListener("click", closeDrawer);
    elements.cancelDrawerBtn.addEventListener("click", closeDrawer);
    elements.drawerBackdrop.addEventListener("click", closeDrawer);
    elements.saveDrawerBtn.addEventListener("click", saveDrawerChanges);
    elements.drawerReprocessBtn.addEventListener("click", reprocessCurrentReceipt);
    elements.drawerDeleteBtn.addEventListener("click", () => {
      if (state.selectedReceiptId) deleteReceipt(state.selectedReceiptId);
    });

    // Drawer Line Items
    elements.addLineItemBtn.addEventListener("click", addEmptyLineItem);
    elements.drawerLineItemsBody.addEventListener("click", (e) => {
      const delBtn = e.target.closest(".item-del-btn");
      if (delBtn) {
        const row = delBtn.closest("tr");
        if (row) row.remove();
        if (elements.drawerLineItemsBody.querySelectorAll("tr").length === 0) {
          renderDrawerLineItems([]);
        }
      }
    });

    // Image Zoom Modal
    elements.imagePreviewContainer.addEventListener("click", openZoomModal);
    elements.closeZoomBtn.addEventListener("click", closeZoomModal);
    elements.closeZoomBackdrop.addEventListener("click", closeZoomModal);

    // Setup Helper Screen Actions
    elements.retryHealthBtn.addEventListener("click", async () => {
      showToast("Rechecking Ollama connection...", "info");
      await checkHealth();
    });

    elements.bypassDemoBtn.addEventListener("click", () => {
      elements.setupHelperModal.style.display = "none";
      if (state.receipts.length === 0) {
        loadSyntheticSamples();
      }
    });

    // Keyboard Shortcuts
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (elements.imageZoomModal.classList.contains("open")) {
          closeZoomModal();
        } else if (elements.sideDrawer.classList.contains("open")) {
          closeDrawer();
        }
      }
    });

    // Setup table click / inline edit handlers
    setupTableEvents();
  }

  /* ==========================================================================
     INITIALIZATION
     ========================================================================== */
  async function init() {
    bindEvents();
    await checkHealth();
    await loadReceipts();
    initSSE();
  }

  // Start on DOM Ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
