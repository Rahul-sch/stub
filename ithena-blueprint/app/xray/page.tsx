import Link from 'next/link';
import { Code2, FileCode, ArrowRight } from 'lucide-react';

const xrayFiles = [
  {
    name: 'consumer.py',
    path: 'consumer.py',
    description: 'Main Kafka consumer with message processing pipeline, database persistence, and ML detection integration.',
    sections: 18,
    lines: 589,
    tags: ['Kafka', 'PostgreSQL', 'ML', 'Core'],
  },
  {
    name: 'combined_pipeline.py',
    path: 'combined_pipeline.py',
    description: 'Hybrid ML anomaly detection orchestrator combining Isolation Forest and LSTM Autoencoder.',
    sections: 12,
    lines: 310,
    tags: ['ML', 'Detection', 'Hybrid'],
    coming: true,
  },
  {
    name: 'config.py',
    path: 'config.py',
    description: 'Central configuration for Kafka, database, sensor ranges, and ML parameters.',
    sections: 8,
    lines: 480,
    tags: ['Config', 'Settings'],
    coming: true,
  },
];

export default function XRayIndex() {
  return (
    <div className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-[var(--accent-cyan)]/20 flex items-center justify-center">
            <Code2 className="w-6 h-6 text-[var(--accent-cyan)]" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Code X-Ray</h1>
            <p className="text-[var(--foreground-muted)]">Line-by-line commentary synced to source code</p>
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg p-6 mb-8">
          <h2 className="font-semibold mb-2">How to Use Code X-Ray</h2>
          <ul className="text-sm text-[var(--foreground-muted)] space-y-1">
            <li>• <strong>Hover</strong> over code lines to highlight the corresponding commentary</li>
            <li>• <strong>Hover</strong> over commentary cards to highlight the relevant code section</li>
            <li>• <strong>Click</strong> a commentary card to scroll the code to that section</li>
            <li>• <strong>Click</strong> a code line to scroll the commentary to its explanation</li>
            <li>• <strong>Expand</strong> commentary cards to see failure modes, tests, and related docs</li>
          </ul>
        </div>

        {/* File Grid */}
        <h2 className="text-xl font-semibold mb-4">Available Files</h2>
        <div className="space-y-4">
          {xrayFiles.map((file) => (
            <Link
              key={file.path}
              href={file.coming ? '#' : `/xray/${file.path}`}
              className={`block bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg p-6 transition-all ${
                file.coming
                  ? 'opacity-60 cursor-not-allowed'
                  : 'hover:border-[var(--accent-cyan)] hover:shadow-[0_0_20px_rgba(6,182,212,0.2)]'
              } group`}
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-lg bg-[var(--code-bg)] flex items-center justify-center shrink-0">
                  <FileCode className="w-6 h-6 text-[var(--accent-cyan)]" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-mono font-semibold text-[var(--accent-cyan)]">{file.name}</h3>
                    {file.coming && (
                      <span className="text-xs px-2 py-0.5 rounded bg-[var(--background-tertiary)] text-[var(--foreground-muted)]">
                        Coming Soon
                      </span>
                    )}
                    {!file.coming && (
                      <ArrowRight className="w-4 h-4 opacity-0 -translate-x-2 transition-all group-hover:opacity-100 group-hover:translate-x-0 text-[var(--accent-cyan)]" />
                    )}
                  </div>
                  <p className="text-sm text-[var(--foreground-muted)] mb-3">{file.description}</p>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-xs text-[var(--foreground-muted)]">
                      {file.sections} sections • {file.lines} lines
                    </span>
                    <div className="flex gap-1">
                      {file.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-xs px-2 py-0.5 rounded bg-[var(--background-tertiary)] text-[var(--foreground-muted)]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
