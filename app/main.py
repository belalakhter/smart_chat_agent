import os
from flask import Flask, jsonify
from .slack.client import start_socket_client
from .alert.tracker import get_alert_runner
slack_token = os.environ["SLACK_BOT_TOKEN"]
app_token = os.environ["SLACK_APP_TOKEN"]

def create_flask_app():
    app = Flask(__name__)
    alert_runner = get_alert_runner()
    @app.route("/health", methods=["GET"])
    def health_check():
        active_alerts = alert_runner.get_active_alerts()
        return jsonify({
            "status": "healthy",
            "active_alerts": len(active_alerts),
            "runner_active": True
        })

    return app

if __name__ == "__main__":
    print("Starting Slack Socket Mode client...")
    client_socket = start_socket_client()

    app = create_flask_app()
    port = int(os.getenv("PORT", 3000))

    print(f"Starting Flask server on port {port}...")

    app.run(host="0.0.0.0", port=port)
