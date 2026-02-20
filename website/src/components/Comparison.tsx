import ScrollReveal from './ScrollReveal'

const features = [
  'Conversational sidebar',
  'Undo AI actions',
  'PII detection',
  'Formula validation',
  'Deep context (RAG)',
  'Conversation history',
  'Cell formulas',
  'Chart generation',
  'No API key needed',
  'Starting price',
]

type Val = boolean | string

const competitors: { name: string; values: Val[] }[] = [
  {
    name: 'SheetMind',
    values: [true, true, true, true, true, true, true, true, true, 'Free'],
  },
  {
    name: 'GPT for Sheets',
    values: [false, false, false, false, false, false, true, false, false, '$29+'],
  },
  {
    name: 'SheetAI',
    values: [false, false, false, false, 'Partial', false, true, false, 'Varies', 'Free*'],
  },
  {
    name: 'Numerous',
    values: [false, false, false, false, false, false, true, false, true, '$8/mo'],
  },
  {
    name: 'Arcwise',
    values: ['Partial', false, false, false, 'Partial', false, false, false, true, 'Free'],
  },
]

function CellValue({ val }: { val: Val }) {
  if (val === true) {
    return (
      <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center mx-auto">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="3" strokeLinecap="round"><path d="M20 6L9 17l-5-5" /></svg>
      </div>
    )
  }
  if (val === false) {
    return (
      <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center mx-auto">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
      </div>
    )
  }
  return <span className="text-xs font-medium text-slate-500">{val}</span>
}

export default function Comparison() {
  return (
    <section id="comparison" className="py-24 lg:py-32 bg-slate-50/50">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <ScrollReveal className="text-center mb-12">
          <div className="pill-badge mx-auto mb-4 w-fit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M16 3h5v5M8 3H3v5M3 16v5h5M21 16v5h-5" /></svg>
            Compare
          </div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-5xl text-slate-900 tracking-tight">
            How SheetMind <span className="text-gradient">compares</span>
          </h2>
        </ScrollReveal>

        <ScrollReveal>
          <div className="overflow-x-auto -mx-6 px-6">
            <table className="w-full min-w-[640px] border-collapse">
              <thead>
                <tr>
                  <th className="text-left text-sm font-medium text-slate-400 pb-4 pr-4 w-[180px]">Feature</th>
                  {competitors.map((c, i) => (
                    <th
                      key={c.name}
                      className={`text-center text-sm font-display font-bold pb-4 px-3 ${
                        i === 0 ? 'text-emerald-600' : 'text-slate-600'
                      }`}
                    >
                      {c.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {features.map((feature, fi) => (
                  <tr key={feature} className={fi % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}>
                    <td className="text-sm text-slate-700 font-medium py-3.5 pr-4 pl-4 rounded-l-xl">{feature}</td>
                    {competitors.map((c, ci) => (
                      <td
                        key={c.name}
                        className={`text-center py-3.5 px-3 ${ci === 0 ? 'bg-emerald-50/40' : ''} ${
                          ci === competitors.length - 1 ? 'rounded-r-xl' : ''
                        } ${ci === 0 && fi === 0 ? 'rounded-tl-xl' : ''}`}
                      >
                        <CellValue val={c.values[fi]} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ScrollReveal>

        <ScrollReveal className="text-center mt-10">
          <a href="#pricing" className="btn-primary">
            Try SheetMind Free
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
          </a>
        </ScrollReveal>
      </div>
    </section>
  )
}
