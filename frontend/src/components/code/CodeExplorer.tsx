import { useState, useCallback, useEffect, useRef } from 'react';
import { Download, FileCode2, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import type { PipelineFileEntry } from '../../types/pipeline';
import FileTree from './FileTree';
import CodePreview from './CodePreview';

interface CodeExplorerProps {
  correlationId: string;
}

export default function CodeExplorer({ correlationId }: CodeExplorerProps) {
  const [files, setFiles] = useState<PipelineFileEntry[] | null>(null);
  const [filesLoading, setFilesLoading] = useState(true);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [content, setContent] = useState<string>('');
  const [contentLoading, setContentLoading] = useState(false);
  const [contentError, setContentError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const treeScrollRef = useRef<HTMLDivElement>(null);
  const selectedPathRef = useRef<string | null>(null);

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

  useEffect(() => {
    if (!selectedPath) return;
    if (selectedPathRef.current === selectedPath) return;
    selectedPathRef.current = selectedPath;
    setContentLoading(true);
    setContentError(null);
    api.getFileContent(correlationId, selectedPath)
      .then((res) => setContent(res.content))
      .catch((err) => setContentError(err.message))
      .finally(() => setContentLoading(false));
  }, [correlationId, selectedPath]);

  const handleSelect = useCallback((path: string) => {
    setSelectedPath(path);
    setContent('');
    setContentLoading(true);
    setContentError(null);
    api.getFileContent(correlationId, path)
      .then((res) => setContent(res.content))
      .catch((err) => setContentError(err.message))
      .finally(() => setContentLoading(false));
  }, [correlationId]);

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
            <FileTree files={files} selectedPath={selectedPath} onSelect={handleSelect} />
          </div>
          <div className="flex-1 overflow-hidden">
            {selectedPath ? (
              <CodePreview
                filename={selectedPath}
                content={content}
                loading={contentLoading}
                error={contentError || undefined}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-slate-600 text-sm">
                Select a file to preview
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
