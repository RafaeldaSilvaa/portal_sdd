import { useState, useCallback, useEffect, useRef } from 'react';
import { Download, FileCode2, Loader2, X } from 'lucide-react';
import { api } from '../../services/api';
import type { PipelineFileEntry } from '../../types/pipeline';
import FileTree from './FileTree';
import CodePreview from './CodePreview';

interface CodeExplorerProps {
  correlationId: string;
}

interface Tab {
  path: string;
  content: string;
  loading: boolean;
  error?: string;
}

export default function CodeExplorer({ correlationId }: CodeExplorerProps) {
  const [files, setFiles] = useState<PipelineFileEntry[] | null>(null);
  const [filesLoading, setFilesLoading] = useState(true);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [activeTabPath, setActiveTabPath] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const treeScrollRef = useRef<HTMLDivElement>(null);

  const fetchFiles = useCallback(async (initial = false) => {
    if (initial) setFilesLoading(true);
    try {
      const result = await api.listFiles(correlationId);
      setFiles(result);
      setFilesError(null);
    } catch (err) {
      if (initial) setFilesError((err as Error).message);
    } finally {
      if (initial) setFilesLoading(false);
    }
  }, [correlationId]);

  useEffect(() => {
    fetchFiles(true);
    pollRef.current = setInterval(() => fetchFiles(false), 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchFiles]);

  const openTab = useCallback(async (path: string) => {
    setActiveTabPath(path);
    const existing = tabs.find((t) => t.path === path);
    if (existing) return;

    const newTab: Tab = { path, content: '', loading: true };
    setTabs((prev) => [...prev, newTab]);

    try {
      const res = await api.getFileContent(correlationId, path);
      setTabs((prev) => prev.map((t) => t.path === path ? { ...t, content: res.content, loading: false } : t));
    } catch (err) {
      setTabs((prev) => prev.map((t) => t.path === path ? { ...t, error: (err as Error).message, loading: false } : t));
    }
  }, [correlationId, tabs]);

  const closeTab = useCallback((path: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const idx = tabs.findIndex((t) => t.path === path);
    setTabs((prev) => prev.filter((t) => t.path !== path));
    if (activeTabPath === path) {
      const remaining = tabs.filter((t) => t.path !== path);
      if (remaining.length > 0) {
        const nextIdx = Math.min(idx, remaining.length - 1);
        setActiveTabPath(remaining[nextIdx].path);
      } else {
        setActiveTabPath(null);
      }
    }
  }, [tabs, activeTabPath]);

  const handleSelect = useCallback((path: string) => {
    openTab(path);
  }, [openTab]);

  const activeTab = tabs.find((t) => t.path === activeTabPath);
  const downloadUrl = api.getDownloadUrl(correlationId);
  const hasFiles = files && files.length > 0;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div className="flex items-center gap-2">
          <FileCode2 className="h-4 w-4 text-emasdep-400" />
          <h3 className="text-sm font-semibold text-slate-300">Generated Artifacts</h3>
          {files && <span className="text-xs text-slate-500">{files.length} files</span>}
        </div>
        {hasFiles && (
          <a
            href={downloadUrl}
            download
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            Download All
          </a>
        )}
      </div>

      {filesLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
        </div>
      ) : filesError ? (
        <div className="flex items-center justify-center py-16 text-slate-500 text-sm">
          {filesError}
        </div>
      ) : !hasFiles ? (
        <div className="flex items-center justify-center py-16 text-slate-600 text-sm italic">
          No artifacts generated yet. Run a pipeline to see files here.
        </div>
      ) : (
        <div className="flex h-96">
          <div ref={treeScrollRef} className="w-56 shrink-0 border-r border-slate-800 overflow-y-auto bg-slate-900/30">
            <FileTree files={files} selectedPath={activeTabPath} onSelect={handleSelect} />
          </div>
          <div className="flex flex-1 flex-col overflow-hidden">
            {tabs.length > 0 && (
              <div className="flex shrink-0 border-b border-slate-800 overflow-x-auto bg-slate-900/60">
                {tabs.map((tab) => {
                  const isActive = tab.path === activeTabPath;
                  return (
                    <button
                      key={tab.path}
                      onClick={() => setActiveTabPath(tab.path)}
                      className={`flex items-center gap-1 px-3 py-1.5 text-xs border-r border-slate-800 transition-colors shrink-0 ${
                        isActive
                          ? 'bg-slate-800 text-emasdep-300 border-t border-t-emasdep-500'
                          : 'bg-slate-900/40 text-slate-500 hover:bg-slate-800/50 hover:text-slate-300'
                      }`}
                    >
                      <span className="max-w-32 truncate">{tab.path.split('/').pop()}</span>
                      <X
                        className="h-3 w-3 ml-1 hover:text-red-400 shrink-0"
                        onClick={(e) => closeTab(tab.path, e)}
                      />
                    </button>
                  );
                })}
              </div>
            )}
            <div className="flex-1 overflow-hidden">
              {activeTab ? (
                <CodePreview
                  filename={activeTab.path}
                  content={activeTab.content}
                  loading={activeTab.loading}
                  error={activeTab.error}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-600 text-sm">
                  Select a file to preview
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
