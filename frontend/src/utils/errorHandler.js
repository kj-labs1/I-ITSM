/**
 * Centralized Error Extraction and Formatting Utility.
 *
 * Extracts human-readable, safe error messages from API response envelopes,
 * FastAPI/Pydantic validation lists, and network errors.
 */

const STATUS_CODE_MESSAGES = {
  400: "Bad request. Please verify the submitted information.",
  401: "Authentication required or your session has expired. Please log in again.",
  403: "Permission denied. You do not have access to perform this action.",
  404: "Requested resource was not found.",
  409: "Conflict with current resource state.",
  422: "Validation error. Please verify the submitted fields.",
  429: "Too many requests. Please wait a moment and try again.",
  500: "Internal server error. Please try again later.",
  502: "Bad Gateway. The service is temporarily unreachable.",
  503: "Service temporarily unavailable. Please try again shortly.",
  504: "Gateway timeout. The server took too long to respond.",
};

/**
 * Formats a FastAPI / Pydantic validation error array into a clean readable string.
 * e.g., [{loc: ['body', 'required_skill'], msg: 'Field required'}] -> "Required skill: Field required"
 */
export function formatValidationErrors(details) {
  if (!Array.isArray(details) || details.length === 0) {
    return "";
  }

  return details
    .map((item) => {
      if (typeof item === "string") return item;
      if (!item || typeof item !== "object") return String(item);

      const locParts = Array.isArray(item.loc)
        ? item.loc.filter((p) => !["body", "query", "path"].includes(String(p).toLowerCase()))
        : [];

      const rawField = locParts.join(".");
      const formattedField = rawField
        ? rawField
            .split(".")
            .map((part) => part.charAt(0).toUpperCase() + part.slice(1).replace(/_/g, " "))
            .join(" ")
        : "Field";

      const cleanMsg = item.msg || "Invalid value";
      return `${formattedField}: ${cleanMsg}`;
    })
    .join("; ");
}

/**
 * Sanitizes an error message to prevent leaking internal stack traces or SQL statements.
 */
function sanitizeMessage(msg) {
  if (!msg || typeof msg !== "string") return "";

  // Check for internal server stack traces or database queries
  const isTraceback = msg.includes("Traceback (most recent call last)") || msg.includes('File "');
  const isSqlError = /sqlalchemy|psycopg2|SELECT |INSERT INTO |UPDATE |DELETE FROM /i.test(msg);

  if (isTraceback || isSqlError) {
    return "An internal server error occurred. Please contact the administrator.";
  }

  return msg.trim();
}

/**
 * Extracts a meaningful human-readable error message from response payloads or Error objects.
 *
 * @param {any} errorOrData - Error instance, Axios/Fetch response data, or error string
 * @param {number|null} [statusCode] - Optional HTTP status code
 * @param {string} [fallback] - Optional custom fallback message
 * @returns {string} Human-friendly error message
 */
export function extractErrorMessage(errorOrData, statusCode = null, fallback = "") {
  if (!errorOrData && !statusCode) {
    return fallback || "An unexpected error occurred. Please try again.";
  }

  // Handle network / fetch failures
  if (errorOrData instanceof Error) {
    const isNetwork =
      errorOrData.name === "TypeError" &&
      (errorOrData.message.includes("fetch") || errorOrData.message.includes("NetworkError"));

    if (isNetwork) {
      return "Network error: Unable to connect to the server. Please check your connection.";
    }

    if (errorOrData.name === "AbortError") {
      return "Request timed out. Please try again.";
    }

    // If the error object has attached response data
    if (errorOrData.data) {
      return extractErrorMessage(errorOrData.data, errorOrData.status || statusCode, fallback);
    }

    // Ignore generic "Request failed (status)" messages if status fallback exists
    const genericPattern = /^Request failed \((\d+)\)$/;
    if (!genericPattern.test(errorOrData.message) && errorOrData.message && errorOrData.message !== "[object Object]") {
      const sanitized = sanitizeMessage(errorOrData.message);
      if (sanitized) return sanitized;
    }

    statusCode = errorOrData.status || statusCode;
  }

  const data = typeof errorOrData === "object" && errorOrData !== null ? errorOrData : {};

  // 1. Direct message (from IITSMException content={"message": ...})
  if (typeof data.message === "string" && data.message.trim()) {
    const sanitized = sanitizeMessage(data.message);
    if (sanitized) return sanitized;
  }

  // 2. FastAPI / Pydantic detail
  if (data.detail !== undefined && data.detail !== null) {
    if (typeof data.detail === "string" && data.detail.trim()) {
      const sanitized = sanitizeMessage(data.detail);
      if (sanitized) return sanitized;
    }
    if (Array.isArray(data.detail)) {
      const formatted = formatValidationErrors(data.detail);
      if (formatted) return formatted;
    }
    if (typeof data.detail === "object" && typeof data.detail.message === "string") {
      const sanitized = sanitizeMessage(data.detail.message);
      if (sanitized) return sanitized;
    }
  }

  // 3. Error field (e.g. data.error)
  if (typeof data.error === "string" && data.error.trim()) {
    const sanitized = sanitizeMessage(data.error);
    if (sanitized) return sanitized;
  }
  if (data.error && typeof data.error === "object" && typeof data.error.message === "string") {
    const sanitized = sanitizeMessage(data.error.message);
    if (sanitized) return sanitized;
  }

  // 4. HTTP Status code fallback
  const code = Number(statusCode || data.status);
  if (code && STATUS_CODE_MESSAGES[code]) {
    return STATUS_CODE_MESSAGES[code];
  }

  // 5. Explicit or default fallback
  return fallback || "An unexpected error occurred. Please try again.";
}

export default extractErrorMessage;
