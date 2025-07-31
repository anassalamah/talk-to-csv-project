// All JavaScript from the previous HTML_TEMPLATE goes here
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('query-form');
    const input = document.getElementById('query-input');
    const submitButton = document.getElementById('submit-button');
    const chatHistory = document.getElementById('chat-history');
    const errorDisplay = document.getElementById('error-display');

    let currentAgentMessage = null;

    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = (input.scrollHeight) + 'px';
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!submitButton.disabled) {
                form.requestSubmit();
            }
        }
    });

    const socket = io({ transports: ['websocket', 'polling'] });

    socket.on('connect', () => {
        console.log('✅ Socket.IO connected!');
        errorDisplay.textContent = '';
        submitButton.disabled = false;
        submitButton.textContent = 'أرسل';
    });

    socket.on('connect_error', () => {
        errorDisplay.textContent = 'Connection Failed. Please ensure the server is running.';
        submitButton.disabled = true;
        submitButton.textContent = 'Error';
    });

    function appendMessage(text, sender, isPending = false) {
        const messageEl = document.createElement('div');
        messageEl.classList.add('chat-message', `${sender}-message`);

        if (isPending) {
            messageEl.innerHTML = `
                <div class="agent-status-container" style="display: none;">
                    <details open>
                        <summary>
                            ⚙️ Agent Status
                            <span class="agent-status-summary-text">Initializing...</span>
                        </summary>
                        <div class="agent-status-details"></div>
                    </details>
                </div>
                <div class="assistant-content">
                    <div class="thinking-indicator"><span></span><span></span><span></span></div>
                </div>
            `;
        } else {
            const contentDiv = document.createElement('div');
            contentDiv.textContent = text;
            messageEl.appendChild(contentDiv);
        }
        
        chatHistory.appendChild(messageEl);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return messageEl;
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = input.value.trim();
        if (query && !submitButton.disabled) {
            appendMessage(query, 'user');
            currentAgentMessage = appendMessage('', 'assistant', true);
            
            submitButton.disabled = true;
            submitButton.textContent = '...';
            input.value = '';
            input.style.height = 'auto';

            socket.emit('run_query', { query: query });
        }
    });

    socket.on('stage_update', function(data) {
        if (!currentAgentMessage) return;

        const statusContainer = currentAgentMessage.querySelector('.agent-status-container');
        const summaryText = currentAgentMessage.querySelector('.agent-status-summary-text');
        const detailsContainer = currentAgentMessage.querySelector('.agent-status-details');
        const assistantContent = currentAgentMessage.querySelector('.assistant-content');

        if (statusContainer.style.display === 'none') {
            statusContainer.style.display = 'block';
        }

        let detailContent = '';

        switch(data.stage) {
            case 'router':
                summaryText.textContent = `🔀 Routing... Decision: ${data.decision || 'analysis'}`;
                break;
            case 'planner':
            case 'reflection':
                summaryText.textContent = `📝 Generating Code...`;
                if (data.code) {
                    detailContent = `<strong>Generated Code:</strong><pre><code>${data.code}</code></pre>`;
                    detailsContainer.innerHTML = detailContent;
                }
                break;
            case 'execution':
                summaryText.textContent = `⚙️ Executing... (Attempt ${data.attempt}/${data.max_retries})`;
                if (data.status === 'complete') {
                    detailContent = `<strong>Attempt ${data.attempt} Output:</strong><pre>${data.output}</pre>`;
                } else if (data.status === 'failed') {
                    detailContent = `<div class="error-message"><strong>Attempt ${data.attempt} Failed:</strong></div><pre>${data.output}</pre>`;
                }
                detailsContainer.innerHTML += detailContent;
                break;
            case 'synthesis':
                summaryText.textContent = `💡 Final Answer Synthesized`;
                if (data.status === 'complete' && data.answer) {
                    assistantContent.innerHTML = marked.parse(data.answer);
                }
                break;
        }
    });

    socket.on('query_complete', function(data) {
        submitButton.disabled = false;
        submitButton.textContent = 'أرسل';

        if (currentAgentMessage) {
            const detailsContainer = currentAgentMessage.querySelector('.agent-status-details');
            const detailsElement = currentAgentMessage.querySelector('details');
            
            if(detailsContainer && data.timings) {
                let logText = `\n\n<strong>Performance Log:</strong>\nTotal Time: ${data.timings['Total Time'].toFixed(2)}s`;
                detailsContainer.innerHTML += `<pre>${logText}</pre>`;
            }
            
            if (detailsElement) {
                detailsElement.removeAttribute('open');
            }
        }
        currentAgentMessage = null;
    });

    socket.on('agent_error', function(data) {
        if (currentAgentMessage) {
            const assistantContent = currentAgentMessage.querySelector('.assistant-content');
            assistantContent.innerHTML = `<p class="error-message">An error occurred. Please see details below.</p>`;
            
            const statusContainer = currentAgentMessage.querySelector('.agent-status-container');
            statusContainer.style.display = 'block';
            currentAgentMessage.querySelector('.agent-status-summary-text').textContent = 'Error!';
            currentAgentMessage.querySelector('.agent-status-details').innerHTML = `<div class="error-message">${data.error}</div>`;
        } else {
            errorDisplay.textContent = `Error: ${data.error}`;
        }
        submitButton.disabled = false;
        submitButton.textContent = 'أرسل';
        currentAgentMessage = null;
    });
});