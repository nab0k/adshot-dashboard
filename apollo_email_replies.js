(function () {
  var section = document.getElementById("apollo-email-replies-section");
  var listEl = document.getElementById("aer-list");
  var metaEl = document.getElementById("aer-meta");

  if (!section || !listEl || !metaEl) return;

  function fmtDate(value) {
    if (!value) return "—";
    var d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleDateString("uk-UA", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric"
    });
  }

  function fmtDateTime(value) {
    if (!value) return "";
    var d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString("uk-UA", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  }

  function replySignal(replyClass) {
    var red = ["not_interested", "unsubscribe", "already_left_company_or_not_right_person"];
    var green = ["willing_to_meet", "follow_up_question", "person_referral"];

    if (red.indexOf(replyClass) !== -1) return { color: "red", label: "негативний" };
    if (green.indexOf(replyClass) !== -1) return { color: "green", label: "позитивний" };
    return { color: "yellow", label: "увага" };
  }

  function replyClassLabel(value) {
    var map = {
      willing_to_meet: "готовий",
      follow_up_question: "питання",
      person_referral: "referral",
      out_of_office: "OOO",
      already_left_company_or_not_right_person: "не та людина",
      not_interested: "відмова",
      unsubscribe: "unsubscribe",
      none_of_the_above: "інше"
    };
    return map[value] || value || "інше";
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function addChip(parent, text) {
    if (!text) return;
    parent.appendChild(el("span", "aer-chip", text));
  }

  function renderMessage(parent, m) {
    var direction = m.direction === "sent" ? "sent" : "received";
    var msg = el("div", "aer-msg " + direction);

    var who = m.from_name || m.from_email || "";
    var when = fmtDateTime(m.at);
    var label = direction === "sent" ? "Sent" : "Received";

    msg.appendChild(el("div", "aer-msg-head", label + " · " + who + (when ? " · " + when : "")));
    msg.appendChild(el("div", "", m.text || ""));

    parent.appendChild(msg);
  }

  function renderTable(replies) {
    listEl.innerHTML = "";

    var wrap = el("div", "aer-table-wrap");
    var table = document.createElement("table");
    var thead = document.createElement("thead");
    var header = document.createElement("tr");

    ["Контакт", "Тема", "Дата", "Сигнал"].forEach(function (name) {
      header.appendChild(el("th", "", name));
    });

    thead.appendChild(header);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");

    replies.forEach(function (r) {
      var contact = r.contact || {};
      var name = contact.name || contact.email || "Unknown contact";
      var email = contact.email || "";
      var company = contact.company || "";
      var subject = r.subject || "";
      var signal = replySignal(r.reply_class);

      var row = el("tr", "aer-main-row");

      var tdContact = document.createElement("td");
      var nameLine = el("div", "aer-name", name + " ");
      var caret = el("span", "aer-caret", "▶");
      nameLine.appendChild(caret);
      tdContact.appendChild(nameLine);
      tdContact.appendChild(el("div", "aer-sub", email || company || "—"));

      var tdSubject = document.createElement("td");
      tdSubject.appendChild(el("div", "aer-subject", subject || "—"));

      var tdDate = document.createElement("td");
      tdDate.appendChild(el("div", "aer-date", fmtDate(r.received_at)));

      var tdSignal = document.createElement("td");
      var sigWrap = el("span", "aer-signal");
      sigWrap.appendChild(el("span", "aer-dot " + signal.color));
      sigWrap.appendChild(el("span", "", replyClassLabel(r.reply_class)));
      tdSignal.appendChild(sigWrap);

      row.appendChild(tdContact);
      row.appendChild(tdSubject);
      row.appendChild(tdDate);
      row.appendChild(tdSignal);

      var detail = el("tr", "aer-detail-row");
      var detailTd = document.createElement("td");
      detailTd.colSpan = 4;

      var meta = el("div", "aer-thread-meta");
      addChip(meta, "Email: " + (email || "—"));
      if (company) addChip(meta, "Company: " + company);
      addChip(meta, "Subject: " + (subject || "—"));

      var messages = Array.isArray(r.thread_messages) && r.thread_messages.length
        ? r.thread_messages
        : [{
            direction: "received",
            from_name: name,
            from_email: email,
            at: r.received_at,
            text: r.reply_text || ""
          }];

      addChip(meta, "Messages: " + messages.length);
      detailTd.appendChild(meta);

      var thread = el("div", "aer-thread");
      messages.forEach(function (m) {
        renderMessage(thread, m);
      });

      detailTd.appendChild(thread);
      detail.appendChild(detailTd);

      row.addEventListener("click", function () {
        var isOpen = detail.style.display === "table-row";

        section.querySelectorAll(".aer-detail-row").forEach(function (x) {
          x.style.display = "none";
        });

        section.querySelectorAll(".aer-caret").forEach(function (x) {
          x.textContent = "▶";
        });

        if (!isOpen) {
          detail.style.display = "table-row";
          caret.textContent = "▼";
        }
      });

      tbody.appendChild(row);
      tbody.appendChild(detail);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    listEl.appendChild(wrap);
  }

  fetch("apollo_email_replies.json?v=" + Date.now(), { cache: "no-store" })
    .then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(function (data) {
      var replies = Array.isArray(data.replies)
        ? data.replies.filter(function (r) {
            return String(r.reply_text || "").trim();
          })
        : [];

      metaEl.textContent = replies.length + " реальних email-відповідей · " + (data.mailbox || "serhii@adshot-eu.com");

      if (!replies.length) {
        listEl.innerHTML = "";
        listEl.appendChild(el("div", "aer-empty", "Поки немає email-відповідей з реальним текстом."));
        return;
      }

      renderTable(replies);
    })
    .catch(function (err) {
      console.error("Apollo email thread viewer failed:", err);
      metaEl.textContent = "Не вдалося завантажити Apollo email replies";
      listEl.innerHTML = "";
      listEl.appendChild(el("div", "aer-empty", "apollo_email_replies.json не завантажився."));
    });
})();
