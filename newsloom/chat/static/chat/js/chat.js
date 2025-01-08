// Function to decode unicode escape sequences
function decodeUnicode(str) {
    return str.replace(/\\u([0-9a-fA-F]{4})/g, (match, p1) =>
        String.fromCharCode(parseInt(p1, 16))
    );
}

// Function to add click-to-copy functionality to code blocks
function addCodeBlockFeatures(element) {
    element.querySelectorAll('pre code').forEach(block => {
        // Add click-to-copy
        block.style.cursor = 'pointer';
        block.title = 'Click to copy';
        block.onclick = function() {
            navigator.clipboard.writeText(block.textContent).then(() => {
                const originalTitle = block.title;
                block.title = 'Copied!';
                setTimeout(() => {
                    block.title = originalTitle;
                }, 2000);
            });
        };

        // Apply syntax highlighting
        hljs.highlightElement(block);
    });
}

// Parse markdown content safely
function parseMarkdown(content) {
    try {
        // First decode any unicode escape sequences
        const decodedContent = decodeUnicode(content);
        return marked.parse(decodedContent);
    } catch (error) {
        console.error('Error parsing markdown:', error);
        return escapeHtml(content);
    }
}

// Parse existing messages on page load
document.addEventListener('DOMContentLoaded', function() {
    // Parse messages with markdown data attribute
    document.querySelectorAll('.message-content[data-markdown]').forEach(content => {
        const markdown = content.getAttribute('data-markdown');
        if (markdown) {
            try {
                content.innerHTML = parseMarkdown(markdown);
                addCodeBlockFeatures(content);
            } catch (error) {
                console.error('Error processing message:', error);
                content.innerHTML = escapeHtml(markdown);
            }
        }
    });
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

// Safely escape HTML to prevent XSS
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
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

// Create a message element with markdown support
function createMessageElement(content, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (isUser) {
        // For user messages, just escape HTML
        contentDiv.innerHTML = escapeHtml(content);
    } else {
        // For assistant messages, parse markdown and store original content
        contentDiv.setAttribute('data-markdown', content);
        contentDiv.innerHTML = parseMarkdown(content);
        addCodeBlockFeatures(contentDiv);
    }

    messageDiv.appendChild(contentDiv);
    return messageDiv;
}

chatSocket.onmessage = function(e) {
    try {
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

        // Add assistant message with markdown support
        const assistantMessageDiv = createMessageElement(data.response, false);
        messagesDiv.appendChild(assistantMessageDiv);

        // Scroll to bottom
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (error) {
        console.error('Error handling message:', error);
    }
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

        // Add user message
        const userMessageDiv = createMessageElement(message, true);
        messagesDiv.appendChild(userMessageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        chatSocket.send(JSON.stringify({
            'message': message,
            'chat_id': currentChatId
        }));
        messageInputDom.value = '';
    }
};
