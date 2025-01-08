// Initialize markdown parser with GFM (GitHub Flavored Markdown)
marked.setOptions({
    gfm: true,
    breaks: true,
    highlight: function(code, lang) {
        if (Prism.languages[lang]) {
            return Prism.highlight(code, Prism.languages[lang], lang);
        }
        return code;
    }
});

// Get current chat ID from URL or data attribute
const pathParts = window.location.pathname.split('/');
const currentChatId = pathParts[pathParts.length - 2] === 'chat' ? null : pathParts[pathParts.length - 2];

const chatSocket = new WebSocket(
    'ws://' + window.location.host + '/ws/chat/'
);

const messagesDiv = document.getElementById('chat-messages');
const messageInputDom = document.getElementById('chat-message-input');
const submitButton = document.getElementById('chat-message-submit');

let currentRenamingChatId = null;

// Function to safely escape HTML
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Function to render message content with markdown
function renderMessageContent(content, isUser) {
    // Escape HTML in the content first
    const escapedContent = escapeHtml(content);

    // Parse markdown
    const htmlContent = marked(escapedContent);

    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;

    // Create message content element
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = htmlContent;

    // Add message content to message container
    messageDiv.appendChild(contentDiv);

    return messageDiv;
}

// Handle rename button clicks
document.querySelectorAll('.rename-button').forEach(button => {
    button.onclick = function(e) {
        e.preventDefault();
        e.stopPropagation();
        const chatId = this.dataset.chatId;
        const chatTitle = this.closest('.chat-item').querySelector('.chat-title').textContent;
        currentRenamingChatId = chatId;
        document.getElementById('new-chat-title').value = chatTitle;
        document.getElementById('rename-dialog').style.display = 'block';
    };
});

// Handle dialog buttons
document.getElementById('cancel-rename').onclick = function() {
    document.getElementById('rename-dialog').style.display = 'none';
};

document.getElementById('confirm-rename').onclick = function() {
    const newTitle = document.getElementById('new-chat-title').value.trim();
    if (newTitle && currentRenamingChatId) {
        chatSocket.send(JSON.stringify({
            'type': 'rename_chat',
            'chat_id': currentRenamingChatId,
            'new_title': newTitle
        }));
        document.getElementById('rename-dialog').style.display = 'none';
    }
};

chatSocket.onmessage = function(e) {
    // Hide loader and re-enable input
    document.getElementById('chat-loader').style.display = 'none';
    messageInputDom.disabled = false;
    submitButton.disabled = false;

    const data = JSON.parse(e.data);

    if (data.type === 'chat_renamed') {
        // Update the chat title in the UI
        const chatItem = document.querySelector(`.chat-item [data-chat-id="${data.chat_id}"]`).closest('.chat-item');
        if (chatItem) {
            chatItem.querySelector('.chat-title').textContent = data.new_title;
        }
        return;
    }

    // Add user message with markdown support
    if (data.message) {
        messagesDiv.appendChild(renderMessageContent(data.message, true));
    }

    // Add assistant message with markdown support
    if (data.response) {
        messagesDiv.appendChild(renderMessageContent(data.response, false));
    }

    // Scroll to bottom
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
};

chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly');
};

messageInputDom.focus();
messageInputDom.onkeyup = function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        submitButton.click();
        e.preventDefault();
    }
};

submitButton.onclick = function(e) {
    const message = messageInputDom.value.trim();
    if (message) {
        // Show loader
        document.getElementById('chat-loader').style.display = 'flex';
        // Disable input and button while processing
        messageInputDom.disabled = true;
        submitButton.disabled = true;

        // Add user message immediately with markdown support
        messagesDiv.appendChild(renderMessageContent(message, true));
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        chatSocket.send(JSON.stringify({
            'message': message,
            'chat_id': currentChatId
        }));
        messageInputDom.value = '';
    }
};

// Initialize existing messages with markdown support
document.querySelectorAll('.message-content').forEach(content => {
    const isUser = content.closest('.message').classList.contains('user');
    const originalText = content.textContent;
    content.innerHTML = marked(escapeHtml(originalText));
});

// Re-run Prism highlighting on all code blocks
Prism.highlightAll();
