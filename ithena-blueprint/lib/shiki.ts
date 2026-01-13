import { createHighlighter, type Highlighter, type BundledLanguage, type BundledTheme } from 'shiki';

let highlighter: Highlighter | null = null;

export async function getHighlighter() {
  if (!highlighter) {
    highlighter = await createHighlighter({
      themes: ['github-dark'],
      langs: ['python', 'typescript', 'javascript', 'bash', 'json'],
    });
  }
  return highlighter;
}

export async function highlightCode(
  code: string,
  lang: BundledLanguage = 'python',
  theme: BundledTheme = 'github-dark'
) {
  const hl = await getHighlighter();
  return hl.codeToHtml(code, {
    lang,
    theme,
    structure: 'classic',
  });
}

export interface HighlightedLine {
  lineNumber: number;
  html: string;
  tokens: Array<{
    content: string;
    color?: string;
    fontStyle?: number;
  }>;
}

export async function highlightCodeLines(
  code: string,
  lang: BundledLanguage = 'python',
  theme: BundledTheme = 'github-dark'
): Promise<HighlightedLine[]> {
  const hl = await getHighlighter();
  const lines = code.split('\n');

  return lines.map((line, index) => {
    const tokens = hl.codeToTokens(line || ' ', { lang, theme });

    return {
      lineNumber: index + 1,
      html: hl.codeToHtml(line || ' ', { lang, theme, structure: 'inline' }),
      tokens: tokens.tokens[0]?.map(token => ({
        content: token.content,
        color: token.color,
        fontStyle: token.fontStyle,
      })) || [],
    };
  });
}
