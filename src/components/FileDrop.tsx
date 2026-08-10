import { useCallback, useRef, useState } from 'react';
import styles from './FileDrop.module.css';

interface FileDropProps {
  onText: (text: string, fileName: string) => void;
  textLabel: string;
  hint?: string;
  parseErrorText: (name: string) => string;
  parsingText: (name: string) => string;
  compact?: boolean;
}

// Configure pdf.js worker once at module load (Vite resolves the URL).
let pdfjsReady = false;
async function ensurePdfJs() {
  if (pdfjsReady) return;
  const pdfjsLib = await import('pdfjs-dist');
  // @ts-ignore workerSrc is a string URL
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
  ).toString();
  pdfjsReady = true;
}

async function parsePdf(file: File): Promise<string> {
  await ensurePdfJs();
  const pdfjsLib = await import('pdfjs-dist');
  const buf = await file.arrayBuffer();
  const doc = await pdfjsLib.getDocument({ data: buf }).promise;
  let text = '';
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    // @ts-ignore items are heterogeneous text marks
    text += content.items.map((it) => ('str' in it ? it.str : '')).join(' ') + '\n';
  }
  return text.trim();
}

export default function FileDrop({
  onText,
  textLabel,
  hint,
  parseErrorText,
  parsingText,
  compact,
}: FileDropProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      const lower = file.name.toLowerCase();
      try {
        if (lower.endsWith('.pdf')) {
          setBusy(parsingText(file.name));
          const text = await parsePdf(file);
          if (!text) throw new Error('empty');
          onText(text, file.name);
        } else if (lower.endsWith('.txt') || lower.endsWith('.md')) {
          setBusy(parsingText(file.name));
          const text = await file.text();
          onText(text, file.name);
        } else {
          setError(parseErrorText(file.name));
          return;
        }
      } catch {
        setError(parseErrorText(file.name));
      } finally {
        setBusy(null);
      }
    },
    [onText, parseErrorText, parsingText],
  );

  return (
    <div className={`${styles.wrap} ${compact ? styles.compact : ''}`}>
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.md,.pdf"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void handleFile(f);
          e.target.value = '';
        }}
      />
      <button
        type="button"
        className={styles.button}
        onClick={() => inputRef.current?.click()}
        disabled={Boolean(busy)}
      >
        ⬆ {textLabel}
      </button>
      {hint && <span className={styles.hint}>{hint}</span>}
      {busy && <span className={styles.busy}>{busy}</span>}
      {error && <span className={styles.error}>{error}</span>}
    </div>
  );
}
