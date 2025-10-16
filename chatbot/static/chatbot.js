// Cybersecurity Chatbot with Gemini API Integration
class SecurityChatbot {
    constructor() {
        this.messageContainer = document.getElementById('chatbot-messages');
        this.inputField = document.getElementById('chatbot-input-field');
        this.sendButton = document.getElementById('chatbot-send-button');
        this.toggleButton = document.getElementById('chatbot-toggle');
        this.resetButton = document.getElementById('chatbot-reset');
        this.chatContainer = document.getElementById('chatbot-container');
        
        this.initEventListeners();
    }

    initEventListeners() {
        // Send message on button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter key
        this.inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Toggle chatbot visibility
        this.toggleButton.addEventListener('click', () => {
            this.chatContainer.classList.toggle('collapsed');
            // Change icon based on state
            const icon = this.toggleButton.querySelector('i');
            if (this.chatContainer.classList.contains('collapsed')) {
                icon.className = 'fas fa-comment';
            } else {
                icon.className = 'fas fa-times';
                this.inputField.focus();
            }
        });
        
        // Reset conversation
        this.resetButton.addEventListener('click', () => this.resetConversation());
    }

    sendMessage() {
        const message = this.inputField.value.trim();
        if (message === '') return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        this.inputField.value = '';
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Send message to backend
        fetch('/chatbot/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Add bot response to chat
            if (data.response) {
                this.addMessage(data.response, 'bot');
            } else if (data.error) {
                this.addMessage(`Error: ${data.error}`, 'bot');
            }
        })
        .catch(error => {
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Show error message
            this.addMessage('Sorry, there was an error communicating with the chatbot. Please try again later.', 'bot');
            console.error('Error:', error);
        });
    }

    addMessage(text, sender) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        
        // Process markdown-like formatting for bot messages
        if (sender === 'bot') {
            // Convert markdown-style code blocks
            text = text.replace(/```(\w+)?\n([\s\S]*?)\n```/g, '<pre><code>$2</code></pre>');
            
            // Convert markdown-style inline code
            text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
            
            // Convert markdown-style bold
            text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            
            // Convert markdown-style italic
            text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
            
            // Convert markdown-style links
            text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
            
            // Convert line breaks to <br>
            text = text.replace(/\n/g, '<br>');
        } else {
            // For user messages, just handle line breaks
            text = text.replace(/\n/g, '<br>');
        }
        
        messageElement.innerHTML = text;
        this.messageContainer.appendChild(messageElement);
        
        // Scroll to bottom
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }

    showTypingIndicator() {
        const typingIndicator = document.createElement('div');
        typingIndicator.classList.add('typing-indicator');
        typingIndicator.id = 'typing-indicator';
        typingIndicator.innerHTML = '<span></span><span></span><span></span>';
        this.messageContainer.appendChild(typingIndicator);
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    resetConversation() {
        // Clear UI
        this.messageContainer.innerHTML = '';
        
        // Add welcome message
        this.addMessage('Hello! I\'m your cybersecurity assistant. How can I help you today?', 'bot');
        
        // Reset conversation on server
        fetch('/chatbot/reset', {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error resetting conversation:', data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Create chatbot HTML structure
    const chatbotHTML = `
        <div id="chatbot-toggle" class="chatbot-toggle">
            <i class="fas fa-comment"></i>
        </div>
        <div id="chatbot-container" class="chatbot-container collapsed">
            <div class="chatbot-header">
                <h3 class="chatbot-title">Cybersecurity Assistant</h3>
                <div class="chatbot-controls">
                    <button id="chatbot-reset" class="chatbot-control-btn">
                        <i class="fas fa-redo"></i>
                    </button>
                </div>
            </div>
            <div id="chatbot-messages" class="chatbot-messages"></div>
            <div class="chatbot-input">
                <input type="text" id="chatbot-input-field" placeholder="Ask a cybersecurity question...">
                <button id="chatbot-send-button">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        </div>
    `;
    
    // Create container for chatbot
    const chatbotContainer = document.createElement('div');
    chatbotContainer.innerHTML = chatbotHTML;
    document.body.appendChild(chatbotContainer);
    
    // Initialize chatbot
    const chatbot = new SecurityChatbot();
    
    // Add welcome message
    chatbot.addMessage('Hello! I\'m your cybersecurity assistant. How can I help you today?', 'bot');
});