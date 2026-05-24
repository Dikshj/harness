'use client';
import { useEffect, useMemo, useState } from 'react';

interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  retries?: number;
  latency_ms?: number;
  scores?: { score?: number; max_score?: number };
  results?: {
    execution_graph?: { nodes?: string[]; edges?: string[][] };
    traces?: Array<Record<string, unknown>>;
    eval_result?: { score?: number; max_score?: number };
    pr_lifecycle?: PullRequestLifecycle;
  };
}

interface ExecutionStep {
  id: string;
  agent: string;
  status: string;
  output_payload?: Record<string, unknown>;
}

interface PullRequestLifecycle {
  dry_run: boolean;
  branch: string;
  base_branch: string;
  has_changes: boolean;
  pr_body: string;
  error?: string;
  skipped?: string;
}

export default function Home() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selected, setSelected] = useState<Task | null>(null);
  const [steps, setSteps] = useState<ExecutionStep[]>([]);
  const [preparingPr, setPreparingPr] = useState(false);
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [repoPath, setRepoPath] = useState('.');
  const [testCommand, setTestCommand] = useState('pytest');

  const fetchTasks = async () => {
    const res = await fetch('/api/tasks', { cache: 'no-store' });
    const data = await res.json();
    setTasks(data);
    setSelected((current) => data.find((task: Task) => task.id === current?.id) ?? data[0] ?? null);
  };

  useEffect(() => {
    fetchTasks();
    const timer = window.setInterval(fetchTasks, 5000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selected?.id) {
      setSteps([]);
      return;
    }
    fetch(`/api/tasks/${selected.id}/steps`, { cache: 'no-store' })
      .then((res) => res.ok ? res.json() : [])
      .then(setSteps)
      .catch(() => setSteps([]));
  }, [selected?.id, selected?.status]);

  const metrics = useMemo(() => {
    const completed = tasks.filter((task) => task.status === 'completed').length;
    const failed = tasks.filter((task) => task.status === 'failed').length;
    const retries = tasks.reduce((sum, task) => sum + (task.retries ?? 0), 0);
    const completedLatencies = tasks
      .map((task) => task.latency_ms ?? 0)
      .filter((latency) => latency > 0);
    const averageLatency = completedLatencies.length
      ? Math.round(completedLatencies.reduce((sum, latency) => sum + latency, 0) / completedLatencies.length)
      : 0;
    const averageScore = tasks.length
      ? Math.round(tasks.reduce((sum, task) => sum + (task.scores?.score ?? task.results?.eval_result?.score ?? 0), 0) / tasks.length)
      : 0;
    return { completed, failed, retries, averageScore, averageLatency };
  }, [tasks]);

  const createTask = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description: desc, repo_path: repoPath, test_command: testCommand }),
    });
    setTitle('');
    setDesc('');
    fetchTasks();
  };

  const runTask = async (task: Task) => {
    await fetch(`/api/tasks/${task.id}/run`, { method: 'POST' });
    fetchTasks();
  };

  const preparePullRequest = async (task: Task) => {
    setPreparingPr(true);
    await fetch(`/api/tasks/${task.id}/pull-request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dry_run: true }),
    });
    await fetchTasks();
    setPreparingPr(false);
  };

  const traces = selected?.results?.traces ?? [];
  const graphNodes = selected?.results?.execution_graph?.nodes ?? [];
  const prLifecycle = selected?.results?.pr_lifecycle;

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-6">
          <section className="border-b border-zinc-800 pb-5">
            <h1 className="text-2xl font-semibold">Autonomous Engineering Harness</h1>
            <p className="mt-2 text-sm text-zinc-400">Agent planning, sandbox execution, evaluation, retry loops, and observability in one control plane.</p>
          </section>

          <section className="grid grid-cols-2 gap-3">
            <Metric label="Completed" value={metrics.completed} />
            <Metric label="Failed" value={metrics.failed} />
            <Metric label="Retries" value={metrics.retries} />
            <Metric label="Avg score" value={metrics.averageScore} />
            <Metric label="Avg latency" value={formatLatency(metrics.averageLatency)} />
          </section>

          <form onSubmit={createTask} className="space-y-3 border-t border-zinc-800 pt-5">
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Task title" className="w-full border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-cyan-500" />
            <textarea value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="GitHub issue or coding task" className="min-h-24 w-full border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-cyan-500" />
            <input value={repoPath} onChange={(e) => setRepoPath(e.target.value)} placeholder="Repository path" className="w-full border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-cyan-500" />
            <input value={testCommand} onChange={(e) => setTestCommand(e.target.value)} placeholder="Test command" className="w-full border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-cyan-500" />
            <button className="w-full bg-cyan-500 px-3 py-2 text-sm font-medium text-zinc-950 hover:bg-cyan-400">Create task</button>
          </form>
        </aside>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-3">
            {tasks.map((task) => (
              <div key={task.id} onClick={() => setSelected(task)} className={`w-full cursor-pointer border px-4 py-3 text-left ${selected?.id === task.id ? 'border-cyan-500 bg-zinc-900' : 'border-zinc-800 bg-zinc-950 hover:bg-zinc-900'}`}>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-medium">{task.title}</div>
                    <div className="mt-1 text-xs text-zinc-500">{task.id}</div>
                  </div>
                  <Status value={task.status} />
                </div>
                <div className="mt-3 flex items-center gap-3 text-xs text-zinc-400">
                  <span>Score {task.scores?.score ?? task.results?.eval_result?.score ?? 0}</span>
                  <span>Retries {task.retries ?? 0}</span>
                  <span>{formatLatency(task.latency_ms)}</span>
                  <button
                    disabled={task.status === 'running'}
                    onClick={(e) => { e.stopPropagation(); runTask(task); }}
                    className="ml-auto border border-emerald-700 px-3 py-1 text-emerald-300 hover:bg-emerald-950 disabled:cursor-not-allowed disabled:border-zinc-800 disabled:text-zinc-600 disabled:hover:bg-transparent"
                  >
                    {task.status === 'running' ? 'Running' : 'Run'}
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-6 border-l border-zinc-800 pl-6">
            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Execution DAG</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {(graphNodes.length ? graphNodes : ['repo_context', 'planner', 'coder', 'tester', 'reviewer', 'eval']).map((node) => (
                  <span key={node} className="border border-zinc-700 px-2 py-1 text-xs text-zinc-300">{node}</span>
                ))}
              </div>
            </section>

            <section>
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Pull request</h2>
                {selected && (
                  <button
                    onClick={() => preparePullRequest(selected)}
                    disabled={preparingPr}
                    className="border border-cyan-700 px-3 py-1 text-xs text-cyan-200 hover:bg-cyan-950 disabled:cursor-not-allowed disabled:border-zinc-800 disabled:text-zinc-600"
                  >
                    {preparingPr ? 'Preparing' : 'Prepare'}
                  </button>
                )}
              </div>
              <div className="mt-3 border border-zinc-800 bg-zinc-900 p-3 text-sm text-zinc-300">
                {!prLifecycle && <div className="text-zinc-500">No PR artifact prepared.</div>}
                {prLifecycle && (
                  <div className="space-y-2">
                    <div>Branch <span className="text-cyan-300">{prLifecycle.branch}</span></div>
                    <div>Base <span className="text-zinc-100">{prLifecycle.base_branch}</span></div>
                    <div>Changes <span className={prLifecycle.has_changes ? 'text-emerald-300' : 'text-amber-300'}>{prLifecycle.has_changes ? 'detected' : 'none detected'}</span></div>
                    {prLifecycle.error && <div className="text-red-300">{prLifecycle.error}</div>}
                    {prLifecycle.skipped && <div className="text-amber-300">{prLifecycle.skipped}</div>}
                    <pre className="max-h-48 overflow-auto border border-zinc-800 bg-zinc-950 p-2 text-xs text-zinc-400">{prLifecycle.pr_body}</pre>
                  </div>
                )}
              </div>
            </section>

            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Evaluation</h2>
              <div className="mt-3 text-5xl font-semibold text-cyan-300">{selected?.scores?.score ?? selected?.results?.eval_result?.score ?? 0}</div>
              <div className="text-sm text-zinc-500">out of {selected?.scores?.max_score ?? selected?.results?.eval_result?.max_score ?? 100}</div>
            </section>

            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Steps</h2>
              <div className="mt-3 space-y-2">
                {steps.length === 0 && <div className="text-sm text-zinc-500">No persisted steps yet.</div>}
                {steps.map((step) => (
                  <div key={step.id} className="flex items-center justify-between border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm">
                    <span className="text-zinc-200">{step.agent}</span>
                    <Status value={step.status} />
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Trace</h2>
              <div className="mt-3 space-y-2">
                {traces.length === 0 && <div className="text-sm text-zinc-500">No execution trace yet.</div>}
                {traces.map((trace, index) => (
                  <pre key={index} className="overflow-auto border border-zinc-800 bg-zinc-900 p-3 text-xs text-zinc-300">{JSON.stringify(trace, null, 2)}</pre>
                ))}
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="border border-zinc-800 bg-zinc-900 p-3">
      <div className="text-xs uppercase tracking-wide text-zinc-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function Status({ value }: { value: string }) {
  const color = ['completed', 'success'].includes(value) ? 'text-emerald-300' : ['failed', 'failure'].includes(value) ? 'text-red-300' : 'text-amber-300';
  return <span className={`text-xs font-medium uppercase ${color}`}>{value}</span>;
}

function formatLatency(value?: number) {
  if (!value || value <= 0) {
    return '0 ms';
  }
  if (value < 1000) {
    return `${Math.round(value)} ms`;
  }
  return `${(value / 1000).toFixed(1)} s`;
}
