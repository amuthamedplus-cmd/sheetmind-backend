'use client'

import { useEffect, useState } from 'react'

export default function DashboardMock() {
  const [typed, setTyped] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setTyped(true), 1200)
    return () => clearTimeout(t)
  }, [])

  return (
    <div className="relative w-full max-w-5xl mx-auto mt-12 lg:mt-16">
      {/* Floating decorative elements */}
      <div className="absolute -top-8 -left-6 w-14 h-14 rounded-2xl bg-emerald-100 border border-emerald-200/60 flex items-center justify-center animate-float shadow-lg shadow-emerald-100/50 z-10">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-emerald-600">
          <rect x="3" y="3" width="7" height="7" rx="1" fill="currentColor" opacity="0.5" />
          <rect x="14" y="3" width="7" height="7" rx="1" fill="currentColor" opacity="0.7" />
          <rect x="3" y="14" width="7" height="7" rx="1" fill="currentColor" opacity="0.7" />
          <rect x="14" y="14" width="7" height="7" rx="1" fill="currentColor" />
        </svg>
      </div>

      <div className="absolute -top-4 -right-4 w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200/60 flex items-center justify-center animate-float-delayed shadow-lg shadow-amber-100/50 z-10">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-amber-500">
          <path d="M12 2l2.4 7.2H22l-6 4.8 2.4 7.2L12 16.4 5.6 21.2 8 14 2 9.2h7.6L12 2Z" fill="currentColor" />
        </svg>
      </div>

      <div className="absolute -bottom-6 -left-4 w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200/60 flex items-center justify-center animate-float-slow shadow-lg shadow-blue-100/50 z-10">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-blue-500">
          <rect x="3" y="12" width="4" height="8" rx="1" fill="currentColor" opacity="0.5" />
          <rect x="10" y="8" width="4" height="12" rx="1" fill="currentColor" opacity="0.7" />
          <rect x="17" y="4" width="4" height="16" rx="1" fill="currentColor" />
        </svg>
      </div>

      <div className="absolute -bottom-4 -right-6 w-14 h-14 rounded-2xl bg-purple-50 border border-purple-200/60 flex items-center justify-center animate-float shadow-lg shadow-purple-100/50 z-10" style={{ animationDelay: '3s' }}>
        <span className="text-purple-500 font-mono font-bold text-sm italic">fx</span>
      </div>

      {/* Glow effect behind the mock */}
      <div className="absolute inset-0 bg-gradient-to-b from-emerald-200/30 via-emerald-100/20 to-transparent rounded-3xl blur-3xl scale-105 -z-10" />

      {/* Main dashboard container */}
      <div className="dashboard-shadow rounded-2xl overflow-hidden bg-white border border-slate-200/80">
        {/* Top bar — Google Sheets style */}
        <div className="bg-gradient-to-b from-slate-50 to-slate-100/80 border-b border-slate-200/60 px-4 py-2.5 flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-emerald-500 flex items-center justify-center">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="white"><rect x="3" y="3" width="8" height="8" /><rect x="13" y="3" width="8" height="8" /><rect x="3" y="13" width="8" height="8" /><rect x="13" y="13" width="8" height="8" /></svg>
            </div>
            <span className="text-sm font-medium text-slate-700">Sales Data Q4</span>
          </div>
          <div className="flex-1" />
          <div className="hidden sm:flex items-center gap-1.5">
            {['File', 'Edit', 'View', 'Insert', 'Format'].map((item) => (
              <span key={item} className="text-xs text-slate-500 px-2 py-1 rounded hover:bg-slate-200/60 cursor-default">{item}</span>
            ))}
          </div>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center">
              <span className="text-xs font-bold text-emerald-700">SM</span>
            </div>
          </div>
        </div>

        {/* Formula bar */}
        <div className="bg-white border-b border-slate-100 px-4 py-1.5 flex items-center gap-3">
          <span className="text-xs font-mono text-slate-400 bg-slate-50 px-2 py-0.5 rounded border border-slate-200 min-w-[40px] text-center">A1</span>
          <span className="text-xs font-mono text-slate-400 px-1">fx</span>
          <span className="text-xs text-slate-500">Company</span>
        </div>

        {/* Main content area */}
        <div className="flex min-h-[380px] lg:min-h-[420px]">
          {/* Spreadsheet grid */}
          <div className="flex-1 overflow-hidden">
            {/* Column headers */}
            <div className="flex border-b border-slate-100 bg-slate-50/60">
              <div className="w-10 min-w-[40px] border-r border-slate-100" />
              {['A', 'B', 'C', 'D'].map((col) => (
                <div key={col} className="flex-1 min-w-[80px] px-3 py-1.5 text-center text-xs font-medium text-slate-400 border-r border-slate-100/60">
                  {col}
                </div>
              ))}
            </div>

            {/* Data rows */}
            {[
              { n: 1, cells: ['Company', 'Revenue', 'Region', 'Status'], header: true },
              { n: 2, cells: ['Acme Corp', '$45,200', 'West', 'Active'] },
              { n: 3, cells: ['Beta Labs', '$32,100', 'East', 'Active'] },
              { n: 4, cells: ['Gamma Inc', '$67,800', 'West', 'Active'], highlighted: true },
              { n: 5, cells: ['Delta Co', '$28,500', 'North', 'Pending'] },
              { n: 6, cells: ['Epsilon Ltd', '$51,300', 'East', 'Active'], highlighted: true },
              { n: 7, cells: ['Zeta Group', '$39,700', 'West', 'Active'] },
              { n: 8, cells: ['', '', '', ''] },
              { n: 9, cells: ['', '', '', ''] },
              { n: 10, cells: ['', '', '', ''] },
            ].map((row) => (
              <div
                key={row.n}
                className={`flex border-b border-slate-50 ${
                  row.highlighted ? 'bg-emerald-50/50' : row.header ? 'bg-slate-50/40' : ''
                }`}
              >
                <div className="w-10 min-w-[40px] px-1 py-1.5 text-center text-[11px] text-slate-300 border-r border-slate-100/40 flex-shrink-0">
                  {row.n}
                </div>
                {row.cells.map((cell, i) => (
                  <div
                    key={i}
                    className={`flex-1 min-w-[80px] px-3 py-1.5 text-xs border-r border-slate-50 truncate ${
                      row.header ? 'font-semibold text-slate-700' : 'text-slate-600'
                    } ${row.highlighted && i === 1 ? 'text-emerald-700 font-medium' : ''}`}
                  >
                    {cell}
                  </div>
                ))}
              </div>
            ))}
          </div>

          {/* Sidebar panel */}
          <div className="w-[240px] lg:w-[280px] border-l border-slate-200 bg-gradient-to-b from-slate-50/80 to-white flex flex-col flex-shrink-0">
            {/* Sidebar header */}
            <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
                  <path d="M12 2l2 5h5l-4 3.5 1.5 5L12 13l-4.5 2.5L9 10.5 5 7h5l2-5Z" />
                </svg>
              </div>
              <span className="font-display font-bold text-sm text-slate-800">SheetMind</span>
              <span className="ml-auto px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-700">AI</span>
            </div>

            {/* Chat messages */}
            <div className="flex-1 px-3 py-3 space-y-3 overflow-hidden">
              {/* User message */}
              <div className="flex justify-end">
                <div className="bg-emerald-600 text-white rounded-2xl rounded-tr-md px-3.5 py-2 text-xs leading-relaxed max-w-[90%] shadow-sm">
                  Summarize sales by region
                </div>
              </div>

              {/* AI response */}
              <div
                className={`transition-all duration-700 ${typed ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}
              >
                <div className="bg-white rounded-2xl rounded-tl-md px-3.5 py-3 text-xs leading-relaxed border border-slate-100 shadow-sm space-y-2">
                  {/* Confidence badge */}
                  <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center">
                      <span className="text-[9px] font-bold text-emerald-700">94</span>
                    </div>
                    <span className="text-[10px] font-semibold text-emerald-600">High Confidence</span>
                  </div>

                  <p className="text-slate-700">
                    Here&apos;s your sales breakdown by region:
                  </p>

                  <div className="space-y-1 bg-slate-50 rounded-lg p-2">
                    <div className="flex justify-between">
                      <span className="text-slate-500">West</span>
                      <span className="font-semibold text-slate-800">$152,700</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">East</span>
                      <span className="font-semibold text-slate-800">$83,400</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">North</span>
                      <span className="font-semibold text-slate-800">$28,500</span>
                    </div>
                  </div>

                  {/* Source link */}
                  <div className="flex items-center gap-1 text-emerald-600 cursor-pointer hover:text-emerald-700 transition-colors">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" /></svg>
                    <span className="text-[10px] font-medium underline decoration-emerald-300">Rows 2-7 &bull; Sheet1</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Input area with undo */}
            <div className="px-3 pb-3 space-y-2">
              <div className="flex gap-1.5">
                <button className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-amber-50 border border-amber-200/60 text-[10px] font-medium text-amber-700 hover:bg-amber-100/80 transition-colors">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 7v6h6" /><path d="M21 17a9 9 0 00-9-9 9 9 0 00-6.69 3L3 13" /></svg>
                  Undo
                </button>
                <span className="text-[10px] text-slate-400 flex items-center">3 actions</span>
              </div>
              <div className="flex items-center gap-2 bg-white rounded-xl border border-slate-200 px-3 py-2">
                <input
                  type="text"
                  placeholder="Ask about your data..."
                  className="flex-1 text-xs text-slate-500 outline-none bg-transparent"
                  readOnly
                />
                <div className="w-6 h-6 rounded-lg bg-emerald-500 flex items-center justify-center">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z" /></svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sheet tabs */}
        <div className="bg-slate-50 border-t border-slate-200/60 px-4 py-1.5 flex items-center gap-1">
          <div className="flex items-center gap-0.5">
            <div className="px-4 py-1 rounded-t-md bg-white border border-b-0 border-slate-200 text-xs font-medium text-emerald-700 shadow-sm">
              Sheet1
            </div>
            <div className="px-4 py-1 text-xs text-slate-400">
              Sheet2
            </div>
          </div>
          <button className="w-5 h-5 rounded flex items-center justify-center text-slate-400 hover:bg-slate-200/60 transition-colors text-xs">+</button>
        </div>
      </div>
    </div>
  )
}
