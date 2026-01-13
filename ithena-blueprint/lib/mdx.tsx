import { compileMDX } from 'next-mdx-remote/rsc';
import remarkGfm from 'remark-gfm';
import rehypeSlug from 'rehype-slug';
import rehypeAutolinkHeadings from 'rehype-autolink-headings';
import { CalloutBlock } from '@/components/wiki/CalloutBlock';
import { GlossaryTerm } from '@/components/wiki/GlossaryTerm';
import { MermaidDiagram } from '@/components/wiki/MermaidDiagram';

export interface WikiFrontmatter {
  title: string;
  slug: string;
  category: 'fundamentals' | 'kafka' | 'ml' | 'database' | 'security' | 'frontend';
  tags: string[];
  readingTime: number;
  prerequisites?: string[];
  description?: string;
}

export interface Heading {
  level: number;
  text: string;
  slug: string;
}

/**
 * Compile MDX content with custom components and plugins
 */
export async function compileWikiMDX(source: string) {
  return await compileMDX<WikiFrontmatter>({
    source,
    options: {
      parseFrontmatter: true,
      mdxOptions: {
        remarkPlugins: [remarkGfm],
        rehypePlugins: [
          rehypeSlug,
          [
            rehypeAutolinkHeadings,
            {
              behavior: 'wrap',
              properties: {
                className: ['heading-anchor'],
              },
            },
          ],
        ],
      },
    },
    components: {
      Callout: CalloutBlock,
      Glossary: GlossaryTerm,
      Mermaid: MermaidDiagram,
      // Style standard elements
      h1: (props) => <h1 className="text-4xl font-bold mb-6 mt-8" {...props} />,
      h2: (props) => <h2 className="text-3xl font-semibold mb-4 mt-8" {...props} />,
      h3: (props) => <h3 className="text-2xl font-semibold mb-3 mt-6" {...props} />,
      h4: (props) => <h4 className="text-xl font-semibold mb-2 mt-4" {...props} />,
      p: (props) => <p className="mb-4 leading-relaxed text-[var(--foreground-muted)]" {...props} />,
      ul: (props) => <ul className="list-disc list-inside mb-4 space-y-2" {...props} />,
      ol: (props) => <ol className="list-decimal list-inside mb-4 space-y-2" {...props} />,
      li: (props) => <li className="ml-4 text-[var(--foreground-muted)]" {...props} />,
      code: (props) => {
        const { children, className, ...rest } = props;
        const isInline = !className;

        if (isInline) {
          return (
            <code
              className="px-1.5 py-0.5 rounded bg-[var(--code-bg)] text-[var(--accent-cyan)] font-mono text-sm"
              {...rest}
            >
              {children}
            </code>
          );
        }

        return (
          <code className={`block p-4 rounded-lg bg-[var(--code-bg)] overflow-x-auto ${className}`} {...rest}>
            {children}
          </code>
        );
      },
      pre: (props) => (
        <pre className="mb-4 overflow-x-auto rounded-lg border border-[var(--background-tertiary)]" {...props} />
      ),
      blockquote: (props) => (
        <blockquote
          className="border-l-4 border-[var(--accent-cyan)] pl-4 italic my-4 text-[var(--foreground-muted)]"
          {...props}
        />
      ),
      a: (props) => (
        <a
          className="text-[var(--accent-cyan)] hover:text-[var(--accent-purple)] underline transition-colors"
          {...props}
        />
      ),
      table: (props) => (
        <div className="overflow-x-auto mb-4">
          <table className="w-full border-collapse" {...props} />
        </div>
      ),
      th: (props) => (
        <th className="border border-[var(--background-tertiary)] px-4 py-2 bg-[var(--background-secondary)] text-left font-semibold" {...props} />
      ),
      td: (props) => (
        <td className="border border-[var(--background-tertiary)] px-4 py-2 text-[var(--foreground-muted)]" {...props} />
      ),
    },
  });
}

/**
 * Extract headings from MDX content for table of contents
 */
export function extractHeadings(content: string): Heading[] {
  const headingRegex = /^(#{1,4})\s+(.+)$/gm;
  const headings: Heading[] = [];
  let match;

  while ((match = headingRegex.exec(content)) !== null) {
    const level = match[1].length;
    const text = match[2].trim();
    const slug = text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');

    headings.push({ level, text, slug });
  }

  return headings;
}
