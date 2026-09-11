import React, { useState, useEffect } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
} from "lucide-react";
import { QualityGateResponse } from "../types/api";
import { apiService } from "../services/api";

interface QualityGateBadgeProps {
  analysisId: string;
  initialData?: QualityGateResponse;
}

export const QualityGateBadge: React.FC<QualityGateBadgeProps> = ({ analysisId, initialData }) => {
  const [data, setData] = useState<QualityGateResponse | null>(initialData || null);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(!initialData);

  useEffect(() => {
    if (initialData) {
      setData(initialData);
      setLoading(false);
      return;
    }

    let isMounted = true;
    apiService
      .getQualityGate(analysisId)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [analysisId, initialData]);

  if (loading || !data) {
    return (
      <div className="inline-flex items-center px-3 py-1.5 rounded-md bg-slate-100 border border-slate-200 text-xs text-slate-500 animate-pulse">
        <div className="w-3.5 h-3.5 mr-2 rounded-full bg-slate-200" />
        Evaluating Quality Gate...
      </div>
    );
  }

  const isPassed = data.status === "PASSED";
  const isWarning = data.status === "WARNING";
  const isFailed = data.status === "FAILED";

  const getStatusStyles = () => {
    if (isPassed) {
      return {
        badge: "bg-emerald-50 border-emerald-200 text-emerald-800 hover:bg-emerald-100/80",
        icon: <CheckCircle2 className="w-4 h-4 text-emerald-600 mr-2 shrink-0" />,
        text: "PASSED",
      };
    }
    if (isWarning) {
      return {
        badge: "bg-amber-50 border-amber-200 text-amber-800 hover:bg-amber-100/80",
        icon: <AlertTriangle className="w-4 h-4 text-amber-600 mr-2 shrink-0" />,
        text: "WARNING",
      };
    }
    return {
      badge: "bg-rose-50 border-rose-200 text-rose-800 hover:bg-rose-100/80",
      icon: <XCircle className="w-4 h-4 text-rose-600 mr-2 shrink-0" />,
      text: "FAILED",
    };
  };

  const style = getStatusStyles();

  return (
    <div className="relative inline-block text-left">
      {/* Trigger Button / Badge */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`flex items-center px-3 py-1.5 rounded-md border text-xs font-semibold tracking-wide transition shadow-sm ${style.badge}`}
      >
        {style.icon}
        <span>QUALITY GATE: {style.text}</span>
        <span className="ml-2 text-[11px] opacity-75">
          ({data.passed_count}/{data.total_conditions} passing)
        </span>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 ml-1.5 opacity-70" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 ml-1.5 opacity-70" />
        )}
      </button>

      {/* Expandable Dropdown Checklist */}
      {expanded && (
        <div className="absolute right-0 mt-2 w-96 max-w-[90vw] p-4 bg-white border border-slate-200 rounded-lg shadow-xl z-40 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200">
            <div className="flex items-center space-x-1.5">
              {isPassed && <ShieldCheck className="w-4 h-4 text-emerald-600" />}
              {isWarning && <ShieldAlert className="w-4 h-4 text-amber-600" />}
              {isFailed && <ShieldX className="w-4 h-4 text-rose-600" />}
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Release Conditions Checklist
              </h4>
            </div>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                isPassed
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : isWarning
                  ? "bg-amber-50 text-amber-700 border-amber-200"
                  : "bg-rose-50 text-rose-700 border-rose-200"
              }`}
            >
              {data.status}
            </span>
          </div>

          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {data.conditions.map((c) => (
              <div
                key={c.condition_id}
                className={`p-2.5 rounded-md border text-xs ${
                  c.passed
                    ? "bg-emerald-50/40 border-emerald-200/80 text-slate-700"
                    : c.severity === "fail"
                    ? "bg-rose-50/70 border-rose-200 text-rose-900"
                    : "bg-amber-50/70 border-amber-200 text-amber-900"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {c.passed ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    ) : c.severity === "fail" ? (
                      <XCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    )}
                    <span className="font-mono font-semibold text-[11px] text-slate-900">
                      {c.condition_id}
                    </span>
                  </div>
                  <span className="text-[10px] uppercase font-bold text-slate-500">
                    {c.severity === "fail" ? "Strict Gate" : "Warning"}
                  </span>
                </div>

                <p className="mt-1 text-[11px] leading-relaxed text-slate-600">{c.message}</p>

                <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-slate-200 text-[10px] text-slate-500 font-mono">
                  <span>Actual: <strong className="text-slate-900">{c.actual_value}</strong></span>
                  <span>Rule: <strong className="text-slate-700">{c.operator} {c.threshold}</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
