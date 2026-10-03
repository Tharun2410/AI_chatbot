/* BRO chat — robust version: one delegated click handler, null-safe, shows real errors */
document.addEventListener("DOMContentLoaded", function () {
    console.log("BRO script loaded");

    const $ = (id) => document.getElementById(id);
    const messageInput = $("message");
    const sendButton = $("send-button");
    const chatBox = $("chat-box");
    const welcomeScreen = $("welcome-screen");
    const menuDropdown = $("menu-dropdown");
    const statusText = $("connection-status");

    if (!messageInput || !sendButton || !chatBox) {
        console.error("BRO: missing #message, #send-button or #chat-box in the HTML. Use the new index.html.");
        return;
    }

    /* ---------- helpers ---------- */
    function closeMenu() { if (menuDropdown) menuDropdown.classList.remove("show"); }
    function setStatus(t) { if (statusText) statusText.textContent = t; }
    function scrollDown() {
        requestAnimationFrame(() => chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" }));
    }
    function addMessage(role, text) {
        const div = document.createElement("div");
        div.className = "message " + role;
        const p = document.createElement("p");
        p.textContent = text;
        div.appendChild(p);
        chatBox.appendChild(div);
        scrollDown();
    }
    function addTyping() {
        const w = document.createElement("div");
        w.className = "message bot typing-message";
        w.innerHTML = '<div class="typing-box"><span class="typing-label">BRO</span><div class="typing-dots"><span></span><span></span><span></span></div></div>';
        chatBox.appendChild(w);
        scrollDown();
        return w;
    }
    function setLoading(on) {
        sendButton.disabled = on;
        sendButton.classList.toggle("loading", on);
    }
    function resetChat() {
        chatBox.querySelectorAll(".message").forEach((m) => m.remove());
        if (welcomeScreen) welcomeScreen.style.display = "block";
        closeMenu();
        messageInput.focus();
    }

    /* ---------- send message to Django ---------- */
    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || sendButton.disabled) return;

        const csrf = document.querySelector("[name=csrfmiddlewaretoken]");
        if (!csrf) {
            addMessage("bot", "Security token not found. Please refresh the page.");
            return;
        }

        if (welcomeScreen) welcomeScreen.style.display = "none";
        addMessage("user", message);
        messageInput.value = "";
        setLoading(true);
        const typing = addTyping();

        try {
            const response = await fetch("/chat/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrf.value },
                body: JSON.stringify({ message: message }),
            });
            const raw = await response.text();
            typing.remove();

            let data = null;
            try { data = JSON.parse(raw); } catch (e) {}

            if (!response.ok) {
                addMessage("bot", (data && data.error) || "Server error (HTTP " + response.status + "). Check your Django /chat/ view and terminal.");
                setStatus("Busy");
            } else if (!data || !data.reply || !String(data.reply).trim()) {
                addMessage("bot", "The server replied, but without a 'reply' field. Check your /chat/ view.");
            } else {
                setStatus("Online");
                addMessage("bot", data.reply);
            }
        } catch (error) {
            console.error("Chat request failed:", error);
            typing.remove();
            addMessage("bot", "Unable to reach the server. Is Django running?");
            setStatus("Offline");
        } finally {
            setLoading(false);
            messageInput.focus();
        }
    }

    /* ---------- ONE delegated click handler (works for every button) ---------- */
    document.addEventListener("click", function (event) {
        const t = event.target;

        const card = t.closest(".suggestion-card");
        if (card) { messageInput.value = card.dataset.prompt || ""; sendMessage(); return; }

        const hist = t.closest(".history-item");
        if (hist) { messageInput.value = hist.dataset.prompt || ""; messageInput.focus(); return; }

        const chip = t.closest(".chip");
        if (chip) {
            const prefix = chip.dataset.prefix || "";
            if (!messageInput.value.startsWith(prefix)) messageInput.value = prefix + messageInput.value;
            messageInput.focus();
            return;
        }

        if (t.closest("#send-button")) { sendMessage(); return; }
        if (t.closest("#new-chat-button")) { messageInput.value = ""; resetChat(); return; }
        if (t.closest("#clear-chat")) { resetChat(); return; }
        if (t.closest("#focus-input")) { messageInput.focus(); closeMenu(); return; }

        if (t.closest("#theme-toggle")) {
            const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
            document.documentElement.dataset.theme = next;
            try { localStorage.setItem("bro-theme", next); } catch (e) {}
            closeMenu();
            return;
        }

        if (t.closest("#menu-button")) { menuDropdown && menuDropdown.classList.toggle("show"); return; }
        if (!t.closest("#menu-dropdown")) closeMenu();
    });

    /* ---------- keyboard ---------- */
    messageInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    /* ---------- sidebar search ---------- */
    const search = $("history-search");
    if (search) {
        search.addEventListener("input", function () {
            const q = search.value.toLowerCase();
            document.querySelectorAll("#chat-history .history-item").forEach((item) => {
                item.classList.toggle("hidden", !item.textContent.toLowerCase().includes(q));
            });
        });
    }

    /* ---------- greeting ---------- */
    const greeting = $("greeting");
    if (greeting) {
        const h = new Date().getHours();
        greeting.textContent = h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
    }

    messageInput.focus();
});