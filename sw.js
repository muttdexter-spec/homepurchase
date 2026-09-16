var VERSION = "c488d171d4fd";
var C = "walk-" + VERSION;
var FILES = ["index.html", "full.html", "mobile.html", "manifest.json"];

self.addEventListener("install", function(e){
  self.skipWaiting();
  e.waitUntil(caches.open(C).then(function(c){ return c.addAll(FILES); }).catch(function(){}));
});

self.addEventListener("activate", function(e){
  e.waitUntil(caches.keys().then(function(ks){
    return Promise.all(ks.filter(function(k){ return k !== C; }).map(function(k){ return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});

/* Network first. The deployed page always wins when there is a network; the cache is the
   fallback for a basement, not the source of truth. */
self.addEventListener("fetch", function(e){
  var r = e.request;
  if (r.method !== "GET" || new URL(r.url).origin !== self.location.origin) return;
  e.respondWith(
    fetch(r).then(function(resp){
      if (resp && resp.ok) {
        var copy = resp.clone();
        caches.open(C).then(function(c){ c.put(r, copy); }).catch(function(){});
      }
      return resp;
    }).catch(function(){
      return caches.match(r).then(function(hit){
        return hit || caches.match("index.html");
      });
    })
  );
});
