export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  streaming?: boolean;
}

export interface ToolLampState {
  id: string;
  label: string;
  icon: string;
  active: boolean;
  animKey: number;
  i18nKey?: string;
}

/** Lightweight conversation summary returned by /conversations. */
export interface ConversationSummary {
  id: string;
  title: string;
  preview?: string;
  lastMessageAt?: number;
  createdAt?: number;
  userId?: string;
  messageCount?: number;
}

export interface ListConversationsParams {
  userId: string;
  limit?: number;
  order?: 'asc' | 'desc';
  after?: string;
  before?: string;
}

export interface ListConversationsResponse {
  conversations: ConversationSummary[];
  nextCursor?: string;
  previousCursor?: string;
}

/* ───────────────────── Job library / market / matching ───────────────────── */

export type InterviewMode = 'resume' | 'project' | 'knowledge' | 'jd';

export interface Job {
  id: string;
  title: string;
  company: string;
  salary: string;
  city?: string;
  district?: string;
  experience?: string;
  education?: string;
  skills: string[];
  description?: string;
  source?: string;
  crawled_at?: string;
}

export interface MarketReport {
  total: number;
  top_skills: [string, number][];
  cities: [string, number][];
  education: [string, number][];
  experience: [string, number][];
  salary_avg_k?: number | null;
}

export interface MatchRow extends Job {
  score: number;
  reason: string;
}

export interface MatchResponse {
  mode: 'single' | 'rank';
  job?: MatchRow;
  ranked?: MatchRow[];
}
