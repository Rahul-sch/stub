import { BookOpen, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface WikiArticle {
  slug: string;
  title: string;
  description: string;
  readingTime: number;
  tags: string[];
}

interface WikiCategory {
  id: string;
  label: string;
  icon: string;
  articles: WikiArticle[];
}

const wikiCategories: WikiCategory[] = [
  {
    id: 'fundamentals',
    label: 'Fundamentals',
    icon: '🧭',
    articles: [
      {
        slug: 'data-flow-overview',
        title: 'Data Flow Overview',
        description:
          'End-to-end journey of sensor data from edge devices through Kafka to dashboard',
        readingTime: 8,
        tags: ['architecture', 'overview'],
      },
      {
        slug: 'exactly-once-semantics',
        title: 'Exactly-Once Semantics',
        description:
          'How Ithena guarantees no duplicate data with coordinated Kafka and database transactions',
        readingTime: 10,
        tags: ['kafka', 'reliability'],
      },
      {
        slug: 'graceful-shutdown',
        title: 'Graceful Shutdown Patterns',
        description:
          'Handling SIGINT/SIGTERM to prevent data loss and ensure clean consumer termination',
        readingTime: 6,
        tags: ['reliability', 'best-practices'],
      },
    ],
  },
  {
    id: 'kafka',
    label: 'Kafka & Streaming',
    icon: '🌊',
    articles: [
      {
        slug: 'kafka-deep-dive',
        title: 'Kafka Deep Dive',
        description:
          'Complete guide to Kafka architecture, topics, partitions, consumer groups, and offset management',
        readingTime: 15,
        tags: ['kafka', 'streaming', 'deep-dive'],
      },
      {
        slug: 'kafka-consumer-patterns',
        title: 'Consumer Patterns',
        description:
          'At-most-once, at-least-once, and exactly-once delivery patterns with code examples',
        readingTime: 12,
        tags: ['kafka', 'patterns'],
      },
      {
        slug: 'offset-management',
        title: 'Offset Management',
        description:
          'Auto-commit vs manual commit strategies and their impact on data integrity',
        readingTime: 10,
        tags: ['kafka', 'offsets'],
      },
    ],
  },
  {
    id: 'ml',
    label: 'ML & Detection',
    icon: '🤖',
    articles: [
      {
        slug: 'ml-detection',
        title: 'ML Detection Pipeline',
        description:
          'Hybrid anomaly detection combining rule-based checks with Isolation Forest and LSTM',
        readingTime: 14,
        tags: ['machine-learning', 'anomaly-detection'],
      },
      {
        slug: 'isolation-forest',
        title: 'Isolation Forest Explained',
        description:
          'How Isolation Forest detects outliers by randomly partitioning feature space',
        readingTime: 11,
        tags: ['machine-learning', 'isolation-forest'],
      },
      {
        slug: 'lstm-autoencoder',
        title: 'LSTM Autoencoder',
        description:
          'Sequence-to-sequence neural networks for detecting temporal anomalies in sensor data',
        readingTime: 13,
        tags: ['machine-learning', 'lstm', 'deep-learning'],
      },
      {
        slug: 'hybrid-strategies',
        title: 'Hybrid Detection Strategies',
        description:
          'Combining multiple detection methods to leverage strengths and minimize false positives',
        readingTime: 9,
        tags: ['machine-learning', 'strategy'],
      },
    ],
  },
  {
    id: 'database',
    label: 'Database & Persistence',
    icon: '💾',
    articles: [
      {
        slug: 'database-schema',
        title: 'Database Schema',
        description:
          'Complete schema breakdown: sensor_readings, anomaly_detections, alerts, audit_logs_v2',
        readingTime: 12,
        tags: ['database', 'schema', 'postgresql'],
      },
      {
        slug: 'neon-deployment',
        title: 'Neon Cloud Deployment',
        description:
          'Serverless PostgreSQL with instant branching, auto-scaling, and scale-to-zero',
        readingTime: 10,
        tags: ['database', 'neon', 'cloud'],
      },
      {
        slug: 'connection-pooling',
        title: 'Connection Pooling',
        description:
          'Managing database connections efficiently with psycopg2 and PgBouncer',
        readingTime: 8,
        tags: ['database', 'performance'],
      },
    ],
  },
];

export default function WikiIndex() {
  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-[var(--accent-purple)]/20 flex items-center justify-center">
              <BookOpen className="w-7 h-7 text-[var(--accent-purple)]" />
            </div>
            <div>
              <h1 className="text-4xl font-bold">First Principles Wiki</h1>
              <p className="text-[var(--foreground-muted)] mt-1">
                Deep-dive documentation with concepts before code
              </p>
            </div>
          </div>

          <div className="bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg p-6">
            <p className="text-[var(--foreground-muted)] leading-relaxed">
              Each article builds understanding from first principles using{' '}
              <span className="text-[var(--accent-cyan)]">ELI5 callouts</span>,{' '}
              <span className="text-[var(--accent-purple)]">Mermaid diagrams</span>, and{' '}
              <span className="text-[var(--accent-orange)]">
                glossary terms
              </span>
              . Start with Fundamentals, then explore by interest.
            </p>
          </div>
        </div>

        {/* Categories */}
        <div className="space-y-12">
          {wikiCategories.map((category) => (
            <section key={category.id}>
              <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
                <span className="text-3xl">{category.icon}</span>
                <span>{category.label}</span>
                <span className="text-sm font-normal text-[var(--foreground-muted)]">
                  ({category.articles.length} articles)
                </span>
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {category.articles.map((article) => (
                  <Link
                    key={article.slug}
                    href={`/wiki/${article.slug}`}
                    className="group block bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg p-6 hover:border-[var(--accent-purple)] transition-colors"
                  >
                    <h3 className="text-xl font-semibold mb-2 group-hover:text-[var(--accent-purple)] transition-colors flex items-center justify-between">
                      {article.title}
                      <ArrowRight className="w-5 h-5 text-[var(--accent-purple)] opacity-0 group-hover:opacity-100 transition-opacity" />
                    </h3>

                    <p className="text-sm text-[var(--foreground-muted)] mb-4 line-clamp-2">
                      {article.description}
                    </p>

                    <div className="flex items-center justify-between">
                      <div className="flex gap-2 flex-wrap">
                        {article.tags.slice(0, 2).map((tag) => (
                          <span
                            key={tag}
                            className="text-xs px-2 py-1 rounded bg-[var(--background-tertiary)] text-[var(--foreground-muted)]"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>

                      <span className="text-xs text-[var(--foreground-muted)]">
                        {article.readingTime} min
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
