'use client';
import { useEffect, useMemo, useState } from 'react';

interface Run {
  id: string;
  title: string;
  description?: string;
  status: string;
  latency_ms?: number;
  scores?: { score?: number; max_score?: number };
  results?: {
    summary?: string;
    traces?: Trace[];
    memory_hits?: Array<Record<string, unknown>>;
    execution_graph?: { nodes?: string[]; edges?: string[][] };
    score?: { score?: number; max_score?: number };
  };
}

interface Trace {
  node: string;
  depth: number;
  goal: string;
  context_chars: number;
  compressed_chars: number;
  spawned: number;
  memory_hits: number;
}

interface Step {
  id: string;
  agent: string;
  tool?: string;
  status: string;
}

export default function Home() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<Run | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [title, setTitle] = useState('');
  const [goal, setGoal] = useState('');
  const [context, setContext] = useState('');
  const [maxDepth, setMaxDepth] = useState(3);
  const [branchFactor, setBranchFactor] = useState(3);
  const [contextWindow, setContextWindow] = useState(1200);

  const fetchRuns = async () => {
    const res = await fetch('/api/runs', { cache: 'no-store' });
    const data = await res.json();
    setRuns(data);
    setSelected((current) => data.find((run: Run) => run.id === current?.id) ?? data[0] ?? null);
  };

  useEffect(() => {
    fetchRuns();
    const timer = window.setInterval(fetchRuns, 4000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selected?.id) {
      setSteps([]);
      return;
    }
    fetch(`/api/runs/${selected.id}/steps`, { cache: 'no-store' })
      .then((res) => res.ok ? res.json() : [])
      .then(setSteps)
      .catch(() => setSteps([]));
  }, [selected?.id, selected?.status]);

  const metrics = useMemo(() => {
    const completed = runs.filter((run) => run.status === 'completed').length;
    const running = runs.filter((run) => run.status === 'running').length;
    const nodes = runs.reduce((sum, run) => sum + (run.results?.traces?.length ?? 0), 0);
    const avgScore = runs.length
      ? Math.round(runs.reduce((sum, run) => sum + (run.scores?.score ?? run.results?.score?.score ?? 0), 0) / runs.length)
      : 0;
    return { completed, running, nodes, avgScore };
  }, [runs]);

  const createRun = async (event: React.FormEvent) => {
    event.preventDefault();
    await fetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        goal,
        context,
        max_depth: maxDepth,
        branch_factor: branchFactor,
        context_window: contextWindow,
      }),
    });
    setTitle('');
    setGoal('');
    setContext('');
    fetchRuns();
  };

  const executeRun = async (run: Run) => {
    await fetch(`/api/runs/${run.id}/execute`, { method: 'POST' });
    fetchRuns();
  };

  const traces = selected?.results?.traces ?? [];
  const memoryHits = selected?.results?.memory_hits ?? [];

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100">
      <div className="mx-auto grid max-w-7xl gap-6 px-5 py-5 lg:grid-cols-[380px_1fr]">
        <aside className="space-y-5">
          <section className="border-b border-neutral-800 pb-5">
            <h1 className="text-2xl font-semibold">RLM Harness</h1>
            <p className="mt-2 text-sm text-neutral-400">Self-recursive coding agent runs that decompose long context into sandboxed subcalls with persistent memory.</p>
          </section>

          <section className="grid grid-cols-2 gap-3">
            <Metric label="Completed" value={metrics.completed} />
            <Metric label="Running" value={metrics.running} />
            <Metric label="RLM nodes" value={metrics.nodes} />
            <Metric label="Avg score" value={metrics.avgScore} />
          </section>

          <form onSubmit={createRun} className="space-y-3 border-t border-neutral-800 pt-5">
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Run title" className="w-full border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-teal-500" />
            <textarea value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Coding goal" className="min-h-20 w-full border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-teal-500" />
            <textarea value={context} onChange={(e) => setContext(e.target.value)} placeholder="Long context to recursively decompose" className="min-h-36 w-full border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-teal-500" />
            <div className="grid grid-cols-3 gap-2">
              <NumberField label="Depth" value={maxDepth} setValue={setMaxDepth} />
              <NumberField label="Branch" value={branchFactor} setValue={setBranchFactor} />
              <NumberField label="Window" value={contextWindow} setValue={setContextWindow} />
            </div>
            <button className="w-full bg-teal-500 px-3 py-2 text-sm font-medium text-neutral-950 hover:bg-teal-400">Create RLM run</button>
          </form>
        </aside>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_430px]">
          <div className="space-y-3">
            {runs.length === 0 && <div className="border border-neutral-800 p-5 text-sm text-neutral-500">No RLM runs yet.</div>}
            {runs.map((run) => (
              <div key={run.id} onClick={() => setSelected(run)} className={`cursor-pointer border px-4 py-3 ${selected?.id === run.id ? 'border-teal-500 bg-neutral-900' : 'border-neutral-800 bg-neutral-950 hover:bg-neutral-900'}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-medium">{run.title}</div>
                    <div className="mt-1 text-xs text-neutral-500">{run.id}</div>
                  </div>
                  <Status value={run.status} />
                </div>
                <div className="mt-3 line-clamp-2 text-sm text-neutral-400">{run.description}</div>
                <div className="mt-3 flex items-center gap-3 text-xs text-neutral-400">
                  <span>{run.results?.traces?.length ?? 0} nodes</span>
                  <span>{formatLatency(run.latency_ms)}</span>
                  <span>Score {run.scores?.score ?? run.results?.score?.score ?? 0}</span>
                  <button
                    disabled={run.status === 'running'}
                    onClick={(event) => { event.stopPropagation(); executeRun(run); }}
                    className="ml-auto border border-teal-700 px-3 py-1 text-teal-200 hover:bg-teal-950 disabled:cursor-not-allowed disabled:border-neutral-800 disabled:text-neutral-600"
                  >
                    {run.status === 'running' ? 'Running' : 'Execute'}
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-5 border-l border-neutral-800 pl-6">
            <Panel title="Summary">
              <div className="text-sm leading-6 text-neutral-300">{selected?.results?.summary ?? 'Select or execute a run to see the recursive result.'}</div>
            </Panel>

            <Panel title="Recursive Graph">
              <div className="flex flex-wrap gap-2">
                {(selected?.results?.execution_graph?.nodes ?? ['root']).map((node) => (
                  <span key={node} className="border border-neutral-700 px-2 py-1 text-xs text-neutral-300">{node}</span>
                ))}
              </div>
            </Panel>

            <Panel title="Memory Hits">
              {memoryHits.length === 0 && <div className="text-sm text-neutral-500">No matching memory yet.</div>}
              {memoryHits.map((hit, index) => (
                <pre key={index} className="mt-2 max-h-32 overflow-auto border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-400">{JSON.stringify(hit, null, 2)}</pre>
              ))}
            </Panel>

            <Panel title="Sandbox Steps">
              {steps.length === 0 && <div className="text-sm text-neutral-500">No persisted steps yet.</div>}
              {steps.map((step) => (
                <div key={step.id} className="mb-2 flex items-center justify-between border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm">
                  <span>{step.agent}</span>
                  <span className="text-xs text-neutral-500">{step.tool}</span>
                  <Status value={step.status} />
                </div>
              ))}
            </Panel>

            <Panel title="Trace">
              {traces.length === 0 && <div className="text-sm text-neutral-500">No trace yet.</div>}
              {traces.map((trace) => (
                <pre key={trace.node} className="mb-2 overflow-auto border border-neutral-800 bg-neutral-900 p-3 text-xs text-neutral-300">{JSON.stringify(trace, null, 2)}</pre>
              ))}
            </Panel>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="border border-neutral-800 bg-neutral-900 p-3">
      <div className="text-xs uppercase text-neutral-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function NumberField({ label, value, setValue }: { label: string; value: number; setValue: (value: number) => void }) {
  return (
    <label className="text-xs text-neutral-500">
      {label}
      <input type="number" value={value} onChange={(e) => setValue(Number(e.target.value))} className="mt-1 w-full border border-neutral-700 bg-neutral-900 px-2 py-2 text-sm text-neutral-100 outline-none focus:border-teal-500" />
    </label>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase text-neutral-500">{title}</h2>
      {children}
    </section>
  );
}

function Status({ value }: { value: string }) {
  const color = ['completed', 'success'].includes(value) ? 'text-emerald-300' : ['failed', 'failure'].includes(value) ? 'text-red-300' : 'text-amber-300';
  return <span className={`text-xs font-medium uppercase ${color}`}>{value}</span>;
}

function formatLatency(value?: number) {
  if (!value || value <= 0) return '0 ms';
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}
