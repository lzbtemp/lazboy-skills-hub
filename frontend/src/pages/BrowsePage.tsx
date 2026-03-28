import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Blocks, Server, Wrench } from 'lucide-react';
import { useSkills } from '../hooks/useSkills';
import { useSearch } from '../hooks/useSearch';
import SkillGrid from '../components/skills/SkillGrid';
import McpGrid from '../components/mcp/McpGrid';
import ToolGrid from '../components/tools/ToolGrid';
import Pagination from '../components/common/Pagination';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SearchBar from '../components/search/SearchBar';
import FilterPanel from '../components/search/FilterPanel';
import SortDropdown from '../components/search/SortDropdown';
import mcpServers from '../data/mcp-servers';
import allTools from '../data/tools';

const TOOLS_PER_PAGE = 24;

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

  // ── Skills data ──
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

  // ── MCP data (static, client-side filter/search) ──
  const filteredMcpServers = useMemo(() => {
    let results = mcpServers;
    if (category) {
      results = results.filter((s) => s.category.toLowerCase() === category.toLowerCase());
    }
    if (query) {
      const q = query.toLowerCase();
      results = results.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.category.toLowerCase().includes(q) ||
          s.owner.toLowerCase().includes(q),
      );
    }
    if (sort === 'name') {
      results = [...results].sort((a, b) => a.name.localeCompare(b.name));
    }
    return results;
  }, [category, query, sort]);

  // ── Tools data (derived from MCP servers, client-side filter/search/paginate) ──
  const filteredTools = useMemo(() => {
    let results = allTools;
    if (category) {
      results = results.filter((t) => t.category.toLowerCase() === category.toLowerCase());
    }
    if (query) {
      const q = query.toLowerCase();
      results = results.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q) ||
          t.serverName.toLowerCase().includes(q) ||
          t.category.toLowerCase().includes(q),
      );
    }
    if (sort === 'name') {
      results = [...results].sort((a, b) => a.name.localeCompare(b.name));
    }
    return results;
  }, [category, query, sort]);

  const toolsTotalPages = Math.max(1, Math.ceil(filteredTools.length / TOOLS_PER_PAGE));
  const pagedTools = filteredTools.slice((page - 1) * TOOLS_PER_PAGE, page * TOOLS_PER_PAGE);

  // Subtitle counts
  const subtitle =
    activeTab === 'skills' && data
      ? `${data.total} skill${data.total !== 1 ? 's' : ''} available`
      : activeTab === 'mcp-servers'
        ? `${filteredMcpServers.length} MCP server${filteredMcpServers.length !== 1 ? 's' : ''} available`
        : activeTab === 'tools'
          ? `${filteredTools.length} tool${filteredTools.length !== 1 ? 's' : ''} across ${mcpServers.length} MCP servers`
          : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Editorial header */}
      <div className="mb-8 animate-fade-in-up">
        <h1 className="text-4xl lg:text-5xl font-bold text-[#1B3A6B] tracking-tight mb-2">Browse</h1>
        {subtitle && (
          <p className="text-sm text-[#2C2C2C]/60 font-medium">
            {subtitle}
            {category && <span className="text-[#1B3A6B]/60 ml-1">in selected category</span>}
          </p>
        )}
      </div>

      {/* Top-level tabs */}
      <div className="flex gap-1 mb-8 bg-white/40 backdrop-blur-sm rounded-xl p-1 w-fit border border-[#1B3A6B]/[0.05] animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => updateParams({ tab: tab.id, page: '1', category: '', q: '' })}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-white/80 backdrop-blur-sm text-[#1B3A6B] shadow-sm shadow-[#1B3A6B]/[0.08] border border-[#1B3A6B]/[0.06]'
                  : 'text-[#2C2C2C]/45 hover:text-[#2C2C2C]/70 hover:bg-white/30'
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
          <aside className="hidden lg:block w-60 shrink-0">
            <div className="bg-white/50 backdrop-blur-xl rounded-2xl border border-[#1B3A6B]/[0.06] p-5 sticky top-24 shadow-sm shadow-[#1B3A6B]/[0.03]">
              <FilterPanel
                selectedCategory={category}
                onCategoryChange={(slug) => updateParams({ category: slug })}
              />
            </div>
          </aside>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-8">
              <div className="flex-1">
                <SearchBar
                  value={query}
                  onChange={(q) => updateParams({ q })}
                  placeholder="Search skills..."
                />
              </div>
              {!isSearching && (
                <SortDropdown
                  value={sort}
                  onChange={(s) => updateParams({ sort: s })}
                />
              )}
            </div>

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

      {/* MCP Servers tab */}
      {activeTab === 'mcp-servers' && (
        <div className="flex gap-10">
          <aside className="hidden lg:block w-60 shrink-0">
            <div className="bg-white/50 backdrop-blur-xl rounded-2xl border border-[#1B3A6B]/[0.06] p-5 sticky top-24 shadow-sm shadow-[#1B3A6B]/[0.03]">
              <FilterPanel
                selectedCategory={category}
                onCategoryChange={(slug) => updateParams({ category: slug })}
              />
            </div>
          </aside>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-8">
              <div className="flex-1">
                <SearchBar
                  value={query}
                  onChange={(q) => updateParams({ q })}
                  placeholder="Search MCP servers..."
                />
              </div>
              {!isSearching && (
                <SortDropdown
                  value={sort}
                  onChange={(s) => updateParams({ sort: s })}
                />
              )}
            </div>

            <div className="lg:hidden mb-4">
              <select
                value={category}
                onChange={(e) => updateParams({ category: e.target.value })}
                className="w-full px-4 py-3 bg-white border border-gray-100 rounded-xl text-sm shadow-sm"
              >
                <option value="">All Categories</option>
              </select>
            </div>

            <McpGrid servers={filteredMcpServers} />
          </div>
        </div>
      )}

      {/* Tools tab */}
      {activeTab === 'tools' && (
        <div className="flex gap-10">
          <aside className="hidden lg:block w-60 shrink-0">
            <div className="bg-white/50 backdrop-blur-xl rounded-2xl border border-[#1B3A6B]/[0.06] p-5 sticky top-24 shadow-sm shadow-[#1B3A6B]/[0.03]">
              <FilterPanel
                selectedCategory={category}
                onCategoryChange={(slug) => updateParams({ category: slug })}
              />
            </div>
          </aside>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-8">
              <div className="flex-1">
                <SearchBar
                  value={query}
                  onChange={(q) => updateParams({ q })}
                  placeholder="Search tools (e.g. screenshot, query, search)..."
                />
              </div>
              {!isSearching && (
                <SortDropdown
                  value={sort}
                  onChange={(s) => updateParams({ sort: s })}
                />
              )}
            </div>

            <div className="lg:hidden mb-4">
              <select
                value={category}
                onChange={(e) => updateParams({ category: e.target.value })}
                className="w-full px-4 py-3 bg-white border border-gray-100 rounded-xl text-sm shadow-sm"
              >
                <option value="">All Categories</option>
              </select>
            </div>

            <ToolGrid tools={pagedTools} />

            {filteredTools.length > TOOLS_PER_PAGE && (
              <Pagination
                page={page}
                totalPages={toolsTotalPages}
                onPageChange={(p) => updateParams({ page: String(p) })}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
