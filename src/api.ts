/**
 * Backend API (EdgeOne Makers)
 *
 * Route mapping (file → route):
 *   agents/chat/index.py        → POST /chat           Strict interviewer (SSE)
 *   agents/chat/stop.py         → POST /chat/stop      Abort the active run
 *   agents/job-agent/index.py   → POST /job-agent      Job-search agent (SSE)
 *   cloud-functions/history/index.py          → POST /history
 *   cloud-functions/conversations/index.py    → POST /conversations
 *   cloud-functions/clear-history/index.py    → POST /clear-history
 *   cloud-functions/delete-conversation/index.py → POST /delete-conversation
 *   cloud-functions/jobs/index.py    → POST /jobs       Job library
 *   cloud-functions/report/index.py  → POST /report      Market report
 *   cloud-functions/match/index.py   → POST /match       Resume vs one JD
 *   cloud-functions/match-rank/index.py → POST /match-rank Resume vs all jobs
 */

import type {
  Message,
  ListConversationsParams,
  ListConversationsResponse,
  Job,
  MarketReport,
  MatchResponse,
  InterviewMode,
} from './types';

export const API = {
  chat: '/chat',
  chatStop: '/chat/stop',                  // FIX: was '/stop', real route is /chat/stop
  jobAgent: '/job-agent',
  history: '/history',
  clearHistory: '/clear-history',
  conversations: '/conversations',
  deleteConversation: '/delete-conversation',
  jobs: '/jobs',
  report: '/report',
  match: '/match',
  matchRank: '/match-rank',
} as const;

/**
 * EdgeOne Pages preview links add `eo_token` / `eo_time` query params for access
 * control. Relative API fetches would otherwise hit the page's 401 gate. If the
 * current page URL carries preview tokens, forward them to backend requests.
 */
function withPreviewToken(endpoint: string): string {
  if (typeof window === 'undefined' || !endpoint) return endpoint;
  const search = new URLSearchParams(window.location.search);
  const token = search.get('eo_token');
  const time = search.get('eo_time');
  const key = search.get('eo_key');
  if (!token && !time && !key) return endpoint;
  const url = new URL(endpoint, window.location.href);
  if (token) url.searchParams.set('eo_token', token);
  if (time) url.searchParams.set('eo_time', time);
  if (key) url.searchParams.set('eo_key', key);
  return url.pathname + url.search;
}

export interface RawSseEvent {
  eventType: string;
  data: unknown;
  raw: string;
  timestamp: number;
}

export interface StreamCallbacks {
  onTextDelta: (delta: string) => void;
  onToolCalled: (toolName: string) => void;
  onDone: () => void;
  onError: (err: Error) => void;
  onRawEvent?: (event: RawSseEvent) => void;
}

export interface StreamOptions {
  userId?: string;
  userMsgId?: string;
  botMsgId?: string;
  /** Extra fields merged into the request body (e.g. interview mode/jdId/material). */
  extraBody?: Record<string, unknown>;
}

/**
 * Generic SSE stream against any agents/* endpoint.
 * Backend pushes events: text_delta / tool_called / done / error
 * Returns an AbortController the caller can use to abort (or pair with the
 * matching /.../stop endpoint for graceful abort).
 */
export function streamMessage(
  endpoint: string,
  message: string,
  callbacks: StreamCallbacks,
  conversationId?: string,
  options?: StreamOptions,
): AbortController {
  const ctrl = new AbortController();

  (async () => {
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (conversationId) headers['makers-conversation-id'] = conversationId;

      const res = await fetch(withPreviewToken(endpoint), {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message,
          userId: options?.userId,
          userMsgId: options?.userMsgId,
          botMsgId: options?.botMsgId,
          ...(options?.extraBody || {}),
        }),
        signal: ctrl.signal,
      });

      if (!res.ok) {
        callbacks.onError(new Error(`HTTP ${res.status}: ${await res.text().catch(() => '')}`));
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) { callbacks.onError(new Error('ReadableStream not supported')); return; }

      const decoder = new TextDecoder();
      let buffer = '';
      let doneReceived = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';
        for (const part of parts) {
          if (!part.trim()) continue;
          dispatchSseChunk(part, callbacks, () => { doneReceived = true; });
        }
      }
      if (!doneReceived) callbacks.onDone();
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      callbacks.onError(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return ctrl;
}

/** Stream POST /chat (strict interviewer). */
export function sendMessageStream(
  message: string,
  callbacks: StreamCallbacks,
  conversationId?: string,
  options?: StreamOptions,
): AbortController {
  return streamMessage(API.chat, message, callbacks, conversationId, options);
}

/** Stream POST /job-agent (job-search agent). */
export function sendJobAgentStream(
  message: string,
  callbacks: StreamCallbacks,
  conversationId?: string,
  options?: StreamOptions,
): AbortController {
  return streamMessage(API.jobAgent, message, callbacks, conversationId, options);
}

/** Parse a single SSE event and dispatch to the corresponding callback. */
function dispatchSseChunk(part: string, cb: StreamCallbacks, markDone: () => void): void {
  let eventType = '';
  let data = '';
  for (const line of part.split('\n')) {
    if (line.startsWith('event: ')) eventType = line.slice(7);
    else if (line.startsWith('data: ')) data = line.slice(6);
  }
  if (!eventType || !data) return;

  let parsed: unknown = null;
  try { parsed = JSON.parse(data); } catch { /* keep raw */ }

  if (cb.onRawEvent) {
    cb.onRawEvent({ eventType, data: parsed, raw: data, timestamp: Date.now() });
  }

  if (eventType === 'text_delta' && parsed && typeof parsed === 'object') {
    cb.onTextDelta((parsed as { delta?: string }).delta ?? '');
  } else if (eventType === 'tool_called' && parsed && typeof parsed === 'object') {
    cb.onToolCalled((parsed as { tool?: string }).tool ?? '');
  } else if (eventType === 'error') {
    const msg = parsed && typeof parsed === 'object' ? (parsed as { message?: string }).message : '';
    cb.onError(new Error(msg || 'agent returned error'));
  } else if (eventType === 'done') {
    markDone();
    cb.onDone();
  }
}

/** Get conversation history for restoring the chat window after page refresh. */
export async function fetchConversationHistory(
  conversationId: string,
  userId?: string,
): Promise<Message[]> {
  try {
    const res = await fetch(withPreviewToken(API.history), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: conversationId, user_id: userId }),
    });
    if (!res.ok) return [];
    const data = await res.json().catch(() => null) as { messages?: Message[] } | null;
    return Array.isArray(data?.messages) ? data.messages : [];
  } catch {
    return [];
  }
}

/** Request the backend to abort the currently running agent (per-endpoint). */
export async function stopAgent(endpoint: string, conversationId?: string): Promise<boolean> {
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (conversationId) headers['makers-conversation-id'] = conversationId;
    const res = await fetch(withPreviewToken(endpoint), {
      method: 'POST',
      headers,
      body: JSON.stringify({ conversation_id: conversationId }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** Clear backend conversation history for the given conversation ID. */
export async function clearConversationHistory(
  conversationId?: string,
  userId?: string,
): Promise<boolean> {
  if (!conversationId) return false;
  try {
    const res = await fetch(withPreviewToken(API.clearHistory), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: conversationId, user_id: userId }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** List conversations for the given user (eo-uuid). */
export async function listConversations(
  params: ListConversationsParams,
): Promise<ListConversationsResponse> {
  const empty: ListConversationsResponse = { conversations: [] };
  try {
    const res = await fetch(withPreviewToken(API.conversations), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: params.userId,
        limit: params.limit,
        order: params.order,
        after: params.after,
        before: params.before,
      }),
    });
    if (!res.ok) return empty;
    const data = (await res.json().catch(() => null)) as ListConversationsResponse | null;
    if (!data || !Array.isArray(data.conversations)) return empty;
    return { conversations: data.conversations, nextCursor: data.nextCursor, previousCursor: data.previousCursor };
  } catch {
    return empty;
  }
}

/** Permanently delete a conversation (irreversible). */
export async function deleteConversation(
  conversationId: string,
  userId?: string,
): Promise<boolean> {
  if (!conversationId) return false;
  try {
    const res = await fetch(withPreviewToken(API.deleteConversation), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: conversationId, user_id: userId }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/* ───────────────────────────── Job library / report / matching ───────────── */

export interface JobsQuery {
  query?: string;
  city?: string;
  skill?: string;
}

export async function fetchJobs(params: JobsQuery = {}): Promise<Job[]> {
  try {
    const res = await fetch(withPreviewToken(API.jobs), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) return [];
    const data = await res.json().catch(() => null) as { jobs?: Job[] } | null;
    return Array.isArray(data?.jobs) ? data.jobs : [];
  } catch {
    return [];
  }
}

export async function fetchReport(): Promise<MarketReport | null> {
  try {
    const res = await fetch(withPreviewToken(API.report), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    if (!res.ok) return null;
    return (await res.json().catch(() => null)) as MarketReport | null;
  } catch {
    return null;
  }
}

export async function fetchMatch(resume: string, jdId: string): Promise<MatchResponse | null> {
  try {
    const res = await fetch(withPreviewToken(API.match), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume, jdId }),
    });
    if (!res.ok) return null;
    return (await res.json().catch(() => null)) as MatchResponse | null;
  } catch {
    return null;
  }
}

export async function fetchMatchRank(resume: string): Promise<MatchResponse | null> {
  try {
    const res = await fetch(withPreviewToken(API.matchRank), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume }),
    });
    if (!res.ok) return null;
    return (await res.json().catch(() => null)) as MatchResponse | null;
  } catch {
    return null;
  }
}

export type { InterviewMode };
