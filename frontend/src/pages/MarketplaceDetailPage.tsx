import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, Package, ExternalLink, Terminal, Check, Copy } from 'lucide-react';
import { useState } from 'react';
import { fetchMarketplaceSkillDetail } from '../api/github';
import SkillContentViewer from '../components/skills/SkillContentViewer';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function MarketplaceDetailPage() {
  const { org, repo, slug } = useParams<{ org: string; repo: string; slug: string }>();
  const [copied, setCopied] = useState<string | null>(null);

  const { data: skill, isLoading, error } = useQuery({
    queryKey: ['marketplace-skill', org, repo, slug],
    queryFn: () => fetchMarketplaceSkillDetail(org!, repo!, slug!),
    enabled: !!org && !!repo && !!slug,
  });

  const handleCopy = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  if (isLoading) return <LoadingSpinner />;

  if (error || !skill) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center animate-fade-in">
        <p className="text-[#C0392B] text-lg">Skill not found</p>
        <Link to="/marketplace" className="text-[#1B3A6B] hover:underline mt-4 inline-block">
          Back to Marketplace
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Gradient hero header */}
      <div className="relative bg-gradient-to-br from-[#1B3A6B] via-[#152f58] to-[#1B3A6B]/90 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute w-48 h-48 rounded-full border border-white/[0.04]" style={{ top: '-10%', right: '10%' }} />
          <div className="absolute w-32 h-32 rounded-full bg-[#8FAF8A]/[0.04]" style={{ bottom: '10%', left: '5%' }} />
        </div>
        <div className="absolute inset-0 noise-overlay" />

        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-12">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-1.5 text-sm text-white/35 mb-8">
            <Link to="/" className="hover:text-white/70 transition-colors">Home</Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <Link to="/marketplace" className="hover:text-white/70 transition-colors">Marketplace</Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-white/50">{skill.source.displayName}</span>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-white/60 truncate">{skill.name}</span>
          </nav>

          <div className="flex items-start gap-5">
            <div className="w-14 h-14 rounded-2xl bg-white/[0.08] backdrop-blur-sm border border-white/[0.1] flex items-center justify-center shrink-0">
              <Package className="w-7 h-7 text-white/70" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-white tracking-tight">{skill.name}</h1>
                <span className="text-xs text-white/30 bg-white/[0.08] px-2.5 py-0.5 rounded-full backdrop-blur-sm">v{skill.version}</span>
              </div>
              <p className="text-white text-base font-normal line-clamp-3 max-w-2xl leading-relaxed">{skill.description}</p>
              <div className="flex items-center gap-4 text-sm text-white/40 mt-4">
                <span
                  className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/[0.08] text-white/60"
                >
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: skill.source.color }} />
                  {skill.source.displayName}
                </span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/[0.08] text-white/60">
                  {skill.category}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Main content */}
          <div className="flex-1 min-w-0">
            <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm">
              <SkillContentViewer content={skill.content} />
            </div>
          </div>

          {/* Sidebar */}
          <aside className="w-full lg:w-72 shrink-0">
            <div className="sticky top-24 space-y-4">
              {/* Install card */}
              <div className="bg-[#FAF8F5] rounded-lg border border-gray-200 p-4 space-y-3">
                <h3 className="text-sm font-semibold text-[#1B3A6B]">Install</h3>

                <div>
                  <p className="text-xs text-gray-500 mb-1">CLI install</p>
                  <div
                    onClick={() => handleCopy(skill.installCommand, 'install')}
                    className="flex items-center gap-2 px-3 py-2 bg-[#1B3A6B] text-white rounded-md text-xs font-mono cursor-pointer hover:bg-[#1B3A6B]/90"
                  >
                    <Terminal className="w-3 h-3 shrink-0" />
                    <code className="truncate">{skill.installCommand}</code>
                    {copied === 'install' ? <Check className="w-3 h-3 text-green-400 ml-auto shrink-0" /> : <Copy className="w-3 h-3 text-gray-400 ml-auto shrink-0" />}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-500 mb-1">Copy SKILL.md</p>
                  <button
                    onClick={() => handleCopy(skill.content, 'content')}
                    className="w-full flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm hover:bg-gray-50 transition-colors"
                  >
                    {copied === 'content' ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4 text-gray-400" />}
                    <span>{copied === 'content' ? 'Copied!' : 'Copy content'}</span>
                  </button>
                </div>
              </div>

              {/* Source info card */}
              <div className="bg-[#FAF8F5] rounded-lg border border-gray-200 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2.5 bg-[#1B3A6B]/[0.06] border-b border-gray-200">
                  <h3 className="text-xs font-semibold text-[#1B3A6B] uppercase tracking-wide">Source</h3>
                </div>
                <div className="p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: skill.source.color }} />
                    <span className="text-sm font-medium text-[#1B3A6B]">{skill.source.displayName}</span>
                  </div>
                  <a
                    href={skill.githubUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-xs text-[#1B3A6B]/60 hover:text-[#1B3A6B] transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    View on GitHub
                  </a>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
