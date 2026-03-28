#!/usr/bin/env python3
"""
Generate Express middleware boilerplate files.

Generates ready-to-use middleware for common concerns: authentication,
input validation, error handling, rate limiting, and request logging.

Usage:
    python generate_middleware.py --output ./src/middleware
    python generate_middleware.py --output ./src/middleware --types auth validation error-handler
    python generate_middleware.py --output ./src/middleware --lang js
"""

import argparse
import os
import sys
from pathlib import Path
from textwrap import dedent

AVAILABLE_MIDDLEWARE = [
    "auth",
    "validation",
    "error-handler",
    "rate-limiter",
    "logger",
]


def generate_auth_ts() -> str:
    return dedent("""\
        import { Request, Response, NextFunction } from 'express';
        import jwt from 'jsonwebtoken';

        const JWT_SECRET = process.env.JWT_SECRET;

        if (!JWT_SECRET) {
          throw new Error('JWT_SECRET environment variable is required');
        }

        export interface AuthenticatedRequest extends Request {
          user: {
            id: string;
            email: string;
            role: string;
          };
        }

        /**
         * Verify JWT token from the Authorization header.
         * Attaches decoded user payload to req.user.
         */
        export function authenticate(
          req: Request,
          res: Response,
          next: NextFunction,
        ): void {
          const authHeader = req.headers.authorization;

          if (!authHeader?.startsWith('Bearer ')) {
            res.status(401).json({
              success: false,
              error: 'Authentication required',
              code: 'MISSING_TOKEN',
            });
            return;
          }

          const token = authHeader.slice(7);

          try {
            const decoded = jwt.verify(token, JWT_SECRET!) as AuthenticatedRequest['user'];
            (req as AuthenticatedRequest).user = decoded;
            next();
          } catch (error) {
            const message =
              error instanceof jwt.TokenExpiredError
                ? 'Token has expired'
                : 'Invalid token';

            res.status(401).json({
              success: false,
              error: message,
              code: 'INVALID_TOKEN',
            });
          }
        }

        /**
         * Role-based access control middleware factory.
         * Requires authenticate middleware to run first.
         *
         * @param allowedRoles - Array of roles that can access the route
         */
        export function requireRole(...allowedRoles: string[]) {
          return (req: Request, res: Response, next: NextFunction): void => {
            const user = (req as AuthenticatedRequest).user;

            if (!user) {
              res.status(401).json({
                success: false,
                error: 'Authentication required',
                code: 'NOT_AUTHENTICATED',
              });
              return;
            }

            if (!allowedRoles.includes(user.role)) {
              res.status(403).json({
                success: false,
                error: 'Insufficient permissions',
                code: 'FORBIDDEN',
              });
              return;
            }

            next();
          };
        }

        /**
         * Permission-based access control.
         */
        const ROLE_PERMISSIONS: Record<string, string[]> = {
          admin: ['read', 'write', 'delete', 'manage'],
          editor: ['read', 'write'],
          viewer: ['read'],
        };

        export function requirePermission(permission: string) {
          return (req: Request, res: Response, next: NextFunction): void => {
            const user = (req as AuthenticatedRequest).user;
            const permissions = ROLE_PERMISSIONS[user?.role] ?? [];

            if (!permissions.includes(permission)) {
              res.status(403).json({
                success: false,
                error: `Permission '${permission}' required`,
                code: 'INSUFFICIENT_PERMISSION',
              });
              return;
            }

            next();
          };
        }
    """)


def generate_auth_js() -> str:
    return dedent("""\
        const jwt = require('jsonwebtoken');

        const JWT_SECRET = process.env.JWT_SECRET;

        if (!JWT_SECRET) {
          throw new Error('JWT_SECRET environment variable is required');
        }

        /**
         * Verify JWT token from the Authorization header.
         * Attaches decoded user payload to req.user.
         */
        function authenticate(req, res, next) {
          const authHeader = req.headers.authorization;

          if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({
              success: false,
              error: 'Authentication required',
              code: 'MISSING_TOKEN',
            });
          }

          const token = authHeader.slice(7);

          try {
            req.user = jwt.verify(token, JWT_SECRET);
            next();
          } catch (error) {
            const message =
              error.name === 'TokenExpiredError'
                ? 'Token has expired'
                : 'Invalid token';

            res.status(401).json({
              success: false,
              error: message,
              code: 'INVALID_TOKEN',
            });
          }
        }

        /**
         * Role-based access control middleware factory.
         * @param  {...string} allowedRoles
         */
        function requireRole(...allowedRoles) {
          return (req, res, next) => {
            if (!req.user) {
              return res.status(401).json({
                success: false,
                error: 'Authentication required',
                code: 'NOT_AUTHENTICATED',
              });
            }

            if (!allowedRoles.includes(req.user.role)) {
              return res.status(403).json({
                success: false,
                error: 'Insufficient permissions',
                code: 'FORBIDDEN',
              });
            }

            next();
          };
        }

        module.exports = { authenticate, requireRole };
    """)


def generate_validation_ts() -> str:
    return dedent("""\
        import { Request, Response, NextFunction } from 'express';
        import { ZodSchema, ZodError } from 'zod';

        /**
         * Validate request body against a Zod schema.
         * Returns 400 with field-level error details on failure.
         *
         * @param schema - Zod schema to validate against
         */
        export function validateBody(schema: ZodSchema) {
          return (req: Request, res: Response, next: NextFunction): void => {
            const result = schema.safeParse(req.body);

            if (!result.success) {
              res.status(400).json({
                success: false,
                error: 'Validation failed',
                code: 'VALIDATION_ERROR',
                details: formatZodError(result.error),
              });
              return;
            }

            req.body = result.data;
            next();
          };
        }

        /**
         * Validate request query parameters against a Zod schema.
         */
        export function validateQuery(schema: ZodSchema) {
          return (req: Request, res: Response, next: NextFunction): void => {
            const result = schema.safeParse(req.query);

            if (!result.success) {
              res.status(400).json({
                success: false,
                error: 'Invalid query parameters',
                code: 'VALIDATION_ERROR',
                details: formatZodError(result.error),
              });
              return;
            }

            req.query = result.data;
            next();
          };
        }

        /**
         * Validate request URL parameters against a Zod schema.
         */
        export function validateParams(schema: ZodSchema) {
          return (req: Request, res: Response, next: NextFunction): void => {
            const result = schema.safeParse(req.params);

            if (!result.success) {
              res.status(400).json({
                success: false,
                error: 'Invalid URL parameters',
                code: 'VALIDATION_ERROR',
                details: formatZodError(result.error),
              });
              return;
            }

            next();
          };
        }

        /**
         * Format Zod errors into a clean, client-friendly structure.
         */
        function formatZodError(error: ZodError): Record<string, string[]> {
          const formatted: Record<string, string[]> = {};

          for (const issue of error.issues) {
            const path = issue.path.join('.') || '_root';
            if (!formatted[path]) {
              formatted[path] = [];
            }
            formatted[path].push(issue.message);
          }

          return formatted;
        }
    """)


def generate_validation_js() -> str:
    return dedent("""\
        /**
         * Validate request body against a Zod schema.
         * @param {import('zod').ZodSchema} schema
         */
        function validateBody(schema) {
          return (req, res, next) => {
            const result = schema.safeParse(req.body);

            if (!result.success) {
              return res.status(400).json({
                success: false,
                error: 'Validation failed',
                code: 'VALIDATION_ERROR',
                details: result.error.flatten(),
              });
            }

            req.body = result.data;
            next();
          };
        }

        /**
         * Validate request query parameters against a Zod schema.
         * @param {import('zod').ZodSchema} schema
         */
        function validateQuery(schema) {
          return (req, res, next) => {
            const result = schema.safeParse(req.query);

            if (!result.success) {
              return res.status(400).json({
                success: false,
                error: 'Invalid query parameters',
                code: 'VALIDATION_ERROR',
                details: result.error.flatten(),
              });
            }

            req.query = result.data;
            next();
          };
        }

        module.exports = { validateBody, validateQuery };
    """)


def generate_error_handler_ts() -> str:
    return dedent("""\
        import { Request, Response, NextFunction } from 'express';

        /**
         * Base application error class.
         * All custom errors should extend this.
         */
        export class AppError extends Error {
          public readonly statusCode: number;
          public readonly code: string;
          public readonly details?: unknown;
          public readonly isOperational: boolean;

          constructor(
            statusCode: number,
            message: string,
            code: string,
            details?: unknown,
          ) {
            super(message);
            this.name = this.constructor.name;
            this.statusCode = statusCode;
            this.code = code;
            this.details = details;
            this.isOperational = true;
            Error.captureStackTrace(this, this.constructor);
          }
        }

        export class NotFoundError extends AppError {
          constructor(message = 'Resource not found') {
            super(404, message, 'NOT_FOUND');
          }
        }

        export class ConflictError extends AppError {
          constructor(message = 'Resource already exists') {
            super(409, message, 'CONFLICT');
          }
        }

        export class ValidationError extends AppError {
          constructor(details: unknown) {
            super(400, 'Validation failed', 'VALIDATION_ERROR', details);
          }
        }

        export class UnauthorizedError extends AppError {
          constructor(message = 'Authentication required') {
            super(401, message, 'UNAUTHORIZED');
          }
        }

        export class ForbiddenError extends AppError {
          constructor(message = 'Insufficient permissions') {
            super(403, message, 'FORBIDDEN');
          }
        }

        export class RateLimitError extends AppError {
          constructor(retryAfterSeconds: number) {
            super(429, 'Too many requests', 'RATE_LIMIT_EXCEEDED', {
              retryAfter: retryAfterSeconds,
            });
          }
        }

        /**
         * Centralized error handling middleware.
         * Must be registered LAST in the Express middleware chain.
         */
        export function errorHandler(
          err: Error,
          req: Request,
          res: Response,
          _next: NextFunction,
        ): void {
          // Known operational errors
          if (err instanceof AppError) {
            res.status(err.statusCode).json({
              success: false,
              error: err.message,
              code: err.code,
              ...(err.details ? { details: err.details } : {}),
            });
            return;
          }

          // Zod validation errors
          if (err.name === 'ZodError') {
            res.status(400).json({
              success: false,
              error: 'Validation failed',
              code: 'VALIDATION_ERROR',
              details: (err as any).flatten?.() ?? err.message,
            });
            return;
          }

          // JWT errors
          if (err.name === 'JsonWebTokenError' || err.name === 'TokenExpiredError') {
            res.status(401).json({
              success: false,
              error: 'Invalid or expired token',
              code: 'AUTH_ERROR',
            });
            return;
          }

          // Unknown / programming errors — log full details, return generic message
          console.error('[UNHANDLED ERROR]', {
            message: err.message,
            stack: err.stack,
            path: req.path,
            method: req.method,
            requestId: req.headers['x-request-id'],
          });

          res.status(500).json({
            success: false,
            error: 'Internal server error',
            code: 'INTERNAL_ERROR',
          });
        }

        /**
         * 404 handler for unmatched routes.
         * Register AFTER all route definitions.
         */
        export function notFoundHandler(req: Request, res: Response): void {
          res.status(404).json({
            success: false,
            error: `Route ${req.method} ${req.path} not found`,
            code: 'ROUTE_NOT_FOUND',
          });
        }

        /**
         * Async handler wrapper — eliminates try/catch boilerplate in controllers.
         */
        export function asyncHandler(
          fn: (req: Request, res: Response, next: NextFunction) => Promise<void>,
        ) {
          return (req: Request, res: Response, next: NextFunction): void => {
            fn(req, res, next).catch(next);
          };
        }
    """)


def generate_error_handler_js() -> str:
    return dedent("""\
        /**
         * Base application error class.
         */
        class AppError extends Error {
          constructor(statusCode, message, code, details) {
            super(message);
            this.name = this.constructor.name;
            this.statusCode = statusCode;
            this.code = code;
            this.details = details;
            this.isOperational = true;
            Error.captureStackTrace(this, this.constructor);
          }
        }

        class NotFoundError extends AppError {
          constructor(message = 'Resource not found') {
            super(404, message, 'NOT_FOUND');
          }
        }

        class ValidationError extends AppError {
          constructor(details) {
            super(400, 'Validation failed', 'VALIDATION_ERROR', details);
          }
        }

        /**
         * Centralized error handling middleware.
         */
        function errorHandler(err, req, res, _next) {
          if (err instanceof AppError) {
            return res.status(err.statusCode).json({
              success: false,
              error: err.message,
              code: err.code,
              ...(err.details ? { details: err.details } : {}),
            });
          }

          console.error('[UNHANDLED ERROR]', {
            message: err.message,
            stack: err.stack,
            path: req.path,
          });

          res.status(500).json({
            success: false,
            error: 'Internal server error',
            code: 'INTERNAL_ERROR',
          });
        }

        function asyncHandler(fn) {
          return (req, res, next) => fn(req, res, next).catch(next);
        }

        module.exports = {
          AppError, NotFoundError, ValidationError,
          errorHandler, asyncHandler,
        };
    """)


def generate_rate_limiter_ts() -> str:
    return dedent("""\
        import { Request, Response, NextFunction } from 'express';

        interface RateLimitRecord {
          count: number;
          resetAt: number;
        }

        interface RateLimitOptions {
          /** Maximum number of requests per window */
          maxRequests: number;
          /** Window duration in milliseconds */
          windowMs: number;
          /** Function to extract the client identifier (default: IP address) */
          keyExtractor?: (req: Request) => string;
          /** Message returned when rate limit is exceeded */
          message?: string;
        }

        const DEFAULT_OPTIONS: RateLimitOptions = {
          maxRequests: 100,
          windowMs: 60 * 1000, // 1 minute
          message: 'Too many requests, please try again later',
        };

        /**
         * In-memory rate limiter middleware.
         *
         * For production use with multiple server instances, replace the
         * in-memory store with Redis.
         *
         * @param options - Rate limiting configuration
         */
        export function rateLimit(options: Partial<RateLimitOptions> = {}) {
          const config = { ...DEFAULT_OPTIONS, ...options };
          const store = new Map<string, RateLimitRecord>();

          // Periodic cleanup of expired entries
          const cleanupInterval = setInterval(() => {
            const now = Date.now();
            for (const [key, record] of store) {
              if (now > record.resetAt) {
                store.delete(key);
              }
            }
          }, config.windowMs);

          // Prevent the interval from keeping the process alive
          if (cleanupInterval.unref) {
            cleanupInterval.unref();
          }

          return (req: Request, res: Response, next: NextFunction): void => {
            const key = config.keyExtractor
              ? config.keyExtractor(req)
              : req.ip ?? req.socket.remoteAddress ?? 'unknown';

            const now = Date.now();
            let record = store.get(key);

            if (!record || now > record.resetAt) {
              record = { count: 0, resetAt: now + config.windowMs };
              store.set(key, record);
            }

            record.count++;

            // Set rate limit headers
            const remaining = Math.max(0, config.maxRequests - record.count);
            const resetSeconds = Math.ceil((record.resetAt - now) / 1000);

            res.set('X-RateLimit-Limit', String(config.maxRequests));
            res.set('X-RateLimit-Remaining', String(remaining));
            res.set('X-RateLimit-Reset', String(resetSeconds));

            if (record.count > config.maxRequests) {
              res.set('Retry-After', String(resetSeconds));
              res.status(429).json({
                success: false,
                error: config.message,
                code: 'RATE_LIMIT_EXCEEDED',
                retryAfter: resetSeconds,
              });
              return;
            }

            next();
          };
        }

        /**
         * Stricter rate limit for authentication endpoints.
         */
        export const authRateLimit = rateLimit({
          maxRequests: 10,
          windowMs: 15 * 60 * 1000, // 15 minutes
          message: 'Too many login attempts, please try again later',
        });

        /**
         * Standard API rate limit.
         */
        export const apiRateLimit = rateLimit({
          maxRequests: 100,
          windowMs: 60 * 1000, // 1 minute
        });
    """)


def generate_rate_limiter_js() -> str:
    return dedent("""\
        /**
         * In-memory rate limiter middleware.
         * @param {{ maxRequests?: number, windowMs?: number, message?: string }} options
         */
        function rateLimit(options = {}) {
          const {
            maxRequests = 100,
            windowMs = 60 * 1000,
            message = 'Too many requests, please try again later',
          } = options;

          const store = new Map();

          setInterval(() => {
            const now = Date.now();
            for (const [key, record] of store) {
              if (now > record.resetAt) store.delete(key);
            }
          }, windowMs).unref();

          return (req, res, next) => {
            const key = req.ip || 'unknown';
            const now = Date.now();
            let record = store.get(key);

            if (!record || now > record.resetAt) {
              record = { count: 0, resetAt: now + windowMs };
              store.set(key, record);
            }

            record.count++;
            const remaining = Math.max(0, maxRequests - record.count);

            res.set('X-RateLimit-Limit', String(maxRequests));
            res.set('X-RateLimit-Remaining', String(remaining));

            if (record.count > maxRequests) {
              return res.status(429).json({
                success: false,
                error: message,
                code: 'RATE_LIMIT_EXCEEDED',
              });
            }

            next();
          };
        }

        module.exports = { rateLimit };
    """)


def generate_logger_ts() -> str:
    return dedent("""\
        import { Request, Response, NextFunction } from 'express';
        import crypto from 'crypto';

        interface LogEntry {
          level: 'info' | 'warn' | 'error';
          message: string;
          timestamp: string;
          requestId: string;
          method: string;
          path: string;
          [key: string]: unknown;
        }

        /**
         * Request logging middleware.
         *
         * Assigns a unique request ID, logs the request on arrival,
         * and logs the response with duration on completion.
         */
        export function requestLogger(
          req: Request,
          res: Response,
          next: NextFunction,
        ): void {
          const requestId =
            (req.headers['x-request-id'] as string) || crypto.randomUUID();
          const start = Date.now();

          // Attach request ID so downstream code can include it in logs
          req.headers['x-request-id'] = requestId;
          res.set('X-Request-Id', requestId);

          // Log incoming request
          log('info', 'Request received', {
            requestId,
            method: req.method,
            path: req.originalUrl,
            userAgent: req.headers['user-agent'],
            ip: req.ip,
          });

          // Log response when finished
          res.on('finish', () => {
            const durationMs = Date.now() - start;
            const level = res.statusCode >= 500 ? 'error' : res.statusCode >= 400 ? 'warn' : 'info';

            log(level, 'Response sent', {
              requestId,
              method: req.method,
              path: req.originalUrl,
              statusCode: res.statusCode,
              durationMs,
            });
          });

          next();
        }

        /**
         * Structured JSON logger.
         */
        function log(
          level: LogEntry['level'],
          message: string,
          data: Record<string, unknown> = {},
        ): void {
          const entry: LogEntry = {
            level,
            message,
            timestamp: new Date().toISOString(),
            requestId: (data.requestId as string) ?? '',
            method: (data.method as string) ?? '',
            path: (data.path as string) ?? '',
            ...data,
          };

          const output = JSON.stringify(entry);

          switch (level) {
            case 'error':
              console.error(output);
              break;
            case 'warn':
              console.warn(output);
              break;
            default:
              console.log(output);
          }
        }

        /**
         * Create a child logger bound to a specific request context.
         */
        export function createRequestLogger(requestId: string) {
          return {
            info: (msg: string, data?: Record<string, unknown>) =>
              log('info', msg, { ...data, requestId }),
            warn: (msg: string, data?: Record<string, unknown>) =>
              log('warn', msg, { ...data, requestId }),
            error: (msg: string, data?: Record<string, unknown>) =>
              log('error', msg, { ...data, requestId }),
          };
        }
    """)


def generate_logger_js() -> str:
    return dedent("""\
        const crypto = require('crypto');

        /**
         * Request logging middleware.
         */
        function requestLogger(req, res, next) {
          const requestId = req.headers['x-request-id'] || crypto.randomUUID();
          const start = Date.now();

          req.headers['x-request-id'] = requestId;
          res.set('X-Request-Id', requestId);

          console.log(JSON.stringify({
            level: 'info',
            message: 'Request received',
            timestamp: new Date().toISOString(),
            requestId,
            method: req.method,
            path: req.originalUrl,
          }));

          res.on('finish', () => {
            const durationMs = Date.now() - start;
            console.log(JSON.stringify({
              level: res.statusCode >= 500 ? 'error' : 'info',
              message: 'Response sent',
              timestamp: new Date().toISOString(),
              requestId,
              method: req.method,
              path: req.originalUrl,
              statusCode: res.statusCode,
              durationMs,
            }));
          });

          next();
        }

        module.exports = { requestLogger };
    """)


# Map middleware type to generator functions
GENERATORS = {
    "ts": {
        "auth": ("auth.ts", generate_auth_ts),
        "validation": ("validate.ts", generate_validation_ts),
        "error-handler": ("errorHandler.ts", generate_error_handler_ts),
        "rate-limiter": ("rateLimiter.ts", generate_rate_limiter_ts),
        "logger": ("requestLogger.ts", generate_logger_ts),
    },
    "js": {
        "auth": ("auth.js", generate_auth_js),
        "validation": ("validate.js", generate_validation_js),
        "error-handler": ("errorHandler.js", generate_error_handler_js),
        "rate-limiter": ("rateLimiter.js", generate_rate_limiter_js),
        "logger": ("requestLogger.js", generate_logger_js),
    },
}


def generate_index_file(output_dir: Path, files_written: list, lang: str) -> str:
    """Generate an index file that re-exports all middleware."""
    ext = "ts" if lang == "ts" else "js"
    lines = [f"// Auto-generated middleware index\n"]

    if lang == "ts":
        for fname in sorted(files_written):
            module = fname.replace(f".{ext}", "")
            lines.append(f"export * from './{module}';")
    else:
        for fname in sorted(files_written):
            module = fname.replace(f".{ext}", "")
            lines.append(f"module.exports = {{")
            lines.append(f"  ...require('./{module}'),")
        # Close for JS
        if files_written:
            lines_js = ["// Auto-generated middleware index\n"]
            lines_js.append("module.exports = {")
            for fname in sorted(files_written):
                module = fname.replace(f".{ext}", "")
                lines_js.append(f"  ...require('./{module}'),")
            lines_js.append("};")
            return "\n".join(lines_js) + "\n"

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Generate Express middleware boilerplate files.",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for generated middleware files",
    )
    parser.add_argument(
        "--types", "-t",
        nargs="*",
        choices=AVAILABLE_MIDDLEWARE,
        default=AVAILABLE_MIDDLEWARE,
        help=f"Which middleware to generate (default: all). Options: {', '.join(AVAILABLE_MIDDLEWARE)}",
    )
    parser.add_argument(
        "--lang", "-l",
        choices=["ts", "js"],
        default="ts",
        help="Language to generate: ts (TypeScript) or js (JavaScript). Default: ts",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Do not generate an index file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files without prompting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated without writing files",
    )

    args = parser.parse_args()
    output_dir = Path(args.output).resolve()
    generators = GENERATORS[args.lang]

    if args.dry_run:
        print(f"Would create directory: {output_dir}")
        for mw_type in args.types:
            if mw_type in generators:
                fname, _ = generators[mw_type]
                print(f"  Would write: {output_dir / fname}")
        if not args.no_index:
            ext = "ts" if args.lang == "ts" else "js"
            print(f"  Would write: {output_dir / f'index.{ext}'}")
        return

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    files_written = []

    for mw_type in args.types:
        if mw_type not in generators:
            print(f"Warning: Unknown middleware type '{mw_type}', skipping", file=sys.stderr)
            continue

        fname, generator_fn = generators[mw_type]
        filepath = output_dir / fname

        if filepath.exists() and not args.force:
            print(f"  SKIP {filepath} (already exists, use --force to overwrite)")
            continue

        content = generator_fn()
        filepath.write_text(content, encoding="utf-8")
        files_written.append(fname)
        print(f"  CREATED {filepath}")

    # Generate index file
    if not args.no_index and files_written:
        ext = "ts" if args.lang == "ts" else "js"
        index_path = output_dir / f"index.{ext}"
        index_content = generate_index_file(output_dir, files_written, args.lang)
        index_path.write_text(index_content, encoding="utf-8")
        print(f"  CREATED {index_path}")

    total = len(files_written)
    print(f"\nGenerated {total} middleware file{'s' if total != 1 else ''} in {output_dir}")


if __name__ == "__main__":
    main()
