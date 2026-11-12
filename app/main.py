import logging
import os
import threading
import time
from collections import defaultdict, deque

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request


load_dotenv()

# Keep the existing environment variable contract exactly as-is.
PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
AGENT_NAME = os.environ["AGENT_NAME"]

# Flask serves the HTML page and static assets from app/templates and app/static.
app = Flask(__name__)

# Simple console logging so server-side exceptions are visible for debugging.
logging.basicConfig(level=logging.INFO)

# This educational prototype keeps one Foundry conversation alive for the life
# of the process so we can demonstrate shared conversation context simply.
_foundry_lock = threading.Lock()
_foundry_openai_client = None
_foundry_conversation_id = None

# Very small in-memory rate limiter: 10 requests per minute per client IP.
_rate_limit_window_seconds = 60
_rate_limit_max_requests = 10
_requests_by_ip = defaultdict(deque)

# Lightweight topic guard for obvious out-of-scope requests.
ALLOWED_SUPPORT_KEYWORDS = (
    "techstore",
    "product",
    "products",
    "price",
    "prices",
    "cost",
    "stock",
    "inventory",
    "order",
    "orders",
    "shipping",
    "delivery",
    "return",
    "returns",
    "refund",
    "refunds",
    "warranty",
    "warranties",
    "payment",
    "payments",
    "policy",
    "policies",
    "store",
    "purchase",
    "purchased",
    "checkout",
    "invoice",
)

OUT_OF_SCOPE_MESSAGE = (
    "I can only help with TechStore products, orders, shipping, returns, "
    "warranties, payments, and other e-commerce support topics."
)

GENERIC_ERROR_MESSAGE = (
    "Sorry, something went wrong while contacting TechStore AI Support."
)


def initialize_foundry():
    """Create the Azure client and one reusable Foundry conversation."""
    global _foundry_openai_client, _foundry_conversation_id

    with _foundry_lock:
        if _foundry_openai_client and _foundry_conversation_id:
            return

        # Flask -> Azure SDK starts here:
        # 1. DefaultAzureCredential resolves the local Azure identity.
        # 2. AIProjectClient connects to the existing Foundry project endpoint.
        # 3. get_openai_client(agent_name=...) binds to the existing agent.
        credential = DefaultAzureCredential()
        project = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=credential,
        )
        _foundry_openai_client = project.get_openai_client(
            agent_name=AGENT_NAME
        )

        # SDK -> Foundry Agent conversation creation happens here once.
        conversation = _foundry_openai_client.conversations.create()
        _foundry_conversation_id = conversation.id
        app.logger.info(
            "Initialized Foundry conversation: %s", _foundry_conversation_id
        )


def is_valid_message(message):
    """Validate shape and size before any Azure call is attempted."""
    if not isinstance(message, str):
        return False

    if not message.strip():
        return False

    if len(message) > 500:
        return False

    return True


def is_in_scope(message):
    """Allow only simple e-commerce support topics using keyword checks."""
    normalized = message.lower()
    return any(keyword in normalized for keyword in ALLOWED_SUPPORT_KEYWORDS)


def is_rate_limited(client_ip):
    """Track request timestamps in memory for a simple per-IP limit."""
    now = time.time()
    timestamps = _requests_by_ip[client_ip]

    while timestamps and now - timestamps[0] > _rate_limit_window_seconds:
        timestamps.popleft()

    if len(timestamps) >= _rate_limit_max_requests:
        return True

    timestamps.append(now)
    return False


def send_message_to_foundry(message):
    """Send one user message into the existing conversation and return text."""
    initialize_foundry()

    with _foundry_lock:
        # Flask -> Azure SDK:
        # The backend passes the user's text to the Azure SDK only after local
        # validation, scope checks, and rate-limit checks succeed.
        #
        # Azure SDK -> Foundry Agent:
        # responses.create(...) sends the message into the named agent while
        # attaching it to the one reusable conversation ID created at startup.
        response = _foundry_openai_client.responses.create(
            conversation=_foundry_conversation_id,
            input=message,
        )
        return response.output_text


@app.route("/")
def index():
    """Serve the single-page chat interface."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Accept browser messages and return the agent response as JSON."""
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    client_ip = client_ip.split(",")[0].strip() or "unknown"

    if is_rate_limited(client_ip):
        return jsonify({"response": "Too many requests. Please wait a minute."}), 429

    data = request.get_json(silent=True) or {}
    message = data.get("message")

    if not is_valid_message(message):
        return (
            jsonify(
                {
                    "response": (
                        "Message must be a non-empty string up to 500 characters."
                    )
                }
            ),
            400,
        )

    if not is_in_scope(message):
        return jsonify({"response": OUT_OF_SCOPE_MESSAGE}), 400

    try:
        agent_response = send_message_to_foundry(message.strip())
        return jsonify({"response": agent_response})
    except Exception:
        # Log real server details privately. Never expose credentials, stack
        # traces, endpoints, or internal settings to the browser response.
        app.logger.exception("Foundry request failed")
        return jsonify({"response": GENERIC_ERROR_MESSAGE}), 500


# Create the shared Foundry conversation when the application starts.
initialize_foundry()


if __name__ == "__main__":
    app.run(debug=True)
