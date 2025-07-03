# test_db_connection.py
import asyncio
import logging
from psycopg_pool import AsyncConnectionPool
from psycopg.errors import OperationalError

# --- Configure Basic Logging for this test script ---
# This logger is just for this test script, separate from your service's logger_config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- IMPORTANT: Replace these with YOUR actual PostgreSQL credentials ---
# These should match what you successfully used in your UI app and in notification_service/config.py
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"  # e.g., "events_db"
DB_USER = "postgres"       # e.g., "admin"
DB_PASSWORD = "jdevlab_db_postgres"   # e.g., "password"
# ---------------------------------------------------------------------

async def test_db_connection():
    """
    Attempts to connect to PostgreSQL using AsyncConnectionPool,
    executes a simple query, and closes the pool.
    """
    logger.info("Starting database connection test...")
    pool = None # Initialize pool to None
    try:
        # Create the connection pool (no 'await' here)
        pool = AsyncConnectionPool(
            conninfo=f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}",
            min_size=1,
            max_size=1
        )
        
        # Await the .wait() method to establish initial connections
        await pool.wait()
        logger.info("Successfully created and waited for AsyncConnectionPool.")

        # Try to get a connection from the pool and execute a simple query
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 as test_result;")
                result = await cur.fetchone()
                logger.info(f"Successfully executed test query. Result: {result}")
        
        logger.info("Connection test successful!")

    except OperationalError as e:
        logger.error(f"PostgreSQL Operational Error: {e}", exc_info=True)
        logger.error("Connection test FAILED due to operational error. Check DB server, port-forward, and credentials.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during the database connection test: {e}")
        logger.error("Connection test FAILED due to an unexpected error.")
    finally:
        if pool:
            logger.info("Closing the connection pool...")
            await pool.close()
            logger.info("Connection pool closed.")

if __name__ == "__main__":
    # Ensure kubectl port-forward service/postgres-service 5432:5432 is running in another terminal
    logger.info("Make sure 'kubectl port-forward service/postgres-service 5432:5432' is running in another terminal.")
    asyncio.run(test_db_connection())
    logger.info("Test script finished.")