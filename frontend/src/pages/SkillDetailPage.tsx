import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tag as TagIcon, User, ChevronRight, Package } from 'lucide-react';
import { fetchSkillBySlug } from '../api/github';
import SkillContentViewer from '../components/skills/SkillContentViewer';
import InstallInstructions from '../components/skills/InstallInstructions';
import FileExplorer from '../components/skills/FileExplorer';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function SkillDetailPage() {
  const { slug } = useParams<{ slug: string }>();

  const { data: skill, isLoading, error } = useQuery({
    queryKey: ['skill', slug],
    queryFn: async () => {
      return await fetchSkillBySlug(slug!);
    },
    enabled: !!slug,
  });

  if (isLoading) return <LoadingSpinner />;

  if (error || !skill) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center animate-fade-in">
        <p className="text-[#C0392B] text-lg">Skill not found</p>
        <Link to="/browse" className="text-[#1B3A6B] hover:underline mt-4 inline-block">
          Back to Browse
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Gradient hero header */}
      <div className="relative bg-gradient-to-br from-[#1B3A6B] via-[#152f58] to-[#1B3A6B]/90 overflow-hidden">
        {/* Decorative elements */}
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
            <Link to="/browse" className="hover:text-white/70 transition-colors">Browse</Link>
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
              <div className="flex items-center gap-5 text-sm text-white/40 mt-4">
                <span className="inline-flex items-center gap-1.5">
                  <User className="w-4 h-4" />
                  {skill.author.display_name || skill.author.username}
                </span>
                <Link
                  to={`/browse?category=${skill.category.slug}`}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/[0.08] text-white/60 hover:bg-white/[0.12] transition-colors backdrop-blur-sm"
                >
                  {skill.category.name}
                </Link>
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

            {/* Tags */}
            {skill.tags.length > 0 && (
              <div className="mt-5 flex items-center gap-2 flex-wrap">
                <TagIcon className="w-4 h-4 text-[#2C2C2C]/20" />
                {skill.tags.map((tag) => (
                  <Link
                    key={tag.id}
                    to={`/browse?tag=${tag.slug}`}
                    className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-white text-[#2C2C2C]/55 border border-gray-100 hover:border-[#8FAF8A]/40 hover:bg-[#8FAF8A]/10 hover:scale-105 transition-all duration-200"
                  >
                    {tag.name}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <aside className="w-full lg:w-72 shrink-0">
            <div className="sticky top-24 space-y-4">
              <InstallInstructions slug={skill.slug} content={skill.content} />
              <FileExplorer skillSlug={skill.slug} />
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
