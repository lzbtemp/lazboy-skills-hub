import { Link } from 'react-router-dom';
import { ArrowRight, Server, Star, Users } from 'lucide-react';
import type { McpServer } from '../../types';

interface Props {
  server: McpServer;
}

export default function McpCard({ server }: Props) {
  return (
    <Link
      to={`/mcp/${server.slug}`}
      className="group flex flex-col rounded-2xl overflow-hidden glass-card h-full"
    >
      {/* Accent stripe — sage green to distinguish from skills */}
      <div className="h-0.5 bg-gradient-to-r from-[#8FAF8A] via-[#8FAF8A]/60 to-transparent" />

      <div className="p-4 flex flex-col flex-1">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <h3 className="text-sm font-bold text-[#2C2C2C] line-clamp-1 group-hover:text-[#1B3A6B] transition-colors tracking-tight">
              {server.name}
            </h3>
            {server.popular && (
              <span className="inline-flex items-center text-[9px] font-semibold text-amber-600 bg-amber-50 px-1 py-0.5 rounded-full shrink-0">
                <Star className="w-2.5 h-2.5 fill-amber-500 text-amber-500" />
              </span>
            )}
          </div>
          <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-[#8FAF8A] shrink-0 bg-[#8FAF8A]/10 px-1.5 py-0.5 rounded-full uppercase tracking-wider">
            <Server className="w-2.5 h-2.5" />
            MCP
          </span>
        </div>

        <p className="text-xs text-[#2C2C2C]/55 line-clamp-2 mb-3 leading-relaxed flex-1">
          {server.description}
        </p>

        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gradient-to-r from-[#1B3A6B]/12 to-[#1B3A6B]/8 text-[#1B3A6B]">
            {server.category}
          </span>
        </div>

        {server.usedBy && server.usedBy.length > 0 && (
          <div className="mt-2 flex items-center gap-1.5 text-[10px] text-[#2C2C2C]/35">
            <Users className="w-2.5 h-2.5 shrink-0" />
            <span className="truncate">{server.usedBy.join(', ')}</span>
          </div>
        )}

        <div className="mt-3 pt-3 border-t border-gray-50 flex items-center justify-between text-[11px] text-[#2C2C2C]/35">
          <span className="font-medium">{server.owner}</span>
          <ArrowRight className="w-3 h-3 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300 text-[#1B3A6B]" />
        </div>
      </div>
    </Link>
  );
}
