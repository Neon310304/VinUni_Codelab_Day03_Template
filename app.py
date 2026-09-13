from pathlib import Path
import sys

from flask import Flask, jsonify, render_template, request


ROOT_DIR = Path(__file__).resolve().parent
STARTER_CODE_DIR = ROOT_DIR / "starter-code"
sys.path.insert(0, str(STARTER_CODE_DIR))

from template import ReActAgent  # noqa: E402


app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    user_input = str(payload.get("message", "")).strip()

    if not user_input:
        return jsonify({"error": "Vui lòng nhập câu hỏi."}), 400

    result = ReActAgent(max_iterations=5).run(user_input)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)