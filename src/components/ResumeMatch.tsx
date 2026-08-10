import { useEffect, useState } from 'react';
import type { Job, MatchResponse, MatchRow } from '../types';
import { fetchJobs, fetchMatch, fetchMatchRank } from '../api';
import { useT } from '../i18n';
import FileDrop from './FileDrop';
import styles from './ResumeMatch.module.css';

interface Props {
  onUseJd: (job: Job) => void;
}

function scoreClass(score: number): string {
  if (score >= 70) return styles.scoreHigh;
  if (score >= 40) return styles.scoreMid;
  return styles.scoreLow;
}

export default function ResumeMatch({ onUseJd }: Props) {
  const { t } = useT();
  const [resume, setResume] = useState('');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jdId, setJdId] = useState('');
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchJobs({}).then(setJobs); }, []);

  const runMatch = async (all: boolean) => {
    if (!resume.trim()) { window.alert(t('match.missingResume')); return; }
    setLoading(true);
    const res = all ? await fetchMatchRank(resume) : await fetchMatch(resume, jdId);
    setResult(res);
    setLoading(false);
  };

  const rows: MatchRow[] = result?.mode === 'rank' ? (result.ranked ?? []) : result?.job ? [result.job] : [];

  return (
    <div className={styles.wrap}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t('match.title')}</h1>
        <p className={styles.subtitle}>{t('match.subtitle')}</p>
      </header>

      <section className={styles.inputCard}>
        <label className={styles.label}>{t('match.resumeLabel')}</label>
        <textarea
          className={styles.textarea}
          placeholder={t('match.resumePlaceholder')}
          value={resume}
          onChange={(e) => setResume(e.target.value)}
          rows={7}
        />
        <FileDrop
          textLabel={t('match.uploadLabel')}
          hint={t('match.uploadHint')}
          parseErrorText={(n) => t('upload.parseError').replace('{name}', n)}
          parsingText={(n) => t('upload.parsing').replace('{name}', n)}
          onText={(text) => setResume(text)}
        />
      </section>

      <section className={styles.controls}>
        <div className={styles.jdSelect}>
          <label className={styles.label}>{t('match.selectJdLabel')}</label>
          <select className={styles.select} value={jdId} onChange={(e) => setJdId(e.target.value)}>
            <option value="">{t('match.selectJdPlaceholder')}</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>{j.title} @ {j.company}</option>
            ))}
          </select>
        </div>
        <div className={styles.btns}>
          <button className={styles.primary} onClick={() => runMatch(false)} disabled={loading}>
            {t('match.matchBtn')}
          </button>
          <button className={styles.ghost} onClick={() => runMatch(true)} disabled={loading}>
            {t('match.allJobsBtn')}
          </button>
        </div>
      </section>

      {loading && <p className={styles.muted}>{t('match.loading')}</p>}
      {!loading && result && (
        <section className={styles.results}>
          <h2 className={styles.resultsTitle}>
            {result.mode === 'rank' ? t('match.rankTitle') : t('match.scoreTitle')}
          </h2>
          {rows.length === 0 && <p className={styles.muted}>{t('common.noData')}</p>}
          {rows.map((r) => (
            <div key={r.id} className={styles.row}>
              <div className={styles.rowHead}>
                <div>
                  <h3 className={styles.rowTitle}>{r.title}</h3>
                  <p className={styles.rowMeta}>{r.company}{r.city ? ` · ${r.city}` : ''} · {r.salary}</p>
                </div>
                <div className={`${styles.score} ${scoreClass(r.score)}`}>{r.score}</div>
              </div>
              <p className={styles.reason}>{r.reason}</p>
              <button className={styles.useBtn} onClick={() => onUseJd(r)}>{t('match.useForInterview')}</button>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
