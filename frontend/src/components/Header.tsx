import React from "react";
import { Terminal, BookOpen } from "lucide-react";

export const Header: React.FC = () => {
  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-1.5 bg-indigo-600 border border-indigo-700 rounded-md text-white shadow-sm">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-bold tracking-tight text-slate-900 font-mono">
                Codebase Intelligence Engine
              </h1>
              <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 font-mono">
                v0.1.0
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center space-x-1.5 font-mono text-slate-700 hover:text-slate-900 px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200/70 border border-slate-200 transition"
          >
            <BookOpen className="w-3.5 h-3.5 text-slate-500" />
            <span>API Docs</span>
          </a>

          <div className="hidden sm:flex items-center space-x-1.5 font-mono text-slate-700 px-2.5 py-1 rounded bg-slate-100 border border-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span className="text-[11px]">Zero-Execution Sandbox</span>
          </div>
        </div>
      </div>
    </header>
  );
};
