import ScrollReveal from './ScrollReveal'

const steps = [
  {
    number: '01',
    title: 'Install from Marketplace',
    description:
      'Add SheetMind to your Google Sheets with one click. It opens as a sidebar inside your existing spreadsheets — no new app to learn, no data to export.',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
      </svg>
    ),
  },
  {
    number: '02',
    title: 'Ask in plain English',
    description:
      'Type what you need. "Calculate quarterly growth." "Find duplicate emails." "Create a pivot summary with a chart." SheetMind understands your sheet context automatically.',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10Z" />
        <path d="M8 9h8M8 13h4" />
      </svg>
    ),
  },
  {
    number: '03',
    title: 'Review, approve, and undo',
    description:
      'See confidence scores on every response. Click source links to verify. Approve actions or undo any step with one click. You are always in control.',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
      </svg>
    ),
  },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 lg:py-32 bg-white relative">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <ScrollReveal className="text-center mb-16">
          <div className="pill-badge mx-auto mb-4 w-fit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 20V10M18 20V4M6 20v-4" /></svg>
            How It Works
          </div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-5xl text-slate-900 tracking-tight">
            Three steps to <span className="text-gradient">smarter spreadsheets</span>
          </h2>
          <p className="mt-4 text-lg text-slate-500 max-w-xl mx-auto">
            Get started in under 30 seconds. No API keys. No configuration. No leaving Google Sheets.
          </p>
        </ScrollReveal>

        <div className="grid md:grid-cols-3 gap-8 lg:gap-12">
          {steps.map((step, i) => (
            <ScrollReveal key={step.number} delay={i * 120}>
              <div className="relative text-center group">
                {/* Connector line */}
                {i < steps.length - 1 && (
                  <div className="hidden md:block absolute top-14 left-[60%] w-[80%] h-px bg-gradient-to-r from-emerald-300/60 to-emerald-100/20" />
                )}

                {/* Number circle */}
                <div className="relative inline-flex mb-6">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-50 to-emerald-100/60 border border-emerald-200/40 flex items-center justify-center text-emerald-600 group-hover:scale-105 group-hover:shadow-lg group-hover:shadow-emerald-100 transition-all duration-300">
                    {step.icon}
                  </div>
                  <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                    <span className="text-xs font-display font-bold text-white">{step.number}</span>
                  </div>
                </div>

                <h3 className="font-display font-bold text-xl text-slate-900 mb-3">{step.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed max-w-xs mx-auto">{step.description}</p>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  )
}
