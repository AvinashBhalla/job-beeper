import PostalMime from "postal-mime";
import type { Address, Email } from "postal-mime";

interface AlertLink {
  url: string;
  title: string;
}

interface AlertEvent {
  schema_version: 1;
  event_id: string;
  message_id: string;
  envelope_from: string;
  envelope_to: string;
  header_from: string;
  subject: string;
  received_at: string;
  links: AlertLink[];
}

interface Env {
  ALERT_EVENTS: Queue<AlertEvent>;
  GOOGLE_ALERTS_ALLOWED_FROM: string;
  GOOGLE_ALERTS_INBOUND_TO: string;
  JOB_BEEPER_WEBHOOK_URL: string;
  JOB_BEEPER_WEBHOOK_SECRET: string;
  MAX_RAW_EMAIL_BYTES?: string;
}

const MAX_RAW_EMAIL_BYTES = 2 * 1024 * 1024;
const MAX_EXTRACTED_LINKS = 100;
const MAX_LINKS_PER_QUEUE_EVENT = 20;
const MAX_QUEUED_EVENT_BYTES = 96 * 1024;
const MAX_MIME_NESTING_DEPTH = 30;
const MAX_MIME_PARTS = 200;

function mailboxAddress(address: Address | undefined): string {
  if (!address || !("address" in address) || typeof address.address !== "string") {
    return "";
  }
  return address.address.trim().toLowerCase();
}

function decodeHtml(value: string): string {
  return value
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#(\d+);/g, (_, code: string) => {
      const value = Number(code);
      return Number.isInteger(value) && value >= 0 && value <= 0x10ffff
        ? String.fromCodePoint(value)
        : "";
    })
    .replace(/&#x([0-9a-f]+);/gi, (_, code: string) => {
      const value = Number.parseInt(code, 16);
      return Number.isInteger(value) && value >= 0 && value <= 0x10ffff
        ? String.fromCodePoint(value)
        : "";
    });
}

function plainAnchorText(value: string): string {
  return decodeHtml(value.replace(/<[^>]*>/g, " "))
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 500);
}

function isCandidateLabel(label: string): boolean {
  const normalized = label.toLowerCase();
  return Boolean(label) && !/(unsubscribe|manage alerts|edit alert|stop receiving|view this alert|privacy policy|help center)/i.test(normalized);
}

function candidateUrl(value: string): string | null {
  const cleaned = decodeHtml(value).replace(/&amp;/gi, "&").trim();
  if (!cleaned || cleaned.length > 2048) return null;
  try {
    const parsed = new URL(cleaned);
    if (!["http:", "https:"].includes(parsed.protocol)) return null;
    if (!parsed.hostname || parsed.username || parsed.password) return null;
    if (parsed.hostname === "localhost" || parsed.hostname.endsWith(".localhost")) return null;
    return parsed.toString();
  } catch {
    return null;
  }
}

function extractLinks(email: Email): AlertLink[] {
  const found = new Map<string, AlertLink>();

  if (email.html) {
    const anchorPattern = /<a\b([^>]*)>([\s\S]*?)<\/a\s*>/gi;
    for (const match of email.html.matchAll(anchorPattern)) {
      const attrs = match[1] || "";
      const hrefMatch = attrs.match(/\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/i);
      if (!hrefMatch) continue;
      const href = candidateUrl(hrefMatch[1] || hrefMatch[2] || hrefMatch[3] || "");
      const title = plainAnchorText(match[2] || "");
      if (!href || !isCandidateLabel(title)) continue;
      if (!found.has(href)) found.set(href, { url: href, title });
      if (found.size >= MAX_EXTRACTED_LINKS) break;
    }
  }

  if (found.size === 0 && email.text) {
    const urlPattern = /https?:\/\/[^\s<>"']+/gi;
    for (const match of email.text.matchAll(urlPattern)) {
      const href = candidateUrl(match[0].replace(/[),.;]+$/, ""));
      if (!href || found.has(href)) continue;
      found.set(href, { url: href, title: "" });
      if (found.size >= MAX_EXTRACTED_LINKS) break;
    }
  }

  return Array.from(found.values());
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function enqueueAlert(email: Email, envelopeFrom: string, envelopeTo: string, links: AlertLink[], queue: Queue<AlertEvent>): Promise<void> {
  const messageId = (email.messageId || "").trim().slice(0, 512);
  const subject = (email.subject || "").replace(/[\r\n\t]+/g, " ").trim().slice(0, 512);
  const headerFrom = mailboxAddress(email.from);
  const receivedAt = (email.date || "").slice(0, 80);

  const batches: AlertLink[][] = [];
  for (let index = 0; index < links.length; index += MAX_LINKS_PER_QUEUE_EVENT) {
    batches.push(links.slice(index, index + MAX_LINKS_PER_QUEUE_EVENT));
  }
  if (batches.length === 0) batches.push([]);

  const messages: Array<{ body: AlertEvent }> = [];
  for (const [index, batch] of batches.entries()) {
    const identity = [
      messageId,
      subject,
      receivedAt,
      headerFrom,
      String(index),
      ...batch.map((link) => link.url),
    ].join("\n");
    const event: AlertEvent = {
      schema_version: 1,
      event_id: await sha256Hex(identity),
      message_id: messageId,
      envelope_from: envelopeFrom.slice(0, 320),
      envelope_to: envelopeTo.slice(0, 320),
      header_from: headerFrom.slice(0, 512),
      subject,
      received_at: receivedAt,
      links: batch,
    };
    const encoded = new TextEncoder().encode(JSON.stringify(event));
    if (encoded.byteLength > MAX_QUEUED_EVENT_BYTES) {
      throw new Error("A parsed Google Alert event exceeded the safe queue payload size.");
    }
    messages.push({ body: event });
  }
  if (messages.length > 0) await queue.sendBatch(messages);
}

async function signRequest(body: string, timestamp: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signedBytes = new TextEncoder().encode(`${timestamp}.${body}`);
  const signature = await crypto.subtle.sign("HMAC", key, signedBytes);
  return Array.from(new Uint8Array(signature), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function allowedSenders(env: Env): Set<string> {
  return new Set(
    (env.GOOGLE_ALERTS_ALLOWED_FROM || "")
      .split(",")
      .map((address) => address.trim().toLowerCase())
      .filter(Boolean),
  );
}

export default {
  async email(message: ForwardableEmailMessage, env: Env): Promise<void> {
    const expectedRecipient = (env.GOOGLE_ALERTS_INBOUND_TO || "").trim().toLowerCase();
    const senderAllowlist = allowedSenders(env);
    if (!expectedRecipient || senderAllowlist.size === 0) {
      message.setReject("Google Alerts ingress is not configured.");
      return;
    }

    const envelopeFrom = message.from.trim().toLowerCase();
    const envelopeTo = message.to.trim().toLowerCase();
    if (envelopeTo !== expectedRecipient) {
      message.setReject("Unexpected JobBeeper recipient.");
      return;
    }

    const maxRawBytes = Math.max(
      64 * 1024,
      Math.min(Number(env.MAX_RAW_EMAIL_BYTES || MAX_RAW_EMAIL_BYTES), 5 * 1024 * 1024),
    );
    if (message.rawSize > maxRawBytes) {
      message.setReject("Message exceeds the configured processing limit.");
      return;
    }

    let parsed: Email;
    try {
      parsed = await PostalMime.parse(message.raw, {
        maxNestingDepth: MAX_MIME_NESTING_DEPTH,
        maxPartCount: MAX_MIME_PARTS,
        maxRfc822NestingDepth: 3,
      });
    } catch (error) {
      console.error("Google Alerts MIME parse failed", {
        errorType: error instanceof Error ? error.name : "UnknownError",
        rawSize: message.rawSize,
      });
      message.setReject("Message could not be safely parsed.");
      return;
    }

    const headerFrom = mailboxAddress(parsed.from);
    if (!senderAllowlist.has(headerFrom)) {
      message.setReject("Message sender is not an allowed Google Alerts sender.");
      return;
    }

    const links = extractLinks(parsed);
    try {
      await enqueueAlert(parsed, envelopeFrom, envelopeTo, links, env.ALERT_EVENTS);
    } catch (error) {
      console.error("Google Alerts event queue failed", {
        errorType: error instanceof Error ? error.name : "UnknownError",
        linkCount: links.length,
      });
      // Throwing fails the inbound email action. Gmail retains its original
      // Inbox copy; after the filter forwards successfully, the queue consumer
      // handles backend delivery retries independently.
      throw error;
    }
  },

  async queue(batch: MessageBatch<AlertEvent>, env: Env): Promise<void> {
    const webhookUrl = new URL(env.JOB_BEEPER_WEBHOOK_URL);
    if (webhookUrl.protocol !== "https:") {
      throw new Error("JobBeeper webhook URL must use HTTPS.");
    }
    if (!env.JOB_BEEPER_WEBHOOK_SECRET || env.JOB_BEEPER_WEBHOOK_SECRET.length < 32) {
      throw new Error("JobBeeper webhook secret is not configured.");
    }

    for (const message of batch.messages) {
      const body = JSON.stringify(message.body);
      const timestamp = String(Math.floor(Date.now() / 1000));
      const signature = await signRequest(body, timestamp, env.JOB_BEEPER_WEBHOOK_SECRET);
      try {
        const response = await fetch(webhookUrl, {
          method: "POST",
          redirect: "manual",
          headers: {
            "Content-Type": "application/json",
            "X-JobBeeper-Timestamp": timestamp,
            "X-JobBeeper-Signature": signature,
          },
          body,
        });
        if (response.ok) {
          message.ack();
        } else {
          console.error("Google Alerts backend rejected queued event", {
            status: response.status,
          });
          message.retry({ delaySeconds: response.status === 429 ? 60 : 30 });
        }
      } catch (error) {
        console.error("Google Alerts backend request failed", {
          errorType: error instanceof Error ? error.name : "UnknownError",
        });
        message.retry({ delaySeconds: 30 });
      }
    }
  },
} satisfies ExportedHandler<Env>;
