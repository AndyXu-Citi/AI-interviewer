import type { InterviewMode } from '../types';
import type { MessageKeys } from '../i18n';
import FileDrop from './FileDrop';
import styles from './InterviewSetup.module.css';

export interface InterviewSetupData {
  mode: InterviewMode;
  material: string;
  jdId?: string;
}

interface InterviewSetupProps {
  value: InterviewSetupData;
  onChange: (v: InterviewSetupData) => void;
  onStart: () => void;
  jdOptions: { id: string; label: string }[];
  jdOptionsLoading: boolean;
  t: (k: MessageKeys) => string;
}

const MODES: InterviewMode[] = ['resume', 'project', 'knowledge', 'jd'];

export default function InterviewSetup({
  value,
  onChange,
  onStart,
  jdOptions,
  jdOptionsLoading,
  t,
}: InterviewSetupProps) {
  const set = (patch: Partial<InterviewSetupData>) => onChange({ ...value, ...patch });

  const materialPlaceholder =
    value.mode === 'knowledge'
      ? t('interview.knowledgePlaceholder')
      : t('interview.materialPlaceholder');

  return (
    <div className={styles.panel}>
      <div className={styles.head}>
        <span className={styles.title}>{t('interview.setupTitle')}</span>
        <span className={styles.hint}>{t('interview.setupHint')}</span>
      </div>

      <div className={styles.modes}>
        {MODES.map((m) => (
          <button
            key={m}
            type="button"
            className={`${styles.modeBtn} ${value.mode === m ? styles.modeActive : ''}`}
            onClick={() => set({ mode: m, ...(m !== 'jd' ? { jdId: undefined } : {}) })}
          >
            {t(`interview.mode.${m}` as MessageKeys)}
          </button>
        ))}
      </div>

      {value.mode === 'jd' ? (
        <div className={styles.field}>
          <label className={styles.label}>{t('interview.jdSelectLabel')}</label>
          <select
            className={styles.select}
            value={value.jdId ?? ''}
            onChange={(e) => set({ jdId: e.target.value || undefined })}
            disabled={jdOptionsLoading}
          >
            <option value="">{jdOptionsLoading ? t('jobs.loading') : t('interview.jdSelectPlaceholder')}</option>
            {jdOptions.map((o) => (
              <option key={o.id} value={o.id}>{o.label}</option>
            ))}
          </select>
        </div>
      ) : (
        <div className={styles.field}>
          <label className={styles.label}>{t('interview.materialPlaceholder')}</label>
          <textarea
            className={styles.textarea}
            value={value.material}
            placeholder={materialPlaceholder}
            onChange={(e) => set({ material: e.target.value })}
            rows={5}
          />
          <FileDrop
            textLabel={t('interview.uploadLabel')}
            hint={t('interview.uploadHint')}
            parseErrorText={(n) => t('upload.parseError').replace('{name}', n)}
            parsingText={(n) => t('upload.parsing').replace('{name}', n)}
            onText={(text) => set({ material: text })}
          />
        </div>
      )}

      <button type="button" className={styles.start} onClick={onStart}>
        {t('interview.startBtn')}
      </button>
    </div>
  );
}
