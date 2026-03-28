import { Link, useNavigate } from 'react-router-dom';
import { useState, useMemo } from 'react';
import {
  Search, ArrowRight, Server, Layers, Monitor,
  Brain, Palette, Settings, TestTube2, ShieldCheck, Wrench
} from 'lucide-react';
import { useSkills } from '../hooks/useSkills';
import SkillGrid from '../components/skills/SkillGrid';
import McpGrid from '../components/mcp/McpGrid';
import ToolGrid from '../components/tools/ToolGrid';
import mcpServers from '../data/mcp-servers';
import allTools from '../data/tools';
import { SplineScene } from '@/components/ui/splite';
import { Spotlight } from '@/components/ui/spotlight';
import { Typewriter } from '@/components/ui/typewriter-text';
import { TextRotate } from '@/components/ui/text-rotate';

const ROLES = [
  { label: 'FRONTEND', icon: Monitor, slug: 'frontend' },
  { label: 'BACKEND', icon: Server, slug: 'backend' },
  { label: 'FULL STACK', icon: Layers, slug: 'full stack' },
  { label: 'DEVOPS', icon: Settings, slug: 'devops' },
  { label: 'DATA/AI', icon: Brain, slug: 'data/ai' },
  { label: 'DESIGNER', icon: Palette, slug: 'designer' },
  { label: 'QA/TESTING', icon: TestTube2, slug: 'qa/testing' },
  { label: 'SECURITY', icon: ShieldCheck, slug: 'security' },
];

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRole, setSelectedRole] = useState<string | null>(null);

  const handleRoleClick = (slug: string) => {
    const isActive = selectedRole === slug;
    setSelectedRole(isActive ? null : slug);
    navigate(`/browse?category=${encodeURIComponent(slug)}`);
  };
  const navigate = useNavigate();
  const { data: featuredSkills } = useSkills({ perPage: 6, sort: 'newest' });

  const featuredMcp = useMemo(() => mcpServers.slice(0, 6), []);
  const popularTools = useMemo(() => allTools.slice(0, 6), []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/browse?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <div>
      {/* Hero with 3D Robot */}
      <div className="relative overflow-hidden bg-gradient-to-br from-[#1B3A6B] via-[#152f58] to-[#0f2140] text-white">
        <Spotlight
          className="-top-40 left-0 md:left-60 md:-top-20"
          fill="#8FAF8A"
        />

        {/* Noise texture */}
        <div className="absolute inset-0 noise-overlay" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col lg:flex-row items-center min-h-[320px]">
            {/* Left content */}
            <div className="flex-1 py-10 lg:py-14 z-10 text-center lg:text-left">
              <div className="mb-4 animate-fade-in-up min-h-[28px]">
                <Typewriter
                  text="AI skills, MCP servers, and tools — all in one place. Install with a single command and supercharge your AI agents."
                  speed={50}
                  loop={false}
                  cursor="_"
                  className="text-base sm:text-lg text-white font-semibold tracking-wide"
                />
              </div>
              <div className="mb-6 animate-fade-in-up flex items-center gap-2 justify-center lg:justify-start" style={{ animationDelay: '0.08s' }}>
                <span className="text-sm text-white font-bold">AI resources for</span>
                <TextRotate
                  texts={[
                    "Code Generation",
                    "API Integration",
                    "Data Analysis",
                    "Cloud Deployment",
                    "Testing & QA",
                    "Security Audits",
                  ]}
                  mainClassName="text-sm font-bold text-[#8FAF8A] overflow-hidden px-2 py-0.5 bg-[#8FAF8A]/10 rounded-md"
                  splitLevelClassName="overflow-hidden"
                  staggerFrom="last"
                  staggerDuration={0.025}
                  rotationInterval={2500}
                  transition={{ type: "spring", damping: 30, stiffness: 400 }}
                />
              </div>
              <div className="inline-block text-left">
                <p className="text-sm text-white/60 mb-2 animate-fade-in-up whitespace-nowrap" style={{ animationDelay: '0.12s' }}>
                  Discover, browse, and install AI skills, MCP servers, and tools.
                </p>

                {/* Glass search bar — matches text width */}
                <form onSubmit={handleSearch} className="relative animate-fade-in-up" style={{ animationDelay: '0.24s' }}>
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search skills, servers, tools..."
                    className="w-full pl-11 pr-4 py-3 rounded-xl text-white bg-white/[0.08] backdrop-blur-md border border-white/[0.12] shadow-2xl placeholder-white/30 focus:outline-none focus:bg-white/[0.12] focus:border-white/[0.2] transition-all text-sm"
                  />
                </form>
              </div>
            </div>

            {/* Right — 3D Robot */}
            <div className="flex-1 relative h-[280px] lg:h-[320px] w-full">
              <SplineScene
                scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
                className="w-full h-full"
              />
            </div>
          </div>
        </div>

      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-20">
        {/* Role Selector */}
        <section className="mb-20 animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
          <div className="flex items-center gap-3 mb-8">
            <Settings className="w-5 h-5 text-[#2C2C2C]/40" />
            <h2 className="text-sm font-bold text-[#2C2C2C]/60 uppercase tracking-[0.15em]">I am a...</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {ROLES.map((role) => {
              const isActive = selectedRole === role.slug;
              return (
                <button
                  key={role.label}
                  onClick={() => handleRoleClick(role.slug)}
                  className={`group flex flex-col items-center gap-3 px-4 py-6 rounded-xl border-2 transition-all duration-200 ${
                    isActive
                      ? 'bg-[#1B3A6B] border-[#1B3A6B] text-white shadow-lg shadow-[#1B3A6B]/20'
                      : 'bg-white border-gray-200 text-[#2C2C2C] hover:border-[#1B3A6B]/30 hover:shadow-md'
                  }`}
                >
                  <role.icon className={`w-6 h-6 ${isActive ? 'text-white' : 'text-[#2C2C2C]/50 group-hover:text-[#1B3A6B]'} transition-colors`} />
                  <span className={`text-xs font-bold tracking-wide ${isActive ? 'text-white' : 'text-[#2C2C2C]/70'}`}>
                    {role.label}
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Latest Skills */}
        {featuredSkills && featuredSkills.data.length > 0 && (
          <section className="mb-16 animate-fade-in-up" style={{ animationDelay: '0.25s' }}>
            <div className="flex items-center justify-between mb-10">
              <div className="flex items-center gap-4">
                <h2 className="text-3xl font-bold text-[#1B3A6B] tracking-tight">Latest Skills</h2>
                <div className="flex-1 h-px bg-gradient-to-r from-[#1B3A6B]/15 to-transparent" />
              </div>
              <Link
                to="/browse?tab=skills"
                className="group inline-flex items-center gap-2 text-sm font-medium text-[#C0392B] hover:text-[#C0392B]/80 transition-colors"
              >
                View all <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>
            <SkillGrid skills={featuredSkills.data} />
          </section>
        )}

        {/* Featured MCP Servers */}
        {featuredMcp.length > 0 && (
          <section className="mb-16 animate-fade-in-up" style={{ animationDelay: '0.35s' }}>
            <div className="flex items-center justify-between mb-10">
              <div className="flex items-center gap-4">
                <Server className="w-5 h-5 text-[#8FAF8A]" />
                <h2 className="text-3xl font-bold text-[#1B3A6B] tracking-tight">Featured MCP Servers</h2>
                <div className="flex-1 h-px bg-gradient-to-r from-[#8FAF8A]/25 to-transparent" />
              </div>
              <Link
                to="/browse?tab=mcp-servers"
                className="group inline-flex items-center gap-2 text-sm font-medium text-[#C0392B] hover:text-[#C0392B]/80 transition-colors"
              >
                View all <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>
            <McpGrid servers={featuredMcp} />
          </section>
        )}

        {/* Popular Tools */}
        {popularTools.length > 0 && (
          <section className="animate-fade-in-up" style={{ animationDelay: '0.45s' }}>
            <div className="flex items-center justify-between mb-10">
              <div className="flex items-center gap-4">
                <Wrench className="w-5 h-5 text-[#C0392B]/60" />
                <h2 className="text-3xl font-bold text-[#1B3A6B] tracking-tight">Popular Tools</h2>
                <div className="flex-1 h-px bg-gradient-to-r from-[#C0392B]/15 to-transparent" />
              </div>
              <Link
                to="/browse?tab=tools"
                className="group inline-flex items-center gap-2 text-sm font-medium text-[#C0392B] hover:text-[#C0392B]/80 transition-colors"
              >
                View all <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>
            <ToolGrid tools={popularTools} />
          </section>
        )}
      </div>
    </div>
  );
}
