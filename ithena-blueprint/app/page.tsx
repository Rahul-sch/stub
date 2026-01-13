import Link from 'next/link';
import { BookOpen, Code2, Map, HelpCircle, Zap, ArrowRight } from 'lucide-react';

const modes = [
  {
    id: 'wiki',
    label: 'First Principles Wiki',
    description: 'Deep-dive documentation with ELI5 callouts, diagrams, and glossary terms. Master concepts before code.',
    icon: BookOpen,
    href: '/wiki',
    color: 'purple',
    stats: ['15+ articles', '6 categories', 'Beginner friendly'],
  },
  {
    id: 'xray',
    label: 'Code X-Ray',
    description: 'Line-by-line commentary synced to actual source code. Hover to highlight, click to navigate.',
    icon: Code2,
    href: '/xray',
    color: 'cyan',
    stats: ['consumer.py', 'combined_pipeline.py', '18+ sections'],
  },
  {
    id: 'map',
    label: 'System Map',
    description: 'Interactive node graph showing data flow from sensors to 3D twin. Click nodes for deep dives.',
    icon: Map,
    href: '/map',
    color: 'orange',
    stats: ['6 nodes', 'Live data flow', 'Cross-linked'],
  },
  {
    id: 'faq',
    label: 'Warlord FAQ',
    description: 'High-stakes Q&A for interviews and troubleshooting. Searchable, tagged, battle-tested.',
    icon: HelpCircle,
    href: '/faq',
    color: 'green',
    stats: ['Critical topics', 'Searchable', 'Tagged'],
  },
];

export default function Home() {
  return (
    <div className="min-h-screen p-8">
      {/* Hero Section */}
      <section className="max-w-4xl mx-auto mb-16">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--accent-cyan)] to-[var(--accent-purple)] flex items-center justify-center shadow-lg">
            <Zap className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-4xl font-bold text-gradient">Ithena: The Blueprint</h1>
          </div>
        </div>
        <p className="text-xl text-[var(--foreground-muted)] max-w-2xl mb-6">
          Interactive Learning OS for mastering the <span className="text-[var(--accent-cyan)]">Rig Alpha</span> industrial IoT system.
          From concepts to line-by-line code, 0% → 100% mastery.
        </p>
        <div className="flex flex-wrap gap-4 text-sm text-[var(--foreground-muted)]">
          <span className="px-3 py-1 rounded-full bg-[var(--background-secondary)] border border-[var(--background-tertiary)]">
            50 Sensor Parameters
          </span>
          <span className="px-3 py-1 rounded-full bg-[var(--background-secondary)] border border-[var(--background-tertiary)]">
            Hybrid ML Detection
          </span>
          <span className="px-3 py-1 rounded-full bg-[var(--background-secondary)] border border-[var(--background-tertiary)]">
            Real-time 3D Twin
          </span>
          <span className="px-3 py-1 rounded-full bg-[var(--background-secondary)] border border-[var(--background-tertiary)]">
            Production-Grade
          </span>
        </div>
      </section>

      {/* Mode Cards */}
      <section className="max-w-4xl mx-auto">
        <h2 className="text-2xl font-semibold mb-6">Choose Your Learning Mode</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {modes.map((mode) => {
            const Icon = mode.icon;
            return (
              <Link
                key={mode.id}
                href={mode.href}
                className={`mode-card mode-card-${mode.id} group`}
              >
                <div className="flex items-start gap-4">
                  <div
                    className="w-12 h-12 rounded-lg flex items-center justify-center shrink-0"
                    style={{
                      background: `rgba(var(--accent-${mode.color}-rgb, 59, 130, 246), 0.15)`,
                    }}
                  >
                    <Icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                      {mode.label}
                      <ArrowRight className="w-4 h-4 opacity-0 -translate-x-2 transition-all group-hover:opacity-100 group-hover:translate-x-0" />
                    </h3>
                    <p className="text-sm text-[var(--foreground-muted)] mb-4">
                      {mode.description}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {mode.stats.map((stat, i) => (
                        <span
                          key={i}
                          className="text-xs px-2 py-1 rounded bg-[var(--background-tertiary)] text-[var(--foreground-muted)]"
                        >
                          {stat}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Quick Start */}
      <section className="max-w-4xl mx-auto mt-16">
        <h2 className="text-2xl font-semibold mb-6">Quick Start Path</h2>
        <div className="flex flex-col md:flex-row items-stretch gap-4">
          <Link
            href="/wiki/data-flow-overview"
            className="flex-1 p-6 bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg hover:border-[var(--accent-blue)] transition-colors group"
          >
            <span className="text-2xl font-bold text-[var(--accent-blue)]">1</span>
            <h3 className="font-medium mt-2 mb-1">Understand the Flow</h3>
            <p className="text-sm text-[var(--foreground-muted)]">
              Read the Data Flow Overview in the Wiki to understand the architecture.
            </p>
          </Link>
          <Link
            href="/xray/consumer.py"
            className="flex-1 p-6 bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg hover:border-[var(--accent-cyan)] transition-colors group"
          >
            <span className="text-2xl font-bold text-[var(--accent-cyan)]">2</span>
            <h3 className="font-medium mt-2 mb-1">Dive Into Code</h3>
            <p className="text-sm text-[var(--foreground-muted)]">
              Use Code X-Ray on consumer.py to see exactly how messages flow.
            </p>
          </Link>
          <Link
            href="/map"
            className="flex-1 p-6 bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg hover:border-[var(--accent-orange)] transition-colors group"
          >
            <span className="text-2xl font-bold text-[var(--accent-orange)]">3</span>
            <h3 className="font-medium mt-2 mb-1">See the Big Picture</h3>
            <p className="text-sm text-[var(--foreground-muted)]">
              Explore the System Map to visualize how components connect.
            </p>
          </Link>
        </div>
      </section>
    </div>
  );
}
