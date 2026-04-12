import { useState } from 'react';
import { Check, Copy, Download, Terminal } from 'lucide-react';

const RAW_BASE = 'https://raw.githubusercontent.com/LZBRetail/lazboy-agent-skills/main/skills';

interface Props {
  slug: string;
  content: string;
}

export default function InstallInstructions({ slug, content }: Props) {
  const [copied, setCopied] = useState<string | null>(null);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied('content');
    setTimeout(() => setCopied(null), 2000);
  };

  const handleCopyNpx = async () => {
    const command = `npx @lazboy/skills add ${slug}`;
    await navigator.clipboard.writeText(command);
    setCopied('npx');
    setTimeout(() => setCopied(null), 2000);
  };

  const handleCopyGlobal = async () => {
    const command = `npx @lazboy/skills add ${slug} --global`;
    await navigator.clipboard.writeText(command);
    setCopied('global');
    setTimeout(() => setCopied(null), 2000);
  };

  const handleDownload = () => {
    window.open(`${RAW_BASE}/${slug}/SKILL.md`, '_blank');
  };

  return (
    <div className="bg-[#FAF8F5] rounded-lg border border-gray-200 p-4 space-y-3">
      <h3 className="text-sm font-semibold text-[#1B3A6B]">Install</h3>

      <div>
        <p className="text-xs text-gray-500 mb-1">CLI (recommended)</p>
        <div
          onClick={handleCopyNpx}
          className="flex items-center gap-2 px-3 py-2 bg-[#1B3A6B] text-white rounded-md text-xs font-mono cursor-pointer hover:bg-[#1B3A6B]/90"
        >
          <Terminal className="w-3 h-3 shrink-0" />
          <code className="truncate">npx @lazboy/skills add {slug}</code>
          {copied === 'npx' ? <Check className="w-3 h-3 text-green-400 ml-auto shrink-0" /> : <Copy className="w-3 h-3 text-gray-400 ml-auto shrink-0" />}
        </div>
      </div>

      <div>
        <p className="text-xs text-gray-500 mb-1">Global install (all projects)</p>
        <div
          onClick={handleCopyGlobal}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 text-white rounded-md text-xs font-mono cursor-pointer hover:bg-gray-700"
        >
          <Terminal className="w-3 h-3 shrink-0" />
          <code className="truncate">npx @lazboy/skills add {slug} --global</code>
          {copied === 'global' ? <Check className="w-3 h-3 text-green-400 ml-auto shrink-0" /> : <Copy className="w-3 h-3 text-gray-400 ml-auto shrink-0" />}
        </div>
      </div>

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
    </div>
  );
}
