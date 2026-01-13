import { notFound } from 'next/navigation';
import path from 'path';
import fs from 'fs';
import { compileWikiMDX } from '@/lib/mdx';
import { ArticleRenderer } from '@/components/wiki/ArticleRenderer';

interface WikiPageProps {
  params: {
    slug: string;
  };
}

async function getWikiArticle(slug: string) {
  const articlePath = path.join(
    process.cwd(),
    'content',
    'wiki',
    `${slug}.mdx`
  );

  // Check if file exists
  if (!fs.existsSync(articlePath)) {
    return null;
  }

  const source = fs.readFileSync(articlePath, 'utf-8');
  const { content, frontmatter } = await compileWikiMDX(source);

  return {
    content,
    frontmatter,
    source, // Pass raw source for heading extraction
  };
}

export default async function WikiArticlePage({ params }: WikiPageProps) {
  const article = await getWikiArticle(params.slug);

  if (!article) {
    notFound();
  }

  return (
    <ArticleRenderer
      frontmatter={article.frontmatter}
      content={article.content}
      source={article.source}
    />
  );
}

// Generate static params for all wiki articles
export async function generateStaticParams() {
  const wikiDir = path.join(process.cwd(), 'content', 'wiki');

  // Create directory if it doesn't exist
  if (!fs.existsSync(wikiDir)) {
    fs.mkdirSync(wikiDir, { recursive: true });
    return [];
  }

  const files = fs.readdirSync(wikiDir);

  return files
    .filter((file) => file.endsWith('.mdx'))
    .map((file) => ({
      slug: file.replace(/\.mdx$/, ''),
    }));
}
