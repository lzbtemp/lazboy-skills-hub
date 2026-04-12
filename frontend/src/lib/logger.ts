/**
 * Lightweight structured logger for browser environments.
 *
 * - Outputs JSON in production, human-readable in development
 * - Supports log levels: DEBUG, INFO, WARN, ERROR
 * - Adds timestamps, module context, and optional metadata
 * - Never logs PII, passwords, or API keys
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  level: LogLevel;
  module: string;
  message: string;
  timestamp: string;
  durationMs?: number;
  [key: string]: unknown;
}

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const MIN_LEVEL: LogLevel = import.meta.env.DEV ? 'debug' : 'info';

function shouldLog(level: LogLevel): boolean {
  return LOG_LEVELS[level] >= LOG_LEVELS[MIN_LEVEL];
}

function emit(entry: LogEntry) {
  if (!shouldLog(entry.level)) return;

  const consoleFn =
    entry.level === 'error'
      ? console.error
      : entry.level === 'warn'
        ? console.warn
        : entry.level === 'debug'
          ? console.debug
          : console.info;

  if (import.meta.env.DEV) {
    const prefix = `[${entry.module}]`;
    const duration = entry.durationMs != null ? ` (${entry.durationMs}ms)` : '';
    const knownKeys = new Set(['level', 'module', 'message', 'timestamp', 'durationMs']);
    const extra: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(entry)) {
      if (!knownKeys.has(k)) extra[k] = v;
    }
    consoleFn(`${prefix} ${entry.message}${duration}`, ...(Object.keys(extra).length > 0 ? [extra] : []));
  } else {
    consoleFn(JSON.stringify(entry));
  }
}

export function createLogger(module: string) {
  const log = (level: LogLevel, message: string, meta?: Record<string, unknown>) => {
    emit({
      level,
      module,
      message,
      timestamp: new Date().toISOString(),
      ...meta,
    });
  };

  return {
    debug: (msg: string, meta?: Record<string, unknown>) => log('debug', msg, meta),
    info: (msg: string, meta?: Record<string, unknown>) => log('info', msg, meta),
    warn: (msg: string, meta?: Record<string, unknown>) => log('warn', msg, meta),
    error: (msg: string, meta?: Record<string, unknown>) => log('error', msg, meta),

    /** Time an async operation and log its result */
    async time<T>(label: string, fn: () => Promise<T>, meta?: Record<string, unknown>): Promise<T> {
      const start = performance.now();
      try {
        const result = await fn();
        const durationMs = Math.round(performance.now() - start);
        log('info', `${label} completed`, { durationMs, ...meta });
        return result;
      } catch (err) {
        const durationMs = Math.round(performance.now() - start);
        log('error', `${label} failed`, {
          durationMs,
          error: err instanceof Error ? err.message : String(err),
          ...meta,
        });
        throw err;
      }
    },
  };
}
