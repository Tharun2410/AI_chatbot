const messageInput = document.getElementById("message");
const sendButton = document.getElementById("send-button");
const chatBox = document.getElementById("chat-box");


sendButton.addEventListener("click", sendMessage);


messageInput.addEventListener("keydown", function (event) {

    if (event.key === "Enter") {
        sendMessage();
    }

});


async function sendMessage() {

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
            <p>${escapeHtml(message)}</p>
        </div>
    `;


    messageInput.value = "";

    sendButton.disabled = true;


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


        // Safely read response
        const text = await response.text();


        let data;

        try {

            data = JSON.parse(text);

        } catch (error) {

            console.error(
                "Invalid server response:",
                text
            );

            throw new Error(
                "Server returned an invalid response."
            );
        }


        // Server returned an error
        if (!response.ok) {

            chatBox.innerHTML += `
                <div class="message bot">
                    <p>${escapeHtml(
                        data.error ||
                        "AI service is temporarily unavailable."
                    )}</p>
                </div>
            `;

            return;
        }


        // Show AI response
        chatBox.innerHTML += `
            <div class="message bot">
                <p>${escapeHtml(data.reply)}</p>
            </div>
        `;


        // Scroll to bottom
        chatBox.scrollTop = chatBox.scrollHeight;


    } catch (error) {

        console.error(
            "Chat error:",
            error
        );


        chatBox.innerHTML += `
            <div class="message bot">
                <p>Something went wrong. Please try again.</p>
            </div>
        `;

    } finally {

        sendButton.disabled = false;

        messageInput.focus();

    }

}


/*
    Prevent HTML injection
*/
function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}