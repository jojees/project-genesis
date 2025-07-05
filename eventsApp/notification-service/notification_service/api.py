# # eventsApp/notification-service/notification_service/api.py
# from flask import Flask, jsonify

# app = Flask(__name__)

# @app.route('/healthz', methods=['GET'])
# def health_check():
#     return jsonify({"status": "healthy", "service": "notification-service"}), 200

# # You'll add more API endpoints here later for retrieving alerts
# # @app.route('/alerts', methods=['GET'])
# # def get_alerts():
# #     # This will query PostgreSQL
# #     pass

# # @app.route('/alerts/<alert_id>', methods=['GET'])
# # def get_alert_by_id(alert_id):
# #     # This will query PostgreSQL for a specific alert
# #     pass

# if __name__ == '__main__':
#     # This block is for local development only, not for production K8s deployment
#     app.run(debug=True, host='0.0.0.0', port=5000)
#####################################################################
########       Before adding postgres query api       ###############
#####################################################################
# notification_service/notification_service/api.py

# from flask import Flask, jsonify
from quart import Quart, jsonify, request
# Import the PostgreSQLService, we'll need it to fetch data
from notification_service.postgres_service import PostgreSQLService
from .logger_config import logger

# logger = logging.getLogger(__name__)

# This function will take the Flask app instance and PostgreSQL service instance
# and register all the API routes onto that app.
def register_api_routes(app: Quart, pg_service: PostgreSQLService):
    """
    Registers API routes onto the given Flask application instance.
    Args:
        app (Flask): The Flask application instance.
        pg_service (PostgreSQLService): The initialized PostgreSQLService instance.
    """

    @app.route('/healthz', methods=['GET'])
    def health_check():
        """Simple health check endpoint for the API."""
        return jsonify({"status": "healthy", "service": "notification-service-api"}), 200

    @app.route('/alerts', methods=['GET'])
    async def get_all_alerts():
        """API endpoint to fetch all alerts from PostgreSQL."""
        try:
            if not pg_service:
                logger.error("PostgreSQLService not initialized for API. Cannot fetch alerts.")
                return jsonify({"error": "Service not ready to fetch alerts"}), 503

            # Get 'limit' and 'offset' from query parameters
            # They will be strings, so convert them to int, or default to None
            limit_str = request.args.get('limit')
            offset_str = request.args.get('offset')

            limit = None
            if limit_str:
                try:
                    limit = int(limit_str)
                    if limit <= 0:
                        return jsonify({"error": "Limit must be a positive integer."}), 400
                except ValueError:
                    return jsonify({"error": "Limit must be an integer."}), 400

            offset = None
            if offset_str:
                try:
                    offset = int(offset_str)
                    if offset < 0:
                        return jsonify({"error": "Offset cannot be negative."}), 400
                except ValueError:
                    return jsonify({"error": "Offset must be an integer."}), 400

            # Fetch alerts using the parsed limit and offset
            # The fetch_all_alerts in postgres_service is already updated to handle None
            alerts_data = await pg_service.fetch_all_alerts(limit=limit, offset=offset)
            log_msg = f"Successfully fetched {len(alerts)} alerts via API"
            if limit:
                log_msg += f" (limit={limit})"
            if offset:
                log_msg += f" (offset={offset})"
            pg_service.logger.info(log_msg + ".")

            return jsonify(alerts_data), 200
        except Exception as e:
            logger.error(f"Error fetching alerts via API: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve alerts", "details": str(e)}), 500

    @app.route('/alerts/<alert_id>', methods=['GET'])
    async def get_alert_by_id(alert_id: str):
        """API endpoint to fetch a single alert by ID from PostgreSQL."""
        try:
            if not pg_service:
                logger.error("PostgreSQLService not initialized for API. Cannot fetch specific alert.")
                return jsonify({"error": "Service not ready to fetch specific alert"}), 503

            alert_data = await pg_service.fetch_alert_by_id(alert_id) # This function needs to be added to pg_service
            if alert_data:
                return jsonify(alert_data), 200
            else:
                return jsonify({"message": "Alert not found"}), 404
        except Exception as e:
            logger.error(f"Error fetching alert by ID '{alert_id}' via API: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve alert by ID", "details": str(e)}), 500