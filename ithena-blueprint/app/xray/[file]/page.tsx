import { notFound } from 'next/navigation';
import fs from 'fs';
import path from 'path';
import { XRayViewer } from './XRayViewer';
import { highlightCodeLines } from '@/lib/shiki';
import type { XRayFile } from '@/lib/types';

interface PageProps {
  params: Promise<{ file: string }>;
}

async function getXRayData(fileName: string) {
  try {
    // Load X-Ray JSON
    const xrayPath = path.join(process.cwd(), 'content', 'xray', `${fileName}.json`);
    if (!fs.existsSync(xrayPath)) {
      return null;
    }
    const xrayContent = fs.readFileSync(xrayPath, 'utf-8');
    const xray: XRayFile = JSON.parse(xrayContent);

    // Load source code
    const codePath = path.join(process.cwd(), 'public', 'code', fileName);
    if (!fs.existsSync(codePath)) {
      return null;
    }
    const code = fs.readFileSync(codePath, 'utf-8');

    // Pre-render syntax highlighting on server
    const highlightedLines = await highlightCodeLines(code, xray.language);

    return { xray, code, highlightedLines };
  } catch (error) {
    console.error('Error loading X-Ray data:', error);
    return null;
  }
}

export default async function XRayPage({ params }: PageProps) {
  const { file } = await params;
  const fileName = decodeURIComponent(file);

  const data = await getXRayData(fileName);

  if (!data) {
    notFound();
  }

  return <XRayViewer xray={data.xray} code={data.code} highlightedLines={data.highlightedLines} />;
}

export async function generateStaticParams() {
  // Pre-generate pages for known files
  return [
    { file: 'consumer.py' },
  ];
}
