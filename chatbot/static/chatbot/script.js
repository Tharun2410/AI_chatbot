const messageInput = document.getElementById("message");
const sendButton = document.getElementById("send-button");
const chatBox = document.getElementById("chat-box");


sendButton.addEventListener("click", sendMessage);


messageInput.addEventListener("keydown", function (event) {

    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }

});


async function sendMessage() {

    const message = messageInput.value.trim();


    if (!message) {
        return;
    }


    const csrfElement = document.querySelector(
        '[name=csrfmiddlewaretoken]'
    );


    if (!csrfElement) {

        console.error(
            "CSRF token not found."
        );

        addBotMessage(
            "Something went wrong. Please refresh the page."
        );

        return;
    }


    const csrfToken = csrfElement.value;


    // -------------------------------
    // Show user message
    // -------------------------------

    addUserMessage(message);


    messageInput.value = "";

    sendButton.disabled = true;


    try {

        const response = await fetch(
            "/chat/",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json",

                    "X-CSRFToken":
                        csrfToken
                },

                body: JSON.stringify({
                    message: message
                })
            }
        );


        // --------------------------------
        // Read server response safely
        // --------------------------------

        const responseText =
            await response.text();


        console.log(
            "Server response:",
            responseText
        );


        let data;


        try {

            data = JSON.parse(
                responseText
            );

        } catch (jsonError) {

            console.error(
                "JSON parsing error:",
                jsonError
            );

            console.error(
                "Raw response:",
                responseText
            );

            addBotMessage(
                "The server returned an unexpected response. Please try again."
            );

            return;
        }


        // --------------------------------
        // Server error
        // --------------------------------

        if (!response.ok) {

            addBotMessage(
                data.error ||
                "AI service is temporarily unavailable."
            );

            return;
        }


        // --------------------------------
        // Successful AI response
        // --------------------------------

        if (
            data.reply === undefined ||
            data.reply === null
        ) {

            addBotMessage(
                "The AI returned an empty response. Please try again."
            );

            return;
        }


        addBotMessage(
            data.reply
        );


    } catch (error) {

        console.error(
            "Chat request error:",
            error
        );


        addBotMessage(
            "Unable to connect to the AI service. Please try again."
        );


    } finally {

        sendButton.disabled = false;

        messageInput.focus();

    }

}


// =====================================
// ADD USER MESSAGE
// =====================================

function addUserMessage(message) {

    const messageDiv =
        document.createElement("div");

    messageDiv.className =
        "message user";


    const paragraph =
        document.createElement("p");

    paragraph.textContent =
        message;


    messageDiv.appendChild(
        paragraph
    );


    chatBox.appendChild(
        messageDiv
    );


    scrollChatToBottom();
}


// =====================================
// ADD BOT MESSAGE
// =====================================

function addBotMessage(message) {

    const messageDiv =
        document.createElement("div");

    messageDiv.className =
        "message bot";


    const paragraph =
        document.createElement("p");

    paragraph.textContent =
        message;


    messageDiv.appendChild(
        paragraph
    );


    chatBox.appendChild(
        messageDiv
    );


    scrollChatToBottom();
}


// =====================================
// SCROLL CHAT
// =====================================

function scrollChatToBottom() {

    chatBox.scrollTop =
        chatBox.scrollHeight;
}