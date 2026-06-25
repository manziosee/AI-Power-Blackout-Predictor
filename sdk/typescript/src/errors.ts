export class BlackoutApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    public readonly url: string
  ) {
    super(`BlackoutAPI ${status} — ${detail} (${url})`);
    this.name = "BlackoutApiError";
  }
}

export class BlackoutNetworkError extends Error {
  constructor(message: string, public readonly cause?: unknown) {
    super(message);
    this.name = "BlackoutNetworkError";
  }
}

export class BlackoutAuthError extends BlackoutApiError {}
