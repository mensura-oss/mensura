/**
 * A controllable `EventSource` stand-in for tests. jsdom ships no `EventSource`,
 * so `useLiveEvents` treats live updates as a progressive enhancement and simply
 * early-returns. Installing this fake lets a test open the same subscription the
 * app opens and then deterministically `emit(...)` server events into it, so the
 * SSE→cache-invalidation→refetch loop can be exercised without a real network
 * stream. It intentionally mirrors only the surface `useLiveEvents` touches:
 * `addEventListener`/`removeEventListener`, `close`, and construction with a URL.
 */
export class FakeEventSource {
  static instances: FakeEventSource[] = [];

  readonly url: string;
  readonly withCredentials = false;
  closed = false;
  private readonly listeners = new Map<
    string,
    Set<(event: MessageEvent) => void>
  >();

  constructor(url: string | URL) {
    this.url = url.toString();
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, handler: (event: MessageEvent) => void): void {
    const handlers = this.listeners.get(type) ?? new Set();
    handlers.add(handler);
    this.listeners.set(type, handlers);
  }

  removeEventListener(
    type: string,
    handler: (event: MessageEvent) => void,
  ): void {
    this.listeners.get(type)?.delete(handler);
  }

  close(): void {
    this.closed = true;
  }

  /** Deliver a named event to every registered listener, JSON-encoding objects. */
  emit(type: string, data: unknown): void {
    const payload = {
      type,
      data: typeof data === "string" ? data : JSON.stringify(data),
    } as MessageEvent;
    for (const handler of this.listeners.get(type) ?? []) {
      handler(payload);
    }
  }

  /** The most recently constructed instance (the subscription under test). */
  static latest(): FakeEventSource {
    const instance = FakeEventSource.instances.at(-1);
    if (!instance) {
      throw new Error("No FakeEventSource has been constructed.");
    }
    return instance;
  }

  static reset(): void {
    FakeEventSource.instances = [];
  }
}

/**
 * Install {@link FakeEventSource} as the global `EventSource` for a test and
 * return a restore function that puts the original (usually `undefined` in
 * jsdom) back and clears captured instances.
 */
export function installFakeEventSource(): () => void {
  const original = (globalThis as { EventSource?: unknown }).EventSource;
  FakeEventSource.reset();
  (globalThis as { EventSource?: unknown }).EventSource =
    FakeEventSource as unknown as typeof EventSource;
  return () => {
    (globalThis as { EventSource?: unknown }).EventSource = original;
    FakeEventSource.reset();
  };
}
