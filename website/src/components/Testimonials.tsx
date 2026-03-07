'use client'

import { useState, useEffect, useCallback } from 'react'
import ScrollReveal from './ScrollReveal'

const testimonials = [
  {
    quote:
      'I was skeptical about another AI tool for Sheets, but the undo feature changed everything. I can let the AI try things without worrying about messing up my data.',
    name: 'Sarah K.',
    title: 'Data Analyst, SaaS Company',
    avatar: 'https://i.pravatar.cc/96?u=sarah_k_analyst',
  },
  {
    quote:
      "The confidence scores are brilliant. I know immediately when to trust the output and when to double-check. Saves me hours of manual verification every week.",
    name: 'James R.',
    title: 'Financial Analyst',
    avatar: 'https://i.pravatar.cc/96?u=james_r_finance99',
  },
  {
    quote:
      "We handle customer PII daily. SheetMind is the only AI tool that actually warns us before processing sensitive data. That alone is worth the subscription.",
    name: 'Priya M.',
    title: 'Operations Manager',
    avatar: 'https://i.pravatar.cc/96?u=priya_m_ops_mgr',
  },
  {
    quote:
      'The =SHEETMIND() formula is a game-changer. I categorized 2,000 product descriptions in minutes instead of days. The batch processing is incredibly fast.',
    name: 'Alex T.',
    title: 'E-commerce Manager',
    avatar: 'https://i.pravatar.cc/96?u=alex_t_ecommerce7',
  },
]

export default function Testimonials() {
  const [current, setCurrent] = useState(0)
  const [paused, setPaused] = useState(false)

  const next = useCallback(() => {
    setCurrent((c) => (c + 1) % testimonials.length)
  }, [])

  const prev = () => {
    setCurrent((c) => (c - 1 + testimonials.length) % testimonials.length)
  }

  useEffect(() => {
    if (paused) return
    const id = setInterval(next, 5000)
    return () => clearInterval(id)
  }, [paused, next])

  const t = testimonials[current]

  return (
    <section className="py-24 lg:py-32 bg-slate-50/50">
      <div className="max-w-3xl mx-auto px-6 lg:px-8">
        <ScrollReveal className="text-center mb-16">
          <div className="pill-badge mx-auto mb-4 w-fit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10Z" />
            </svg>
            Testimonials
          </div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-5xl text-slate-900 tracking-tight">
            What spreadsheet professionals <span className="text-gradient">are saying</span>
          </h2>
        </ScrollReveal>

        <div
          className="relative px-8 sm:px-12"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
        >
          {/* Card */}
          <div
            key={current}
            className="glass-card rounded-2xl p-8 lg:p-12 text-center"
            style={{ animation: 'fadeIn 0.4s ease-out' }}
          >
            {/* Stars */}
            <div className="flex justify-center gap-1 mb-6">
              {[1, 2, 3, 4, 5].map((n) => (
                <svg key={n} width="20" height="20" viewBox="0 0 24 24" fill="#f59e0b">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2Z" />
                </svg>
              ))}
            </div>

            {/* Quote */}
            <blockquote className="text-base sm:text-lg lg:text-xl text-slate-700 leading-relaxed mb-8 max-w-2xl mx-auto">
              &ldquo;{t.quote}&rdquo;
            </blockquote>

            {/* Author */}
            <div className="flex flex-col items-center gap-3">
              <img
                src={t.avatar}
                alt={t.name}
                className="w-16 h-16 rounded-full ring-4 ring-emerald-100 object-cover shadow-md"
                loading="lazy"
              />
              <div>
                <div className="font-display font-bold text-slate-900">{t.name}</div>
                <div className="text-sm text-slate-400 mt-0.5">{t.title}</div>
              </div>
            </div>
          </div>

          {/* Prev button */}
          <button
            onClick={prev}
            className="absolute left-0 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white border border-slate-200 shadow-md flex items-center justify-center text-slate-400 hover:text-emerald-600 hover:border-emerald-200 transition-all"
            aria-label="Previous testimonial"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>

          {/* Next button */}
          <button
            onClick={next}
            className="absolute right-0 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white border border-slate-200 shadow-md flex items-center justify-center text-slate-400 hover:text-emerald-600 hover:border-emerald-200 transition-all"
            aria-label="Next testimonial"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        </div>

        {/* Dots */}
        <div className="flex justify-center gap-2 mt-8">
          {testimonials.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrent(i)}
              className={`h-2 rounded-full transition-all duration-300 ${
                i === current ? 'bg-emerald-500 w-6' : 'bg-slate-300 w-2 hover:bg-slate-400'
              }`}
              aria-label={`Go to testimonial ${i + 1}`}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
