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
      {/* Hero */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-700 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">
            La-Z-Boy Skills Repository
          </h1>
          <p className="text-lg text-indigo-100 max-w-2xl mx-auto mb-8">
            Discover, share, and install reusable AI agent skills across La-Z-Boy teams.
            Enhance your agents with domain expertise and repeatable workflows.
          </p>

          <form onSubmit={handleSearch} className="max-w-xl mx-auto relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search skills..."
              className="w-full pl-12 pr-4 py-3.5 rounded-xl text-gray-900 bg-white shadow-lg focus:outline-none focus:ring-2 focus:ring-white/50"
            />
          </form>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Categories */}
        {categories && (
          <section className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Browse by Category</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {categories.map((cat) => (
                <Link
                  key={cat.id}
                  to={`/browse?category=${cat.slug}`}
                  className="flex flex-col items-center gap-2 p-4 bg-white rounded-lg border border-gray-200 hover:border-indigo-300 hover:shadow-sm transition-all text-center"
                >
                  <span className="text-2xl font-mono text-indigo-600">
                    {ICON_MAP[cat.icon || ''] || '...'}
                  </span>
                  <span className="text-sm font-medium text-gray-700">{cat.name}</span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Featured Skills */}
        {featuredSkills && featuredSkills.data.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">Latest Skills</h2>
              <Link
                to="/browse"
                className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800"
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
