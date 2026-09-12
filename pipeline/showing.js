/* Showing record runtime.
   Reads SHOW_DATA = {houses:{k:{slug,name,psf,rank,verdict}}}.
   Storage: the artifact's shared db when the page runs as an artifact, localStorage otherwise.
   Nothing here recomputes the model. Answers are exported as a patch for score.py. */
(function () {
  var LS = "walk-showings-v1", LSP = "walk-showings-people";
  var ST = {}, PEOPLE = { a: "Alex", b: "Her" }, WHO = "a", DB = null, MODE = "all", T = {}, BOOTED = false;
  var H = (SHOW_DATA && SHOW_DATA.houses) || {};

  function rec(k) { if (!ST[k]) ST[k] = {}; return ST[k]; }
  function nowISO() { return new Date().toISOString(); }
  function pill(t, c) { var e = document.getElementById("syncpill"); if (e) { e.textContent = t; e.className = "pill " + (c || ""); } }

  function lsRead() { try { return JSON.parse(localStorage.getItem(LS) || "{}"); } catch (e) { return {}; } }
  function lsWrite() { try { localStorage.setItem(LS, JSON.stringify(ST)); } catch (e) { } }

  function touched(r) {
    if (!r) return false;
    if (r.visited || r.verdict || (r.notes || "").trim()) return true;
    var n = 0;
    ["tells", "mech", "targ", "walk", "gut"].forEach(function (g) { if (r[g] && Object.keys(r[g]).length) n++; });
    return n > 0;
  }
  function answered(r) {
    var c = 0, g = (r && r.tells) || {};
    Object.keys(g).forEach(function (f) { if (g[f] && g[f] !== "not_shown") c++; });
    return c;
  }

  /* ---------------- persistence ---------------- */
  function queue(k) { clearTimeout(T[k]); T[k] = setTimeout(function () { persist(k); }, 700); }
  function persist(k) {
    var r = rec(k);
    r.ts = nowISO(); r.by = PEOPLE[WHO] || WHO;
    lsWrite();
    if (!DB) { pill("Saved on this device", "warn"); return; }
    pill("Saving…");
    DB.doc("showings/" + k).set(r).then(function () { pill("Saved for both of you", "ok"); })
      .catch(function (e) { pill(e && e.code === "not_granted" ? "Saved on this device" : "Save failed, kept locally", "warn"); });
  }
  function savePeople() {
    try { localStorage.setItem(LSP, JSON.stringify(PEOPLE)); } catch (e) { }
    if (DB) DB.doc("meta/people").set({ a: PEOPLE.a, b: PEOPLE.b, ts: nowISO() }).catch(function () { });
  }

  function boot() {
    ST = lsRead();
    try { var p = JSON.parse(localStorage.getItem(LSP) || "null"); if (p && p.a) PEOPLE = { a: p.a, b: p.b || "Her" }; } catch (e) { }
    paint(); applyMode(); BOOTED = true;
    if (!(window.claude && window.claude.use)) { pill("This device only", "warn"); return; }
    pill("Connecting…");
    window.claude.use("db").then(function (db) {
      if (!db) { pill("This device only", "warn"); return; }
      DB = db;
      db.doc("meta/people").get().then(function (s) {
        var d = s.exists && s.data(); if (d && d.a) { PEOPLE = { a: d.a, b: d.b || "Her" }; paint(); }
      }).catch(function () { });
      db.collection("showings").onSnapshot(function (snap) {
        var pushed = [];
        snap.docs.forEach(function (doc) {
          var k = doc.id, d = doc.data() || {}, mine = ST[k];
          if (!mine || (mine.ts || "") <= (d.ts || "")) ST[k] = d;
          else pushed.push(k);
        });
        lsWrite(); paint(); applyMode();
        pill("Saved for both of you", "ok");
        pushed.forEach(function (k) { persist(k); });                     // local notes newer than the store
        Object.keys(ST).forEach(function (k) {                            // notes taken before db was reachable
          if (touched(ST[k]) && !snap.docs.some(function (d) { return d.id === k; })) persist(k);
        });
      }, function () { pill("Live sync dropped, still saving here", "warn"); });
    }).catch(function () { pill("This device only", "warn"); });
  }

  /* The generic fourteen are built here rather than repeated in every card's markup. */
  function fillWalk(host) {
    if (!host || host.dataset.filled) return;
    var k = host.dataset.walk, W = (SHOW_DATA && SHOW_DATA.walk) || [], h = "";
    for (var i = 0; i < W.length; i++) {
      h += '<li class="tri-row"><span class="tt"></span>'
        + '<span class="tri"><button type="button" class="ok" data-kind="walk" data-h="' + k + '" data-i="' + i + '" data-v="ok">Fine</button>'
        + '<button type="button" class="no" data-kind="walk" data-h="' + k + '" data-i="' + i + '" data-v="issue">Problem</button></span>'
        + '<input class="tn" type="text" placeholder="what you saw" data-kind="walkn" data-h="' + k + '" data-i="' + i + '"></li>';
    }
    host.innerHTML = h;
    host.querySelectorAll(".tt").forEach(function (e, i) { e.textContent = W[i]; });
    host.dataset.filled = "1";
  }
  function fillOpen() { document.querySelectorAll(".rec.open .walkhost").forEach(fillWalk); }

  /* ---------------- paint ---------------- */
  function paint() {
    document.querySelectorAll(".rec").forEach(function (s) { if (touched(ST[s.dataset.rec])) s.classList.add("open"); });
    fillOpen();
    document.querySelectorAll("[data-kind]").forEach(function (el) {
      var kd = el.dataset.kind, k = el.dataset.h, r = (k && ST[k]) || {};
      if (kd === "tell") el.classList.toggle("on", ((r.tells || {})[el.dataset.f] || "") === el.dataset.v);
      else if (kd === "targ" || kd === "walk") el.classList.toggle("on", (((r[kd] || {})[el.dataset.i] || {}).s || "") === el.dataset.v);
      else if (kd === "targn" || kd === "walkn") {
        var g = kd === "targn" ? "targ" : "walk", v = ((r[g] || {})[el.dataset.i] || {}).n || "";
        if (document.activeElement !== el) el.value = v;
      }
      else if (kd === "mech") { if (document.activeElement !== el) el.value = (r.mech || {})[el.dataset.f] || ""; el.classList.toggle("set", !!(r.mech || {})[el.dataset.f]); }
      else if (kd === "verdict") el.classList.toggle("on", (r.verdict || "") === el.dataset.v);
      else if (kd === "gut") el.classList.toggle("on", String((r.gut || {})[el.dataset.who] || "") === el.dataset.v);
      else if (kd === "notes") { if (document.activeElement !== el) el.value = r.notes || ""; }
      else if (kd === "visited") el.classList.toggle("on", !!r.visited);
    });
    document.querySelectorAll(".tri-row").forEach(function (row) {
      var b = row.querySelector("button[data-kind]"); if (!b) return;
      var r = ST[b.dataset.h] || {}, s = ((r[b.dataset.kind] || {})[b.dataset.i] || {}).s || "";
      row.classList.toggle("flagged", s === "issue");
      row.classList.toggle("done", s === "ok");
    });
    document.querySelectorAll("[data-person]").forEach(function (e) { e.textContent = PEOPLE[e.dataset.person] || ""; });
    document.querySelectorAll("[data-meta]").forEach(function (e) {
      var k = e.dataset.meta, r = ST[k] || {}, bits = [];
      if (r.date) bits.push("seen " + r.date);
      var a = answered(r); if (a) bits.push(a + " settled");
      if (r.verdict) bits.push(r.verdict);
      if (r.by && bits.length) bits.push("last by " + r.by);
      e.textContent = bits.join(" · ");
    });
    var w = document.getElementById("who-a"), x = document.getElementById("who-b");
    if (w && document.activeElement !== w) w.value = PEOPLE.a;
    if (x && document.activeElement !== x) x.value = PEOPLE.b;
    document.querySelectorAll("#whosw .sw").forEach(function (b) { b.classList.toggle("on", b.dataset.who === WHO); });
    document.querySelectorAll("#whosw .sw").forEach(function (b) { b.textContent = PEOPLE[b.dataset.who] || b.dataset.who; });
  }

  /* ---------------- modes ---------------- */
  function want(k) {
    var r = ST[k] || {};
    if (MODE === "all") return true;
    if (MODE === "seen") return touched(r);
    if (MODE === "short") return r.verdict === "shortlist";
    if (MODE === "todo") return !touched(r) && (H[k] || {}).verdict !== "STOP";
    return true;
  }
  function applyMode() {
    document.querySelectorAll("#whos .m").forEach(function (b) { b.classList.toggle("on", b.dataset.v === MODE); });
    var n = 0;
    document.querySelectorAll(".lot").forEach(function (a) {
      var ok = want(a.dataset.slug); a.classList.toggle("hide", !ok); if (ok) n++;
    });
    var strip = document.getElementById("strip");
    if (!strip) return;
    if (MODE === "all") { strip.classList.remove("on"); return; }
    strip.classList.add("on");
    var ks = Object.keys(H).filter(want).sort(function (x, y) { return (H[x].psf || 0) - (H[y].psf || 0); });
    var lab = MODE === "seen" ? "Houses you have walked, cheapest per usable foot first"
      : MODE === "short" ? "Your shortlist, cheapest per usable foot first" : "Not walked yet, in model rank order";
    if (MODE === "todo") ks = Object.keys(H).filter(want).sort(function (x, y) { return H[x].rank - H[y].rank; });
    var body = ks.length ? "<ol>" + ks.map(function (k) {
      var r = ST[k] || {}, g = r.gut || {}, gs = [];
      if (g.a) gs.push(PEOPLE.a + " " + g.a); if (g.b) gs.push(PEOPLE.b + " " + g.b);
      return "<li><a href='#lot-" + k + "'>" + H[k].name + "</a><span class='sv'>$" + H[k].psf + "/sf"
        + (r.verdict ? " · " + r.verdict : "") + (gs.length ? " · " + gs.join(", ") : "")
        + " · model rank " + H[k].rank + "</span></li>";
    }).join("") + "</ol>" : "<p class='empty'>Nothing in here yet.</p>";
    strip.innerHTML = "<h3>" + lab + " · " + ks.length + " of " + Object.keys(H).length + "</h3>" + body;
  }

  /* ---------------- export ---------------- */
  function buildExport() {
    var patch = {}, showings = {};
    Object.keys(ST).forEach(function (k) {
      var r = ST[k]; if (!touched(r) || !H[k]) return;
      showings[H[k].slug] = r;
      var p = {};
      Object.keys(r.tells || {}).forEach(function (f) {
        var v = r.tells[f]; if (!v || v === "not_shown") return;
        p[f] = v === "true" ? true : v === "false" ? false : v;
      });
      var m = {}; Object.keys(r.mech || {}).forEach(function (f) { if (String(r.mech[f]).trim()) m[f] = r.mech[f]; });
      if (Object.keys(m).length) p.mech_confirmed = m;
      var flags = [];
      ["targ", "walk"].forEach(function (g) {
        Object.keys(r[g] || {}).forEach(function (i) {
          var c = r[g][i]; if (c && c.s === "issue") flags.push((c.n || "").trim() || (g === "walk" ? "walk check " + i : "listing check " + i));
        });
      });
      if (flags.length) p.showing_flags = flags;
      if (r.verdict) p.showing_verdict = r.verdict;
      if (Object.keys(p).length) patch[H[k].slug] = p;
    });
    return JSON.stringify({ generated: nowISO(), people: PEOPLE, observations_patch: patch, showings: showings }, null, 2);
  }
  function doExport() {
    var txt = buildExport(), box = document.getElementById("expbox"), ta = document.getElementById("exptext");
    box.classList.add("on"); ta.value = txt; ta.focus(); ta.select();
    if (navigator.clipboard) navigator.clipboard.writeText(txt).then(function () { pill("Copied to the clipboard", "ok"); }).catch(function () { });
    if (window.claude && window.claude.use) {
      window.claude.use("downloads").then(function (dl) {
        if (!dl) return;
        dl.save({ filename: "showings-" + new Date().toISOString().slice(0, 10) + ".json", data: txt }).catch(function () { });
      }).catch(function () { });
    }
  }

  /* ---------------- events ---------------- */
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-kind]"); if (!b) return;
    var kd = b.dataset.kind, k = b.dataset.h, v = b.dataset.v;
    if (kd === "mode") { MODE = v; applyMode(); return; }
    if (kd === "export") { doExport(); return; }
    if (kd === "who") { WHO = b.dataset.who; paint(); return; }
    if (!k) return;
    var r = rec(k);
    if (kd === "tell") { r.tells = r.tells || {}; if (r.tells[b.dataset.f] === v) delete r.tells[b.dataset.f]; else r.tells[b.dataset.f] = v; }
    else if (kd === "targ" || kd === "walk") {
      var m = r[kd] = r[kd] || {}, i = b.dataset.i; m[i] = m[i] || {};
      m[i].s = m[i].s === v ? "" : v;
      if (!m[i].s && !m[i].n) delete m[i];
    }
    else if (kd === "verdict") r.verdict = r.verdict === v ? "" : v;
    else if (kd === "gut") { r.gut = r.gut || {}; var w = b.dataset.who; if (String(r.gut[w]) === v) delete r.gut[w]; else r.gut[w] = Number(v); }
    else if (kd === "visited") { r.visited = !r.visited; if (r.visited && !r.date) r.date = new Date().toISOString().slice(0, 10); }
    else return;
    if (touched(r) && !r.date) r.date = new Date().toISOString().slice(0, 10);
    if (touched(r)) r.visited = true;
    queue(k); paint(); applyMode();
  });

  document.addEventListener("input", function (ev) {
    var el = ev.target; if (!el.dataset || !el.dataset.kind || el.tagName === "BUTTON") return;
    var kd = el.dataset.kind, k = el.dataset.h;
    if (kd === "person") {
      PEOPLE[el.dataset.who] = el.value || (el.dataset.who === "a" ? "Alex" : "Her");
      clearTimeout(T.__p); T.__p = setTimeout(function () { savePeople(); paint(); applyMode(); }, 700);
      return;
    }
    if (!k) return;
    var r = rec(k);
    if (kd === "mech") { r.mech = r.mech || {}; if (el.value) r.mech[el.dataset.f] = el.value; else delete r.mech[el.dataset.f]; }
    else if (kd === "targn" || kd === "walkn") {
      var g = kd === "targn" ? "targ" : "walk", m = r[g] = r[g] || {}, i = el.dataset.i;
      m[i] = m[i] || {}; m[i].n = el.value; if (!m[i].s && !m[i].n) delete m[i];
    }
    else if (kd === "notes") r.notes = el.value;
    else return;
    if (touched(r)) { r.visited = true; if (!r.date) r.date = new Date().toISOString().slice(0, 10); }
    queue(k); applyMode();
    document.querySelectorAll("[data-meta='" + k + "']").forEach(function (e) { e.textContent = e.textContent; });
  });

  document.addEventListener("click", function (ev) {
    if (ev.target.closest("button,input,textarea,a")) return;
    var h = ev.target.closest(".rec-head"); if (!h) return;
    var sec = h.closest(".rec");
    sec.classList.toggle("open");
    if (sec.classList.contains("open")) { fillWalk(sec.querySelector(".walkhost")); paint(); }
  });

  if (document.readyState !== "loading") boot();
  else document.addEventListener("DOMContentLoaded", boot);
})();
