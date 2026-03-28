import { useParams, Link } from 'react-router-dom';
import { ChevronRight, Server, Zap, Lightbulb, Wrench, ExternalLink } from 'lucide-react';
import mcpServers from '../data/mcp-servers';

export default function McpDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const server = mcpServers.find((s) => s.slug === slug);

  if (!server) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center animate-fade-in">
        <p className="text-[#C0392B] text-lg">MCP Server not found</p>
        <Link to="/browse?tab=mcp-servers" className="text-[#1B3A6B] hover:underline mt-4 inline-block">
          Back to Browse
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Gradient hero header */}
      <div className="relative bg-gradient-to-br from-[#1B3A6B] via-[#152f58] to-[#1B3A6B]/90 overflow-hidden">
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
            <Link to="/browse?tab=mcp-servers" className="hover:text-white/70 transition-colors">MCP Servers</Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-white/60 truncate">{server.name}</span>
          </nav>

          <div className="flex items-start gap-5">
            <div className="w-14 h-14 rounded-2xl bg-white/[0.08] backdrop-blur-sm border border-white/[0.1] flex items-center justify-center shrink-0">
              <Server className="w-7 h-7 text-[#8FAF8A]/80" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-white tracking-tight">{server.name}</h1>
                {server.version && (
                  <span className="text-xs text-white/30 bg-white/[0.08] px-2.5 py-0.5 rounded-full backdrop-blur-sm">
                    v{server.version}
                  </span>
                )}
                <span className="text-[10px] font-semibold text-[#8FAF8A] bg-[#8FAF8A]/15 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                  MCP Server
                </span>
              </div>
              <p className="text-white text-base font-normal max-w-2xl leading-relaxed">{server.description}</p>
              <div className="flex items-center gap-5 text-sm text-white/40 mt-4">
                <span className="inline-flex items-center gap-1.5">{server.owner}</span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/[0.08] text-white/60 backdrop-blur-sm">
                  {server.category}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Main content */}
          <div className="flex-1 min-w-0 space-y-6">
            {/* Capabilities */}
            {server.capabilities && server.capabilities.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm">
                <div className="flex items-center gap-2 mb-5">
                  <Zap className="w-5 h-5 text-[#1B3A6B]/60" />
                  <h2 className="text-lg font-bold text-[#1B3A6B] tracking-tight">Capabilities</h2>
                </div>
                <ul className="space-y-3">
                  {server.capabilities.map((cap, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-[#2C2C2C]/70 leading-relaxed">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#8FAF8A] mt-2 shrink-0" />
                      {cap}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Use Cases */}
            {server.useCases && server.useCases.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm">
                <div className="flex items-center gap-2 mb-5">
                  <Lightbulb className="w-5 h-5 text-[#1B3A6B]/60" />
                  <h2 className="text-lg font-bold text-[#1B3A6B] tracking-tight">Use Cases</h2>
                </div>
                <ul className="space-y-3">
                  {server.useCases.map((uc, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-[#2C2C2C]/70 leading-relaxed">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#1B3A6B]/30 mt-2 shrink-0" />
                      {uc}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Available Tools */}
            {server.tools && server.tools.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm">
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2">
                    <Wrench className="w-5 h-5 text-[#1B3A6B]/60" />
                    <h2 className="text-lg font-bold text-[#1B3A6B] tracking-tight">Available Tools</h2>
                  </div>
                  <span className="text-xs text-[#2C2C2C]/30 font-medium">
                    {server.tools.length} tool{server.tools.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="space-y-2">
                  {server.tools.map((tool, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 px-4 py-3 rounded-xl bg-[#FAF8F5] border border-gray-100/60 hover:border-[#1B3A6B]/10 transition-colors"
                    >
                      <code className="text-xs font-mono font-semibold text-[#1B3A6B] bg-[#1B3A6B]/8 px-2 py-0.5 rounded-md shrink-0 mt-0.5">
                        {tool.name}
                      </code>
                      <span className="text-sm text-[#2C2C2C]/55 leading-relaxed">{tool.description}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar — info card */}
          <aside className="w-full lg:w-72 shrink-0">
            <div className="sticky top-24">
              <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
                <h3 className="text-sm font-bold text-[#2C2C2C]/60 uppercase tracking-wider mb-4">Details</h3>
                <dl className="space-y-4 text-sm">
                  <div>
                    <dt className="text-[#2C2C2C]/35 text-xs uppercase tracking-wider mb-1">Category</dt>
                    <dd className="text-[#2C2C2C]/80 font-medium">{server.category}</dd>
                  </div>
                  <div>
                    <dt className="text-[#2C2C2C]/35 text-xs uppercase tracking-wider mb-1">Owner</dt>
                    <dd className="text-[#2C2C2C]/80 font-medium">{server.owner}</dd>
                  </div>
                  <div>
                    <dt className="text-[#2C2C2C]/35 text-xs uppercase tracking-wider mb-1">Type</dt>
                    <dd className="inline-flex items-center gap-1.5 text-[#8FAF8A] font-medium">
                      <Server className="w-3.5 h-3.5" />
                      MCP Server
                    </dd>
                  </div>
                  {server.version && (
                    <div>
                      <dt className="text-[#2C2C2C]/35 text-xs uppercase tracking-wider mb-1">Version</dt>
                      <dd className="text-[#2C2C2C]/80 font-medium">v{server.version}</dd>
                    </div>
                  )}
                  {server.tools && (
                    <div>
                      <dt className="text-[#2C2C2C]/35 text-xs uppercase tracking-wider mb-1">Tools</dt>
                      <dd className="text-[#2C2C2C]/80 font-medium">{server.tools.length} available</dd>
                    </div>
                  )}
                  {server.npmPackage && (
                    <div>
                      <dt className="text-[#2C2C2C]/35 text-xs uppercase tracking-wider mb-1">Package</dt>
                      <dd className="text-xs font-mono text-[#1B3A6B]/70 break-all">{server.npmPackage}</dd>
                    </div>
                  )}
                </dl>
                {server.source && (
                  <a
                    href={server.source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-5 flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl border border-gray-100 text-sm font-medium text-[#2C2C2C]/50 hover:text-[#1B3A6B] hover:border-[#1B3A6B]/20 hover:bg-[#1B3A6B]/5 transition-all"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    View Source
                  </a>
                )}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
