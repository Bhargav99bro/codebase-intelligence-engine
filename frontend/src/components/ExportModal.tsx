import React, { useState } from "react";
import {
  Download,
  FileText,
  FileCode,
  FileJson,
  Copy,
  Check,
  X,
} from "lucide-react";
import { apiService } from "../services/api";

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysisId: string;
}

export const ExportModal: React.FC<ExportModalProps> = ({ isOpen, onClose, analysisId }) => {
  const [copied, setCopied] = useState(false);
  const [copying, setCopying] = useState(false);

  if (!isOpen) return null;

  const sarifUrl = apiService.getExportUrl(analysisId, "sarif");
  const markdownUrl = apiService.getExportUrl(analysisId, "markdown");
  const jsonUrl = apiService.getExportUrl(analysisId, "json");

  const handleCopyMarkdown = async () => {
    try {
      setCopying(true);
      const mdContent = await apiService.getMarkdownReport(analysisId);
      await navigator.clipboard.writeText(mdContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (e) {
      console.error("Failed to copy markdown", e);
    } finally {
      setCopying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-6 overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Download className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Export Intelligence Report</h3>
              <p className="text-xs text-slate-400">Standard export formats for CI/CD, IDEs, and architectural reviews</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Options List */}
        <div className="py-6 space-y-4">
          {/* 1. SARIF v2.1.0 */}
          <div className="flex items-start justify-between p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition">
            <div className="flex items-start space-x-3">
              <FileCode className="w-6 h-6 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-sm text-slate-100">OASIS SARIF v2.1.0</h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Static Analysis Results Interchange Format. Ideal for GitHub Code Scanning, SonarQube, and VS Code.
                </p>
              </div>
            </div>
            <a
              href={sarifUrl}
              download={`analysis-${analysisId}.sarif`}
              className="flex items-center px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shrink-0 transition"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              .sarif
            </a>
          </div>

          {/* 2. Executive Markdown */}
          <div className="flex items-start justify-between p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition">
            <div className="flex items-start space-x-3">
              <FileText className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-sm text-slate-100">Executive Markdown Audit Report</h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Full architectural report formatted in GitHub Flavored Markdown for PR comments, wikis, and audits.
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2 shrink-0">
              <button
                onClick={handleCopyMarkdown}
                disabled={copying}
                className="flex items-center px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400 mr-1.5" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 mr-1.5" />
                    Copy
                  </>
                )}
              </button>
              <a
                href={markdownUrl}
                download={`analysis-${analysisId}-report.md`}
                className="flex items-center px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
              >
                <Download className="w-3.5 h-3.5 mr-1.5" />
                .md
              </a>
            </div>
          </div>

          {/* 3. Consolidated JSON */}
          <div className="flex items-start justify-between p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition">
            <div className="flex items-start space-x-3">
              <FileJson className="w-6 h-6 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-sm text-slate-100">Consolidated JSON Intelligence Payload</h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Complete machine-readable dump with schema_version: "1.0", health scores, hotspots, and dependencies.
                </p>
              </div>
            </div>
            <a
              href={jsonUrl}
              download={`analysis-${analysisId}-export.json`}
              className="flex items-center px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shrink-0 transition"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              .json
            </a>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex justify-end pt-3 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
