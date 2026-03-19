import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Terminal, Package, Loader2, ChevronRight, ExternalLink } from 'lucide-react';
import { fetchAllMarketplaceSkills } from '../api/github';
import type { MarketplaceSkill, MarketplaceSource } from '../api/github';

function SkillCard({ skill }: { skill: MarketplaceSkill }) {
  return (
    <Link
      to={`/marketplace/${skill.source.org}/${skill.source.repo}/${skill.slug}`}
      className="group flex flex-col bg-white rounded-2xl border border-gray-100 overflow-hidden hover:border-[#1B3A6B]/15 hover:shadow-lg transition-all duration-300 h-full"
    >
      <div className="flex flex-col flex-1 p-5">
        <div className="flex items-start justify-between mb-2">
          <h3 className="text-sm font-semibold text-[#1B3A6B] group-hover:text-[#C0392B] transition-colors">
            {skill.name}
          </h3>
          <ChevronRight className="w-3.5 h-3.5 text-[#2C2C2C]/40 group-hover:text-[#1B3A6B]/70 transition-colors shrink-0 mt-0.5" />
        </div>
        <p className="text-xs text-[#2C2C2C]/70 leading-relaxed flex-1 line-clamp-3">
          {skill.description}
        </p>
        <div className="mt-3 flex items-center gap-2">
          {skill.category && (
            <span className="text-[10px] uppercase tracking-wider font-medium text-[#1B3A6B]/70 bg-[#1B3A6B]/[0.08] px-2 py-0.5 rounded-full">
              {skill.category}
            </span>
          )}
        </div>
      </div>
      <div className="px-5 py-3 bg-[#1B3A6B]/[0.02] border-t border-gray-50 opacity-0 group-hover:opacity-100 transition-opacity">
        <code className="text-[10px] text-[#1B3A6B]/60 font-mono">{skill.installCommand}</code>
      </div>
    </Link>
  );
}

function ProviderSection({ source, skills }: { source: MarketplaceSource; skills: MarketplaceSkill[] }) {
  return (
    <section className="mb-12">
      <div className="flex items-center gap-3 mb-6">
        <span
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: source.color }}
        />
        <h2 className="text-lg font-semibold text-[#1B3A6B]">{source.displayName}</h2>
        <span className="text-xs text-[#2C2C2C]/60">{skills.length} skills</span>
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto text-xs text-[#1B3A6B]/60 hover:text-[#1B3A6B]/90 transition-colors flex items-center gap-1"
        >
          View repo <ExternalLink className="w-3 h-3" />
        </a>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {skills.map((skill) => (
          <SkillCard key={`${source.org}-${skill.slug}`} skill={skill} />
        ))}
      </div>
    </section>
  );
}

export default function MarketplacePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['marketplace-skills'],
    queryFn: fetchAllMarketplaceSkills,
    staleTime: 1000 * 60 * 10,
  });

  const totalSkills = data?.reduce((sum, group) => sum + group.skills.length, 0) ?? 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="mb-8 animate-fade-in-up">
        <div className="flex items-center gap-3 mb-2">
          <Package className="w-8 h-8 text-[#1B3A6B]/70" />
          <h1 className="text-4xl lg:text-5xl font-bold text-[#1B3A6B] tracking-tight">Marketplace</h1>
        </div>
        <p className="text-sm text-[#2C2C2C]/70">
          Discover and install community-built AI agent skills from open-source providers
        </p>
      </div>

      {/* Install banner */}
      <div className="mb-10 bg-[#1B3A6B]/[0.03] border border-[#1B3A6B]/[0.08] rounded-xl px-5 py-4 flex items-center gap-3">
        <Terminal className="w-4 h-4 text-[#1B3A6B]/50 shrink-0" />
        <div>
          <p className="text-xs text-[#2C2C2C]/70 mb-0.5">Install skills from any provider</p>
          <code className="text-sm text-[#1B3A6B] font-mono font-medium">$ npx skills add https://github.com/&lt;org&gt;/&lt;repo&gt; --skill &lt;skill-name&gt;</code>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-[#1B3A6B]/40 animate-spin mb-3" />
          <p className="text-sm text-[#2C2C2C]/35">Loading marketplace skills...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-center py-16">
          <p className="text-[#C0392B] text-sm">Failed to load marketplace skills. GitHub API rate limit may have been reached.</p>
        </div>
      )}

      {/* Provider sections */}
      {data && (
        <div>
          <p className="text-xs text-[#2C2C2C]/50 mb-8 uppercase tracking-widest">
            {totalSkills} skills from {data.length} providers
          </p>
          {data.map(({ source, skills }) => (
            <ProviderSection key={source.org} source={source} skills={skills} />
          ))}
        </div>
      )}
    </div>
  );
}
