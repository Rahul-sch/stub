import { HelpCircle } from 'lucide-react';

export default function FAQPage() {
  return (
    <div className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-[var(--accent-green)]/20 flex items-center justify-center">
            <HelpCircle className="w-6 h-6 text-[var(--accent-green)]" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Warlord FAQ</h1>
            <p className="text-[var(--foreground-muted)]">High-stakes Q&A for interviews and troubleshooting</p>
          </div>
        </div>

        <div className="bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg p-8 text-center">
          <h2 className="text-xl font-semibold mb-2">Coming Soon</h2>
          <p className="text-[var(--foreground-muted)]">
            Searchable, tagged Q&A covering critical topics from system design to troubleshooting.
          </p>
        </div>
      </div>
    </div>
  );
}
