import { useEffect, useState } from 'react';
import { Save, RefreshCw, Server, Key, Thermometer, Sliders, Cpu, Wifi, WifiOff } from 'lucide-react';
import { api, type LLMConfig, type OllamaModel } from '../services/api';

const PROVIDERS = [
  { value: 'ollama', label: 'Ollama (Local)' },
  { value: 'openai', label: 'OpenAI Compatible' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'mock', label: 'Mock (Offline)' },
];

const COMMON_MODELS: Record<string, string[]> = {
  ollama: ['llama3.2:1b', 'llama3.2:3b', 'llama3.1:8b', 'mistral:latest', 'phi3:mini', 'gemma2:2b'],
  openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'deepseek-v4-flash', 'deepseek-chat', 'claude-3-haiku', 'claude-3-sonnet'],
  gemini: ['gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  mock: ['mock'],
};

export default function Settings() {
  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);

  useEffect(() => {
    api.getConfig().then(setConfig);
  }, []);

  const provider = config?.EMASDEP_LLM_PROVIDER || 'ollama';

  const refreshOllamaModels = async () => {
    setLoadingModels(true);
    try {
      const res = await api.listOllamaModels();
      setOllamaModels(res.models || []);
    } catch { }
    setLoadingModels(false);
  };

  const update = (key: keyof LLMConfig, value: string) => {
    if (!config) return;
    setConfig({ ...config, [key]: value });
  };

  const save = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const result = await api.updateConfig(config);
      setConfig(result);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { }
    setSaving(false);
  };

  const testConnection = async () => {
    if (!config) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await api.testConfig(config);
      setTestResult(result);
    } catch (err) {
      setTestResult({ status: 'error', message: (err as Error).message });
    }
    setTesting(false);
  };

  if (!config) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin w-8 h-8 text-emasdep-400" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-6 px-4 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Settings</h1>
        <p className="text-slate-400 mt-1">Configure your LLM provider and portal preferences</p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
        <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-emasdep-400" />
          LLM Provider
        </h2>

        <div className="grid gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1 flex items-center gap-1">
              <Server className="w-4 h-4" /> Provider
            </label>
            <select
              value={provider}
              onChange={(e) => update('EMASDEP_LLM_PROVIDER', e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:ring-2 focus:ring-emasdep-500 focus:outline-none"
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>

          {(provider === 'openai' || provider === 'gemini') && (
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1 flex items-center gap-1">
                <Key className="w-4 h-4" /> API Key
              </label>
              <input
                type="password"
                value={config.EMASDEP_LLM_API_KEY}
                onChange={(e) => update('EMASDEP_LLM_API_KEY', e.target.value)}
                placeholder={provider === 'gemini' ? 'AIza...' : 'sk-...'}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:ring-2 focus:ring-emasdep-500 focus:outline-none"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Base URL</label>
            <input
              type="url"
              value={config.EMASDEP_LLM_BASE_URL}
              onChange={(e) => update('EMASDEP_LLM_BASE_URL', e.target.value)}
              placeholder={provider === 'ollama' ? 'http://127.0.0.1:11434' : 'https://api.openai.com/v1'}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:ring-2 focus:ring-emasdep-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Model</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={config.EMASDEP_LLM_MODEL}
                onChange={(e) => update('EMASDEP_LLM_MODEL', e.target.value)}
                list="model-suggestions"
                placeholder="llama3.2:1b"
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:ring-2 focus:ring-emasdep-500 focus:outline-none"
              />
              {provider === 'ollama' && (
                <button
                  onClick={refreshOllamaModels}
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-300 hover:bg-slate-700"
                  title="Refresh local models"
                >
                  <RefreshCw className={`w-4 h-4 ${loadingModels ? 'animate-spin' : ''}`} />
                </button>
              )}
            </div>
            <datalist id="model-suggestions">
              {(ollamaModels.length > 0
                ? ollamaModels.map((m) => m.name)
                : COMMON_MODELS[provider] || []
              ).map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
            {ollamaModels.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {ollamaModels.map((m) => (
                  <button
                    key={m.name}
                    onClick={() => update('EMASDEP_LLM_MODEL', m.name)}
                    className={`text-xs px-2 py-0.5 rounded-full border cursor-pointer transition-colors ${config.EMASDEP_LLM_MODEL === m.name
                        ? 'bg-emasdep-600 border-emasdep-500 text-white'
                        : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500'
                      }`}
                  >
                    {m.name.replace(':latest', '')}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1 flex items-center gap-1">
                <Thermometer className="w-4 h-4" /> Temperature
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={config.EMASDEP_LLM_TEMPERATURE}
                  onChange={(e) => update('EMASDEP_LLM_TEMPERATURE', e.target.value)}
                  className="flex-1 accent-emasdep-500"
                />
                <span className="text-slate-300 w-8 text-right text-sm">{config.EMASDEP_LLM_TEMPERATURE}</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1 flex items-center gap-1">
                <Sliders className="w-4 h-4" /> Max Tokens
              </label>
              <input
                type="number"
                min={256}
                max={131072}
                step={256}
                value={config.EMASDEP_LLM_MAX_TOKENS}
                onChange={(e) => update('EMASDEP_LLM_MAX_TOKENS', e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:ring-2 focus:ring-emasdep-500 focus:outline-none"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={testConnection}
            disabled={testing}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-lg text-slate-200 font-medium transition-colors border border-slate-700"
          >
            {testing ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Wifi className="w-4 h-4" />
            )}
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 bg-emasdep-600 hover:bg-emasdep-500 disabled:opacity-50 rounded-lg text-white font-medium transition-colors"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
          {saved && (
            <span className="text-emerald-400 text-sm animate-pulse">Saved!</span>
          )}
        </div>
        {testResult && (
          <div className={`flex items-start gap-2 p-3 rounded-lg border text-sm mt-2 ${
            testResult.status === 'ok'
              ? 'bg-emerald-950/20 border-emerald-800 text-emerald-300'
              : 'bg-red-950/20 border-red-800 text-red-300'
          }`}>
            {testResult.status === 'ok' ? <Wifi className="w-4 h-4 mt-0.5 shrink-0" /> : <WifiOff className="w-4 h-4 mt-0.5 shrink-0" />}
            <span>{testResult.message}</span>
          </div>
        )}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-slate-200 mb-2">System Info</h2>
        <div className="text-sm text-slate-400 space-y-1">
          <p>Environment: <span className="text-slate-300">{config.EMASDEP_ENV}</span></p>
          <p>Provider: <span className="text-slate-300">{provider}</span></p>
          <p>Model: <span className="text-slate-300">{config.EMASDEP_LLM_MODEL}</span></p>
        </div>
      </div>
    </div>
  );
}
