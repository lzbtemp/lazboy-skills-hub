import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Download, Tag as TagIcon, User } from 'lucide-react';
import api from '../api/client';
import type { Skill } from '../types';
import SkillContentViewer from '../components/skills/SkillContentViewer';
import InstallInstructions from '../components/skills/InstallInstructions';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function SkillDetailPage() {
  const { slug } = useParams<{ slug: string }>();

  const { data: skill, isLoading, error } = useQuery({
    queryKey: ['skill', slug],
    queryFn: async () => {
      const { data } = await api.get<Skill>(`/skills/${slug}`);
      return data;
    },
    enabled: !!slug,
  });

  if (isLoading) return <LoadingSpinner />;

  if (error || !skill) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <p className="text-red-500 text-lg">Skill not found</p>
        <Link to="/browse" className="text-indigo-600 hover:underline mt-4 inline-block">
          Back to Browse
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link to="/browse" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to Browse
      </Link>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{skill.name}</h1>
              <span className="text-sm text-gray-400">v{skill.version}</span>
            </div>
            <p className="text-gray-600 mb-3">{skill.description}</p>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="inline-flex items-center gap-1">
                <User className="w-4 h-4" />
                {skill.author.display_name || skill.author.username}
              </span>
              <span className="inline-flex items-center gap-1">
                <Download className="w-4 h-4" />
                {skill.install_count} installs
              </span>
              <Link
                to={`/browse?category=${skill.category.slug}`}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
              >
                {skill.category.name}
              </Link>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <SkillContentViewer content={skill.content} />
          </div>

          {skill.tags.length > 0 && (
            <div className="mt-4 flex items-center gap-2 flex-wrap">
              <TagIcon className="w-4 h-4 text-gray-400" />
              {skill.tags.map((tag) => (
                <Link
                  key={tag.id}
                  to={`/browse?tag=${tag.slug}`}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200"
                >
                  {tag.name}
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <aside className="w-full lg:w-72 shrink-0">
          <InstallInstructions slug={skill.slug} content={skill.content} />
        </aside>
      </div>
    </div>
  );
}
