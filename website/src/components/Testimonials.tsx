import ScrollReveal from './ScrollReveal'

const testimonials = [
  {
    quote:
      'I was skeptical about another AI tool for Sheets, but the undo feature changed everything. I can let the AI try things without worrying about messing up my data.',
    name: 'Sarah K.',
    title: 'Data Analyst, SaaS Company',
    image: 'https://randomuser.me/api/portraits/women/44.jpg',
    ring: 'ring-emerald-200',
  },
  {
    quote:
      "The confidence scores are brilliant. I know immediately when to trust the output and when to double-check. Saves me hours of manual verification every week.",
    name: 'James R.',
    title: 'Financial Analyst',
    image: 'https://randomuser.me/api/portraits/men/32.jpg',
    ring: 'ring-blue-200',
  },
  {
    quote:
      "We handle customer PII daily. SheetMind is the only AI tool that actually warns us before processing sensitive data. That alone is worth the subscription.",
    name: 'Priya M.',
    title: 'Operations Manager',
    image: 'https://randomuser.me/api/portraits/women/68.jpg',
    ring: 'ring-purple-200',
  },
  {
    quote:
      'The =SHEETMIND() formula is a game-changer. I categorized 2,000 product descriptions in minutes instead of days. The batch processing is incredibly fast.',
    name: 'Alex T.',
    title: 'E-commerce Manager',
    image: 'https://randomuser.me/api/portraits/men/75.jpg',
    ring: 'ring-amber-200',
  },
]

export default function Testimonials() {
  return (
    <section className="py-24 lg:py-32 bg-slate-50/50">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <ScrollReveal className="text-center mb-16">
          <div className="pill-badge mx-auto mb-4 w-fit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10Z" /></svg>
            Testimonials
          </div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-5xl text-slate-900 tracking-tight">
            What spreadsheet professionals <span className="text-gradient">are saying</span>
          </h2>
        </ScrollReveal>

        <div className="grid md:grid-cols-2 gap-5 lg:gap-6">
          {testimonials.map((t, i) => (
            <ScrollReveal key={t.name} delay={i * 100}>
              <div className="glass-card rounded-2xl p-6 lg:p-8 h-full flex flex-col group hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
                {/* Stars */}
                <div className="flex gap-1 mb-4">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <svg key={n} width="16" height="16" viewBox="0 0 24 24" fill="#f59e0b">
                      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2Z" />
                    </svg>
                  ))}
                </div>

                <blockquote className="text-slate-600 leading-relaxed flex-1 text-[15px]">
                  &ldquo;{t.quote}&rdquo;
                </blockquote>

                <div className="flex items-center gap-4 mt-6 pt-6 border-t border-slate-100">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={t.image}
                    alt={t.name}
                    width={48}
                    height={48}
                    className={`w-12 h-12 rounded-full object-cover ring-2 ${t.ring} ring-offset-2`}
                    loading="lazy"
                  />
                  <div>
                    <div className="font-display font-semibold text-sm text-slate-900">{t.name}</div>
                    <div className="text-xs text-slate-400">{t.title}</div>
                  </div>
                </div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  )
}
