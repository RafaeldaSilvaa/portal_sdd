import { useState } from 'react';
import { ChevronRight, ChevronDown, FileIcon, Folder, FolderOpen, Code, FileText } from 'lucide-react';
import type { PipelineFileEntry } from '../../types/pipeline';

const FILE_ICONS: Record<string, typeof FileIcon> = {
  '.py': Code,
  '.md': FileText,
  '.json': FileText,
  '.txt': FileText,
};

function getFileIcon(name: string) {
  const ext = name.includes('.') ? `.${name.split('.').pop()}` : '';
  return FILE_ICONS[ext] || FileIcon;
}

interface FileTreeNodeProps {
  entry: PipelineFileEntry;
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}

function FileTreeNode({ entry, depth, selectedPath, onSelect }: FileTreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 1);
  const isDir = entry.type === 'directory';
  const isSelected = selectedPath === entry.path;

  if (isDir) {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className={`flex w-full items-center gap-1.5 px-2 py-1 text-left text-sm rounded hover:bg-slate-800/60 ${
            isSelected ? 'bg-slate-700/50 text-emasdep-300' : 'text-slate-300'
          }`}
          style={{ paddingLeft: `${12 + depth * 16}px` }}
        >
          {expanded ? <ChevronDown className="h-3.5 w-3.5 shrink-0 text-slate-500" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-500" />}
          {expanded ? <FolderOpen className="h-4 w-4 shrink-0 text-amber-400" /> : <Folder className="h-4 w-4 shrink-0 text-amber-400" />}
          <span className="truncate">{entry.name}</span>
        </button>
        {expanded && entry.children?.map((child) => (
          <FileTreeNode key={child.path} entry={child} depth={depth + 1} selectedPath={selectedPath} onSelect={onSelect} />
        ))}
      </div>
    );
  }

  const Icon = getFileIcon(entry.name);
  const iconColor = entry.name.endsWith('.py') ? 'text-cyan-400' : entry.name.endsWith('.md') ? 'text-blue-400' : 'text-slate-400';

  return (
    <button
      onClick={() => onSelect(entry.path)}
      className={`flex w-full items-center gap-1.5 px-2 py-1 text-left text-sm rounded hover:bg-slate-800/60 ${
        isSelected ? 'bg-emasdep-600/20 text-emasdep-300 border-l-2 border-emasdep-500' : 'text-slate-400 border-l-2 border-transparent'
      }`}
      style={{ paddingLeft: `${12 + depth * 16}px` }}
    >
      <Icon className={`h-4 w-4 shrink-0 ${iconColor}`} />
      <span className="truncate">{entry.name}</span>
    </button>
  );
}

interface FileTreeProps {
  files: PipelineFileEntry[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
}

export default function FileTree({ files, selectedPath, onSelect }: FileTreeProps) {
  if (files.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-600 text-sm italic">
        No files generated yet
      </div>
    );
  }

  return (
    <div className="py-2 space-y-0.5">
      {files.map((entry) => (
        <FileTreeNode key={entry.path} entry={entry} depth={0} selectedPath={selectedPath} onSelect={onSelect} />
      ))}
    </div>
  );
}
