import { useEffect, useState } from 'react';
import type { MarketReport } from '../types';
import { fetchReport } from '../api';
import { useT } from '../i18n';
import styles from './SkillReport.module.css';

function Bar({ label, value, max, suffix }: { label: string; value: number; max: number; suffix?: string }) {
  const pct = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0;
  return (
    <div className={styles.barRow}>
      <span className={styles.barLabel}>{label}</span>
      <div className={styles.barTrack}>
        <div className={styles.barFill} style={{ width: `${pct}%` }} />
      </div>
      <span className={styles.barValue}>{value}{suffix ?? ''}</span>
    </div>
  );
}

export default function SkillReport() {
  const { t } = useT();
  const [report, setReport] = useState<MarketReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReport().then((r) => { setReport(r); setLoading(false); });
  }, []);

  if (loading) return <div className={styles.wrap}><p className={styles.muted}>{t('common.loading')}</p></div>;
  if (!report || report.total === 0) return <div className={styles.wrap}><p className={styles.muted}>{t('report.noData')}</p></div>;

  const maxSkill = report.top_skills[0]?.[1] || 1;

  return (
    <div className={styles.wrap}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t('report.title')}</h1>
        <p className={styles.subtitle}>{t('report.subtitle')}</p>
      </header>

      <div className={styles.statRow}>
        <div className={styles.statCard}>
          <span className={styles.statNum}>{report.total}</span>
          <span className={styles.statLabel}>{t('report.total')}</span>
        </div>
        {report.salary_avg_k != null && (
          <div className={styles.statCard}>
            <span className={styles.statNum}>{report.salary_avg_k}K</span>
            <span className={styles.statLabel}>{t('report.salaryAvg')}</span>
          </div>
        )}
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>{t('report.topSkills')}</h2>
        <div className={styles.bars}>
          {report.top_skills.map(([k, v]) => (
            <Bar key={k} label={k} value={v} max={maxSkill} />
          ))}
        </div>
      </section>

      <div className={styles.grid2}>
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{t('report.cities')}</h2>
          <div className={styles.bars}>
            {report.cities.map(([k, v]) => (
              <Bar key={k} label={k} value={v} max={report.cities[0]?.[1] || 1} />
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{t('report.education')}</h2>
          <div className={styles.bars}>
            {report.education.map(([k, v]) => (
              <Bar key={k} label={k} value={v} max={report.education[0]?.[1] || 1} />
            ))}
          </div>
        </section>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>{t('report.experience')}</h2>
        <div className={styles.bars}>
          {report.experience.map(([k, v]) => (
            <Bar key={k} label={k} value={v} max={report.experience[0]?.[1] || 1} />
          ))}
        </div>
      </section>
    </div>
  );
}
