import {
  Server, TestTube2, Brain, Monitor,
  Palette, Settings, ShieldCheck, Layers
} from 'lucide-react';

const CATEGORIES = [
  { name: 'Frontend', slug: 'frontend', icon: Monitor },
  { name: 'Backend', slug: 'backend', icon: Server },
  { name: 'Full Stack', slug: 'full stack', icon: Layers },
  { name: 'DevOps', slug: 'devops', icon: Settings },
  { name: 'Data/AI', slug: 'data/ai', icon: Brain },
  { name: 'Designer', slug: 'designer', icon: Palette },
  { name: 'QA/Testing', slug: 'qa/testing', icon: TestTube2 },
  { name: 'Security', slug: 'security', icon: ShieldCheck },
];

interface Props {
  selectedCategory: string;
  onCategoryChange: (slug: string) => void;
}

export default function FilterPanel({ selectedCategory, onCategoryChange }: Props) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-bold text-[#1B3A6B]/70 uppercase tracking-[0.15em]">Categories</h3>
        {selectedCategory && (
          <button
            onClick={() => onCategoryChange('')}
            className="text-xs text-[#C0392B] hover:text-[#C0392B]/70 transition-colors font-medium"
          >
            Clear
          </button>
        )}
      </div>
      <div className="space-y-0.5">
        <button
          onClick={() => onCategoryChange('')}
          className={`group flex items-center gap-2.5 w-full text-left px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
            !selectedCategory
              ? 'bg-[#1B3A6B] text-white font-medium shadow-md shadow-[#1B3A6B]/20'
              : 'text-[#2C2C2C]/55 hover:bg-[#1B3A6B]/5 hover:text-[#2C2C2C]/80'
          }`}
        >
          <Layers className={`w-4 h-4 shrink-0 transition-transform duration-200 group-hover:scale-110 ${!selectedCategory ? 'text-white/80' : ''}`} />
          All
        </button>
        {CATEGORIES.map((cat) => {
          const isActive = selectedCategory === cat.slug;
          return (
            <button
              key={cat.slug}
              onClick={() => onCategoryChange(cat.slug)}
              className={`group flex items-center gap-2.5 w-full text-left px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
                isActive
                  ? 'bg-[#1B3A6B] text-white font-medium shadow-md shadow-[#1B3A6B]/20'
                  : 'text-[#2C2C2C]/55 hover:bg-[#1B3A6B]/5 hover:text-[#2C2C2C]/80'
              }`}
            >
              <cat.icon className={`w-4 h-4 shrink-0 transition-transform duration-200 group-hover:scale-110 ${isActive ? 'text-white/80' : ''}`} />
              {cat.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
