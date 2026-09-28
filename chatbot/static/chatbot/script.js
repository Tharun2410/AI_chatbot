const messageInput =
    document.getElementById("message");

const sendButton =
    document.getElementById("send-button");

const chatBox =
    document.getElementById("chat-box");


// =================================
// SEND BUTTON
// =================================

sendButton.addEventListener(
    "click",
    sendMessage
);


// =================================
// ENTER KEY
// =================================

messageInput.addEventListener(
    "keydown",
    function (event) {

        if (event.key === "Enter") {

            event.preventDefault();

            sendMessage();
        }
    }
);


// =================================
// SEND MESSAGE
// =================================

async function sendMessage() {

    const message =
        messageInput.value.trim();

    if (!message) {
        return;
    }


    // -----------------------------
    // CSRF TOKEN
    // -----------------------------

    const csrfElement =
        document.querySelector(
            '[name=csrfmiddlewaretoken]'
        );

    if (!csrfElement) {

        addBotMessage(
            "Security token not found. Please refresh the page."
        );

        return;
    }


    const csrfToken =
        csrfElement.value;


    // -----------------------------
    // Show user message
    // -----------------------------

    addUserMessage(message);

    messageInput.value = "";

    sendButton.disabled = true;


    try {

        const response =
            await fetch(
                "/chat/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "X-CSRFToken":
                            csrfToken
                    },

                    body:
                        JSON.stringify({
                            message: message
                        })
                }
            );


        // -------------------------
        // Read response
        // -------------------------

        const responseText =
            await response.text();

        console.log(
            "Chat API status:",
            response.status
        );

        console.log(
            "Chat API response:",
            responseText
        );


        // -------------------------
        // Parse JSON
        // -------------------------

        let data;

        try {

            data =
                JSON.parse(
                    responseText
                );

        } catch (error) {

            console.error(
                "Invalid JSON:",
                error
            );

            addBotMessage(
                "The server returned an invalid response. Please try again."
            );

            return;
        }


        // -------------------------
        // Server error
        // -------------------------

        if (!response.ok) {

            addBotMessage(
                data.error ||
                "The AI service is temporarily unavailable."
            );

            return;
        }


        // -------------------------
        // Empty AI response
        // -------------------------

        if (
            !data.reply ||
            !data.reply.trim()
        ) {

            addBotMessage(
                "The AI returned an empty response. Please try again."
            );

            return;
        }


        // -------------------------
        // Show AI response
        // -------------------------

        addBotMessage(
            data.reply
        );

    }


    // -----------------------------
    // Network error
    // -----------------------------

    catch (error) {

        console.error(
            "Chat request failed:",
            error
        );

        addBotMessage(
            "Unable to connect to the chatbot server. Please check your connection."
        );
    }


    // -----------------------------
    // Enable button
    // -----------------------------

    finally {

        sendButton.disabled = false;

        messageInput.focus();
    }
}


// =================================
// USER MESSAGE
// =================================

function addUserMessage(message) {

    const messageDiv =
        document.createElement(
            "div"
        );

    messageDiv.className =
        "message user";


    const paragraph =
        document.createElement(
            "p"
        );

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


// =================================
// BOT MESSAGE
// =================================

function addBotMessage(message) {

    const messageDiv =
        document.createElement(
            "div"
        );

    messageDiv.className =
        "message bot";


    const paragraph =
        document.createElement(
            "p"
        );

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


// =================================
// SCROLL
// =================================

function scrollChatToBottom() {

    chatBox.scrollTop =
        chatBox.scrollHeight;
}