import React from "react";
import { Header } from "./components/Header";
import { HealthStatus } from "./components/HealthStatus";
import { Instructions } from "./components/Instructions";
import { RepositoryIngestion } from "./components/RepositoryIngestion";

export const App: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 selection:bg-indigo-100 selection:text-indigo-900 font-sans">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Workspace Utility Heading */}
        <section className="border-b border-slate-200 pb-5">
          <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
            <div>
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                Repository Analysis Workspace
              </h1>
              <p className="text-xs text-slate-600 mt-0.5 max-w-3xl leading-relaxed">
                Deterministic static analysis, concrete AST parsing, dependency graph extraction, and transparent software health scoring.
              </p>
            </div>
            <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-500">
              <span>Host: Linux / Windows</span>
              <span>&bull;</span>
              <span>Parser: Tree-sitter AST</span>
            </div>
          </div>
        </section>

        {/* Repository Ingestion & Multi-Tab Analysis Dashboard */}
        <section>
          <RepositoryIngestion />
        </section>

        {/* Live Subsystem Probes (API, PostgreSQL, Redis) */}
        <section>
          <HealthStatus />
        </section>

        {/* Instructions Section (Workflow Guide) */}
        <section>
          <Instructions />
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white py-5 mt-8 text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>Codebase Intelligence Engine &bull; Production Release v0.1.0</div>
          <div className="flex items-center space-x-4">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-900 transition"
            >
              OpenAPI Docs
            </a>
            <span>&bull;</span>
            <a
              href="http://localhost:8000/redoc"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-900 transition"
            >
              ReDoc
            </a>
            <span>&bull;</span>
            <a
              href="http://localhost:8000/live"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-900 transition"
            >
              Liveness Probe
            </a>
            <span>&bull;</span>
            <a
              href="http://localhost:8000/ready"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-900 transition"
            >
              Readiness Probe
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};
