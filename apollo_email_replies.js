(function () {
  var section = document.getElementById("apollo-email-replies-section");
  var listEl  = document.getElementById("aer-list");
  var metaEl  = document.getElementById("aer-meta");
  if (!section || !listEl || !metaEl) return;

  var currentFilter = "all";

  function fmtDate(v) {
    if (!v) return "—";
    var d = new Date(v);
    return isNaN(d) ? v : d.toLocaleDateString("uk-UA", { day:"2-digit", month:"2-digit", year:"numeric" });
  }

  function fmtDateTime(v) {
    if (!v) return "";
    var d = new Date(v);
    return isNaN(d) ? v : d.toLocaleString("uk-UA", { day:"2-digit", month:"2-digit", year:"numeric", hour:"2-digit", minute:"2-digit" });
  }

  function signalFor(rc) {
    var red   = ["not_interested","unsubscribe","already_left_company_or_not_right_person"];
    var green = ["willing_to_meet","follow_up_question","person_referral"];
    if (red.indexOf(rc) !== -1)   return { color:"red",    label:"відмова" };
    if (green.indexOf(rc) !== -1) return { color:"green",  label: rc === "willing_to_meet" ? "готовий" : "питання" };
    return { color:"yellow", label:"увага" };
  }

  function classLabel(rc) {
    var map = {
      willing_to_meet:"готовий", follow_up_question:"питання", person_referral:"referral",
      out_of_office:"OOO", already_left_company_or_not_right_person:"не та людина",
      not_interested:"відмова", unsubscribe:"unsubscribe", none_of_the_above:"інше"
    };
    return map[rc] || rc || "інше";
  }

  function isUnread(r) {
    var msgs = r.thread_messages || [];
    if (!msgs.length) return false;
    return msgs[msgs.length - 1].direction === "received";
  }

  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt !== undefined && txt !== null) n.textContent = String(txt);
    return n;
  }

  function updateKPIs(replies) {
    var pos  = replies.filter(function(r){ var s=signalFor(r.reply_class); return s.color==="green"; }).length;
    var neg  = replies.filter(function(r){ var s=signalFor(r.reply_class); return s.color==="red"; }).length;
    var attn = replies.filter(function(r){ var s=signalFor(r.reply_class); return s.color==="yellow"; }).length;
    var unr  = replies.filter(isUnread).length;

    document.getElementById("aer-kpi-pos").textContent  = pos;
    document.getElementById("aer-kpi-neg").textContent  = neg;
    document.getElementById("aer-kpi-attn").textContent = attn;
    document.getElementById("aer-kpi-unr").textContent  = unr;
  }

  function renderTable(replies) {
    listEl.innerHTML = "";

    var sorted = replies.slice().sort(function(a, b) {
      var order = { willing_to_meet:0, follow_up_question:1, person_referral:2 };
      var oa = order[a.reply_class] !== undefined ? order[a.reply_class] : 9;
      var ob = order[b.reply_class] !== undefined ? order[b.reply_class] : 9;
      if (oa !== ob) return oa - ob;
      return new Date(b.received_at) - new Date(a.received_at);
    });

    var filtered = currentFilter === "all" ? sorted : sorted.filter(function(r) {
      var s = signalFor(r.reply_class);
      if (currentFilter === "positive") return s.color === "green";
      if (currentFilter === "negative") return s.color === "red";
      if (currentFilter === "attention") return s.color === "yellow";
      return true;
    });

    if (!filtered.length) {
      listEl.appendChild(el("div", "aer-empty", "Немає відповідей у цій категорії."));
      return;
    }

    var wrap  = el("div", "aer-table-wrap");
    var table = document.createElement("table");
    var thead = document.createElement("thead");
    var hrow  = document.createElement("tr");
    ["Контакт", "Тема", "Дата", "Сигнал"].forEach(function(n){ hrow.appendChild(el("th","",n)); });
    thead.appendChild(hrow);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");

    filtered.forEach(function(r) {
      var contact = r.contact || {};
      var name    = contact.name || contact.email || "Unknown";
      var email   = contact.email || "";
      var subject = r.subject || "";
      var sig     = signalFor(r.reply_class);
      var unread  = isUnread(r);

      var row = el("tr", "aer-main-row");

      // Contact cell
      var tdC = document.createElement("td");
      var nameEl = el("div", "aer-name");
      var nameText = document.createTextNode(name + " ");
      nameEl.appendChild(nameText);
      var caret = el("span", "aer-caret", "▶");
      nameEl.appendChild(caret);
      if (unread) {
        var dot = el("span", "aer-unread-dot");
        dot.title = "Ми ще не відповіли";
        nameEl.appendChild(dot);
      }
      tdC.appendChild(nameEl);
      if (email) tdC.appendChild(el("div", "aer-sub", email));

      // Subject cell with preview
      var tdS = document.createElement("td");
      tdS.appendChild(el("div", "aer-subject-line", subject || "—"));
      var preview = r.preview || "";
      if (preview) {
        var firstLine = preview.split(/\r?\n/)[0].trim().slice(0, 90);
        if (firstLine) tdS.appendChild(el("div", "aer-preview", firstLine));
      }

      // Date cell
      var tdD = document.createElement("td");
      tdD.appendChild(el("div", "aer-date", fmtDate(r.received_at)));

      // Signal cell
      var tdSig = document.createElement("td");
      var sigWrap = el("span", "aer-signal");
      sigWrap.appendChild(el("span", "aer-dot " + sig.color));
      sigWrap.appendChild(el("span", "aer-sig-label " + sig.color, classLabel(r.reply_class)));
      tdSig.appendChild(sigWrap);

      row.appendChild(tdC);
      row.appendChild(tdS);
      row.appendChild(tdD);
      row.appendChild(tdSig);

      // Detail row (thread)
      var detail  = el("tr", "aer-detail-row");
      var detailTd = document.createElement("td");
      detailTd.colSpan = 4;

      var thread = el("div", "aer-thread");

      var messages = Array.isArray(r.thread_messages) && r.thread_messages.length
        ? r.thread_messages
        : [{ direction:"received", from_name:name, from_email:email, at:r.received_at, text:r.reply_text||"" }];

      messages.forEach(function(m) {
        var isSent = m.direction === "sent";
        var msgEl  = el("div", "aer-msg-wrap " + (isSent ? "sent" : "received"));
        var head   = el("div", "aer-msg-head", (isSent ? "Ми" : (m.from_name || m.from_email || "Контакт")) + " · " + fmtDateTime(m.at));
        if (isSent) head.style.textAlign = "right";
        var body = el("div", "aer-msg-body " + (isSent ? "sent" : "received"), m.text || "");
        msgEl.appendChild(head);
        msgEl.appendChild(body);
        thread.appendChild(msgEl);
      });

      detailTd.appendChild(thread);
      detail.appendChild(detailTd);

      row.addEventListener("click", function() {
        var isOpen = detail.style.display === "table-row";
        section.querySelectorAll(".aer-detail-row").forEach(function(x){ x.style.display = "none"; });
        section.querySelectorAll(".aer-caret").forEach(function(x){ x.textContent = "▶"; });
        section.querySelectorAll(".aer-main-row").forEach(function(x){ x.classList.remove("active"); });
        if (!isOpen) {
          detail.style.display = "table-row";
          caret.textContent = "▼";
          row.classList.add("active");
          setTimeout(function(){ row.scrollIntoView({ behavior:"smooth", block:"nearest" }); }, 50);
        }
      });

      tbody.appendChild(row);
      tbody.appendChild(detail);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    listEl.appendChild(wrap);
  }

  function applyFilter(replies, filter) {
    currentFilter = filter;
    section.querySelectorAll(".aer-chip").forEach(function(c){ c.classList.remove("active"); });
    section.querySelector(".aer-chip[data-f='" + filter + "']").classList.add("active");
    renderTable(replies);
  }

  fetch("apollo_email_replies.json?v=" + Date.now(), { cache:"no-store" })
    .then(function(res){ if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); })
    .then(function(data) {
      var replies = (data.replies || []).filter(function(r){ return String(r.reply_text||"").trim(); });

      metaEl.textContent = replies.length + " реальних email-відповідей · " + (data.mailbox || "serhii@adshot-eu.com");

      updateKPIs(replies);

      // Filter chips
      var chips = section.querySelector(".aer-chips");
      if (chips) {
        chips.querySelectorAll(".aer-chip").forEach(function(c) {
          c.addEventListener("click", function(){ applyFilter(replies, c.dataset.f); });
        });
      }

      if (!replies.length) {
        listEl.appendChild(el("div","aer-empty","Поки немає email-відповідей з реальним текстом."));
        return;
      }
      renderTable(replies);
    })
    .catch(function(err) {
      console.error("Apollo email replies:", err);
      metaEl.textContent = "Не вдалося завантажити Apollo email replies";
      listEl.appendChild(el("div","aer-empty","apollo_email_replies.json не завантажився."));
    });
})();
