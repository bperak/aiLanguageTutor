/**
 * Application constants
 */

// Default compilation settings
export const DEFAULT_METALANGUAGE = "en";
export const DEFAULT_MODEL = "gpt-4o";

// Polling intervals (in milliseconds)
export const POLL_INTERVAL_ACTIVE = 5000; // When stages are generating
export const POLL_INTERVAL_IDLE = 10000; // When no active generation

// Debug mode (gates console logging)
export const DEBUG = process.env.NODE_ENV === "development";

// Logging utilities
export const log = DEBUG ? console.log : () => {};
export const logError = DEBUG ? console.error : () => {};
export const logWarn = DEBUG ? console.warn : () => {};
