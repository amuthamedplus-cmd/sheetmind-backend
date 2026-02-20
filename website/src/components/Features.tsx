import ScrollReveal from './ScrollReveal'

const features = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10Z" />
        <path d="M8 9h8M8 13h4" />
      </svg>
    ),
    title: 'Conversational AI Sidebar',
    description:
      'Open the sidebar and type what you need in plain English. "Summarize sales by region." "Add a VLOOKUP from Sheet2." "Highlight cells above $10,000." SheetMind reads your actual data and responds with real answers.',
    color: 'emerald',
    badge: null,
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M3 7v6h6" />
        <path d="M21 17a9 9 0 00-9-9 9 9 0 00-6.69 3L3 13" />
      </svg>
    ),
    title: 'Step-by-Step Undo',
    description:
      'SheetMind tracks every change the AI makes — cell edits, formula insertions, formatting. Review what happened and roll back any step individually. No other AI tool for Sheets offers this.',
    color: 'amber',
    badge: 'Only in SheetMind',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
    title: 'PII Detection',
    description:
      'SheetMind automatically detects emails, phone numbers, SSNs, and other PII in your sheet. You see a clear warning banner before anything is processed. Your data, your decision.',
    color: 'rose',
    badge: 'Only in SheetMind',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
      </svg>
    ),
    title: 'Formula Validation',
    description:
      'Every AI-generated formula is checked against a comprehensive library of 120+ Google Sheets functions before touching your sheet. No more #NAME? errors. No broken references.',
    color: 'blue',
    badge: null,
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10Z" />
        <path d="M2 12h20" />
      </svg>
    ),
    title: 'Deep Context with RAG',
    description:
      'Unlike tools that only read cells you reference, SheetMind indexes your full dataset using retrieval-augmented generation. Ask about any pattern across thousands of rows — it finds what matters.',
    color: 'purple',
    badge: null,
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12,6 12,12 16,14" />
      </svg>
    ),
    title: 'Conversation History',
    description:
      'Close the sidebar and come back tomorrow. Your conversation history is saved and you can resume any previous chat with full context. No re-explaining what you were working on.',
    color: 'teal',
    badge: null,
  },
]

const colorMap: Record<string, { bg: string; border: string; text: string; iconBg: string }> = {
  emerald: { bg: 'bg-emerald-50', border: 'border-emerald-200/40', text: 'text-emerald-600', iconBg: 'bg-emerald-100' },
  amber: { bg: 'bg-amber-50', border: 'border-amber-200/40', text: 'text-amber-600', iconBg: 'bg-amber-100' },
  rose: { bg: 'bg-rose-50', border: 'border-rose-200/40', text: 'text-rose-600', iconBg: 'bg-rose-100' },
  blue: { bg: 'bg-blue-50', border: 'border-blue-200/40', text: 'text-blue-600', iconBg: 'bg-blue-100' },
  purple: { bg: 'bg-purple-50', border: 'border-purple-200/40', text: 'text-purple-600', iconBg: 'bg-purple-100' },
  teal: { bg: 'bg-teal-50', border: 'border-teal-200/40', text: 'text-teal-600', iconBg: 'bg-teal-100' },
}

export default function Features() {
  return (
    <section id="features" className="py-24 lg:py-32 bg-slate-50/50 relative overflow-hidden">
      <div className="absolute inset-0 bg-mesh-emerald pointer-events-none opacity-50" />

      <div className="relative max-w-7xl mx-auto px-6 lg:px-8">
        <ScrollReveal className="text-center mb-16">
          <div className="pill-badge mx-auto mb-4 w-fit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" opacity="0.6"><path d="M12 2l2.4 7.2H22l-6 4.8 2.4 7.2L12 16.4 5.6 21.2 8 14 2 9.2h7.6L12 2Z" /></svg>
            Core Features
          </div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-5xl text-slate-900 tracking-tight text-balance">
            Everything your spreadsheet AI should do
            <br />
            <span className="text-gradient">(and most don&apos;t)</span>
          </h2>
          <p className="mt-4 text-lg text-slate-500 max-w-2xl mx-auto">
            SheetMind goes beyond basic AI text generation. It understands your data, takes real
            actions, validates every formula, and gives you full control.
          </p>
        </ScrollReveal>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5 lg:gap-6">
          {features.map((feature, i) => {
            const colors = colorMap[feature.color]
            return (
              <ScrollReveal key={feature.title} delay={i * 80}>
                <div className="relative h-full glass-card glass-card-hover rounded-2xl p-6 lg:p-7 group">
                  {feature.badge && (
                    <div className="absolute top-4 right-4 px-2.5 py-1 rounded-full bg-emerald-500 text-[10px] font-bold text-white uppercase tracking-wider">
                      {feature.badge}
                    </div>
                  )}

                  <div className={`w-12 h-12 rounded-xl ${colors.iconBg} ${colors.text} flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300`}>
                    {feature.icon}
                  </div>

                  <h3 className="font-display font-bold text-lg text-slate-900 mb-3">
                    {feature.title}
                  </h3>

                  <p className="text-sm text-slate-500 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </ScrollReveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}
