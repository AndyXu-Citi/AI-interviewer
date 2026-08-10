import { useState, useCallback } from 'react';
import type { Job } from './types';
import type { MessageKeys } from './i18n';
import { I18nProvider, LangToggle, useT } from './i18n';
import { ThemeToggle, initTheme } from './components/ThemeToggle';
import ChatView, { type LampDef } from './components/ChatView';
import JobLibrary from './components/JobLibrary';
import SkillReport from './components/SkillReport';
import ResumeMatch from './components/ResumeMatch';
import GitHubLink from './components/GitHubLink';
import DeployLink from './components/DeployLink';
import type { InterviewSetupData } from './components/InterviewSetup';
import styles from './App.module.css';

initTheme();

type TabKey = 'jobAgent' | 'jobs' | 'report' | 'match' | 'interview';

const TABS: { key: TabKey; i18nKey: MessageKeys }[] = [
  { key: 'jobAgent', i18nKey: 'tabs.jobAgent' },
  { key: 'jobs', i18nKey: 'tabs.jobs' },
  { key: 'report', i18nKey: 'tabs.report' },
  { key: 'match', i18nKey: 'tabs.match' },
  { key: 'interview', i18nKey: 'tabs.interview' },
];

const INTERVIEWER_LAMPS: LampDef[] = [
  { id: 'lookup_weakness', icon: '🔍', i18nKey: 'tool.weakness' },
  { id: 'get_followup_chain', icon: '⛓️', i18nKey: 'tool.followup' },
  { id: 'search_knowledge', icon: '📚', i18nKey: 'tool.knowledge' },
  { id: 'get_jd', icon: '📋', i18nKey: 'tool.jd' },
];

const JOB_AGENT_LAMPS: LampDef[] = [
  { id: 'search_jobs_tool', icon: '🔎', i18nKey: 'tool.knowledge' },
  { id: 'market_report_tool', icon: '📊', i18nKey: 'tool.statistics' },
];

export default function App() {
  return (
    <I18nProvider>
      <LangToggle />
      <ThemeToggle />
      <AppInner />
    </I18nProvider>
  );
}

function AppInner() {
  const { t } = useT();
  const [tab, setTab] = useState<TabKey>('jobAgent');
  const [pendingSetup, setPendingSetup] = useState<InterviewSetupData | null>(null);

  const handleUseJd = useCallback((job: Job) => {
    setPendingSetup({ mode: 'jd', jdId: job.id, material: '' });
    setTab('interview');
  }, []);

  return (
    <div className={styles.appShell}>
      <div className={styles.blob1} />
      <div className={styles.blob2} />

      <div className={styles.tabBar}>
        <div className={styles.brand}>
          <span className={styles.brandLogo}>🔥</span>
          <span className={styles.brandName}>{t('app.title')}</span>
        </div>
        <nav className={styles.tabs}>
          {TABS.map((tb) => (
            <button
              key={tb.key}
              className={`${styles.tab} ${tab === tb.key ? styles.tabActive : ''}`}
              onClick={() => setTab(tb.key)}
            >
              {t(tb.i18nKey)}
            </button>
          ))}
        </nav>
      </div>

      <main className={styles.tabContent}>
        <div className={`${styles.tabPane} ${tab === 'jobAgent' ? '' : styles.tabPaneHidden}`}>
          <ChatView
            endpoint="/job-agent"
            titleKey="jobAgent.title"
            subtitleKey="jobAgent.subtitle"
            emptyKey="jobAgent.empty"
            presetKeys={['preset.1', 'preset.2']}
            lamps={JOB_AGENT_LAMPS}
            storageKey="eo_jobagent_cid"
          />
        </div>

        <div className={`${styles.tabPane} ${tab === 'jobs' ? '' : styles.tabPaneHidden}`}>
          <JobLibrary onUseJd={handleUseJd} />
        </div>

        <div className={`${styles.tabPane} ${tab === 'report' ? '' : styles.tabPaneHidden}`}>
          <SkillReport />
        </div>

        <div className={`${styles.tabPane} ${tab === 'match' ? '' : styles.tabPaneHidden}`}>
          <ResumeMatch onUseJd={handleUseJd} />
        </div>

        <div className={`${styles.tabPane} ${tab === 'interview' ? '' : styles.tabPaneHidden}`}>
          <ChatView
            endpoint="/chat"
            stopEndpoint="/chat/stop"
            titleKey="interview.title"
            subtitleKey="interview.subtitle"
            emptyKey="interview.subtitle"
            lamps={INTERVIEWER_LAMPS}
            showSidebar
            persist
            storageKey="eo_interview_cid"
            initialSetup={pendingSetup}
          />
        </div>
      </main>

      <GitHubLink />
      <DeployLink />
    </div>
  );
}
