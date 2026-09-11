import React from "react";
import { GitBranch, Layers, AlertCircle, GitCompare, Download } from "lucide-react";

interface Step {
  step: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const STEPS: Step[] = [
  {
    step: "01",
    title: "Analyze a Repository",
    description:
      "Enter a public GitHub or GitLab repository URL. The engine executes an isolated shallow clone, AST parse, and dependency extraction with zero code execution.",
    icon: GitBranch,
  },
  {
    step: "02",
    title: "Review Results",
    description:
      "Explore the 5-pillar software health score, AST symbol hierarchy, complexity distributions, dependency cycles, and git churn hotspots.",
    icon: Layers,
  },
  {
    step: "03",
    title: "Investigate Issues",
    description:
      "Inspect deterministic rule diagnostics across architecture, maintainability, duplication (DUP-001), and hygiene with concrete remediation effort estimates.",
    icon: AlertCircle,
  },
  {
    step: "04",
    title: "Compare Analyses",
    description:
      "Compare two runs of the same repository to evaluate automated PR Quality Gates (PASSED, WARNING, FAILED) and track longitudinal health trajectory.",
    icon: GitCompare,
  },
  {
    step: "05",
    title: "Export Results",
    description:
      "Download audit artifacts in OASIS SARIF v2.1.0 format for CI/CD integration, executive Markdown summaries, or consolidated JSON snapshots.",
    icon: Download,
  },
];

export const Instructions: React.FC = () => {
  return (
    <section className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between pb-4 border-b border-slate-200 mb-5 gap-2">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 font-semibold">Workflow Guide</div>
          <h2 className="text-base font-semibold text-slate-900 tracking-tight mt-0.5">
            How to Use the Codebase Intelligence Engine
          </h2>
        </div>
        <div className="text-xs font-mono text-slate-500">5-Step Analysis Workflow</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {STEPS.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.step}
              className="p-4 rounded-lg border border-slate-200 bg-slate-50/70 flex flex-col justify-between hover:border-slate-300 hover:bg-white transition"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                    {item.step}
                  </span>
                  <Icon className="w-4 h-4 text-slate-500" />
                </div>
                <h3 className="text-sm font-semibold text-slate-900">{item.title}</h3>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">{item.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
