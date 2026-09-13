const form = document.querySelector('#chat-form');
const input = document.querySelector('#message-input');
const messages = document.querySelector('#messages');

function addMessage(text, role) {
  const message = document.createElement('div');
  message.className = `message ${role}-message`;
  message.innerHTML = `<span class="avatar">${role === 'user' ? 'YOU' : 'VA'}</span><div class="bubble"></div>`;
  message.querySelector('.bubble').textContent = text;
  messages.appendChild(message);
  messages.scrollTop = messages.scrollHeight;
}

function addTrace(trace) {
  const details = document.createElement('details');
  details.className = 'trace';
  details.innerHTML = '<summary>Hiển thị ReAct trace</summary><pre></pre>';
  details.querySelector('pre').textContent = JSON.stringify(trace, null, 2);
  messages.appendChild(details);
}

async function sendMessage(message) {
  addMessage(message, 'user');
  input.value = '';
  input.disabled = true;
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Không thể kết nối agent.');
    addMessage(data.answer, 'agent');
    addTrace(data.trace);
  } catch (error) {
    addMessage(`Lỗi: ${error.message}`, 'agent');
  } finally {
    input.disabled = false;
    input.focus();
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (message) sendMessage(message);
});

document.querySelectorAll('[data-prompt]').forEach((button) => {
  button.addEventListener('click', () => sendMessage(button.dataset.prompt));
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});