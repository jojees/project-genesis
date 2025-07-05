# notification_service/notification_service/postgres_service.py
import psycopg
import psycopg.rows as awaitpsycopg # Alias for convenience with row_factory
import json
import datetime
import asyncio
import logging
import uuid
import ipaddress
from tenacity import AsyncRetrying, stop_after_attempt, wait_fixed, before_log, after_log
from psycopg.errors import OperationalError, UniqueViolation
from psycopg_pool import AsyncConnectionPool

from .config import Config # Assuming your config is a class/object
from .logger_config import logger

class PostgreSQLService:
    def __init__(self, config: Config):
        self.config = config
        self.pool = None
        logger.info("PostgreSQLService initialized.")

    async def initialize_pool(self):
        """
        Initializes and returns a connection pool for PostgreSQL.
        Includes retry logic for robustness during startup/reconnects.
        """
        if self.pool:
            logger.debug("PostgreSQL: Connection pool already initialized.")
            return True

        logger.info(f"PostgreSQL: Attempting to initialize connection pool at {self.config.pg_host}:{self.config.pg_port}...")
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(5),
                wait=wait_fixed(5),
                before=before_log(logger, logging.INFO),
                after=after_log(logger, logging.INFO),
                reraise=True
            ):
                with attempt:
                    self.pool = AsyncConnectionPool(
                        conninfo=f"host={self.config.pg_host} port={self.config.pg_port} dbname={self.config.pg_db} user={self.config.pg_user} password={self.config.pg_password}",
                        min_size=1,
                        max_size=10
                    )
                    await self.pool.open() 

                    logger.info("PostgreSQL: Successfully initialized connection pool.")
                    await self._create_alerts_table()
                    return True
        except OperationalError as e:
            logger.error(f"PostgreSQL: Failed to connect or initialize database (OperationalError): {e}", exc_info=True)
            self.pool = None
            raise
        except Exception as e:
            logger.exception(f"PostgreSQL: An unexpected error occurred during PostgreSQL connection pool initialization: {e}")
            self.pool = None
            raise

    async def _create_alerts_table(self):
        """
        Creates the alerts table and necessary indexes if they don't already exist.
        """
        if not self.pool:
            logger.error("PostgreSQL: Cannot create table, no active connection pool.")
            return False

        async with self.pool.connection() as aconn:
            async with aconn.cursor() as acur:
                try:
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS alerts (
                        alert_id UUID PRIMARY KEY,
                        correlation_id UUID NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        alert_name VARCHAR(255) NOT NULL,
                        alert_type VARCHAR(50) NOT NULL,
                        severity VARCHAR(50) NOT NULL,
                        description TEXT,
                        source_service_name VARCHAR(255),
                        rule_id VARCHAR(255),
                        rule_name VARCHAR(255),
                        actor_type VARCHAR(50),
                        actor_id VARCHAR(255),
                        client_ip INET,
                        resource_type VARCHAR(50),
                        resource_id VARCHAR(255),
                        server_hostname VARCHAR(255),
                        action_observed VARCHAR(255),
                        analysis_rule_details JSONB,
                        triggered_by_details JSONB,
                        impacted_resource_details JSONB,
                        metadata JSONB,
                        raw_event_data JSONB NOT NULL
                    );
                    """
                    await acur.execute(create_table_sql)
                    await aconn.commit()
                    logger.info("PostgreSQL: 'alerts' table ensured to exist.")

                    index_sqls = [
                        "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts (timestamp DESC);",
                        "CREATE INDEX IF NOT EXISTS idx_alerts_alert_type ON alerts (alert_type);",
                        "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);",
                        "CREATE INDEX IF NOT EXISTS idx_alerts_actor_id ON alerts (actor_id);",
                        "CREATE INDEX IF NOT EXISTS idx_alerts_server_hostname ON alerts (server_hostname);",
                        "CREATE INDEX IF NOT EXISTS idx_alerts_rule_name ON alerts (rule_name);",
                        "CREATE INDEX IF NOT EXISTS idx_alerts_metadata_gin ON alerts USING GIN (metadata);",
                        "CREATE INDEX IF NOT EXISTS idx_alerts_raw_event_data_gin ON alerts USING GIN (raw_event_data);"
                    ]
                    for sql in index_sqls:
                        try:
                            await acur.execute(sql)
                            await aconn.commit()
                        except UniqueViolation:
                            logger.warning(f"PostgreSQL: Index already exists (or concurrent creation): {sql}")
                            await aconn.rollback()
                        except OperationalError as e:
                            logger.error(f"PostgreSQL: Operational error during index creation for '{sql}': {e}", exc_info=True)
                            await aconn.rollback()
                        except Exception as e:
                            logger.exception(f"PostgreSQL: An unexpected error during index creation for '{sql}': {e}")
                            await aconn.rollback()
                    logger.info("PostgreSQL: Indexes for 'alerts' table ensured to exist.")
                    return True
                except OperationalError as e:
                    logger.error(f"PostgreSQL: Database operational error creating or ensuring 'alerts' table: {e}", exc_info=True)
                    await aconn.rollback()
                    return False
                except Exception as e:
                    logger.exception(f"PostgreSQL: An unexpected error occurred during table creation: {e}")
                    await aconn.rollback()
                    return False

    async def insert_alert(self, alert_payload: dict) -> bool:
        """
        Inserts a parsed alert payload into the PostgreSQL alerts table.
        """
        if not self.pool:
            logger.error("PostgreSQL: No active connection pool. Cannot insert alert.")
            return False

        try:
            async with self.pool.connection() as aconn:
                async with aconn.cursor() as acur:
                    alert_id = alert_payload.get('alert_id')
                    correlation_id = alert_payload.get('correlation_id')
                    
                    timestamp_str = alert_payload['timestamp']
                    if timestamp_str.endswith(('+00:00Z', '-00:00Z')):
                        timestamp_str = timestamp_str[:-1]
                    
                    timestamp = datetime.datetime.fromisoformat(timestamp_str)
                    alert_name = alert_payload.get('alert_name')
                    alert_type = alert_payload.get('alert_type')
                    severity = alert_payload.get('severity')
                    description = alert_payload.get('description')
                    source_service_name = alert_payload.get('source_service_name')

                    rule_details = alert_payload.get('analysis_rule', {})
                    rule_id = rule_details.get('rule_id')
                    rule_name = rule_details.get('rule_name')

                    triggered_by = alert_payload.get('triggered_by', {})
                    actor_type = triggered_by.get('actor_type')
                    actor_id = triggered_by.get('actor_id')
                    
                    client_ip = triggered_by.get('client_ip')
                    if client_ip in ["N/A", "", None]:
                        client_ip_for_db = None
                    else:
                        client_ip_for_db = client_ip 

                    impacted_resource = alert_payload.get('impacted_resource', {})
                    resource_type = impacted_resource.get('resource_type')
                    resource_id = impacted_resource.get('resource_id')
                    server_hostname = impacted_resource.get('server_hostname')

                    action_observed = alert_payload.get('action_observed')

                    analysis_rule_details_jsonb = rule_details
                    triggered_by_details_jsonb = triggered_by
                    impacted_resource_details_jsonb = impacted_resource
                    metadata_jsonb = alert_payload.get('metadata', {})
                    raw_event_data_jsonb = alert_payload.get('raw_event_data', {})

                    insert_sql = """
                    INSERT INTO alerts (
                        alert_id, correlation_id, timestamp, alert_name, alert_type, severity, description,
                        source_service_name, rule_id, rule_name,
                        actor_type, actor_id, client_ip,
                        resource_type, resource_id, server_hostname, action_observed,
                        analysis_rule_details, triggered_by_details, impacted_resource_details, metadata, raw_event_data
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
                    """
                    await acur.execute(insert_sql, (
                        alert_id, correlation_id, timestamp, alert_name, alert_type, severity, description,
                        source_service_name, rule_id, rule_name,
                        actor_type, actor_id, client_ip_for_db,
                        resource_type, resource_id, server_hostname, action_observed,
                        json.dumps(analysis_rule_details_jsonb),
                        json.dumps(triggered_by_details_jsonb),
                        json.dumps(impacted_resource_details_jsonb),
                        json.dumps(metadata_jsonb),
                        json.dumps(raw_event_data_jsonb)
                    ))
                    await aconn.commit()
                    logger.info(f"PostgreSQL: Successfully inserted alert '{alert_name}' (ID: {alert_id}).")
                    return True
        except UniqueViolation as e:
            logger.warning(f"PostgreSQL: Alert with ID {alert_payload.get('alert_id')} already exists. Re-raising for specific consumer handling. Error: {e}")
            raise e
        except OperationalError as e:
            logger.error(f"PostgreSQL: Database operational error inserting alert {alert_payload.get('alert_id')}: {e}", exc_info=True)
            if self.pool: # Use self.pool here
                await self.pool.close()
            self.pool = None
            return False
        except KeyError as e:
            logger.error(f"PostgreSQL: Missing critical field in alert payload: {e}. Payload: {alert_payload}", exc_info=True)
            return False
        except Exception as e:
            logger.exception(f"PostgreSQL: Unexpected error inserting alert {alert_payload.get('alert_id')}: {e}")
            return False

    async def fetch_all_alerts(self, limit: int = None, offset: int = None):
        """Fetches all alerts from the database."""
        alerts = []
        if not self.pool:
            logger.error("PostgreSQL: No active connection pool. Cannot fetch alerts.")
            return []
        try:
            async with self.pool.connection() as conn: # Use self.pool here
                async with conn.cursor(row_factory=awaitpsycopg.dict_row) as acur: # Use awaitpsycopg.dict_row
                    # Select all columns defined in your table, or specific ones you need for the API
                    # Make sure 'payload' is actually a column in your table.
                    # If raw_event_data is the full payload, use that.
                    # Adjust column names as per your CREATE TABLE statement.
                    await acur.execute("""
                        SELECT 
                            alert_id, correlation_id, timestamp, received_at, alert_name, 
                            alert_type, severity, description, source_service_name, rule_id, 
                            rule_name, actor_type, actor_id, client_ip, resource_type, 
                            resource_id, server_hostname, action_observed, 
                            analysis_rule_details, triggered_by_details, 
                            impacted_resource_details, metadata, raw_event_data 
                        FROM alerts 
                        ORDER BY timestamp DESC
                    """)
                    # Conditionally add LIMIT and OFFSET clauses
                    if limit is not None and limit > 0:
                        sql_query += f" LIMIT {limit}"
                    if offset is not None and offset >= 0:
                        sql_query += f" OFFSET {offset}"

                    rows = await acur.fetchall()
                    for row in rows:
                        # Convert UUIDs, datetimes & IP addresses to string for JSON serialization
                        alert_dict = {k: str(v) if isinstance(v, (uuid.UUID, datetime.datetime, ipaddress.IPv4Address, ipaddress.IPv6Address)) else v for k, v in row.items()}
                        # Ensure JSONB fields are actual dicts (they should be if psycopg is configured)
                        # If they are strings, you might need json.loads(v)
                        alert_dict['analysis_rule_details'] = row['analysis_rule_details']
                        alert_dict['triggered_by_details'] = row['triggered_by_details']
                        alert_dict['impacted_resource_details'] = row['impacted_resource_details']
                        alert_dict['metadata'] = row['metadata']
                        alert_dict['raw_event_data'] = row['raw_event_data']
                        alerts.append(alert_dict)
            logger.info(f"Successfully fetched {len(alerts)} alerts from PostgreSQL.")
            return alerts
        except Exception as e:
            logger.error(f"Error fetching alerts from PostgreSQL: {e}", exc_info=True)
            raise # Re-raise the exception to be handled by the API endpoint


    async def fetch_alert_by_id(self, alert_id: str):
        """Fetches a single alert by its ID from the database."""
        if not self.pool:
            logger.error("PostgreSQL: No active connection pool. Cannot fetch specific alert.")
            return None
        try:
            async with self.pool.connection() as conn: # Use self.pool here
                async with conn.cursor(row_factory=awaitpsycopg.dict_row) as acur: # Use awaitpsycopg.dict_row
                    await acur.execute("""
                        SELECT 
                            alert_id, correlation_id, timestamp, received_at, alert_name, 
                            alert_type, severity, description, source_service_name, rule_id, 
                            rule_name, actor_type, actor_id, client_ip, resource_type, 
                            resource_id, server_hostname, action_observed, 
                            analysis_rule_details, triggered_by_details, 
                            impacted_resource_details, metadata, raw_event_data 
                        FROM alerts 
                        WHERE alert_id = %s
                    """, (alert_id,))
                    row = await acur.fetchone()
                    if row:
                        logger.info(f"Successfully fetched alert with ID: {alert_id} from PostgreSQL.")
                        # Convert UUIDs, datetimes & IP addresses to string for JSON serialization
                        alert_dict = {k: str(v) if isinstance(v, (uuid.UUID, datetime.datetime, ipaddress.IPv4Address, ipaddress.IPv6Address)) else v for k, v in row.items()}
                        alert_dict['analysis_rule_details'] = row['analysis_rule_details']
                        alert_dict['triggered_by_details'] = row['triggered_by_details']
                        alert_dict['impacted_resource_details'] = row['impacted_resource_details']
                        alert_dict['metadata'] = row['metadata']
                        alert_dict['raw_event_data'] = row['raw_event_data']
                        return alert_dict
                    else:
                        logger.info(f"Alert with ID: {alert_id} not found in PostgreSQL.")
                        return None
        except Exception as e:
            logger.error(f"Error fetching alert by ID {alert_id} from PostgreSQL: {e}", exc_info=True)
            raise # Re-raise the exception to be handled by the API endpoint

    async def close_pool(self): # Renamed for consistency with class methods
        if self.pool:
            logger.info("PostgreSQL: Attempting to close connection pool.")
            try:
                await self.pool.close()
                logger.info("PostgreSQL: Connection pool closed successfully.")
            except Exception as e:
                logger.error(f"PostgreSQL: Error closing connection pool: {e}", exc_info=True)
            finally:
                self.pool = None