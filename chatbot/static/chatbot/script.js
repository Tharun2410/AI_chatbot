const messageInput =
    document.getElementById("message");

const sendButton =
    document.getElementById("send-button");

const chatBox =
    document.getElementById("chat-box");

const welcomeScreen =
    document.getElementById("welcome-screen");

const newChatButton =
    document.getElementById("new-chat-button");

const menuButton =
    document.getElementById("menu-button");

const menuDropdown =
    document.getElementById("menu-dropdown");

const clearChatButton =
    document.getElementById("clear-chat");

const focusInputButton =
    document.getElementById("focus-input");

const statusText =
    document.getElementById("connection-status");


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

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);


// =================================
// SUGGESTION CARDS
// =================================

document
    .querySelectorAll(".suggestion-card")
    .forEach(button => {

        button.addEventListener(
            "click",
            function () {

                const prompt =
                    this.dataset.prompt;

                messageInput.value =
                    prompt;

                sendMessage();
            }
        );

    });


// =================================
// RECENT CHAT BUTTONS
// =================================

document
    .querySelectorAll(".history-item")
    .forEach(button => {

        button.addEventListener(
            "click",
            function () {

                const prompt =
                    this.dataset.prompt;

                messageInput.value =
                    prompt;

                messageInput.focus();
            }
        );

    });


// =================================
// NEW CHAT
// =================================

newChatButton.addEventListener(
    "click",
    function () {

        const messages =
            chatBox.querySelectorAll(
                ".message"
            );

        messages.forEach(
            message => message.remove()
        );

        welcomeScreen.style.display =
            "block";

        messageInput.value = "";

        messageInput.focus();

        closeMenu();
    }
);


// =================================
// MENU
// =================================

menuButton.addEventListener(
    "click",
    function (event) {

        event.stopPropagation();

        menuDropdown.classList.toggle(
            "show"
        );
    }
);


document.addEventListener(
    "click",
    function (event) {

        if (
            !menuDropdown.contains(event.target) &&
            event.target !== menuButton
        ) {

            closeMenu();
        }
    }
);


function closeMenu() {

    menuDropdown.classList.remove(
        "show"
    );
}


// =================================
// CLEAR CHAT
// =================================

clearChatButton.addEventListener(
    "click",
    function () {

        const messages =
            chatBox.querySelectorAll(
                ".message"
            );

        messages.forEach(
            message => message.remove()
        );

        welcomeScreen.style.display =
            "block";

        closeMenu();

        messageInput.focus();
    }
);


// =================================
// FOCUS INPUT
// =================================

focusInputButton.addEventListener(
    "click",
    function () {

        messageInput.focus();

        closeMenu();
    }
);


// =================================
// SEND MESSAGE
// =================================

async function sendMessage() {

    const message =
        messageInput.value.trim();

    if (
        !message ||
        sendButton.disabled
    ) {
        return;
    }


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


    // Remove welcome screen
    // after first message.

    if (welcomeScreen) {

        welcomeScreen.style.display =
            "none";
    }


    // Show user message

    addUserMessage(
        message
    );


    messageInput.value = "";

    setLoading(true);


    // Show typing indicator

    const typing =
        addTypingIndicator();


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
                            message:
                                message
                        })
                }
            );


        const responseText =
            await response.text();


        console.log(
            "Chat API status:",
            response.status
        );


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

            removeTypingIndicator(
                typing
            );

            addBotMessage(
                "The server returned an invalid response. Please try again."
            );

            return;
        }


        removeTypingIndicator(
            typing
        );


        if (!response.ok) {

            addBotMessage(
                data.error ||
                "The AI service is temporarily unavailable."
            );

            setConnectionStatus(
                "Busy"
            );

            return;
        }


        if (
            !data.reply ||
            !data.reply.trim()
        ) {

            addBotMessage(
                "The AI returned an empty response. Please try again."
            );

            return;
        }


        setConnectionStatus(
            "Online"
        );


        addBotMessage(
            data.reply
        );

    }


    catch (error) {

        console.error(
            "Chat request failed:",
            error
        );


        removeTypingIndicator(
            typing
        );


        addBotMessage(
            "Unable to connect to the chatbot server. Please check your connection."
        );


        setConnectionStatus(
            "Offline"
        );
    }


    finally {

        setLoading(false);

        messageInput.focus();
    }
}


// =================================
// LOADING STATE
// =================================

function setLoading(isLoading) {

    sendButton.disabled =
        isLoading;

    if (isLoading) {

        sendButton.classList.add(
            "loading"
        );

    } else {

        sendButton.classList.remove(
            "loading"
        );
    }
}


// =================================
// TYPING INDICATOR
// =================================

function addTypingIndicator() {

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "message bot typing-message";


    const box =
        document.createElement(
            "div"
        );

    box.className =
        "typing-box";


    box.innerHTML = `
        <span class="typing-label">
            THARUN AI
        </span>

        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;


    wrapper.appendChild(
        box
    );

    chatBox.appendChild(
        wrapper
    );


    scrollChatToBottom();


    return wrapper;
}


// =================================
// REMOVE TYPING
// =================================

function removeTypingIndicator(
    element
) {

    if (
        element &&
        element.parentNode
    ) {

        element.remove();
    }
}


// =================================
// USER MESSAGE
// =================================

function addUserMessage(
    message
) {

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

function addBotMessage(
    message
) {

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
// CONNECTION STATUS
// =================================

function setConnectionStatus(
    status
) {

    if (statusText) {

        statusText.textContent =
            status;
    }
}


// =================================
// SCROLL
// =================================

function scrollChatToBottom() {

    requestAnimationFrame(
        () => {

            chatBox.scrollTo({
                top:
                    chatBox.scrollHeight,

                behavior:
                    "smooth"
            });

        }
    );
}


// =================================
// INITIAL FOCUS
// =================================

window.addEventListener(
    "load",
    function () {

        messageInput.focus();

    }
);