import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  content: string;
}

function stripFrontmatter(markdown: string): string {
  return markdown.replace(/^---\n[\s\S]*?\n---\n?/, '').trim();
}

export default function SkillContentViewer({ content }: Props) {
  const [expanded, setExpanded] = useState(false);
  const cleaned = stripFrontmatter(content);

  return (
    <div>
      <div className={`relative ${!expanded ? 'max-h-[400px] overflow-hidden' : ''}`}>
        <div className="prose prose-sm max-w-none overflow-hidden break-words prose-headings:text-[#1B3A6B] prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-a:text-[#C0392B] prose-p:text-[#2C2C2C]/80 prose-li:text-[#2C2C2C]/80 prose-strong:text-[#2C2C2C] prose-pre:overflow-x-auto prose-pre:max-w-full prose-code:break-all prose-code:text-xs">
          <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
            {cleaned}
          </ReactMarkdown>
        </div>
        {!expanded && (
          <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white to-transparent pointer-events-none" />
        )}
      </div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-[#1B3A6B] bg-[#1B3A6B]/5 hover:bg-[#1B3A6B]/10 rounded-xl transition-colors"
      >
        {expanded ? (
          <>Show less <ChevronUp className="w-4 h-4" /></>
        ) : (
          <>Show full content <ChevronDown className="w-4 h-4" /></>
        )}
      </button>
    </div>
  );
}
