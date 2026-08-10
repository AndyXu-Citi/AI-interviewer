import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import type { Message, ToolLampState, ConversationSummary } from '../types';
import {
  fetchConversationHistory,
  streamMessage,
  stopAgent,
  listConversations,
  deleteConversation,
  fetchJobs,
} from '../api';
import type { RawSseEvent } from '../api';
import ToolIndicators from './ToolIndicators';
import ChatWindow from './ChatWindow';
import ChatInput from './ChatInput';
import DebugPanel from './DebugPanel';
import ConversationSidebar from './ConversationSidebar';
import InterviewSetup, { type InterviewSetupData } from './InterviewSetup';
import { useT } from '../i18n';
import type { MessageKeys } from '../i18n';
import { deleteSnapshot, loadSnapshot, saveSnapshot } from '../lib/chatUiStore';
import styles from '../App.module.css';

export interface LampDef {
  id: string;
  icon: string;
  i18nKey: MessageKeys;
}

export interface ChatViewProps {
  endpoint: string;
  stopEndpoint?: string;
  titleKey: MessageKeys;
  subtitleKey: MessageKeys;
  emptyKey: MessageKeys;
  presetKeys?: MessageKeys[];
  lamps: LampDef[];
  showSidebar?: boolean;
  persist?: boolean;
  storageKey: string;
  initialSetup?: InterviewSetupData | null;
}

const EO_USER_ID_KEY = 'eo-uuid';
const CONVERSATIONS_PAGE_SIZE = 20;
let _historyFetchInFlight = false;

function getOrCreateEoUuid(): string {
  const cached = localStorage.getItem(EO_USER_ID_KEY);
  if (cached) return cached;
  const id = crypto.randomUUID();
  localStorage.setItem(EO_USER_ID_KEY, id);
  return id;
}

export default function ChatView(props: ChatViewProps) {
  const { t } = useT();
  const persist = props.persist ?? false;

  const buildLamps = useCallback(
    (): ToolLampState[] =>
      props.lamps.map((l) => ({
        id: l.id,
        label: t(l.i18nKey),
        icon: l.icon,
        active: false,
        animKey: 0,
        i18nKey: l.i18nKey as string,
      })),
    [props.lamps, t],
  );

  const [messages, setMessages] = useState<Message[]>([]);
  const [lamps, setLamps] = useState<ToolLampState[]>(buildLamps);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(persist);
  const [debugEvents, setDebugEvents] = useState<RawSseEvent[]>([]);
  const [setup, setSetup] = useState<InterviewSetupData | null>(props.initialSetup ?? null);
  const [jdOptions, setJdOptions] = useState<{ id: string; label: string }[]>([]);
  const [jdLoading, setJdLoading] = useState(false);

  // persist-only state
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(persist);
  const [conversationsLoadingMore, setConversationsLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | undefined>(undefined);
  const [activeConversationId, setActiveConversationId] = useState<string>(() =>
    persist ? localStorage.getItem(props.storageKey) || crypto.randomUUID() : crypto.randomUUID(),
  );

  const botMsgIdRef = useRef<string>('');
  const abortCtrlRef = useRef<AbortController | null>(null);
  const hadExistingRef = useRef(persist && Boolean(localStorage.getItem(props.storageKey)));
  const conversationIdRef = useRef<string>(activeConversationId);
  const eoUuidRef = useRef<string>(getOrCreateEoUuid());
  const initDoneRef = useRef(!persist);
  const snapshotTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { conversationIdRef.current = activeConversationId; }, [activeConversationId]);

  useEffect(() => {
    setLamps((prev) => prev.map((l) => ({ ...l, label: t(l.i18nKey as MessageKeys) })));
  }, [t]);

  // Load JD options for the interview setup panel
  useEffect(() => {
    if (!props.showSidebar) return; // only the interview tab shows setup
    let alive = true;
    setJdLoading(true);
    fetchJobs({}).then((jobs) => {
      if (!alive) return;
      setJdOptions(jobs.map((j) => ({ id: j.id, label: `${j.title} @ ${j.company}` })));
      setJdLoading(false);
    });
    return () => { alive = false; };
  }, [props.showSidebar]);

  // Snapshot persistence (persist only)
  useEffect(() => {
    if (!persist || messages.length === 0 || !initDoneRef.current) return;
    if (snapshotTimerRef.current) clearTimeout(snapshotTimerRef.current);
    snapshotTimerRef.current = setTimeout(() => {
      saveSnapshot(conversationIdRef.current, messages).catch(() => {});
    }, 500);
    return () => { if (snapshotTimerRef.current) clearTimeout(snapshotTimerRef.current); };
  }, [messages, persist]);

  const loadConversation = useCallback(async (convId: string) => {
    setHistoryLoading(true);
    let restored = false;
    try {
      const snap = await loadSnapshot(convId).catch(() => [] as Message[]);
      if (snap.length > 0) { restored = true; setMessages(snap); setHistoryLoading(false); }
      const history = await fetchConversationHistory(convId, eoUuidRef.current);
      if (history.length > 0) {
        if (!restored || history.length > snap.length) setMessages(history);
        saveSnapshot(convId, history).catch(() => {});
      } else if (!restored) setMessages([]);
    } finally {
      setHistoryLoading(false);
      initDoneRef.current = true;
    }
  }, []);

  const refreshConversations = useCallback(async (mode: 'replace' | 'append', cursor?: string) => {
    if (!persist) return;
    if (mode === 'append') setConversationsLoadingMore(true); else setConversationsLoading(true);
    try {
      const res = await listConversations({ userId: eoUuidRef.current, limit: CONVERSATIONS_PAGE_SIZE, order: 'desc', after: cursor });
      setNextCursor(res.nextCursor);
      if (mode === 'append') {
        setConversations((prev) => {
          const seen = new Set(prev.map((c) => c.id));
          const merged = [...prev];
          for (const c of res.conversations) if (!seen.has(c.id)) merged.push(c);
          return merged;
        });
      } else setConversations(res.conversations);
    } finally {
      if (mode === 'append') setConversationsLoadingMore(false); else setConversationsLoading(false);
    }
  }, [persist]);

  useEffect(() => {
    if (!persist) return;
    if (_historyFetchInFlight) { void refreshConversations('replace'); return; }
    _historyFetchInFlight = true;
    if (!hadExistingRef.current) {
      setHistoryLoading(false); initDoneRef.current = true;
      void refreshConversations('replace').finally(() => { _historyFetchInFlight = false; });
      return;
    }
    void loadConversation(conversationIdRef.current).finally(() =>
      void refreshConversations('replace').finally(() => { _historyFetchInFlight = false; }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateBotMessage = useCallback((updater: (c: string) => string) => {
    setMessages((prev) => prev.map((m) => (m.id === botMsgIdRef.current ? { ...m, content: updater(m.content) } : m)));
  }, []);

  const clearBotStreaming = useCallback(() => {
    setMessages((prev) => {
      let changed = false;
      const next = prev.map((m) => {
        if (m.id === botMsgIdRef.current && m.streaming) { changed = true; const { streaming, ...rest } = m; return rest; }
        return m;
      });
      return changed ? next : prev;
    });
  }, []);

  const finishStream = useCallback(() => { setLoading(false); abortCtrlRef.current = null; }, []);

  const buildExtra = useCallback(
    (): Record<string, unknown> => (setup ? { mode: setup.mode, jdId: setup.jdId ?? '', material: setup.material } : {}),
    [setup],
  );

  const handleSend = useCallback(
    (text: string) => {
      initDoneRef.current = true;
      const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: text, timestamp: Date.now() };
      const botMsgId = crypto.randomUUID();
      botMsgIdRef.current = botMsgId;
      const botMsg: Message = { id: botMsgId, role: 'assistant', content: '', timestamp: Date.now(), streaming: true };
      setMessages((prev) => [...prev, userMsg, botMsg]);
      setLoading(true);

      let sidebarPrimed = false;
      const cleaned = text.replace(/\s+/g, ' ').trim();
      const optimisticTitle = cleaned.length === 0 ? 'New chat' : cleaned.length <= 8 ? cleaned : `${cleaned.slice(0, 8)}...`;
      const primeSidebar = () => {
        if (sidebarPrimed || !persist) return;
        sidebarPrimed = true;
        const convId = conversationIdRef.current;
        const now = Date.now();
        setConversations((prev) => {
          const idx = prev.findIndex((c) => c.id === convId);
          if (idx === -1) {
            return [{ id: convId, title: optimisticTitle, lastMessageAt: now, userId: eoUuidRef.current }, ...prev];
          }
          const next = [...prev]; const [m] = next.splice(idx, 1); next.unshift({ ...m, lastMessageAt: now });
          return next;
        });
      };

      const ctrl = streamMessage(
        props.endpoint,
        text,
        {
          onTextDelta: (d) => updateBotMessage((c) => c + d),
          onToolCalled: (toolName) => {
            setLamps((prev) => prev.map((l) => (l.id === toolName ? { ...l, active: true, animKey: l.animKey + 1 } : l)));
            setTimeout(() => setLamps((prev) => prev.map((l) => (l.id === toolName ? { ...l, active: false } : l))), 1000);
          },
          onRawEvent: (event) => {
            primeSidebar();
            if (event.eventType === 'text_delta') {
              const delta = (event.data as { delta?: string } | null)?.delta ?? '';
              setDebugEvents((prev) => {
                const last = prev[prev.length - 1];
                if (last && last.eventType === 'text_delta') {
                  const prevDelta = (last.data as { delta?: string } | null)?.delta ?? '';
                  const merged: RawSseEvent = { ...last, data: { delta: prevDelta + delta }, raw: last.raw + delta, timestamp: event.timestamp };
                  return [...prev.slice(0, -1), merged];
                }
                return [...prev, event];
              });
              return;
            }
            setDebugEvents((prev) => [...prev, event]);
          },
          onDone: () => { clearBotStreaming(); finishStream(); if (persist) void refreshConversations('replace'); },
          onError: () => { clearBotStreaming(); updateBotMessage((c) => c || t('status.error')); finishStream(); },
        },
        conversationIdRef.current,
        { userId: eoUuidRef.current, userMsgId: userMsg.id, botMsgId, extraBody: buildExtra() },
      );
      abortCtrlRef.current = ctrl;
    },
    [props.endpoint, updateBotMessage, clearBotStreaming, finishStream, refreshConversations, persist, t, buildExtra],
  );

  const handleStartInterview = useCallback(() => {
    if (!setup) return;
    handleSend('开始面试：请基于上方设置，对我提出第一个问题。');
  }, [setup, handleSend]);

  const handleStop = useCallback(() => {
    if (abortCtrlRef.current) { abortCtrlRef.current.abort(); abortCtrlRef.current = null; }
    updateBotMessage((c) => (c ? c + '\n\n' + t('status.stopped') : t('status.stopped')));
    setLoading(false);
    if (props.stopEndpoint) {
      stopAgent(props.stopEndpoint, conversationIdRef.current).then((ok) => {
        if (!ok) updateBotMessage((c) => c + '\n\n' + t('status.backendError'));
      });
    }
  }, [updateBotMessage, t, props.stopEndpoint]);

  const handleClearLocal = useCallback(() => {
    setMessages([]);
    setDebugEvents([]);
  }, []);

  const handleSelectConversation = useCallback((id: string) => {
    if (loading || id === conversationIdRef.current) return;
    localStorage.setItem(props.storageKey, id);
    conversationIdRef.current = id;
    setActiveConversationId(id);
    setDebugEvents([]);
    void loadConversation(id);
  }, [loading, loadConversation, props.storageKey]);

  const handleNewChat = useCallback(() => {
    if (loading) return;
    const newId = crypto.randomUUID();
    localStorage.setItem(props.storageKey, newId);
    conversationIdRef.current = newId;
    setActiveConversationId(newId);
    setMessages([]); setDebugEvents([]); initDoneRef.current = false; setHistoryLoading(false);
  }, [loading, props.storageKey]);

  const handleLoadMore = useCallback(() => {
    if (!nextCursor || conversationsLoadingMore) return;
    void refreshConversations('append', nextCursor);
  }, [nextCursor, conversationsLoadingMore, refreshConversations]);

  const handleDeleteConversation = useCallback((id: string) => {
    if (loading) return;
    if (!window.confirm(t('sidebar.deleteConfirm'))) return;
    const isActive = id === conversationIdRef.current;
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (isActive) handleNewChat();
    void deleteSnapshot(id).catch(() => {});
    void deleteConversation(id, eoUuidRef.current).catch(() => {});
  }, [loading, t, handleNewChat]);

  const sidebarHasMore = useMemo(() => Boolean(nextCursor), [nextCursor]);

  return (
    <div className={styles.stage}>
      {persist && (
        <ConversationSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          loading={conversationsLoading}
          loadingMore={conversationsLoadingMore}
          hasMore={sidebarHasMore}
          disabled={loading}
          onSelect={handleSelectConversation}
          onCreate={handleNewChat}
          onLoadMore={handleLoadMore}
          onDelete={handleDeleteConversation}
        />
      )}

      <div className={styles.chatPanel}>
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.logo}>⬡</span>
            <div>
              <p className={styles.title}>{t(props.titleKey)}</p>
              <p className={styles.subtitle}>{t(props.subtitleKey)}</p>
            </div>
          </div>
          <ToolIndicators lamps={lamps} />
        </header>

        {props.showSidebar && (
          <InterviewSetup
            value={setup ?? { mode: 'project', material: '' }}
            onChange={setSetup}
            onStart={handleStartInterview}
            jdOptions={jdOptions}
            jdOptionsLoading={jdLoading}
            t={t}
          />
        )}

        <div className={styles.chatWindowShell}>
          <ChatWindow messages={messages} loading={loading} titleKey={props.titleKey} emptyHintKey={props.emptyKey} />
          {historyLoading && messages.length === 0 && (
            <div className={styles.historyOverlay}>
              <div className={styles.historySpinner} />
            </div>
          )}
        </div>
        <ChatInput onSend={handleSend} onStop={handleStop} disabled={loading} presetKeys={props.presetKeys} onClear={handleClearLocal} />
      </div>

      <div className={styles.codePanel}>
        <DebugPanel events={debugEvents} onClear={() => setDebugEvents([])} />
      </div>
    </div>
  );
}
