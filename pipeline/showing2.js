/* Showing record runtime, v2. One note-taker, generalised questions.
   Reads SHOW_DATA = {houses:{k:{slug,name,psf,rank,verdict}}, walk:[...], qs:{key:{opts:[{v,patch}]}}}.
   Storage: the artifact's shared db when published as an artifact, localStorage otherwise.
   Nothing here recomputes the model; answers are exported as a patch for score.py. */
(function () {
  var LS = "walk-showings-v2";
  var ST = {}, DB = null, MODE = "all", T = {};
  /* v6: two people, one record. gut, verdict and notes are per person; everything else is shared. */
  var WHO = "alex";
  function pf(base) { return base + "_" + WHO; }
  function gv(r, base, who) { return r[base + "_" + (who || WHO)]; }
  function mirrorGut() {
    var g = {};
    Object.keys(ST).forEach(function (k) {
      var r = ST[k] || {}, o = {};
      if (r.gut_alex) o.alex = r.gut_alex;
      if (r.gut_partner) o.partner = r.gut_partner;
      if (o.alex || o.partner) g[k] = o;
    });
    try { localStorage.setItem("walk-v6-gut", JSON.stringify(g)); } catch (e) { }
    var picks = {};
    Object.keys(ST).forEach(function (k) {
      var r = ST[k] || {}, o = {};
      if (r.verdict_alex === "shortlist") o.alex = 1;
      if (r.verdict_partner === "shortlist") o.partner = 1;
      if (o.alex || o.partner) picks[k] = o;
    });
    try { localStorage.setItem("walk-v6-picks", JSON.stringify(picks)); } catch (e) { }
    document.querySelectorAll("[data-gut]").forEach(function (el) {
      var r = ST[el.dataset.gut] || {}, b = [];
      if (r.gut_alex) b.push("You " + r.gut_alex);
      if (r.gut_partner) b.push("Partner " + r.gut_partner);
      el.textContent = b.length ? " \u00b7 " + b.join(" \u00b7 ") : "";
    });
    document.querySelectorAll("[data-gpair]").forEach(function (el) {
      var r = ST[el.dataset.gpair] || {}, b = [];
      if (r.gut_alex) b.push("you " + r.gut_alex + "/5");
      if (r.gut_partner) b.push("partner " + r.gut_partner + "/5");
      el.textContent = b.join(" \u00b7 ");
    });
    document.querySelectorAll("[data-gutdis]").forEach(function (el) {
      var r = ST[el.dataset.gutdis] || {};
      el.hidden = !(r.gut_alex && r.gut_partner && Math.abs(r.gut_alex - r.gut_partner) >= 3);
    });
  }
  var H = (SHOW_DATA && SHOW_DATA.houses) || {}, QS = (SHOW_DATA && SHOW_DATA.qs) || {};

  function rec(k) { if (!ST[k]) ST[k] = {}; return ST[k]; }
  function nowISO() { return new Date().toISOString(); }
  function today() { return new Date().toISOString().slice(0, 10); }
  function pill(t, c) { var e = document.getElementById("sr-pill"); if (e) { e.textContent = t; e.className = "sr-pill " + (c || ""); } }
  function lsRead() { try { return JSON.parse(localStorage.getItem(LS) || "{}"); } catch (e) { return {}; } }
  function lsWrite() { try { localStorage.setItem(LS, JSON.stringify(ST)); } catch (e) { } }

  function touched(r) {
    if (!r) return false;
    if (r.visited) return true;
    if (r.verdict_alex || r.verdict_partner || r.gut_alex || r.gut_partner) return true;
    if ((r.notes_alex || "").trim() || (r.notes_partner || "").trim()) return true;
    var n = 0;
    ["ans", "mech", "targ", "walk"].forEach(function (g) { if (r[g] && Object.keys(r[g]).length) n++; });
    return n > 0;
  }
  function settled(r) {
    var c = 0, a = (r && r.ans) || {};
    Object.keys(a).forEach(function (q) { if (a[q] && a[q] !== "unsure") c++; });
    return c;
  }

  /* ---------------- persistence ---------------- */
  function queue(k) { clearTimeout(T[k]); T[k] = setTimeout(function () { persist(k); }, 700); }
  function persist(k) {
    var r = rec(k);
    r.ts = nowISO();
    lsWrite();
    if (!DB) { pill("Saved on this device", "warn"); return; }
    pill("Saving…");
    DB.doc("showings/" + k).set(r).then(function () { pill("Saved", "ok"); })
      .catch(function (e) { pill(e && e.code === "not_granted" ? "Saved on this device" : "Save failed, kept locally", "warn"); });
  }

  function boot() {
    try { WHO = localStorage.getItem("walk-v6-who") || "alex"; } catch (e) { }
    ST = lsRead();
    paint(); applyMode();
    if (!(window.claude && window.claude.use)) { pill("This device only", "warn"); return; }
    pill("Connecting…");
    window.claude.use("db").then(function (db) {
      if (!db) { pill("This device only", "warn"); return; }
      DB = db;
      db.collection("showings").onSnapshot(function (snap) {
        var seen = {};
        snap.docs.forEach(function (doc) {
          var k = doc.id, d = doc.data() || {}; seen[k] = 1;
          var mine = ST[k];
          if (!mine || (mine.ts || "") <= (d.ts || "")) ST[k] = d;
          else persist(k);
        });
        lsWrite(); paint(); applyMode(); pill("Saved", "ok");
        Object.keys(ST).forEach(function (k) { if (touched(ST[k]) && !seen[k]) persist(k); });
      }, function () { pill("Live sync dropped, still saving here", "warn"); });
    }).catch(function () { pill("This device only", "warn"); });
    mirrorGut();
  }

  /* The generic fourteen are built here rather than repeated in every card's markup. */
  function fillWalk(host) {
    if (!host || host.dataset.filled) return;
    var k = host.dataset.walk, W = (SHOW_DATA && SHOW_DATA.walk) || [], h = "";
    for (var i = 0; i < W.length; i++) {
      h += '<li class="sr-row"><span class="sr-t"></span>'
        + '<span class="sr-tri"><button type="button" class="ok" data-kind="walk" data-h="' + k + '" data-i="' + i + '" data-v="ok">Fine</button>'
        + '<button type="button" class="no" data-kind="walk" data-h="' + k + '" data-i="' + i + '" data-v="issue">Problem</button></span>'
        + '<input class="sr-tn" type="text" placeholder="what you saw" data-kind="walkn" data-h="' + k + '" data-i="' + i + '"></li>';
    }
    host.innerHTML = h;
    host.querySelectorAll(".sr-t").forEach(function (e, i) { e.textContent = W[i]; });
    host.dataset.filled = "1";
  }

  /* ---------------- paint ---------------- */
  function paint() {
    document.querySelectorAll(".sr").forEach(function (s) { if (touched(ST[s.dataset.rec])) s.classList.add("open"); });
    document.querySelectorAll(".sr.open .sr-walkhost").forEach(fillWalk);
    document.querySelectorAll("[data-kind]").forEach(function (el) {
      var kd = el.dataset.kind, k = el.dataset.h, r = (k && ST[k]) || {};
      if (kd === "ans") el.classList.toggle("on", ((r.ans || {})[el.dataset.q] || "") === el.dataset.v);
      else if (kd === "targ" || kd === "walk") el.classList.toggle("on", (((r[kd] || {})[el.dataset.i] || {}).s || "") === el.dataset.v);
      else if (kd === "targn" || kd === "walkn") {
        var g = kd === "targn" ? "targ" : "walk", v = ((r[g] || {})[el.dataset.i] || {}).n || "";
        if (document.activeElement !== el) el.value = v;
      }
      else if (kd === "mech") {
        if (document.activeElement !== el) el.value = (r.mech || {})[el.dataset.f] || "";
        el.classList.toggle("set", !!(r.mech || {})[el.dataset.f]);
      }
      else if (kd === "verdict") el.classList.toggle("on", (gv(r, "verdict") || "") === el.dataset.v);
      else if (kd === "gut") el.classList.toggle("on", String(gv(r, "gut") || "") === el.dataset.v);
      else if (kd === "notes") { if (document.activeElement !== el) el.value = gv(r, "notes") || ""; }
      else if (kd === "who") { el.value = WHO; }
      else if (kd === "visited") el.classList.toggle("on", !!r.visited);
    });
    document.querySelectorAll(".sr-row").forEach(function (row) {
      var b = row.querySelector("button[data-kind]"); if (!b) return;
      var r = ST[b.dataset.h] || {}, s = ((r[b.dataset.kind] || {})[b.dataset.i] || {}).s || "";
      row.classList.toggle("flagged", s === "issue");
      row.classList.toggle("done", s === "ok");
    });
    document.querySelectorAll("[data-meta]").forEach(function (e) {
      var r = ST[e.dataset.meta] || {}, bits = [];
      if (r.date) bits.push("seen " + r.date);
      var a = settled(r); if (a) bits.push(a + " settled");
      if (gv(r, "verdict")) bits.push(gv(r, "verdict"));
      if (r.gut_alex) bits.push("you " + r.gut_alex + "/5");
      if (r.gut_partner) bits.push("partner " + r.gut_partner + "/5");
      e.textContent = bits.join(" · ");
    });
  }

  /* ---------------- modes ---------------- */
  function want(k) {
    var r = ST[k] || {};
    if (MODE === "all") return true;
    if (MODE === "seen") return touched(r);
    if (MODE === "short") return r.verdict_alex === "shortlist" || r.verdict_partner === "shortlist";
    if (MODE === "todo") return !touched(r) && (H[k] || {}).verdict !== "STOP";
    return true;
  }
  function applyMode() {
    document.querySelectorAll("#sr-ctl .sr-mode").forEach(function (b) { b.classList.toggle("on", b.dataset.v === MODE); });
    document.querySelectorAll(".lot").forEach(function (a) { a.classList.toggle("sr-hide", !want(a.dataset.slug)); });
    var strip = document.getElementById("sr-strip");
    if (!strip) return;
    if (MODE === "all") { strip.classList.remove("on"); return; }
    strip.classList.add("on");
    var ks = Object.keys(H).filter(want);
    if (MODE === "todo") ks.sort(function (x, y) { return H[x].rank - H[y].rank; });
    else ks.sort(function (x, y) { return (H[x].psf || 0) - (H[y].psf || 0); });
    var lab = MODE === "seen" ? "Houses you have walked, cheapest per usable foot first"
      : MODE === "short" ? "Your shortlist, cheapest per usable foot first" : "Not walked yet, in model rank order";
    var body = ks.length ? "<ol>" + ks.map(function (k) {
      var r = ST[k] || {};
      return "<li><a href='#sr-lot-" + k + "'>" + H[k].name + "</a><span class='sv'>$" + H[k].psf + "/sf"
        + (r.verdict ? " · " + r.verdict : "") + (r.gut ? " · " + r.gut + "/5" : "")
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
      Object.keys(r.ans || {}).forEach(function (q) {
        var v = r.ans[q]; if (!v || v === "unsure") return;
        var def = QS[q]; if (!def) return;
        var op = null;
        for (var i = 0; i < def.opts.length; i++) if (def.opts[i].v === v) op = def.opts[i];
        if (!op || !op.patch) return;
        Object.keys(op.patch).forEach(function (f) { p[f] = op.patch[f]; });
      });
      var m = {}; Object.keys(r.mech || {}).forEach(function (f) { if (String(r.mech[f]).trim()) m[f] = r.mech[f]; });
      if (Object.keys(m).length) p.mech_confirmed = m;
      var flags = [];
      ["targ", "walk"].forEach(function (g) {
        var src = g === "walk" ? (SHOW_DATA.walk || []) : null;
        Object.keys(r[g] || {}).forEach(function (i) {
          var c = r[g][i]; if (!c || c.s !== "issue") return;
          var base = src ? src[+i] : ("listing check " + (+i + 1));
          flags.push((c.n || "").trim() ? base + " — " + c.n.trim() : base);
        });
      });
      if (flags.length) p.showing_flags = flags;
      ["alex", "partner"].forEach(function (w) {
        if (r["verdict_" + w]) p["verdict_" + w] = r["verdict_" + w];
        if (r["gut_" + w]) p["gut_" + w] = r["gut_" + w];
        if ((r["notes_" + w] || "").trim()) p["notes_" + w] = r["notes_" + w].trim();
      });
      /* v6: the four year boxes become the _seen vocabulary score.py reads. A year is
         replaced_<year>; leaving a box empty says nothing, which is not the same as original. */
      var SEEN = {roof_year: "roof_seen", furnace_year: "furnace_seen",
                  ac_year: "ac_seen", water_heater_year: "water_heater_seen"};
      Object.keys(SEEN).forEach(function (f) {
        var y = ((r.mech || {})[f] || "").toString().trim();
        if (/^(19|20)\d{2}$/.test(y)) p[SEEN[f]] = "replaced_" + y;
      });
      if (Object.keys(p).length) patch[H[k].slug] = p;
    });
    return JSON.stringify({ generated: nowISO(), observations_patch: patch, showings: showings }, null, 2);
  }
  function doExport() {
    var txt = buildExport(), box = document.getElementById("sr-expbox"), ta = document.getElementById("sr-exptext");
    box.classList.add("on"); ta.value = txt; ta.focus(); ta.select();
    if (navigator.clipboard) navigator.clipboard.writeText(txt).then(function () { pill("Copied to the clipboard", "ok"); }).catch(function () { });
    if (window.claude && window.claude.use) {
      window.claude.use("downloads").then(function (dl) {
        if (!dl) return;
        dl.save({ filename: "showings-" + today() + ".json", data: txt }).catch(function () { });
      }).catch(function () { });
    }
  }

  /* ---------------- events ---------------- */
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-kind]");
    if (!b) {
      if (ev.target.closest("button,input,textarea,a")) return;
      var h = ev.target.closest(".sr-head"); if (!h) return;
      var sec = h.closest(".sr");
      sec.classList.toggle("open");
      if (sec.classList.contains("open")) { fillWalk(sec.querySelector(".sr-walkhost")); paint(); }
      return;
    }
    var kd = b.dataset.kind, k = b.dataset.h, v = b.dataset.v;
    if (kd === "mode") { MODE = v; applyMode(); return; }
    if (kd === "export") { doExport(); return; }
    if (!k) return;
    var r = rec(k);
    if (kd === "ans") { r.ans = r.ans || {}; if (r.ans[b.dataset.q] === v) delete r.ans[b.dataset.q]; else r.ans[b.dataset.q] = v; }
    else if (kd === "targ" || kd === "walk") {
      var m = r[kd] = r[kd] || {}, i = b.dataset.i; m[i] = m[i] || {};
      m[i].s = m[i].s === v ? "" : v;
      if (!m[i].s && !m[i].n) delete m[i];
    }
    else if (kd === "verdict") r[pf("verdict")] = r[pf("verdict")] === v ? "" : v;
    else if (kd === "gut") r[pf("gut")] = String(r[pf("gut")]) === v ? "" : Number(v);
    else if (kd === "visited") { r.visited = !r.visited; if (r.visited && !r.date) r.date = today(); }
    else return;
    if (touched(r)) { r.visited = true; if (!r.date) r.date = today(); }
    queue(k); paint(); applyMode(); mirrorGut();
  });

  /* the who selector is a change, not a click */
  document.addEventListener("change", function (ev) {
    var el = ev.target;
    if (!el.dataset || el.dataset.kind !== "who") return;
    WHO = el.value === "partner" ? "partner" : "alex";
    document.querySelectorAll("[data-kind=who]").forEach(function (s2) { s2.value = WHO; });
    try { localStorage.setItem("walk-v6-who", WHO); } catch (e) { }
    paint();
  });

  document.addEventListener("input", function (ev) {
    var el = ev.target; if (!el.dataset || !el.dataset.kind || el.tagName === "BUTTON") return;
    var kd = el.dataset.kind, k = el.dataset.h; if (!k) return;
    var r = rec(k);
    if (kd === "mech") { r.mech = r.mech || {}; if (el.value) r.mech[el.dataset.f] = el.value; else delete r.mech[el.dataset.f]; }
    else if (kd === "targn" || kd === "walkn") {
      var g = kd === "targn" ? "targ" : "walk", m = r[g] = r[g] || {}, i = el.dataset.i;
      m[i] = m[i] || {}; m[i].n = el.value; if (!m[i].s && !m[i].n) delete m[i];
    }
    else if (kd === "notes") r[pf("notes")] = el.value;
    else return;
    if (touched(r)) { r.visited = true; if (!r.date) r.date = today(); }
    queue(k); mirrorGut();
  });

  if (document.readyState !== "loading") boot();
  else document.addEventListener("DOMContentLoaded", boot);
})();
