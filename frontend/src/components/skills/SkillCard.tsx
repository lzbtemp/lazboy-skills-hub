import { Link } from 'react-router-dom';
import { Download, ArrowRight } from 'lucide-react';
import type { SkillListItem } from '../../types';

interface Props {
  skill: SkillListItem;
}

export default function SkillCard({ skill }: Props) {
  return (
    <Link
      to={`/skills/${skill.slug}`}
      className="group flex flex-col bg-white rounded-2xl border border-gray-100 overflow-hidden card-hover hover:border-[#1B3A6B]/15 h-full"
    >
      {/* Accent stripe */}
      <div className="h-0.5 bg-gradient-to-r from-[#1B3A6B] via-[#1B3A6B]/60 to-transparent" />

      <div className="p-6 flex flex-col flex-1">
        <div className="flex items-start justify-between gap-3 mb-3">
          <h3 className="text-lg font-bold text-[#2C2C2C] line-clamp-1 group-hover:text-[#1B3A6B] transition-colors tracking-tight">{skill.name}</h3>
          <span className="inline-flex items-center gap-1 text-xs text-[#2C2C2C]/35 shrink-0 bg-[#FAF8F5] px-2 py-0.5 rounded-full">
            <Download className="w-3 h-3" />
            {skill.install_count}
          </span>
        </div>

        <p className="text-sm text-[#2C2C2C]/55 line-clamp-2 mb-5 leading-relaxed flex-1">{skill.description}</p>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gradient-to-r from-[#1B3A6B]/12 to-[#1B3A6B]/8 text-[#1B3A6B]">
            {skill.category.name}
          </span>
          {skill.tags.slice(0, 2).map((tag) => (
            <span
              key={tag.id}
              className="inline-flex items-center px-2 py-0.5 rounded-full text-xs text-[#2C2C2C]/50 bg-[#FAF8F5] border border-gray-100/80"
            >
              {tag.name}
            </span>
          ))}
        </div>

        <div className="mt-5 pt-4 border-t border-gray-50 flex items-center justify-between text-xs text-[#2C2C2C]/35">
          <span className="font-medium">{skill.author.display_name || skill.author.username}</span>
          <div className="flex items-center gap-2">
            <span>v{skill.version}</span>
            <ArrowRight className="w-3.5 h-3.5 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300 text-[#1B3A6B]" />
          </div>
        </div>
      </div>
    </Link>
  );
}
