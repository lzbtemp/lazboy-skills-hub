import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { Search, ArrowRight } from 'lucide-react';
import { useCategories } from '../hooks/useCategories';
import { useSkills } from '../hooks/useSkills';
import SkillGrid from '../components/skills/SkillGrid';

const ICON_MAP: Record<string, string> = {
  code: '{ }',
  server: '|||',
  'check-circle': '+++',
  shield: '[#]',
  database: '(=)',
  cpu: '</>',
  layout: '|-|',
  terminal: '>_',
  cloud: '~~~',
  'file-text': '[=]',
  figma: '(o)',
  briefcase: '[B]',
};

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();
  const { data: categories } = useCategories();
  const { data: featuredSkills } = useSkills({ perPage: 6, sort: 'newest' });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/browse?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <div>
      {/* Hero — Comfort Blue background */}
      <div className="bg-[#1B3A6B] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
          <img
            src="/lazboy-logo.png"
            alt="La-Z-Boy"
            className="h-16 mx-auto mb-6 brightness-0 invert"
          />
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">
            Skills Repository
          </h1>
          <p className="text-lg text-white/70 max-w-2xl mx-auto mb-2">
            Discover, share, and install reusable AI agent skills across La-Z-Boy teams.
          </p>
          <p className="text-sm text-white/50 italic mb-8">
            Live life comfortably.&reg;
          </p>

          <form onSubmit={handleSearch} className="max-w-xl mx-auto relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#2C2C2C]/40" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search skills..."
              className="w-full pl-12 pr-4 py-3.5 rounded-lg text-[#2C2C2C] bg-white shadow-lg focus:outline-none focus:ring-2 focus:ring-[#C0392B]/40"
            />
          </form>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Categories */}
        {categories && (
          <section className="mb-12">
            <h2 className="text-xl font-bold text-[#1B3A6B] mb-6">Browse by Category</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {categories.map((cat) => (
                <Link
                  key={cat.id}
                  to={`/browse?category=${cat.slug}`}
                  className="flex flex-col items-center gap-2 p-4 bg-white rounded-lg border border-gray-200 hover:border-[#1B3A6B]/30 hover:shadow-md transition-all text-center"
                >
                  <span className="text-2xl font-mono text-[#1B3A6B]">
                    {ICON_MAP[cat.icon || ''] || '...'}
                  </span>
                  <span className="text-sm font-medium text-[#2C2C2C]">{cat.name}</span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Featured Skills */}
        {featuredSkills && featuredSkills.data.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-[#1B3A6B]">Latest Skills</h2>
              <Link
                to="/browse"
                className="inline-flex items-center gap-1 text-sm text-[#C0392B] hover:text-[#C0392B]/80"
              >
                View all <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
            <SkillGrid skills={featuredSkills.data} />
          </section>
        )}
      </div>
    </div>
  );
}
