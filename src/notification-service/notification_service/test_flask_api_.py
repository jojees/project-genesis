import asyncio
import logging
import uvicorn
from flask import Flask, jsonify

# Configure a basic logger for this test file
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
temp_logger = logging.getLogger("TempApiTest")

app = Flask(__name__)

@app.route("/test_healthz")
def test_healthz():
    return jsonify({"status": "healthy", "message": "Test API is up!"})

async def run_test_api():
    temp_logger.info("Starting test API server on 0.0.0.0:8000...")
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug", # Set to debug for verbose output
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except Exception as e:
        temp_logger.error(f"Test API server crashed: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(run_test_api())
    except KeyboardInterrupt:
        temp_logger.info("Test API server stopped by user.")
    except Exception as e:
        temp_logger.exception(f"Test API server encountered an unexpected error: {e}")