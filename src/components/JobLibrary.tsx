import { useEffect, useMemo, useState } from 'react';
import type { Job } from '../types';
import { fetchJobs } from '../api';
import { useT } from '../i18n';
import styles from './JobLibrary.module.css';

interface Props {
  onUseJd: (job: Job) => void;
}

export default function JobLibrary({ onUseJd }: Props) {
  const { t } = useT();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [skill, setSkill] = useState('');
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    fetchJobs({}).then((j) => { setJobs(j); setLoading(false); });
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const s = skill.trim().toLowerCase();
    return jobs.filter((j) => {
      if (q) {
        const hay = `${j.title} ${j.company} ${(j.skills || []).join(' ')} ${j.description || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (s && !(j.skills || []).some((x) => x.toLowerCase().includes(s))) return false;
      return true;
    });
  }, [jobs, query, skill]);

  return (
    <div className={styles.wrap}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>{t('jobs.title')}</h1>
          <p className={styles.subtitle}>{t('jobs.subtitle')}</p>
        </div>
        <div className={styles.filters}>
          <input
            className={styles.search}
            placeholder={t('jobs.searchPlaceholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <input
            className={styles.search}
            placeholder={t('jobs.filterSkill')}
            value={skill}
            onChange={(e) => setSkill(e.target.value)}
          />
        </div>
      </header>

      {loading ? (
        <p className={styles.loading}>{t('jobs.loading')}</p>
      ) : filtered.length === 0 ? (
        <p className={styles.empty}>{t('jobs.empty')}</p>
      ) : (
        <>
          <p className={styles.count}>{t('jobs.resultCount').replace('{n}', String(filtered.length))}</p>
          <div className={styles.grid}>
            {filtered.map((j) => (
              <div key={j.id} className={styles.card}>
                <div className={styles.cardTop}>
                  <h3 className={styles.jobTitle}>{j.title}</h3>
                  <span className={styles.salary}>{j.salary}</span>
                </div>
                <p className={styles.company}>{j.company}{j.city ? ` · ${j.city}` : ''}</p>
                <div className={styles.tags}>
                  {(j.skills || []).slice(0, 6).map((s) => (
                    <span key={s} className={styles.tag}>{s}</span>
                  ))}
                </div>
                {openId === j.id && j.description && (
                  <p className={styles.desc}>{j.description}</p>
                )}
                <div className={styles.actions}>
                  <button className={styles.ghost} onClick={() => setOpenId(openId === j.id ? null : j.id)}>
                    {openId === j.id ? t('jobs.detailClose') : t('jobs.viewDetail')}
                  </button>
                  <button className={styles.primary} onClick={() => onUseJd(j)}>
                    {t('jobs.useForInterview')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
