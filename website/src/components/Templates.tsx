import ScrollReveal from './ScrollReveal'

const categories = [
  {
    icon: '📈',
    name: 'Sales',
    count: 10,
    color: 'bg-blue-50 border-blue-200/40',
    examples: ['Pipeline analysis', 'Win/loss breakdown', 'Quota tracking', 'Territory comparison'],
  },
  {
    icon: '📣',
    name: 'Marketing',
    count: 10,
    color: 'bg-purple-50 border-purple-200/40',
    examples: ['Campaign ROI', 'SEO audit', 'Content calendar', 'A/B test results'],
  },
  {
    icon: '💰',
    name: 'Finance',
    count: 10,
    color: 'bg-amber-50 border-amber-200/40',
    examples: ['Budget variance', 'P&L summary', 'Cash flow analysis', 'Expense categorization'],
  },
  {
    icon: '⚙️',
    name: 'Operations',
    count: 10,
    color: 'bg-rose-50 border-rose-200/40',
    examples: ['Inventory tracking', 'SLA monitoring', 'Vendor comparison', 'Capacity planning'],
  },
  {
    icon: '🔧',
    name: 'General',
    count: 12,
    color: 'bg-emerald-50 border-emerald-200/40',
    examples: ['Summarize data', 'Find duplicates', 'Clean messy data', 'Sentiment analysis'],
  },
]

export default function Templates() {
  return (
    <section id="templates" className="py-24 lg:py-32 bg-white">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <ScrollReveal className="text-center mb-16">
          <div className="pill-badge mx-auto mb-4 w-fit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 21V9" /></svg>
            52 Templates
          </div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-5xl text-slate-900 tracking-tight">
            Pre-built prompts for <span className="text-gradient">every team</span>
          </h2>
          <p className="mt-4 text-lg text-slate-500 max-w-xl mx-auto">
            Skip the blank page. Choose from 52 ready-to-use templates across sales, marketing,
            finance, operations, and more.
          </p>
        </ScrollReveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4 lg:gap-5">
          {categories.map((cat, i) => (
            <ScrollReveal key={cat.name} delay={i * 80}>
              <div className={`rounded-2xl border p-5 ${cat.color} h-full group hover:-translate-y-1 hover:shadow-lg transition-all duration-300`}>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl">{cat.icon}</span>
                  <div>
                    <h3 className="font-display font-bold text-base text-slate-900">{cat.name}</h3>
                    <p className="text-xs text-slate-400">{cat.count} templates</p>
                  </div>
                </div>
                <ul className="space-y-2">
                  {cat.examples.map((ex) => (
                    <li key={ex} className="flex items-start gap-2 text-xs text-slate-600">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="mt-0.5 text-slate-300 flex-shrink-0"><path d="M9 18l6-6-6-6" /></svg>
                      {ex}
                    </li>
                  ))}
                </ul>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  )
}
