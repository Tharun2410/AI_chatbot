const messageInput = document.getElementById("message");
const sendButton = document.getElementById("send-button");
const chatBox = document.getElementById("chat-box");

sendButton.addEventListener("click", async function() {

    const message = messageInput.value;

    const csrfToken = document.querySelector(
        '[name=csrfmiddlewaretoken]'
    ).value;

    // Show user's message
    chatBox.innerHTML += `<p><b>You:</b> ${message}</p>`;

    const response = await fetch("/chat/", {
        method: "POST",

        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },

        body: JSON.stringify({
            message: message
        })
    });

    const data = await response.json();

    // Show bot's reply
    chatBox.innerHTML += `<p><b>Bot:</b> ${data.reply}</p>`;

    // Clear input
    messageInput.value = "";
});