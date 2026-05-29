import * as http from 'node:http';
import * as net from 'node:net';

export interface WebhookRequest {
  method: string;
  url: string;
  headers: http.IncomingHttpHeaders;
  body: Record<string, unknown>;
  receivedAt: number;
}

const WEBHOOK_HOST = process.env.WEBHOOK_HOST || 'host.containers.internal';

export class WebhookReceiver {
  private server: http.Server | null = null;
  private requests: WebhookRequest[] = [];
  private port = 0;

  async start(): Promise<void> {
    if (this.server) return;

    this.server = http.createServer((req, res) => {
      let body = '';
      req.on('data', (chunk: Buffer) => {
        body += chunk.toString();
      });
      req.on('end', () => {
        let parsed: Record<string, unknown> = {};
        try {
          parsed = JSON.parse(body);
        } catch {
          parsed = {_raw: body};
        }

        this.requests.push({
          method: req.method ?? 'POST',
          url: req.url ?? '/',
          headers: req.headers,
          body: parsed,
          receivedAt: Date.now(),
        });

        res.writeHead(200, {'Content-Type': 'application/json'});
        res.end('{"ok":true}');
      });
    });

    await new Promise<void>((resolve) => {
      this.server!.listen(0, '0.0.0.0', () => resolve());
    });

    this.port = (this.server.address() as net.AddressInfo).port;
  }

  async stop(): Promise<void> {
    if (!this.server) return;
    await new Promise<void>((resolve, reject) => {
      this.server!.close((err) => (err ? reject(err) : resolve()));
    });
    this.server = null;
    this.requests = [];
    this.port = 0;
  }

  getUrl(path = '/webhook'): string {
    if (!this.server) throw new Error('WebhookReceiver not started');
    return `http://${WEBHOOK_HOST}:${this.port}${path}`;
  }

  getRequests(): WebhookRequest[] {
    return [...this.requests];
  }

  clear(): void {
    this.requests = [];
  }

  async waitForWebhook(
    predicate?: (req: WebhookRequest) => boolean,
    timeout = 30000,
    interval = 500,
  ): Promise<WebhookRequest | null> {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const match = predicate
        ? this.requests.find(predicate)
        : this.requests[0];
      if (match) return match;
      await new Promise((r) => setTimeout(r, interval));
    }
    return null;
  }
}
