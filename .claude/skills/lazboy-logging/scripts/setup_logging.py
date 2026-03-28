#!/usr/bin/env python3
"""Generate logging configuration based on detected framework.

Detects the project framework (Python/FastAPI, Node.js/Express, Java/Spring Boot)
and generates appropriate logging configuration files.

Usage:
    python setup_logging.py /path/to/project
    python setup_logging.py . --framework python
    python setup_logging.py /path/to/project --service-name orders-api --log-level INFO
"""

import argparse
import json
import sys
from pathlib import Path
from textwrap import dedent


FRAMEWORKS = ["python", "node", "java"]


def detect_framework(project_dir: Path) -> str | None:
    """Detect the project framework from configuration files."""
    # Python detection
    if (project_dir / "pyproject.toml").exists():
        return "python"
    if (project_dir / "requirements.txt").exists():
        return "python"
    if (project_dir / "setup.py").exists():
        return "python"
    if (project_dir / "Pipfile").exists():
        return "python"

    # Node.js detection
    if (project_dir / "package.json").exists():
        return "node"

    # Java detection
    if (project_dir / "pom.xml").exists():
        return "java"
    if (project_dir / "build.gradle").exists():
        return "java"
    if (project_dir / "build.gradle.kts").exists():
        return "java"

    return None


def detect_python_framework(project_dir: Path) -> str:
    """Detect specific Python web framework."""
    indicators = {
        "fastapi": ["fastapi", "uvicorn"],
        "flask": ["flask"],
        "django": ["django"],
    }

    # Check pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
        for framework, keywords in indicators.items():
            if any(kw in content for kw in keywords):
                return framework

    # Check requirements.txt
    requirements = project_dir / "requirements.txt"
    if requirements.exists():
        content = requirements.read_text(encoding="utf-8", errors="ignore").lower()
        for framework, keywords in indicators.items():
            if any(kw in content for kw in keywords):
                return framework

    return "generic"


def generate_python_logging_yaml(service_name: str, log_level: str) -> str:
    """Generate Python logging.yaml configuration."""
    return dedent(f"""\
        # Logging configuration for {service_name}
        # Usage: load with logging.config.dictConfig(yaml.safe_load(open('logging.yaml')))

        version: 1
        disable_existing_loggers: false

        formatters:
          json:
            class: pythonjsonlogger.jsonlogger.JsonFormatter
            format: "%(asctime)s %(levelname)s %(name)s %(message)s"
            datefmt: "%Y-%m-%dT%H:%M:%S"
            rename_fields:
              asctime: timestamp
              levelname: level
              name: logger
            static_fields:
              service: "{service_name}"
              environment: "%(ENV)s"

          console:
            format: "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
            datefmt: "%Y-%m-%d %H:%M:%S"

        filters:
          correlation_id:
            "()": "{service_name.replace('-', '_')}.logging_filters.CorrelationIdFilter"

        handlers:
          console:
            class: logging.StreamHandler
            level: DEBUG
            formatter: console
            stream: ext://sys.stdout
            filters:
              - correlation_id

          json_console:
            class: logging.StreamHandler
            level: {log_level}
            formatter: json
            stream: ext://sys.stdout
            filters:
              - correlation_id

          file:
            class: logging.handlers.RotatingFileHandler
            level: {log_level}
            formatter: json
            filename: logs/{service_name}.log
            maxBytes: 10485760  # 10MB
            backupCount: 5
            encoding: utf-8
            filters:
              - correlation_id

        loggers:
          "{service_name.replace('-', '_')}":
            level: {log_level}
            handlers:
              - json_console
            propagate: false

          uvicorn:
            level: WARNING
            handlers:
              - json_console
            propagate: false

          sqlalchemy.engine:
            level: WARNING
            handlers:
              - json_console
            propagate: false

          httpx:
            level: WARNING

        root:
          level: {log_level}
          handlers:
            - json_console
    """)


def generate_python_logging_config(service_name: str, log_level: str) -> str:
    """Generate Python logging_config.py module."""
    module_name = service_name.replace("-", "_")
    return dedent(f'''\
        """Logging configuration for {service_name}.

        Call setup_logging() once at application startup before any other imports.

        Usage:
            from {module_name}.logging_config import setup_logging
            setup_logging(service_name="{service_name}", level="{log_level}")
        """

        import logging
        import logging.config
        import os
        import sys
        from contextvars import ContextVar
        from typing import Any

        # Correlation ID stored per-request via contextvars
        correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


        class CorrelationIdFilter(logging.Filter):
            """Inject correlation_id into every log record."""

            def filter(self, record: logging.LogRecord) -> bool:
                record.correlation_id = correlation_id_var.get("")  # type: ignore[attr-defined]
                return True


        class JsonFormatter(logging.Formatter):
            """Format log records as JSON for production log aggregation."""

            def __init__(self, service_name: str = "{service_name}") -> None:
                super().__init__()
                self.service_name = service_name
                self.environment = os.getenv("ENVIRONMENT", "development")

            def format(self, record: logging.LogRecord) -> str:
                import json
                from datetime import datetime, timezone

                log_entry: dict[str, Any] = {{
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "service": self.service_name,
                    "environment": self.environment,
                }}

                # Add correlation ID if present
                correlation_id = getattr(record, "correlation_id", "")
                if correlation_id:
                    log_entry["correlation_id"] = correlation_id

                # Add extra fields
                if hasattr(record, "__dict__"):
                    for key, value in record.__dict__.items():
                        if key not in logging.LogRecord(
                            "", 0, "", 0, "", (), None
                        ).__dict__ and key not in ("correlation_id",):
                            log_entry[key] = value

                # Add exception info
                if record.exc_info and record.exc_info[1]:
                    log_entry["exception"] = {{
                        "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                        "message": str(record.exc_info[1]),
                        "traceback": self.formatException(record.exc_info),
                    }}

                return json.dumps(log_entry, default=str)


        def setup_logging(
            service_name: str = "{service_name}",
            level: str = "{log_level}",
            json_output: bool | None = None,
        ) -> None:
            """Configure logging for the application.

            Args:
                service_name: Name of the service (appears in every log line).
                level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                json_output: Force JSON output. If None, auto-detects (JSON in production).
            """
            if json_output is None:
                json_output = os.getenv("ENVIRONMENT", "development") != "development"

            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

            # Remove existing handlers
            root_logger.handlers.clear()

            handler = logging.StreamHandler(sys.stdout)
            handler.addFilter(CorrelationIdFilter())

            if json_output:
                handler.setFormatter(JsonFormatter(service_name=service_name))
            else:
                handler.setFormatter(logging.Formatter(
                    fmt="%(asctime)s [%(levelname)-8s] %(name)s [%(correlation_id)s]: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    defaults={{"correlation_id": ""}},
                ))

            root_logger.addHandler(handler)

            # Quiet noisy third-party loggers
            for noisy in ("uvicorn.access", "httpx", "httpcore", "sqlalchemy.engine"):
                logging.getLogger(noisy).setLevel(logging.WARNING)

            logging.getLogger(service_name.replace("-", "_")).info(
                "Logging configured",
                extra={{"level": level, "json_output": json_output}},
            )
    ''')


def generate_python_middleware(service_name: str) -> str:
    """Generate FastAPI logging middleware."""
    return dedent(f'''\
        """Request logging middleware for FastAPI.

        Injects correlation ID into every request and logs request/response metadata.

        Usage:
            from {service_name.replace("-", "_")}.logging_middleware import RequestLoggingMiddleware
            app.add_middleware(RequestLoggingMiddleware)
        """

        import logging
        import time
        import uuid

        from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
        from starlette.requests import Request
        from starlette.responses import Response

        from {service_name.replace("-", "_")}.logging_config import correlation_id_var

        logger = logging.getLogger(__name__)


        class RequestLoggingMiddleware(BaseHTTPMiddleware):
            """Log every request with timing and inject correlation ID."""

            async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
                # Extract or generate correlation ID
                correlation_id = (
                    request.headers.get("X-Correlation-ID")
                    or request.headers.get("X-Request-ID")
                    or str(uuid.uuid4())
                )
                correlation_id_var.set(correlation_id)

                start_time = time.perf_counter()

                try:
                    response = await call_next(request)
                except Exception:
                    logger.exception(
                        "Request failed with unhandled exception",
                        extra={{
                            "method": request.method,
                            "path": request.url.path,
                            "correlation_id": correlation_id,
                        }},
                    )
                    raise

                duration_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "Request completed",
                    extra={{
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                        "correlation_id": correlation_id,
                    }},
                )

                response.headers["X-Correlation-ID"] = correlation_id
                response.headers["X-Request-Duration-Ms"] = str(round(duration_ms, 2))

                return response
    ''')


def generate_node_winston_config(service_name: str, log_level: str) -> str:
    """Generate Node.js Winston logging configuration."""
    return dedent(f"""\
        // Logging configuration for {service_name}
        // Usage: const logger = require('./logger');
        //        logger.info('message', {{ key: 'value' }});

        const winston = require('winston');
        const {{ v4: uuidv4 }} = require('uuid');

        const environment = process.env.NODE_ENV || 'development';
        const isProduction = environment === 'production';

        // JSON format for production (log aggregation)
        const jsonFormat = winston.format.combine(
          winston.format.timestamp({{ format: 'YYYY-MM-DDTHH:mm:ss.SSSZ' }}),
          winston.format.errors({{ stack: true }}),
          winston.format.json(),
          winston.format((info) => {{
            info.service = '{service_name}';
            info.environment = environment;
            return info;
          }})()
        );

        // Human-readable format for development
        const devFormat = winston.format.combine(
          winston.format.timestamp({{ format: 'YYYY-MM-DD HH:mm:ss' }}),
          winston.format.errors({{ stack: true }}),
          winston.format.colorize(),
          winston.format.printf(({{ timestamp, level, message, ...meta }}) => {{
            const metaStr = Object.keys(meta).length ? ' ' + JSON.stringify(meta) : '';
            return `${{timestamp}} [${{level}}]: ${{message}}${{metaStr}}`;
          }})
        );

        const logger = winston.createLogger({{
          level: process.env.LOG_LEVEL || '{log_level.lower()}',
          format: isProduction ? jsonFormat : devFormat,
          defaultMeta: {{
            service: '{service_name}',
          }},
          transports: [
            new winston.transports.Console(),
          ],
          // Do not exit on uncaught exceptions
          exitOnError: false,
        }});

        // Express middleware for request logging with correlation ID
        function requestLogger(req, res, next) {{
          const correlationId = req.headers['x-correlation-id']
            || req.headers['x-request-id']
            || uuidv4();

          req.correlationId = correlationId;
          res.setHeader('X-Correlation-ID', correlationId);

          const start = Date.now();

          res.on('finish', () => {{
            const duration = Date.now() - start;
            logger.info('Request completed', {{
              method: req.method,
              path: req.originalUrl,
              statusCode: res.statusCode,
              durationMs: duration,
              correlationId,
            }});
          }});

          next();
        }}

        // Child logger with correlation ID bound
        function createRequestLogger(correlationId) {{
          return logger.child({{ correlationId }});
        }}

        module.exports = {{
          logger,
          requestLogger,
          createRequestLogger,
        }};
    """)


def generate_java_logback_xml(service_name: str, log_level: str) -> str:
    """Generate Java Logback XML configuration."""
    return dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!--
          Logback configuration for {service_name}
          Place in src/main/resources/logback-spring.xml
        -->
        <configuration scan="true" scanPeriod="30 seconds">

            <springProperty scope="context" name="SERVICE_NAME"
                            source="spring.application.name" defaultValue="{service_name}"/>
            <springProperty scope="context" name="ENVIRONMENT"
                            source="spring.profiles.active" defaultValue="default"/>

            <!-- Console appender for development -->
            <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
                <encoder>
                    <pattern>%d{{yyyy-MM-dd HH:mm:ss.SSS}} [%thread] [%X{{requestId:-}}] %-5level %logger{{36}} - %msg%n</pattern>
                </encoder>
            </appender>

            <!-- JSON appender for production (structured logging) -->
            <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
                <encoder class="net.logstash.logback.encoder.LogstashEncoder">
                    <customFields>
                        {{"service":"${{SERVICE_NAME}}","environment":"${{ENVIRONMENT}}"}}
                    </customFields>
                    <fieldNames>
                        <timestamp>timestamp</timestamp>
                        <level>level</level>
                        <logger>logger</logger>
                        <message>message</message>
                        <thread>thread</thread>
                        <stackTrace>stacktrace</stackTrace>
                    </fieldNames>
                    <includeMdcKeyName>requestId</includeMdcKeyName>
                    <includeMdcKeyName>correlationId</includeMdcKeyName>
                    <includeMdcKeyName>userId</includeMdcKeyName>
                </encoder>
            </appender>

            <!-- Rolling file appender -->
            <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
                <file>logs/${{SERVICE_NAME}}.log</file>
                <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
                    <fileNamePattern>logs/${{SERVICE_NAME}}.%d{{yyyy-MM-dd}}.%i.log.gz</fileNamePattern>
                    <maxFileSize>50MB</maxFileSize>
                    <maxHistory>30</maxHistory>
                    <totalSizeCap>1GB</totalSizeCap>
                </rollingPolicy>
                <encoder class="net.logstash.logback.encoder.LogstashEncoder">
                    <customFields>{{"service":"${{SERVICE_NAME}}"}}</customFields>
                </encoder>
            </appender>

            <!-- Quiet noisy loggers -->
            <logger name="org.springframework.web" level="WARN"/>
            <logger name="org.hibernate.SQL" level="WARN"/>
            <logger name="org.hibernate.type.descriptor.sql" level="WARN"/>
            <logger name="org.apache.http" level="WARN"/>
            <logger name="io.netty" level="WARN"/>

            <!-- Application logger -->
            <logger name="com.lazboy" level="{log_level}"/>

            <!-- Profile-specific configuration -->
            <springProfile name="default,dev">
                <root level="{log_level}">
                    <appender-ref ref="CONSOLE"/>
                </root>
            </springProfile>

            <springProfile name="staging,prod">
                <root level="{log_level}">
                    <appender-ref ref="JSON"/>
                    <appender-ref ref="FILE"/>
                </root>
            </springProfile>

        </configuration>
    """)


def write_file(filepath: Path, content: str, dry_run: bool = False) -> None:
    """Write content to file, creating directories as needed."""
    if dry_run:
        print(f"  [DRY RUN] Would write: {filepath}")
        return
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    print(f"  Created: {filepath}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate logging configuration based on detected or specified framework.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project
  %(prog)s . --framework python --service-name orders-api
  %(prog)s /path/to/project --framework node --log-level DEBUG
  %(prog)s . --framework java --dry-run
        """,
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to the project directory",
    )
    parser.add_argument(
        "--framework",
        choices=FRAMEWORKS,
        default=None,
        help="Target framework (auto-detected if not specified)",
    )
    parser.add_argument(
        "--service-name",
        default=None,
        help="Service name for log metadata (default: directory name)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Default log level (default: INFO)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )

    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    framework = args.framework or detect_framework(project_dir)
    if not framework:
        print("Error: Could not detect framework. Use --framework to specify.", file=sys.stderr)
        sys.exit(1)

    service_name = args.service_name or project_dir.name
    log_level = args.log_level

    print(f"Generating logging config for: {service_name}")
    print(f"  Framework: {framework}")
    print(f"  Log level: {log_level}")
    print()

    if framework == "python":
        py_framework = detect_python_framework(project_dir)
        print(f"  Python framework: {py_framework}")

        write_file(
            project_dir / "logging.yaml",
            generate_python_logging_yaml(service_name, log_level),
            dry_run=args.dry_run,
        )

        module_name = service_name.replace("-", "_")
        src_dir = project_dir / "src" / module_name
        if not src_dir.exists():
            src_dir = project_dir / module_name
        if not src_dir.exists():
            src_dir = project_dir

        write_file(
            src_dir / "logging_config.py",
            generate_python_logging_config(service_name, log_level),
            dry_run=args.dry_run,
        )

        if py_framework == "fastapi":
            write_file(
                src_dir / "logging_middleware.py",
                generate_python_middleware(service_name),
                dry_run=args.dry_run,
            )

    elif framework == "node":
        write_file(
            project_dir / "src" / "logger.js",
            generate_node_winston_config(service_name, log_level),
            dry_run=args.dry_run,
        )

    elif framework == "java":
        write_file(
            project_dir / "src" / "main" / "resources" / "logback-spring.xml",
            generate_java_logback_xml(service_name, log_level),
            dry_run=args.dry_run,
        )

    print("\nLogging configuration generated successfully.")
    if framework == "python":
        print(f"\nNext steps:")
        print(f"  1. pip install python-json-logger")
        print(f"  2. Call setup_logging() at application startup")
    elif framework == "node":
        print(f"\nNext steps:")
        print(f"  1. npm install winston uuid")
        print(f"  2. const {{ logger }} = require('./src/logger');")
    elif framework == "java":
        print(f"\nNext steps:")
        print(f"  1. Add logstash-logback-encoder dependency to pom.xml/build.gradle")
        print(f"  2. The logback-spring.xml will be auto-detected by Spring Boot")


if __name__ == "__main__":
    main()
