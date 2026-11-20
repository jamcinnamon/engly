// 아티팩트의 window.claude 기능(db, sample)을 로컬 서버로 바꿔주는 연결 파일.
// index.html 은 그대로 두고 이 파일만 끼워 넣어서 동작해요.
(function () {
  var listeners = [];

  function snapshot() {
    return fetch("/api/cards").then(function (r) { return r.json(); }).then(function (cards) {
      var snap = {
        metadata: { fromCache: false },
        docs: Object.keys(cards).map(function (id) {
          return { id: id, data: function () { return cards[id]; } };
        })
      };
      listeners.forEach(function (cb) { cb(snap); });
    });
  }
  function post(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) { var e = new Error(j.error || "server error"); e.code = "server"; throw e; }
        return j;
      });
    });
  }

  var db = {
    collection: function () {
      return {
        onSnapshot: function (cb, onErr) {
          listeners.push(cb);
          snapshot().catch(function (e) { if (onErr) onErr(e); });
        },
        add: function (data) { return post("/api/cards", data).then(snapshot); },
        doc: function (id) {
          return {
            set: function (data) { return post("/api/cards/" + id, data).then(snapshot); },
            delete: function () { return post("/api/cards/" + id, { _delete: true }).then(snapshot); }
          };
        }
      };
    }
  };

  // 서버가 글자를 보내는 대로 화면에 흘려보내요.
  var ERR_MARK = "\u0000ERR:";
  function sample(messages, opts) {
    opts = opts || {};
    var text = "";
    function fail(msg) { var e = new Error(msg); e.text = text; throw e; }
    return fetch("/api/sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: messages, quick: opts.modelTier === "quick" }),
      signal: opts.signal
    }).then(function (r) {
      if (!r.ok || !r.body) fail("server error");
      var reader = r.body.getReader(), dec = new TextDecoder();
      function pump() {
        return reader.read().then(function (res) {
          if (res.done) return { text: text };
          text += dec.decode(res.value, { stream: true });
          var i = text.indexOf(ERR_MARK);
          if (i >= 0) { var msg = text.slice(i + ERR_MARK.length); text = text.slice(0, i); fail(msg); }
          if (opts.onText) opts.onText({ text: text });
          return pump();
        });
      }
      return pump();
    }).catch(function (e) {
      if (e.text === undefined) e.text = text;
      throw e;
    });
  }

  window.claude = {
    use: function (name) {
      if (name === "db") return Promise.resolve(db);
      if (name === "sample") return Promise.resolve(sample);
      return Promise.resolve(null);
    }
  };
})();
