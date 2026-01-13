// ============================================
// Ithena: The Blueprint - TypeScript Interfaces
// ============================================

// ===================
// Code X-Ray Types
// ===================

export interface XRayFile {
  filePath: string;
  fileHash: string;
  lastModified: string;
  language: 'python' | 'typescript' | 'javascript';
  entries: XRayEntry[];
}

export interface XRayEntry {
  id: string;
  title: string;
  startLine: number;
  endLine: number;
  anchors: Anchor[];
  why: string;
  whatItDoes: string;
  failureModes: FailureMode[];
  tests: TestSuggestion[];
  perfNotes: string | null;
  securityNotes: string | null;
  relatedDocs: string[];
  relatedNodes: string[];
}

export interface Anchor {
  kind: 'function' | 'class' | 'variable' | 'import' | 'decorator';
  value: string;
  line: number;
}

export interface FailureMode {
  condition: string;
  behavior: string;
  recovery: string;
}

export interface TestSuggestion {
  what: string;
  how: string;
}

export interface LineRange {
  start: number;
  end: number;
}

// ===================
// Wiki Types
// ===================

export interface WikiArticle {
  slug: string;
  title: string;
  category: WikiCategory;
  tags: string[];
  readingTime: number;
  prerequisites: string[];
  content?: string;
}

export type WikiCategory =
  | 'fundamentals'
  | 'kafka'
  | 'ml'
  | 'database'
  | 'security'
  | 'frontend';

export interface WikiIndex {
  categories: WikiCategoryGroup[];
}

export interface WikiCategoryGroup {
  id: WikiCategory;
  label: string;
  articles: { slug: string; title: string }[];
}

// ===================
// System Map Types
// ===================

export interface SystemTopology {
  nodes: MapNode[];
  edges: MapEdge[];
}

export interface MapNode {
  id: string;
  type: NodeType;
  label: string;
  position: { x: number; y: number };
  data: {
    facts: string[];
    wikiLinks: string[];
    xrayLinks: { file: string; entryId: string }[];
  };
}

export type NodeType =
  | 'sensor'
  | 'kafka'
  | 'consumer'
  | 'database'
  | 'dashboard'
  | 'twin';

export interface MapEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated: boolean;
}

// ===================
// FAQ Types
// ===================

export interface FAQ {
  slug: string;
  question: string;
  tags: string[];
  priority: 'critical' | 'high' | 'medium';
  content?: string;
}

export interface FAQIndex {
  faqs: Omit<FAQ, 'content'>[];
}

// ===================
// Glossary Types
// ===================

export interface GlossaryEntry {
  term: string;
  definition: string;
  seeAlso: string[];
}

export interface Glossary {
  entries: GlossaryEntry[];
}

// ===================
// UI State Types
// ===================

export interface XRaySyncState {
  activeEntryId: string | null;
  highlightedLines: LineRange | null;
  scrollTarget: 'code' | 'commentary' | null;
  hoveredLine: number | null;
  setActiveEntry: (id: string | null) => void;
  setHighlightedLines: (range: LineRange | null) => void;
  setScrollTarget: (target: 'code' | 'commentary' | null) => void;
  setHoveredLine: (line: number | null) => void;
  reset: () => void;
}

// ===================
// Navigation Types
// ===================

export type LearningMode = 'wiki' | 'xray' | 'map' | 'faq';

export interface ModeConfig {
  id: LearningMode;
  label: string;
  description: string;
  icon: string;
  href: string;
  color: string;
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
