// Configure marked options
marked.setOptions({
    breaks: true, // Enable line breaks
    gfm: true,    // Enable GitHub Flavored Markdown
    sanitize: true // Sanitize HTML input
});

// Get current chat ID from URL or data attribute
const pathParts = window.location.pathname.split('/');
const currentChatId = pathParts[pathParts.length - 2] === 'chat' ? null : pathParts[pathParts.length - 2];

let chatSocket = null;
let reconnectAttempts = 0;
let isConnected = false;
let isProcessing = false;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000; // 3 seconds

const messagesDiv = document.getElementById('chat-messages');
const messageInputDom = document.getElementById('chat-message-input');
const submitButton = document.getElementById('chat-message-submit');
const stopButton = document.getElementById('stop-processing');
const processingStatus = document.getElementById('processing-status');
const statusMessage = document.querySelector('.status-message');

let currentRenamingChatId = null;

// Create status indicator
const statusIndicator = document.createElement('div');
statusIndicator.className = 'connection-status';
statusIndicator.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 14px;
    z-index: 1000;
    transition: all 0.3s ease;
    display: none;
`;
document.body.appendChild(statusIndicator);

function showStatus(message, type) {
    statusIndicator.textContent = message;
    statusIndicator.style.display = 'block';

    switch (type) {
        case 'error':
            statusIndicator.style.backgroundColor = '#dc3545';
            statusIndicator.style.color = 'white';
            break;
        case 'warning':
            statusIndicator.style.backgroundColor = '#ffc107';
            statusIndicator.style.color = 'black';
            break;
        case 'success':
            statusIndicator.style.backgroundColor = '#28a745';
            statusIndicator.style.color = 'white';
            setTimeout(() => {
                statusIndicator.style.display = 'none';
            }, 3000);
            break;
    }
}

function connectWebSocket() {
    // Use wss:// for HTTPS connections, ws:// for HTTP
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/`;
    console.log('Connecting to WebSocket:', wsUrl);

    if (chatSocket && chatSocket.readyState !== WebSocket.CLOSED) {
        console.log('Closing existing connection before reconnecting');
        chatSocket.close();
    }

    chatSocket = new WebSocket(wsUrl);

    chatSocket.onopen = function () {
        console.log('WebSocket connection established successfully');
        isConnected = true;
        reconnectAttempts = 0;
        showStatus('Connected', 'success');
        messageInputDom.disabled = false;
        submitButton.disabled = false;
    };

    chatSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);

        // Handle heartbeat
        if (data.type === 'heartbeat') {
            chatSocket.send(JSON.stringify({
                'type': 'heartbeat_response'
            }));
            return;
        }

        // Handle status updates
        if (data.type === 'status') {
            statusMessage.textContent = data.message;
            return;
        }

        // Handle process completion or error
        if (data.type === 'process_complete' || data.error) {
            isProcessing = false;
            processingStatus.style.display = 'none';
            messageInputDom.disabled = false;
            submitButton.disabled = false;
        }

        if (data.error) {
            showStatus(data.error, 'error');
            return;
        }

        if (data.type === 'chat_renamed') {
            // Update the chat title in the UI
            const chatItem = document.querySelector(`.chat-item [data-chat-id="${data.chat_id}"]`).closest('.chat-item');
            if (chatItem) {
                chatItem.querySelector('.chat-title').textContent = data.new_title;
            }
            showStatus('Chat renamed successfully', 'success');
            return;
        }

        if (data.type === 'chat_message') {
            // Add assistant message with markdown rendering
            const assistantMessageDiv = document.createElement('div');
            assistantMessageDiv.className = 'message assistant';
            assistantMessageDiv.innerHTML = `<div class="message-content">${marked.parse(data.response)}</div>`;
            messagesDiv.appendChild(assistantMessageDiv);

            // Scroll to bottom
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    };

    chatSocket.onclose = function (e) {
        console.log('WebSocket closed with code:', e.code, 'reason:', e.reason);
        isConnected = false;
        isProcessing = false;
        messageInputDom.disabled = true;
        submitButton.disabled = true;
        processingStatus.style.display = 'none';

        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            showStatus('Connection lost. Reconnecting...', 'warning');
            setTimeout(() => {
                reconnectAttempts++;
                connectWebSocket();
            }, RECONNECT_DELAY);
        } else {
            showStatus('Connection failed. Please refresh the page.', 'error');
        }
    };

    chatSocket.onerror = function (e) {
        console.error('WebSocket error occurred:', e);
        // Only attempt reconnect if we're not already trying
        if (!isConnected && reconnectAttempts === 0) {
            showStatus('Connection error. Attempting to reconnect...', 'warning');
            setTimeout(() => {
                reconnectAttempts++;
                connectWebSocket();
            }, RECONNECT_DELAY);
        }
        showStatus('Connection error', 'error');
    };
}

// Handle stop button click
stopButton.onclick = function () {
    if (isProcessing && isConnected) {
        chatSocket.send(JSON.stringify({
            'type': 'stop_processing'
        }));
    }
};

// Handle rename button clicks
document.querySelectorAll('.rename-button').forEach(button => {
    button.onclick = function (e) {
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
document.getElementById('cancel-rename').onclick = function () {
    document.getElementById('rename-dialog').style.display = 'none';
};

document.getElementById('confirm-rename').onclick = function () {
    const newTitle = document.getElementById('new-chat-title').value.trim();
    if (newTitle && currentRenamingChatId && isConnected) {
        chatSocket.send(JSON.stringify({
            'type': 'rename_chat',
            'chat_id': currentRenamingChatId,
            'new_title': newTitle
        }));
        document.getElementById('rename-dialog').style.display = 'none';
    } else if (!isConnected) {
        showStatus('Not connected. Please wait...', 'warning');
    }
};

// Initialize WebSocket connection
connectWebSocket();

messageInputDom.focus();
messageInputDom.onkeyup = function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        submitButton.click();
        e.preventDefault();
    }
};

submitButton.onclick = function (e) {
    const message = messageInputDom.value.trim();
    if (message && isConnected) {
        // Show processing status
        isProcessing = true;
        processingStatus.style.display = 'flex';
        statusMessage.textContent = 'Processing your request...';

        // Add user message immediately with markdown rendering
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user';
        userMessageDiv.innerHTML = `<div class="message-content">${marked.parse(message)}</div>`;
        messagesDiv.appendChild(userMessageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        try {
            chatSocket.send(JSON.stringify({
                'message': message,
                'chat_id': currentChatId
            }));
            messageInputDom.value = '';
        } catch (error) {
            isProcessing = false;
            showStatus('Failed to send message. Please try again.', 'error');
            processingStatus.style.display = 'none';
            messageInputDom.disabled = false;
            submitButton.disabled = false;
        }
    } else if (!isConnected) {
        showStatus('Not connected. Please wait...', 'warning');
    }
};

// Initialize markdown rendering for existing messages
document.querySelectorAll('.message-content').forEach(content => {
    const text = content.textContent;
    content.innerHTML = marked.parse(text);
});

// Load chat history from localStorage on page load only if there are no messages
window.onload = function () {
    if (currentChatId && messagesDiv.children.length === 0) {
        const savedMessages = localStorage.getItem(`chat_${currentChatId}`);
        if (savedMessages) {
            const messages = JSON.parse(savedMessages);
            messages.forEach(msg => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${msg.type}`;
                messageDiv.innerHTML = `<div class="message-content">${marked.parse(msg.content)}</div>`;
                messagesDiv.appendChild(messageDiv);
            });
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    }
};

// Save messages to localStorage when new messages are added
const observer = new MutationObserver(function (mutations) {
    if (currentChatId) {
        const messages = [];
        document.querySelectorAll('.message').forEach(msg => {
            messages.push({
                type: msg.classList.contains('user') ? 'user' : 'assistant',
                content: msg.querySelector('.message-content').textContent
            });
        });
        localStorage.setItem(`chat_${currentChatId}`, JSON.stringify(messages));
    }
});

observer.observe(messagesDiv, { childList: true, subtree: true });
