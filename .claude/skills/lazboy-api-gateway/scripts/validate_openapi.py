#!/usr/bin/env python3
"""Validate an OpenAPI/Swagger specification file.

Checks for: required fields, response schemas, auth definitions, path parameter
consistency, missing descriptions, and common specification issues.

Usage:
    python validate_openapi.py openapi.yaml
    python validate_openapi.py --strict api-spec.json
    python validate_openapi.py --format json openapi.yml

Supports OpenAPI 3.0.x, 3.1.x, and Swagger 2.0 specifications.
Requires: PyYAML (pip install pyyaml)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    severity: Severity
    rule: str
    message: str
    path: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity.value,
            "rule": self.rule,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class ValidationResult:
    file: str
    spec_version: str = ""
    issues: list[Issue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "specVersion": self.spec_version,
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "summary": {
                "errors": sum(1 for i in self.issues if i.severity == Severity.ERROR),
                "warnings": sum(1 for i in self.issues if i.severity == Severity.WARNING),
                "info": sum(1 for i in self.issues if i.severity == Severity.INFO),
            },
        }


def load_spec(filepath: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load an OpenAPI spec from YAML or JSON file."""
    try:
        text = filepath.read_text()
    except OSError as e:
        return None, f"Cannot read file: {e}"

    suffix = filepath.suffix.lower()
    try:
        if suffix == ".json":
            return json.loads(text), None
        else:
            return yaml.safe_load(text), None
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        return None, f"Parse error: {e}"


def detect_version(spec: dict[str, Any]) -> str:
    """Detect the OpenAPI/Swagger version."""
    if "openapi" in spec:
        return spec["openapi"]
    if "swagger" in spec:
        return f"swagger-{spec['swagger']}"
    return "unknown"


def resolve_ref(spec: dict[str, Any], ref: str) -> Any:
    """Resolve a $ref pointer within the spec."""
    if not ref.startswith("#/"):
        return None
    parts = ref[2:].split("/")
    current = spec
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def check_required_fields(spec: dict[str, Any], result: ValidationResult) -> None:
    """Check for required top-level fields."""
    is_swagger = spec.get("swagger") == "2.0"

    if is_swagger:
        required = ["swagger", "info", "paths"]
    else:
        required = ["openapi", "info", "paths"]

    for field_name in required:
        if field_name not in spec:
            result.add(Issue(
                severity=Severity.ERROR,
                rule="required-field",
                message=f"Required top-level field '{field_name}' is missing.",
                path=f"/{field_name}",
            ))

    # Info object
    info = spec.get("info", {})
    if isinstance(info, dict):
        if "title" not in info:
            result.add(Issue(
                severity=Severity.ERROR,
                rule="required-field",
                message="'info.title' is required.",
                path="/info/title",
            ))
        if "version" not in info:
            result.add(Issue(
                severity=Severity.ERROR,
                rule="required-field",
                message="'info.version' is required.",
                path="/info/version",
            ))
        if "description" not in info:
            result.add(Issue(
                severity=Severity.INFO,
                rule="missing-description",
                message="'info.description' is recommended for API documentation.",
                path="/info/description",
            ))
        if "contact" not in info:
            result.add(Issue(
                severity=Severity.INFO,
                rule="missing-contact",
                message="'info.contact' is recommended. Include team email or support URL.",
                path="/info/contact",
            ))


def check_paths(spec: dict[str, Any], result: ValidationResult) -> None:
    """Validate path definitions."""
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        result.add(Issue(
            severity=Severity.ERROR,
            rule="invalid-paths",
            message="'paths' must be an object.",
            path="/paths",
        ))
        return

    http_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}

    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        # Path must start with /
        if not path_str.startswith("/"):
            result.add(Issue(
                severity=Severity.ERROR,
                rule="invalid-path",
                message=f"Path must start with '/'. Found: '{path_str}'.",
                path=f"/paths/{path_str}",
            ))

        # Check path parameters are defined
        path_params = set(re.findall(r"\{(\w+)\}", path_str))

        for method in http_methods:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue

            op_path = f"/paths/{path_str}/{method}"

            # operationId
            if "operationId" not in operation:
                result.add(Issue(
                    severity=Severity.WARNING,
                    rule="missing-operation-id",
                    message=f"Operation {method.upper()} {path_str} has no operationId.",
                    path=op_path,
                ))

            # Description or summary
            if "description" not in operation and "summary" not in operation:
                result.add(Issue(
                    severity=Severity.WARNING,
                    rule="missing-description",
                    message=f"Operation {method.upper()} {path_str} has no description or summary.",
                    path=op_path,
                ))

            # Responses
            check_responses(spec, operation, op_path, method, result)

            # Path parameter consistency
            check_path_parameters(spec, operation, path_str, path_params, op_path, result)

            # Request body for methods that should have one
            if method in ("post", "put", "patch"):
                check_request_body(spec, operation, op_path, method, path_str, result)


def check_responses(
    spec: dict[str, Any],
    operation: dict[str, Any],
    op_path: str,
    method: str,
    result: ValidationResult,
) -> None:
    """Validate response definitions."""
    responses = operation.get("responses")
    if not responses:
        result.add(Issue(
            severity=Severity.ERROR,
            rule="missing-responses",
            message=f"Operation at {op_path} has no 'responses' defined.",
            path=f"{op_path}/responses",
        ))
        return

    if not isinstance(responses, dict):
        return

    # Should have at least one success response
    success_codes = [c for c in responses if str(c).startswith("2")]
    if not success_codes and "default" not in responses:
        result.add(Issue(
            severity=Severity.WARNING,
            rule="missing-success-response",
            message=f"Operation at {op_path} has no 2xx success response.",
            path=f"{op_path}/responses",
        ))

    # Check for error responses
    error_codes = [c for c in responses if str(c).startswith(("4", "5"))]
    if not error_codes and "default" not in responses:
        result.add(Issue(
            severity=Severity.INFO,
            rule="missing-error-response",
            message=f"Operation at {op_path} has no error responses defined.",
            path=f"{op_path}/responses",
        ))

    # Check response schemas
    for status_code, response in responses.items():
        if isinstance(response, dict) and "$ref" in response:
            response = resolve_ref(spec, response["$ref"]) or response

        if not isinstance(response, dict):
            continue

        resp_path = f"{op_path}/responses/{status_code}"

        if "description" not in response:
            result.add(Issue(
                severity=Severity.WARNING,
                rule="missing-response-description",
                message=f"Response {status_code} at {op_path} has no description.",
                path=resp_path,
            ))

        # For OpenAPI 3.x, check content/schema
        content = response.get("content", {})
        if isinstance(content, dict) and str(status_code) != "204":
            for media_type, media_obj in content.items():
                if isinstance(media_obj, dict) and "schema" not in media_obj:
                    result.add(Issue(
                        severity=Severity.WARNING,
                        rule="missing-response-schema",
                        message=f"Response {status_code} ({media_type}) at {op_path} has no schema.",
                        path=f"{resp_path}/content/{media_type}",
                    ))


def check_path_parameters(
    spec: dict[str, Any],
    operation: dict[str, Any],
    path_str: str,
    path_params: set[str],
    op_path: str,
    result: ValidationResult,
) -> None:
    """Check path parameter consistency."""
    params = operation.get("parameters", [])
    if not isinstance(params, list):
        return

    defined_path_params: set[str] = set()
    for param in params:
        if isinstance(param, dict) and "$ref" in param:
            param = resolve_ref(spec, param["$ref"]) or param
        if isinstance(param, dict) and param.get("in") == "path":
            defined_path_params.add(param.get("name", ""))

    # Parameters in URL but not defined
    missing = path_params - defined_path_params
    for param_name in missing:
        result.add(Issue(
            severity=Severity.ERROR,
            rule="undefined-path-parameter",
            message=f"Path parameter '{{{param_name}}}' in '{path_str}' is not defined in parameters.",
            path=f"{op_path}/parameters",
        ))

    # Parameters defined but not in URL
    extra = defined_path_params - path_params
    for param_name in extra:
        result.add(Issue(
            severity=Severity.WARNING,
            rule="unused-path-parameter",
            message=f"Path parameter '{param_name}' is defined but not in the URL path '{path_str}'.",
            path=f"{op_path}/parameters",
        ))

    # Path parameters must be required
    for param in params:
        if isinstance(param, dict) and "$ref" in param:
            param = resolve_ref(spec, param["$ref"]) or param
        if isinstance(param, dict) and param.get("in") == "path" and not param.get("required", False):
            result.add(Issue(
                severity=Severity.ERROR,
                rule="path-param-not-required",
                message=f"Path parameter '{param.get('name')}' must have 'required: true'.",
                path=f"{op_path}/parameters",
            ))


def check_request_body(
    spec: dict[str, Any],
    operation: dict[str, Any],
    op_path: str,
    method: str,
    path_str: str,
    result: ValidationResult,
) -> None:
    """Check request body definitions for write operations."""
    # OpenAPI 3.x
    if "requestBody" in operation:
        req_body = operation["requestBody"]
        if isinstance(req_body, dict) and "$ref" in req_body:
            req_body = resolve_ref(spec, req_body["$ref"]) or req_body

        if isinstance(req_body, dict):
            content = req_body.get("content", {})
            if not content:
                result.add(Issue(
                    severity=Severity.WARNING,
                    rule="empty-request-body",
                    message=f"Request body at {op_path} has no content definition.",
                    path=f"{op_path}/requestBody",
                ))
            elif isinstance(content, dict):
                for media_type, media_obj in content.items():
                    if isinstance(media_obj, dict) and "schema" not in media_obj:
                        result.add(Issue(
                            severity=Severity.WARNING,
                            rule="missing-request-schema",
                            message=f"Request body ({media_type}) at {op_path} has no schema.",
                            path=f"{op_path}/requestBody/content/{media_type}",
                        ))
    else:
        # Check if there's a body parameter (Swagger 2.0 style)
        params = operation.get("parameters", [])
        has_body = any(
            isinstance(p, dict) and p.get("in") == "body"
            for p in (params if isinstance(params, list) else [])
        )
        if not has_body:
            result.add(Issue(
                severity=Severity.INFO,
                rule="missing-request-body",
                message=f"{method.upper()} {path_str} has no request body defined.",
                path=f"{op_path}/requestBody",
            ))


def check_security(spec: dict[str, Any], result: ValidationResult) -> None:
    """Check security definitions."""
    is_swagger = spec.get("swagger") == "2.0"

    if is_swagger:
        security_defs = spec.get("securityDefinitions", {})
        security_key = "securityDefinitions"
    else:
        components = spec.get("components", {})
        security_defs = components.get("securitySchemes", {}) if isinstance(components, dict) else {}
        security_key = "components/securitySchemes"

    # Check if any security is defined
    global_security = spec.get("security", [])
    if not security_defs and not global_security:
        result.add(Issue(
            severity=Severity.WARNING,
            rule="no-security-defined",
            message="No security schemes or global security are defined. "
                    "APIs should have authentication configured.",
            path=f"/{security_key}",
        ))
        return

    # Validate security scheme definitions
    if isinstance(security_defs, dict):
        for scheme_name, scheme in security_defs.items():
            if not isinstance(scheme, dict):
                continue

            scheme_type = scheme.get("type", "")

            if is_swagger:
                valid_types = {"basic", "apiKey", "oauth2"}
            else:
                valid_types = {"apiKey", "http", "oauth2", "openIdConnect"}

            if scheme_type not in valid_types:
                result.add(Issue(
                    severity=Severity.ERROR,
                    rule="invalid-security-type",
                    message=f"Security scheme '{scheme_name}' has invalid type '{scheme_type}'. "
                            f"Valid types: {', '.join(sorted(valid_types))}.",
                    path=f"/{security_key}/{scheme_name}",
                ))

            # API Key must have name and in
            if scheme_type == "apiKey":
                if "name" not in scheme:
                    result.add(Issue(
                        severity=Severity.ERROR,
                        rule="apikey-missing-name",
                        message=f"API key scheme '{scheme_name}' must have 'name' field.",
                        path=f"/{security_key}/{scheme_name}",
                    ))
                if "in" not in scheme:
                    result.add(Issue(
                        severity=Severity.ERROR,
                        rule="apikey-missing-in",
                        message=f"API key scheme '{scheme_name}' must have 'in' field (header, query, or cookie).",
                        path=f"/{security_key}/{scheme_name}",
                    ))

    # Check that referenced security schemes exist
    if isinstance(global_security, list):
        for security_req in global_security:
            if isinstance(security_req, dict):
                for scheme_name in security_req:
                    if scheme_name not in security_defs:
                        result.add(Issue(
                            severity=Severity.ERROR,
                            rule="undefined-security-scheme",
                            message=f"Global security references undefined scheme '{scheme_name}'.",
                            path="/security",
                        ))


def check_servers(spec: dict[str, Any], result: ValidationResult) -> None:
    """Check server definitions (OpenAPI 3.x only)."""
    if spec.get("swagger"):
        return  # Swagger 2.0 uses host/basePath

    servers = spec.get("servers", [])
    if not servers:
        result.add(Issue(
            severity=Severity.INFO,
            rule="no-servers",
            message="No 'servers' defined. Clients will default to the spec-hosting server.",
            path="/servers",
        ))
        return

    if isinstance(servers, list):
        for i, server in enumerate(servers):
            if isinstance(server, dict):
                url = server.get("url", "")
                if url and url.startswith("http://") and "localhost" not in url:
                    result.add(Issue(
                        severity=Severity.WARNING,
                        rule="insecure-server-url",
                        message=f"Server URL '{url}' uses HTTP. Use HTTPS for production APIs.",
                        path=f"/servers/{i}",
                    ))


def check_component_schemas(spec: dict[str, Any], result: ValidationResult) -> None:
    """Check component/definition schemas for common issues."""
    if spec.get("swagger"):
        schemas = spec.get("definitions", {})
        schema_path = "/definitions"
    else:
        schemas = spec.get("components", {}).get("schemas", {})
        schema_path = "/components/schemas"

    if not isinstance(schemas, dict):
        return

    for schema_name, schema in schemas.items():
        if not isinstance(schema, dict):
            continue

        path = f"{schema_path}/{schema_name}"

        # Schema should have a type or be a composition ($ref, allOf, oneOf, anyOf)
        composition_keys = {"$ref", "allOf", "oneOf", "anyOf"}
        if "type" not in schema and not (composition_keys & set(schema.keys())):
            result.add(Issue(
                severity=Severity.WARNING,
                rule="missing-schema-type",
                message=f"Schema '{schema_name}' has no 'type' or composition keyword.",
                path=path,
            ))

        # Object schemas should list required properties
        if schema.get("type") == "object" and "properties" in schema:
            if "required" not in schema:
                result.add(Issue(
                    severity=Severity.INFO,
                    rule="missing-required-properties",
                    message=f"Schema '{schema_name}' is an object with properties but no 'required' list.",
                    path=path,
                ))

            # Check for property descriptions
            properties = schema.get("properties", {})
            if isinstance(properties, dict):
                undocumented = [
                    name for name, prop in properties.items()
                    if isinstance(prop, dict) and "description" not in prop and "$ref" not in prop
                ]
                if len(undocumented) > 3:
                    result.add(Issue(
                        severity=Severity.INFO,
                        rule="undocumented-properties",
                        message=f"Schema '{schema_name}' has {len(undocumented)} properties without descriptions.",
                        path=path,
                    ))


def validate_spec(filepath: Path, strict: bool = False) -> ValidationResult:
    """Run all validations on an OpenAPI spec file."""
    result = ValidationResult(file=str(filepath))

    spec, error = load_spec(filepath)
    if error:
        result.add(Issue(severity=Severity.ERROR, rule="parse-error", message=error))
        return result

    if not isinstance(spec, dict):
        result.add(Issue(
            severity=Severity.ERROR,
            rule="invalid-spec",
            message="Spec file must contain a YAML/JSON object at the top level.",
        ))
        return result

    result.spec_version = detect_version(spec)

    if result.spec_version == "unknown":
        result.add(Issue(
            severity=Severity.ERROR,
            rule="unknown-version",
            message="Cannot determine spec version. Must have 'openapi' (3.x) or 'swagger' (2.0) field.",
        ))
        return result

    # Run all checks
    check_required_fields(spec, result)
    check_paths(spec, result)
    check_security(spec, result)
    check_servers(spec, result)
    check_component_schemas(spec, result)

    # Strict mode: warnings become errors
    if strict:
        for issue in result.issues:
            if issue.severity == Severity.WARNING:
                issue.severity = Severity.ERROR

    return result


def format_text(results: list[ValidationResult]) -> str:
    """Format results as human-readable text."""
    lines: list[str] = []

    for res in results:
        lines.append(f"\n{'=' * 60}")
        lines.append(f"File: {res.file}")
        lines.append(f"Spec Version: {res.spec_version or 'N/A'}")
        lines.append(f"Valid: {'Yes' if res.valid else 'No'}")
        lines.append(f"{'=' * 60}")

        if not res.issues:
            lines.append("  No issues found.")
            continue

        for issue in res.issues:
            icon = {
                "error": "[ERROR]",
                "warning": "[WARN] ",
                "info": "[INFO] ",
            }[issue.severity.value]
            loc = f" @ {issue.path}" if issue.path else ""
            lines.append(f"  {icon} [{issue.rule}]{loc}")
            lines.append(f"         {issue.message}")

    total_errors = sum(1 for r in results for i in r.issues if i.severity == Severity.ERROR)
    total_warnings = sum(1 for r in results for i in r.issues if i.severity == Severity.WARNING)
    lines.append(f"\n{'=' * 60}")
    lines.append(f"Total: {total_errors} error(s), {total_warnings} warning(s) across {len(results)} file(s)")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate OpenAPI/Swagger specification files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supports: OpenAPI 3.0.x, 3.1.x, Swagger 2.0

Rules checked:
  required-field             Missing required top-level or info fields
  invalid-path               Path not starting with /
  missing-operation-id       Operation without operationId
  missing-description        Missing description/summary on operations or info
  missing-responses          Operation without responses
  missing-success-response   No 2xx response defined
  missing-response-schema    Response without schema
  undefined-path-parameter   Path parameter in URL not defined in parameters
  unused-path-parameter      Parameter defined but not in URL
  path-param-not-required    Path parameter without required: true
  no-security-defined        No security schemes configured
  invalid-security-type      Invalid security scheme type
  insecure-server-url        Non-HTTPS server URL
  missing-schema-type        Schema without type or composition
        """,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="OpenAPI spec file(s) to validate (YAML or JSON)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    results = []
    for filepath in args.files:
        result = validate_spec(filepath.resolve(), strict=args.strict)
        results.append(result)

    if args.format == "json":
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print(format_text(results))

    has_errors = any(not r.valid for r in results)
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
