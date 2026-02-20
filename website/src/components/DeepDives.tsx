import ScrollReveal from './ScrollReveal'

export default function DeepDives() {
  return (
    <section className="py-24 lg:py-32 space-y-24 lg:space-y-32">
      {/* Deep Dive 1: Smart Analysis */}
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <ScrollReveal direction="left">
            <div>
              <div className="pill-badge mb-4 w-fit">Smart Analysis</div>
              <h2 className="font-display font-extrabold text-3xl lg:text-4xl text-slate-900 tracking-tight mb-6">
                Ask questions. Get answers <span className="text-gradient">with proof.</span>
              </h2>
              <p className="text-lg text-slate-500 leading-relaxed mb-8">
                Every response includes a confidence score — green (90-100%), yellow (70-89%), or
                red (below 70%). Click any source reference to jump directly to the cited rows in
                your sheet. Cells highlight for 3 seconds so you can verify instantly.
              </p>

              <div className="flex flex-wrap gap-6 mb-8">
                {[
                  { value: '94%', label: 'Avg Confidence' },
                  { value: '3 sec', label: 'Verification' },
                  { value: '0', label: 'Blind Trust' },
                ].map((stat) => (
                  <div key={stat.label}>
                    <div className="font-display font-extrabold text-3xl text-emerald-600">{stat.value}</div>
                    <div className="text-sm text-slate-400 mt-1">{stat.label}</div>
                  </div>
                ))}
              </div>

              <a href="#pricing" className="btn-secondary text-sm">
                Try It Free
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </a>
            </div>
          </ScrollReveal>

          <ScrollReveal direction="right">
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-br from-emerald-100/50 to-transparent rounded-3xl blur-2xl" />
              <div className="relative bg-white rounded-2xl border border-slate-200/80 shadow-xl overflow-hidden">
                {/* Mock AI response with confidence */}
                <div className="p-5 space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M12 2l2 5h5l-4 3.5 1.5 5L12 13l-4.5 2.5L9 10.5 5 7h5l2-5Z" /></svg>
                    </div>
                    <span className="font-display font-bold text-sm text-slate-800">SheetMind</span>
                  </div>

                  {/* Confidence badge */}
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200/50">
                    <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center">
                      <span className="text-[10px] font-bold text-white">94</span>
                    </div>
                    <span className="text-xs font-semibold text-emerald-700">High Confidence</span>
                    <div className="flex gap-0.5">
                      {[1, 2, 3, 4, 5].map((n) => (
                        <div key={n} className={`w-1 h-3 rounded-full ${n <= 4 ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                      ))}
                    </div>
                  </div>

                  <p className="text-sm text-slate-700 leading-relaxed">
                    Revenue analysis shows <strong>West region leads</strong> with $152,700 (57.6% of total),
                    followed by East at $83,400 and North at $28,500.
                  </p>

                  {/* Source links */}
                  <div className="flex flex-wrap gap-2">
                    {['Rows 2-7', 'Column B', 'Column C'].map((src) => (
                      <span key={src} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-200/40 text-xs font-medium text-emerald-600 cursor-pointer hover:bg-emerald-100 transition-colors">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" /></svg>
                        {src}
                      </span>
                    ))}
                  </div>

                  <div className="pt-3 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-400">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>
                    Analyzed in 1.2 seconds
                  </div>
                </div>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </div>

      {/* Deep Dive 2: Multi-Step Actions */}
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <ScrollReveal direction="left" className="order-2 lg:order-1">
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-bl from-blue-100/50 to-transparent rounded-3xl blur-2xl" />
              <div className="relative bg-white rounded-2xl border border-slate-200/80 shadow-xl overflow-hidden p-5">
                <div className="flex items-center gap-2 mb-5">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M12 2l2 5h5l-4 3.5 1.5 5L12 13l-4.5 2.5L9 10.5 5 7h5l2-5Z" /></svg>
                  </div>
                  <span className="font-display font-bold text-sm text-slate-800">Action Plan</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-700">5 steps</span>
                </div>

                {/* Steps */}
                <div className="space-y-3">
                  {[
                    { step: 1, text: 'Create new sheet "Regional Summary"', status: 'done' },
                    { step: 2, text: 'Add headers + UNIQUE formulas', status: 'done' },
                    { step: 3, text: 'Insert SUMIF calculations', status: 'done' },
                    { step: 4, text: 'Format cells with bold headers', status: 'done' },
                    { step: 5, text: 'Generate bar chart', status: 'active' },
                  ].map((s) => (
                    <div key={s.step} className={`flex items-start gap-3 p-3 rounded-xl ${s.status === 'active' ? 'bg-blue-50 border border-blue-200/50' : 'bg-slate-50'}`}>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                        s.status === 'done' ? 'bg-emerald-500' : 'bg-blue-500 animate-pulse-soft'
                      }`}>
                        {s.status === 'done' ? (
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round"><path d="M20 6L9 17l-5-5" /></svg>
                        ) : (
                          <span className="text-[10px] font-bold text-white">{s.step}</span>
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-slate-700">{s.text}</p>
                        {s.status === 'active' && (
                          <p className="text-xs text-blue-500 mt-1">Processing...</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Undo bar */}
                <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200/60 text-xs font-medium text-amber-700 hover:bg-amber-100 transition-colors">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 7v6h6" /><path d="M21 17a9 9 0 00-9-9 9 9 0 00-6.69 3L3 13" /></svg>
                      Undo Last
                    </button>
                    <button className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-500 hover:bg-slate-100 transition-colors">
                      Undo All
                    </button>
                  </div>
                  <span className="text-xs text-slate-400">4 of 5 complete</span>
                </div>
              </div>
            </div>
          </ScrollReveal>

          <ScrollReveal direction="right" className="order-1 lg:order-2">
            <div>
              <div className="pill-badge mb-4 w-fit">Multi-Step Actions</div>
              <h2 className="font-display font-extrabold text-3xl lg:text-4xl text-slate-900 tracking-tight mb-6">
                From question to <span className="text-gradient">finished sheet</span> in seconds
              </h2>
              <p className="text-lg text-slate-500 leading-relaxed mb-6">
                Tell SheetMind to &quot;create a summary table grouped by region with a bar chart&quot;
                and watch it execute a multi-step plan — creating sheets, writing formulas,
                formatting cells, and generating charts.
              </p>
              <p className="text-base text-slate-600 font-medium">
                Every step is tracked. Every step is undoable.
              </p>
            </div>
          </ScrollReveal>
        </div>
      </div>

      {/* Deep Dive 3: Cell Formulas */}
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <ScrollReveal direction="left">
            <div>
              <div className="pill-badge mb-4 w-fit">Cell Formulas</div>
              <h2 className="font-display font-extrabold text-3xl lg:text-4xl text-slate-900 tracking-tight mb-6">
                <span className="font-mono text-emerald-600">=SHEETMIND()</span>
                <br />
                AI inside any cell
              </h2>
              <p className="text-lg text-slate-500 leading-relaxed mb-8">
                Type a formula with a natural language prompt and get instant AI results directly
                in your cells. Drag down to process hundreds of rows. Each result includes a
                confidence score as a cell comment.
              </p>

              <div className="space-y-3">
                {[
                  '=SHEETMIND("categorize this product", A2)',
                  '=SHEETMIND("extract domain from email", B2)',
                  '=SHEETMIND("is this a qualified lead?", A2:D2)',
                  '=SHEETMIND("summarize in 10 words", C2)',
                ].map((formula) => (
                  <div key={formula} className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-slate-50 border border-slate-200/60 font-mono text-xs text-slate-600 overflow-x-auto">
                    <span className="text-emerald-500 flex-shrink-0">fx</span>
                    <code className="whitespace-nowrap">{formula}</code>
                  </div>
                ))}
              </div>
            </div>
          </ScrollReveal>

          <ScrollReveal direction="right">
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-br from-emerald-100/40 to-purple-100/30 rounded-3xl blur-2xl" />
              <div className="relative bg-white rounded-2xl border border-slate-200/80 shadow-xl overflow-hidden">
                {/* Mini spreadsheet with formulas */}
                <div className="bg-slate-50 border-b border-slate-200/60 px-4 py-2 flex items-center gap-2">
                  <span className="text-xs font-mono text-slate-400 bg-white px-2 py-0.5 rounded border border-slate-200">B2</span>
                  <span className="text-xs font-mono text-slate-400">fx</span>
                  <span className="text-xs font-mono text-emerald-600">=SHEETMIND(&quot;categorize&quot;, A2)</span>
                </div>

                <div className="divide-y divide-slate-100">
                  {/* Header row */}
                  <div className="grid grid-cols-3 text-xs font-semibold text-slate-700">
                    <div className="px-4 py-2.5 bg-slate-50/60 border-r border-slate-100">Product</div>
                    <div className="px-4 py-2.5 bg-slate-50/60 border-r border-slate-100">Category</div>
                    <div className="px-4 py-2.5 bg-slate-50/60">Confidence</div>
                  </div>
                  {/* Data rows */}
                  {[
                    { product: 'Nike Air Max 90', category: 'Footwear', confidence: 97 },
                    { product: 'MacBook Pro 16"', category: 'Electronics', confidence: 99 },
                    { product: 'Organic Green Tea', category: 'Beverages', confidence: 94 },
                    { product: 'Standing Desk Pro', category: 'Furniture', confidence: 92 },
                    { product: 'Yoga Mat Premium', category: 'Fitness', confidence: 96 },
                  ].map((row, i) => (
                    <div key={i} className="grid grid-cols-3 text-xs text-slate-600">
                      <div className="px-4 py-2.5 border-r border-slate-50">{row.product}</div>
                      <div className="px-4 py-2.5 border-r border-slate-50 text-emerald-600 font-medium">{row.category}</div>
                      <div className="px-4 py-2.5 flex items-center gap-1.5">
                        <div className="w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center">
                          <span className="text-[8px] font-bold text-emerald-700">{row.confidence}</span>
                        </div>
                        <div className="flex-1 h-1 bg-slate-100 rounded-full">
                          <div className="h-1 bg-emerald-400 rounded-full" style={{ width: `${row.confidence}%` }} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="px-4 py-3 bg-slate-50 border-t border-slate-200/60 flex items-center justify-between text-xs text-slate-400">
                  <span>5 rows processed</span>
                  <span className="text-emerald-600 font-medium">Avg: 95.6% confidence</span>
                </div>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </div>
    </section>
  )
}
