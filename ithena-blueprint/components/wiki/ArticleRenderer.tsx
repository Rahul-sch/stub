import { TableOfContents } from './TableOfContents';
import { extractHeadings, type WikiFrontmatter } from '@/lib/mdx';
import { Clock, Tag, BookOpen } from 'lucide-react';
import Link from 'next/link';

interface ArticleRendererProps {
  frontmatter: WikiFrontmatter;
  content: React.ReactElement;
  source: string; // Raw MDX source for heading extraction
}

export function ArticleRenderer({
  frontmatter,
  content,
  source,
}: ArticleRendererProps) {
  const headings = extractHeadings(source);

  return (
    <div className="min-h-screen">
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-12 gap-8">
          {/* Main Content Area */}
          <article className="col-span-12 lg:col-span-8">
            {/* Article Header */}
            <header className="mb-8 pb-6 border-b border-[var(--background-tertiary)]">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-xs px-2 py-1 rounded-full bg-[var(--accent-purple)]/20 text-[var(--accent-purple)] uppercase font-semibold">
                  {frontmatter.category}
                </span>
                <div className="flex items-center gap-1 text-sm text-[var(--foreground-muted)]">
                  <Clock className="w-4 h-4" />
                  <span>{frontmatter.readingTime} min read</span>
                </div>
              </div>

              <h1 className="text-5xl font-bold mb-4 text-[var(--foreground)]">
                {frontmatter.title}
              </h1>

              {frontmatter.description && (
                <p className="text-lg text-[var(--foreground-muted)] leading-relaxed mb-4">
                  {frontmatter.description}
                </p>
              )}

              {/* Tags */}
              {frontmatter.tags && frontmatter.tags.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <Tag className="w-4 h-4 text-[var(--foreground-muted)]" />
                  {frontmatter.tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-xs px-2 py-1 rounded bg-[var(--background-secondary)] text-[var(--accent-cyan)] border border-[var(--background-tertiary)]"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Prerequisites */}
              {frontmatter.prerequisites &&
                frontmatter.prerequisites.length > 0 && (
                  <div className="mt-4 p-4 rounded-lg bg-[var(--accent-orange)]/10 border border-[var(--accent-orange)]/30">
                    <div className="flex items-start gap-2">
                      <BookOpen className="w-5 h-5 text-[var(--accent-orange)] mt-0.5 shrink-0" />
                      <div>
                        <div className="text-sm font-semibold text-[var(--accent-orange)] mb-2">
                          Prerequisites
                        </div>
                        <div className="text-sm text-[var(--foreground-muted)]">
                          For best understanding, read these articles first:
                        </div>
                        <ul className="mt-2 space-y-1">
                          {frontmatter.prerequisites.map((prereq) => (
                            <li key={prereq}>
                              <Link
                                href={`/wiki/${prereq}`}
                                className="text-sm text-[var(--accent-cyan)] hover:text-[var(--accent-purple)] underline transition-colors"
                              >
                                {prereq
                                  .split('-')
                                  .map(
                                    (word) =>
                                      word.charAt(0).toUpperCase() + word.slice(1)
                                  )
                                  .join(' ')}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
            </header>

            {/* Article Body with MDX Content */}
            <div className="prose prose-invert max-w-none article-content">
              {content}
            </div>
          </article>

          {/* Sidebar with Table of Contents */}
          <aside className="hidden lg:block col-span-4">
            <TableOfContents headings={headings} />
          </aside>
        </div>
      </div>
    </div>
  );
}
