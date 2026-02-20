import { type ReactNode } from 'react'

interface TrustItem {
  icon: ReactNode
  text: string
  color: string
}

const items: TrustItem[] = [
  {
    text: 'Row-Level Security',
    color: 'bg-emerald-100 text-emerald-600',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0110 0v4" />
      </svg>
    ),
  },
  {
    text: 'Privacy-First Analytics',
    color: 'bg-blue-100 text-blue-600',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
  },
  {
    text: 'Gemini 2.0 Flash',
    color: 'bg-amber-100 text-amber-600',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    ),
  },
  {
    text: '120+ Validated Functions',
    color: 'bg-purple-100 text-purple-600',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
      </svg>
    ),
  },
  {
    text: 'Google Workspace Compatible',
    color: 'bg-teal-100 text-teal-600',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    text: 'Step-by-Step Undo',
    color: 'bg-rose-100 text-rose-600',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 7v6h6" />
        <path d="M21 17a9 9 0 00-9-9 9 9 0 00-6.69 3L3 13" />
      </svg>
    ),
  },
  {
    text: 'RAG-Powered Context',
    color: 'bg-indigo-100 text-indigo-600',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10Z" />
        <path d="M2 12h20" />
      </svg>
    ),
  },
  {
    text: 'Conversation Memory',
    color: 'bg-cyan-100 text-cyan-600',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10Z" />
        <path d="M8 9h8M8 13h4" />
      </svg>
    ),
  },
]

export default function TrustBar() {
  const doubled = [...items, ...items]

  return (
    <section className="py-12 border-y border-slate-100 bg-slate-50/50 overflow-hidden">
      <p className="text-center text-xs font-display font-semibold uppercase tracking-[0.2em] text-slate-400 mb-8">
        Trusted by spreadsheet professionals
      </p>
      <div className="relative">
        {/* Fade edges */}
        <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-slate-50/90 via-slate-50/50 to-transparent z-10 pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-slate-50/90 via-slate-50/50 to-transparent z-10 pointer-events-none" />

        <div className="marquee-track">
          {doubled.map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-3 px-5 py-3 mx-2.5 rounded-2xl bg-white border border-slate-200/70 shadow-sm hover:shadow-md hover:border-slate-300/80 transition-all duration-300 whitespace-nowrap"
            >
              <div className={`w-10 h-10 rounded-xl ${item.color} flex items-center justify-center flex-shrink-0`}>
                {item.icon}
              </div>
              <span className="text-sm font-semibold text-slate-700">{item.text}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
