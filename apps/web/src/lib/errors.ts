export class ApiError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export async function parseApiError(response: Response): Promise<ApiError> {
  let code = "UNKNOWN_ERROR";
  let message = `Request failed with status ${response.status}`;
  let details: Record<string, unknown> = {};

  const text = await response.text().catch(() => null);

  if (text) {
    try {
      const body = JSON.parse(text);
      if (typeof body.code === "string") code = body.code;
      if (typeof body.message === "string") message = body.message;
      if (body.details && typeof body.details === "object") details = body.details;
    } catch {
      message = text;
    }
  }

  return new ApiError(response.status, code, message, details);
}
