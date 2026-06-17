import { Highlight, themes } from 'prism-react-renderer';
import { Loader2, FileX } from 'lucide-react';

const EXT_TO_LANG: Record<string, string> = {
  '.py': 'python',
  '.js': 'javascript',
  '.ts': 'typescript',
  '.tsx': 'tsx',
  '.jsx': 'jsx',
  '.json': 'json',
  '.md': 'markdown',
  '.css': 'css',
  '.html': 'html',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.sh': 'bash',
};

function getLanguage(filename: string): string {
  const ext = filename.includes('.') ? `.${filename.split('.').pop()}` : '';
  return EXT_TO_LANG[ext] || 'python';
}

interface CodePreviewProps {
  filename: string;
  content: string;
  loading?: boolean;
  error?: string;
}

export default function CodePreview({ filename, content, loading, error }: CodePreviewProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-500">
        <FileX className="h-8 w-8 text-red-400" />
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  const language = getLanguage(filename);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900/80 px-4 py-2">
        <span className="text-xs font-medium text-slate-400">{filename}</span>
        <span className="text-[10px] text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">{language}</span>
      </div>
      <div className="flex-1 overflow-auto">
        <Highlight theme={themes.nightOwl} code={content.trimEnd()} language={language}>
          {({ className, style, tokens, getLineProps, getTokenProps }) => (
            <pre className={`${className} m-0 p-4 text-xs leading-relaxed`} style={style}>
              {tokens.map((line, i) => {
                const lineProps = getLineProps({ line });
                return (
                  <div key={i} {...lineProps} style={{ ...lineProps.style, display: 'flex' }}>
                    <span className="mr-4 select-none text-slate-600 text-right w-8 shrink-0">
                      {i + 1}
                    </span>
                    <span className="flex-1">
                      {line.map((token, key) => (
                        <span key={key} {...getTokenProps({ token })} />
                      ))}
                    </span>
                  </div>
                );
              })}
            </pre>
          )}
        </Highlight>
      </div>
    </div>
  );
}
