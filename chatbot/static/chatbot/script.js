const messageInput = document.getElementById("message");
const sendButton = document.getElementById("send-button");
const chatBox = document.getElementById("chat-box");

sendButton.addEventListener("click", async function () {

    const message = messageInput.value.trim();

    if (!message) {
        return;
    }

    const csrfToken = document.querySelector(
        '[name=csrfmiddlewaretoken]'
    ).value;

    // Show user's message
    chatBox.innerHTML += `
        <div class="message user">
            <p>${message}</p>
        </div>
    `;

    messageInput.value = "";

    try {

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

        // Check for backend error
        if (!response.ok) {
            throw new Error(data.error || "Something went wrong");
        }

        // Show bot's reply
        chatBox.innerHTML += `
            <div class="message bot">
                <p>${data.reply}</p>
            </div>
        `;

    } catch (error) {

        console.error("Chat error:", error);

        chatBox.innerHTML += `
            <div class="message bot">
                <p>Sorry, something went wrong: ${error.message}</p>
            </div>
        `;
    }

});