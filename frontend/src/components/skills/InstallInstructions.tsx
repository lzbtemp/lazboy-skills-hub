import { useState } from 'react';
import { Check, Copy, Download, Terminal } from 'lucide-react';
import api from '../../api/client';

interface Props {
  slug: string;
  content: string;
}

export default function InstallInstructions({ slug, content }: Props) {
  const [copied, setCopied] = useState<string | null>(null);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied('content');
    api.post(`/skills/${slug}/install`).catch(() => {});
    setTimeout(() => setCopied(null), 2000);
  };

  const handleCopyCommand = async () => {
    const command = `curl -o SKILL.md ${window.location.origin}/api/v1/skills/${slug}/download`;
    await navigator.clipboard.writeText(command);
    setCopied('command');
    setTimeout(() => setCopied(null), 2000);
  };

  const handleDownload = () => {
    api.post(`/skills/${slug}/install`).catch(() => {});
    window.open(`/api/v1/skills/${slug}/download`, '_blank');
  };

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-700">Install</h3>

      <button
        onClick={handleCopy}
        className="w-full flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm hover:bg-gray-50 transition-colors"
      >
        {copied === 'content' ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4 text-gray-400" />}
        <span>{copied === 'content' ? 'Copied!' : 'Copy SKILL.md content'}</span>
      </button>

      <button
        onClick={handleDownload}
        className="w-full flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm hover:bg-gray-50 transition-colors"
      >
        <Download className="w-4 h-4 text-gray-400" />
        <span>Download SKILL.md</span>
      </button>

      <div className="mt-2">
        <p className="text-xs text-gray-500 mb-1">CLI</p>
        <div
          onClick={handleCopyCommand}
          className="flex items-center gap-2 px-3 py-2 bg-gray-900 text-gray-100 rounded-md text-xs font-mono cursor-pointer hover:bg-gray-800"
        >
          <Terminal className="w-3 h-3 shrink-0" />
          <code className="truncate">curl -o SKILL.md .../api/v1/skills/{slug}/download</code>
          {copied === 'command' ? <Check className="w-3 h-3 text-green-400 ml-auto shrink-0" /> : <Copy className="w-3 h-3 text-gray-500 ml-auto shrink-0" />}
        </div>
      </div>
    </div>
  );
}
