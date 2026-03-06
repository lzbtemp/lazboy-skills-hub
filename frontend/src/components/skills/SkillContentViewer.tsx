import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';

interface Props {
  content: string;
}

export default function SkillContentViewer({ content }: Props) {
  return (
    <div className="prose prose-indigo max-w-none">
      <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
