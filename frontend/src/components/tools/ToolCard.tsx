import { Link } from 'react-router-dom';
import { ArrowRight, Server, Wrench } from 'lucide-react';
import type { FlatTool } from '../../types';

interface Props {
  tool: FlatTool;
}

export default function ToolCard({ tool }: Props) {
  return (
    <Link
      to={`/mcp/${tool.serverSlug}`}
      className="group flex flex-col rounded-2xl overflow-hidden glass-card h-full"
    >
      {/* Accent stripe — red/coral to distinguish from skills (navy) and MCP (sage) */}
      <div className="h-0.5 bg-gradient-to-r from-[#C0392B] via-[#C0392B]/60 to-transparent" />

      <div className="p-4 flex flex-col flex-1">
        {/* Tool name as monospace */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <code className="text-xs font-mono font-bold text-[#1B3A6B] bg-[#1B3A6B]/8 px-2 py-0.5 rounded-lg line-clamp-1">
            {tool.name}
          </code>
          <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-[#C0392B]/70 shrink-0 bg-[#C0392B]/8 px-1.5 py-0.5 rounded-full uppercase tracking-wider">
            <Wrench className="w-2.5 h-2.5" />
            Tool
          </span>
        </div>

        <p className="text-xs text-[#2C2C2C]/55 line-clamp-2 mb-3 leading-relaxed flex-1">
          {tool.description}
        </p>

        {/* Category badge */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gradient-to-r from-[#1B3A6B]/12 to-[#1B3A6B]/8 text-[#1B3A6B]">
            {tool.category}
          </span>
        </div>

        {/* Footer — parent MCP server */}
        <div className="mt-3 pt-3 border-t border-gray-50 flex items-center justify-between text-[11px] text-[#2C2C2C]/35">
          <span className="inline-flex items-center gap-1 font-medium">
            <Server className="w-2.5 h-2.5 text-[#8FAF8A]/60" />
            {tool.serverName}
          </span>
          <ArrowRight className="w-3 h-3 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300 text-[#1B3A6B]" />
        </div>
      </div>
    </Link>
  );
}
