# eventsApp/notification-service/notification_service/api.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "notification-service"}), 200

# You'll add more API endpoints here later for retrieving alerts
# @app.route('/alerts', methods=['GET'])
# def get_alerts():
#     # This will query PostgreSQL
#     pass

# @app.route('/alerts/<alert_id>', methods=['GET'])
# def get_alert_by_id(alert_id):
#     # This will query PostgreSQL for a specific alert
#     pass

if __name__ == '__main__':
    # This block is for local development only, not for production K8s deployment
    app.run(debug=True, host='0.0.0.0', port=5000)