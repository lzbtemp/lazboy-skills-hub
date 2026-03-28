import { useSearchParams } from 'react-router-dom';
import { Blocks, Server, Wrench } from 'lucide-react';
import { useSkills } from '../hooks/useSkills';
import { useSearch } from '../hooks/useSearch';
import SkillGrid from '../components/skills/SkillGrid';
import Pagination from '../components/common/Pagination';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SearchBar from '../components/search/SearchBar';
import FilterPanel from '../components/search/FilterPanel';
import SortDropdown from '../components/search/SortDropdown';

const TABS = [
  { id: 'skills', label: 'Skills', icon: Blocks },
  { id: 'mcp-servers', label: 'MCP Servers', icon: Server },
  { id: 'tools', label: 'Tools', icon: Wrench },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function BrowsePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page') || '1');
  const category = searchParams.get('category') || '';
  const sort = searchParams.get('sort') || 'newest';
  const query = searchParams.get('q') || '';
  const activeTab = (searchParams.get('tab') || 'skills') as TabId;

  const updateParams = (updates: Record<string, string>) => {
    const params = new URLSearchParams(searchParams);
    for (const [key, val] of Object.entries(updates)) {
      if (val) params.set(key, val);
      else params.delete(key);
    }
    if (!('page' in updates)) params.set('page', '1');
    setSearchParams(params);
  };

  const skillsQuery = useSkills({
    page,
    category: category || undefined,
    sort,
  });

  const searchQuery = useSearch({
    query,
    category: category || undefined,
    page,
  });

  const isSearching = query.length > 0;
  const activeQuery = isSearching ? searchQuery : skillsQuery;
  const { data, isLoading, error } = activeQuery;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Editorial header */}
      <div className="mb-8 animate-fade-in-up">
        <h1 className="text-4xl lg:text-5xl font-bold text-[#1B3A6B] tracking-tight mb-2">Browse</h1>
        {activeTab === 'skills' && data && (
          <p className="text-sm text-[#2C2C2C]/35 font-light">
            {data.total} skill{data.total !== 1 ? 's' : ''} available
            {category && <span className="text-[#1B3A6B]/60 ml-1">in selected category</span>}
          </p>
        )}
      </div>

      {/* Top-level tabs */}
      <div className="flex gap-1 mb-8 bg-gray-100/60 rounded-xl p-1 w-fit animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => updateParams({ tab: tab.id, page: '1', category: '' })}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-white text-[#1B3A6B] shadow-sm'
                  : 'text-[#2C2C2C]/45 hover:text-[#2C2C2C]/70'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Skills tab */}
      {activeTab === 'skills' && (
        <div className="flex gap-10">
          {/* Sidebar */}
          <aside className="hidden lg:block w-60 shrink-0">
            <div className="bg-gradient-to-b from-white to-[#FAF8F5]/80 rounded-2xl border border-gray-100 p-5 sticky top-24">
              <FilterPanel
                selectedCategory={category}
                onCategoryChange={(slug) => updateParams({ category: slug })}
              />
            </div>
          </aside>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-8">
              <div className="flex-1">
                <SearchBar
                  value={query}
                  onChange={(q) => updateParams({ q })}
                />
              </div>
              {!isSearching && (
                <SortDropdown
                  value={sort}
                  onChange={(s) => updateParams({ sort: s })}
                />
              )}
            </div>

            {/* Mobile category filter */}
            <div className="lg:hidden mb-4">
              <select
                value={category}
                onChange={(e) => updateParams({ category: e.target.value })}
                className="w-full px-4 py-3 bg-white border border-gray-100 rounded-xl text-sm shadow-sm"
              >
                <option value="">All Categories</option>
              </select>
            </div>

            {isLoading && <LoadingSpinner />}

            {error && (
              <div className="text-center py-16 animate-fade-in">
                <p className="text-[#C0392B]">Failed to load skills. Please try again.</p>
              </div>
            )}

            {data && (
              <>
                <SkillGrid skills={data.data} />
                <Pagination
                  page={data.page}
                  totalPages={data.total_pages}
                  onPageChange={(p) => updateParams({ page: String(p) })}
                />
              </>
            )}
          </div>
        </div>
      )}

      {/* MCP Servers tab — Coming Soon */}
      {activeTab === 'mcp-servers' && (
        <div className="flex flex-col items-center justify-center py-24 animate-fade-in-up">
          <div className="w-16 h-16 rounded-2xl bg-[#1B3A6B]/5 flex items-center justify-center mb-6">
            <Server className="w-8 h-8 text-[#1B3A6B]/40" />
          </div>
          <h2 className="text-2xl font-bold text-[#1B3A6B] mb-3">MCP Servers</h2>
          <p className="text-sm text-[#2C2C2C]/40 max-w-md text-center mb-6">
            Browse and install Model Context Protocol servers that extend your AI agents with external data sources, APIs, and integrations.
          </p>
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#8FAF8A]/10 text-[#8FAF8A] text-xs font-bold uppercase tracking-wider">
            Coming Soon
          </span>
        </div>
      )}

      {/* Tools tab — Coming Soon */}
      {activeTab === 'tools' && (
        <div className="flex flex-col items-center justify-center py-24 animate-fade-in-up">
          <div className="w-16 h-16 rounded-2xl bg-[#1B3A6B]/5 flex items-center justify-center mb-6">
            <Wrench className="w-8 h-8 text-[#1B3A6B]/40" />
          </div>
          <h2 className="text-2xl font-bold text-[#1B3A6B] mb-3">Tools</h2>
          <p className="text-sm text-[#2C2C2C]/40 max-w-md text-center mb-6">
            Standalone developer tools, CLI utilities, and automation scripts that complement your AI agent workflows.
          </p>
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#8FAF8A]/10 text-[#8FAF8A] text-xs font-bold uppercase tracking-wider">
            Coming Soon
          </span>
        </div>
      )}
    </div>
  );
}
