'use client'

import { useState } from 'react'
import ScrollReveal from './ScrollReveal'

const plans = [
  {
    name: 'Free',
    monthlyPrice: 0,
    annualPrice: 0,
    subtitle: 'Try SheetMind with no commitment',
    features: [
      { text: '5 messages to explore', included: true },
      { text: 'AI chat sidebar', included: true },
      { text: '=SHEETMIND() cell formulas', included: true },
      { text: 'Confidence score badges', included: true },
      { text: 'Chart generation', included: true },
      { text: '52 smart templates', included: true },
      { text: 'Formula explainer', included: true },
      { text: 'Clickable source verification', included: false },
      { text: 'Confidence score breakdown', included: false },
      { text: 'Custom templates', included: false },
    ],
    cta: 'Get Started Free',
    highlighted: false,
  },
  {
    name: 'Pro',
    monthlyPrice: 9,
    annualPrice: 7,
    subtitle: 'For professionals who live in spreadsheets',
    badge: 'Most Popular',
    features: [
      { text: '1,000 messages / month', included: true },
      { text: 'Everything in Free', included: true },
      { text: 'Clickable source verification', included: true },
      { text: 'Full confidence breakdown', included: true },
      { text: 'Custom templates', included: true },
      { text: 'Conversation history', included: true },
      { text: 'Priority rate limits (20 req/min)', included: true },
      { text: 'Email support', included: true },
    ],
    cta: 'Upgrade to Pro',
    highlighted: true,
  },
  {
    name: 'Team',
    monthlyPrice: 29,
    annualPrice: 24,
    subtitle: 'For teams that need unlimited AI',
    features: [
      { text: 'Unlimited messages', included: true },
      { text: 'Everything in Pro', included: true },
      { text: '50 req/min rate limit', included: true },
      { text: 'Team template sharing', included: true, badge: 'Soon' },
      { text: 'Conversation export', included: true, badge: 'Soon' },
      { text: 'Email + chat support', included: true },
    ],
    cta: 'Start Team Plan',
    highlighted: false,
  },
]

export default function Pricing() {
  const [annual, setAnnual] = useState(false)

  return (
    <section id="pricing" className="py-24 lg:py-32 bg-white relative overflow-hidden">
      <div className="absolute inset-0 bg-mesh-emerald pointer-events-none opacity-40" />

      <div className="relative max-w-7xl mx-auto px-6 lg:px-8">
        <ScrollReveal className="text-center mb-12">
          <div className="pill-badge mx-auto mb-4 w-fit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" /></svg>
            Pricing
          </div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-5xl text-slate-900 tracking-tight">
            Start free. <span className="text-gradient">Scale when you&apos;re ready.</span>
          </h2>
        </ScrollReveal>

        {/* Toggle */}
        <ScrollReveal className="flex items-center justify-center gap-4 mb-12">
          <span className={`text-sm font-medium transition-colors ${!annual ? 'text-slate-900' : 'text-slate-400'}`}>Monthly</span>
          <button
            onClick={() => setAnnual(!annual)}
            className={`relative w-14 h-7 rounded-full transition-colors duration-300 ${annual ? 'bg-emerald-500' : 'bg-slate-300'}`}
            aria-label="Toggle annual billing"
          >
            <div className={`absolute top-0.5 w-6 h-6 rounded-full bg-white shadow-md transition-transform duration-300 ${annual ? 'translate-x-7.5 left-0.5' : 'left-0.5'}`}
              style={{ transform: annual ? 'translateX(28px)' : 'translateX(0)' }}
            />
          </button>
          <span className={`text-sm font-medium transition-colors ${annual ? 'text-slate-900' : 'text-slate-400'}`}>
            Annual
            <span className="ml-1.5 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold">Save 20%</span>
          </span>
        </ScrollReveal>

        {/* Cards */}
        <div className="grid md:grid-cols-3 gap-5 lg:gap-6 max-w-5xl mx-auto">
          {plans.map((plan, i) => (
            <ScrollReveal key={plan.name} delay={i * 100}>
              <div
                className={`relative rounded-2xl p-6 lg:p-8 h-full flex flex-col transition-all duration-300 ${
                  plan.highlighted
                    ? 'bg-white border-2 border-emerald-500 shadow-xl shadow-emerald-500/10 scale-[1.02] lg:scale-105'
                    : 'glass-card hover:-translate-y-1 hover:shadow-lg'
                }`}
              >
                {plan.badge && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-500/30">
                    {plan.badge}
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="font-display font-bold text-xl text-slate-900">{plan.name}</h3>
                  <p className="text-sm text-slate-400 mt-1">{plan.subtitle}</p>
                </div>

                <div className="mb-6">
                  <div className="flex items-baseline gap-1">
                    <span className="font-display font-extrabold text-4xl lg:text-5xl text-slate-900">
                      ${annual ? plan.annualPrice : plan.monthlyPrice}
                    </span>
                    {plan.monthlyPrice > 0 && (
                      <span className="text-sm text-slate-400">/mo</span>
                    )}
                  </div>
                  {annual && plan.monthlyPrice > 0 && (
                    <p className="text-xs text-slate-400 mt-1">Billed annually</p>
                  )}
                </div>

                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((feature) => (
                    <li key={feature.text} className="flex items-start gap-2.5">
                      {feature.included ? (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" className="flex-shrink-0 mt-0.5">
                          <path d="M20 6L9 17l-5-5" />
                        </svg>
                      ) : (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" className="flex-shrink-0 mt-0.5">
                          <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                      )}
                      <span className={`text-sm ${feature.included ? 'text-slate-600' : 'text-slate-400'}`}>
                        {feature.text}
                        {'badge' in feature && feature.badge && (
                          <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500">
                            {feature.badge}
                          </span>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>

                <button
                  className={`w-full py-3.5 rounded-xl font-display font-semibold text-sm transition-all duration-300 ${
                    plan.highlighted
                      ? 'bg-gradient-to-r from-emerald-600 to-emerald-500 text-white shadow-lg shadow-emerald-500/20 hover:shadow-xl hover:shadow-emerald-500/30 hover:-translate-y-0.5'
                      : 'bg-slate-100 text-slate-700 hover:bg-emerald-50 hover:text-emerald-700'
                  }`}
                >
                  {plan.cta}
                </button>
              </div>
            </ScrollReveal>
          ))}
        </div>

        <ScrollReveal className="text-center mt-8">
          <p className="text-sm text-slate-400">
            All plans include: No API key required &bull; Your data stays private &bull; Cancel anytime
          </p>
        </ScrollReveal>
      </div>
    </section>
  )
}
