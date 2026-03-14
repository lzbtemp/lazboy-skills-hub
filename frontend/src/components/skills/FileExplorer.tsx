import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Folder, FolderOpen, FileText, ChevronRight, ChevronDown } from 'lucide-react';
import { fetchSkillFileTree } from '../../api/github';
import type { FileTreeItem } from '../../api/github';

interface FileNodeProps {
  item: FileTreeItem;
  depth?: number;
}

function FileNode({ item, depth = 0 }: FileNodeProps) {
  const [open, setOpen] = useState(false);
  const isDir = item.type === 'dir';
  const pl = depth * 16;

  return (
    <div>
      <button
        onClick={() => isDir && setOpen(!open)}
        className={`w-full flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-[#1B3A6B]/[0.04] transition-colors rounded-lg ${isDir ? 'cursor-pointer' : 'cursor-default'}`}
        style={{ paddingLeft: `${12 + pl}px` }}
      >
        {isDir ? (
          <>
            {open ? (
              <ChevronDown className="w-3.5 h-3.5 text-[#2C2C2C]/30 shrink-0" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-[#2C2C2C]/30 shrink-0" />
            )}
            {open ? (
              <FolderOpen className="w-4 h-4 text-[#1B3A6B]/60 shrink-0" />
            ) : (
              <Folder className="w-4 h-4 text-[#1B3A6B]/60 shrink-0" />
            )}
          </>
        ) : (
          <>
            <span className="w-3.5" />
            <FileText className="w-4 h-4 text-[#2C2C2C]/35 shrink-0" />
          </>
        )}
        <span className={`truncate ${isDir ? 'font-medium text-[#1B3A6B]/80' : 'text-[#2C2C2C]/65'}`}>
          {item.name}
        </span>
      </button>
      {isDir && open && item.children && (
        <div>
          {item.children.map((child) => (
            <FileNode key={child.name} item={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function countFiles(items: FileTreeItem[]): number {
  return items.reduce((sum, item) => {
    const childCount = item.children ? countFiles(item.children) : 0;
    return sum + 1 + childCount;
  }, 0);
}

interface Props {
  skillSlug: string;
}

export default function FileExplorer({ skillSlug }: Props) {
  const { data: tree, isLoading } = useQuery({
    queryKey: ['skill-tree', skillSlug],
    queryFn: () => fetchSkillFileTree(skillSlug),
  });

  if (isLoading) {
    return (
      <div className="bg-[#FAF8F5] rounded-lg border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#1B3A6B]/[0.06] border-b border-gray-200">
          <h3 className="text-xs font-semibold text-[#1B3A6B] uppercase tracking-wide">File Explorer</h3>
        </div>
        <div className="p-4 space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-5 bg-gray-100 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!tree || tree.length === 0) return null;

  const totalFiles = countFiles(tree);

  return (
    <div className="bg-[#FAF8F5] rounded-lg border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#1B3A6B]/[0.06] border-b border-gray-200">
        <h3 className="text-xs font-semibold text-[#1B3A6B] uppercase tracking-wide">File Explorer</h3>
        <span className="text-xs text-[#2C2C2C]/40 font-medium">{totalFiles}</span>
      </div>
      <div className="p-3">
        {tree.map((item) => (
          <FileNode key={item.name} item={item} />
        ))}
      </div>
    </div>
  );
}
