/* SAM-style local UI — vanilla JS, no framework, no CDN. Client-side view router +
   per-view data fetches. Extended task-by-task (matters/hub/chat/history/settings). */
(function () {
  "use strict";
  var VIEWS = ["chat", "matters", "hub", "history", "settings"];
  var state = { matter: null };
  window.appState = state;
  window.viewHooks = window.viewHooks || {};

  // --- helpers ---------------------------------------------------------------
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  window.esc = esc;

  async function api(path, opts) {
    var r = await fetch(path, opts);
    var data = null;
    try { data = await r.json(); } catch (e) { data = null; }
    if (!r.ok) throw new Error((data && data.detail) || ("HTTP " + r.status));
    return data;
  }
  window.api = api;

  function setActiveMatter(slug, label) {
    state.matter = slug || null;
    var el = document.getElementById("active-matter");
    if (el) el.textContent = label || slug || "none";
    document.querySelectorAll(".matter-picker").forEach(function (sel) {
      if (sel.value !== state.matter) sel.value = state.matter || "";
    });
    if (typeof window.onMatterChange === "function") window.onMatterChange();
  }
  window.setActiveMatter = setActiveMatter;

  // A shared <select> matter picker (reused by Chat + Document Hub).
  async function fillMatterPickers() {
    var data = await api("/matters");
    var matters = (data && data.matters) || [];
    document.querySelectorAll(".matter-picker").forEach(function (sel) {
      sel.innerHTML = '<option value="">— choose matter —</option>' +
        matters.map(function (m) {
          return '<option value="' + esc(m.slug) + '">' + esc(m.display_name) +
            " (" + m.doc_count + ")</option>";
        }).join("");
      if (state.matter) sel.value = state.matter;
    });
    return matters;
  }
  window.fillMatterPickers = fillMatterPickers;

  // --- Matters view ----------------------------------------------------------
  async function renderMatters() {
    var inner = document.querySelector("#view-matters .view-inner");
    inner.innerHTML =
      "<h1>Matters</h1><p class='muted'>Each matter is the scope for search — answers never cross matters.</p>" +
      "<div class='panel'><div style='display:flex;gap:8px'>" +
      "<input id='new-matter-name' type='text' placeholder='New matter name (e.g. Pemberton Logistics)'>" +
      "<button class='btn' id='new-matter-btn'>Create</button></div>" +
      "<div id='new-matter-err' style='color:var(--err);font-size:13px;margin-top:8px'></div></div>" +
      "<div class='panel'><table><thead><tr><th>Matter</th><th>Slug</th><th>Docs</th></tr></thead>" +
      "<tbody id='matters-rows'></tbody></table></div>";

    var matters = [];
    try { var d = await api("/matters"); matters = (d && d.matters) || []; }
    catch (e) { matters = []; }
    document.getElementById("matters-rows").innerHTML = matters.length
      ? matters.map(function (m) {
          return "<tr><td><b>" + esc(m.display_name) + "</b></td><td class='muted'>" +
            esc(m.slug) + "</td><td>" + m.doc_count + "</td></tr>";
        }).join("")
      : "<tr><td colspan='3' class='muted'>No matters yet — create one above.</td></tr>";

    document.getElementById("new-matter-btn").addEventListener("click", async function () {
      var name = document.getElementById("new-matter-name").value;
      var err = document.getElementById("new-matter-err");
      err.textContent = "";
      try {
        await api("/matters", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ display_name: name }),
        });
        await renderMatters();
        await fillMatterPickers();
      } catch (e) { err.textContent = e.message; }
    });
  }
  window.viewHooks.matters = renderMatters;

  // --- router ----------------------------------------------------------------
  function showView(name) {
    if (VIEWS.indexOf(name) === -1) return;
    VIEWS.forEach(function (v) {
      var el = document.getElementById("view-" + v);
      if (el) el.classList.toggle("active", v === name);
    });
    document.querySelectorAll(".nav-item").forEach(function (b) {
      b.classList.toggle("active", b.dataset.view === name);
    });
    var hook = window.viewHooks[name];
    if (typeof hook === "function") hook();
  }
  window.showView = showView;

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".nav-item").forEach(function (b) {
      b.addEventListener("click", function () { showView(b.dataset.view); });
    });
    fillMatterPickers().catch(function () {});
    showView("chat");
  });
})();
