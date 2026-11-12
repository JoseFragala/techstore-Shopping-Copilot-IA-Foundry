const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("chat-messages");
const sendButton = document.getElementById("send-button");

function addMessage(text, role, extraClass = "") {
  const bubble = document.createElement("div");
  bubble.className = `bubble bubble-${role} ${extraClass}`.trim();
  bubble.textContent = text;
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

function setWaitingState(isWaiting) {
  input.disabled = isWaiting;
  sendButton.disabled = isWaiting;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = input.value.trim();
  if (!message) {
    return;
  }

  addMessage(message, "user");
  input.value = "";
  setWaitingState(true);
  const thinkingBubble = addMessage("Thinking...", "agent", "bubble-thinking");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    const data = await response.json();
    thinkingBubble.remove();
    addMessage(data.response || "No response received.", "agent");
  } catch (error) {
    thinkingBubble.remove();
    addMessage("Sorry, the chat request failed.", "agent");
    console.error("Chat request failed:", error);
  } finally {
    setWaitingState(false);
    input.focus();
  }
});
