'use client'

import { useState } from 'react'
import ScrollReveal from './ScrollReveal'

const faqs = [
  {
    q: 'What is SheetMind?',
    a: 'SheetMind is an AI-powered sidebar that works inside Google Sheets. You can ask questions about your data in plain English, generate formulas, create charts, and automate multi-step sheet actions — all without leaving your spreadsheet.',
  },
  {
    q: 'How does SheetMind read my data?',
    a: 'When you send a message, SheetMind reads the headers and data from your selected sheet (up to 200 rows for chat, or uses RAG indexing for larger sheets). Your data is sent to our AI backend for processing and is never stored permanently.',
  },
  {
    q: 'Is my data safe?',
    a: 'Yes. SheetMind never stores your spreadsheet content. Our analytics are privacy-first — we never track your messages or sheet data. We also automatically detect PII (personally identifiable information) and warn you before processing. Your database is protected with row-level security policies.',
  },
  {
    q: 'Do I need an API key?',
    a: 'No. SheetMind works out of the box. No OpenAI API key, no configuration, no setup. Just install and start chatting.',
  },
  {
    q: 'Can SheetMind actually modify my spreadsheet?',
    a: 'Yes! In Action mode, SheetMind can create new sheets, write values, insert formulas, format cells, and generate charts. Every action is tracked and can be undone step-by-step.',
  },
  {
    q: "What's the difference between Chat mode and Action mode?",
    a: 'Chat mode answers questions and provides analysis without modifying your sheet. Action mode can create sheets, write formulas, format data, and generate charts. You choose which mode to use for each conversation.',
  },
  {
    q: 'How is SheetMind different from GPT for Sheets or SheetAI?',
    a: 'Most AI tools for Google Sheets work as cell functions (=GPT(), =AI()). SheetMind is a conversational sidebar that understands your full sheet context, takes multi-step actions, validates formulas against 120+ functions, detects PII automatically, and gives you step-by-step undo. No other tool offers this combination.',
  },
  {
    q: 'What happens when my free messages run out?',
    a: 'You can upgrade to Pro ($9/month) for 1,000 messages per month, or Team ($29/month) for unlimited messages. No pressure — we will let you know when you are running low.',
  },
]

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <section id="faq" className="py-24 lg:py-32 bg-white">
      <div className="max-w-3xl mx-auto px-6 lg:px-8">
        <ScrollReveal className="text-center mb-12">
          <div className="pill-badge mx-auto mb-4 w-fit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01" /></svg>
            FAQ
          </div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-5xl text-slate-900 tracking-tight">
            Frequently asked questions
          </h2>
          <p className="mt-4 text-lg text-slate-500">
            Everything you need to know about SheetMind.
          </p>
        </ScrollReveal>

        <div className="space-y-3">
          {faqs.map((faq, i) => (
            <ScrollReveal key={i} delay={i * 50}>
              <div
                className={`rounded-2xl border transition-all duration-300 ${
                  openIndex === i
                    ? 'border-emerald-200 bg-emerald-50/30 shadow-sm'
                    : 'border-slate-200/60 bg-white hover:border-slate-300'
                }`}
              >
                <button
                  onClick={() => setOpenIndex(openIndex === i ? null : i)}
                  className="w-full flex items-center justify-between p-5 text-left"
                >
                  <span className={`font-display font-semibold text-[15px] pr-4 ${openIndex === i ? 'text-emerald-700' : 'text-slate-800'}`}>
                    {faq.q}
                  </span>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                    openIndex === i ? 'bg-emerald-500 rotate-180' : 'bg-slate-100'
                  }`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={openIndex === i ? 'white' : '#64748b'} strokeWidth="2.5" strokeLinecap="round">
                      <path d="M6 9l6 6 6-6" />
                    </svg>
                  </div>
                </button>
                <div
                  className="overflow-hidden transition-all duration-300"
                  style={{
                    maxHeight: openIndex === i ? '300px' : '0',
                    opacity: openIndex === i ? 1 : 0,
                  }}
                >
                  <p className="px-5 pb-5 text-sm text-slate-500 leading-relaxed">
                    {faq.a}
                  </p>
                </div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  )
}
