'use client'

import { useState } from 'react'
import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'
import ScrollReveal from '@/components/ScrollReveal'

const contactMethods = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><rect x="2" y="4" width="20" height="16" rx="2" /><path d="M22 7l-8.97 5.7a1.94 1.94 0 01-2.06 0L2 7" /></svg>
    ),
    title: 'Email Us',
    description: 'For general inquiries and support.',
    action: 'hello@sheetmind.xyz',
    href: 'mailto:hello@sheetmind.xyz',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10Z" /></svg>
    ),
    title: 'Live Chat',
    description: 'Available for Pro and Team plans.',
    action: 'Start a conversation',
    href: '#',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231z" /></svg>
    ),
    title: 'Twitter / X',
    description: 'Follow us for updates and tips.',
    action: '@sheetmind',
    href: '#',
  },
]

export default function ContactPage() {
  const [form, setForm] = useState({ name: '', email: '', subject: 'General inquiry', message: '' })
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatus('loading')
    setErrorMsg('')

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Something went wrong.')
      setStatus('success')
    } catch (err) {
      setStatus('error')
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    }
  }

  return (
    <main className="min-h-screen">
      <Navbar />

      <section className="pt-28 lg:pt-36 pb-24 lg:pb-32 relative overflow-hidden">
        <div className="absolute inset-0 bg-hero-mesh pointer-events-none" />

        <div className="relative max-w-5xl mx-auto px-6 lg:px-8">
          <ScrollReveal className="text-center mb-16">
            <div className="pill-badge mx-auto mb-4 w-fit">Contact</div>
            <h1 className="font-display font-extrabold text-4xl sm:text-5xl text-slate-900 tracking-tight">
              Get in <span className="text-gradient">touch</span>
            </h1>
            <p className="mt-4 text-lg text-slate-500 max-w-xl mx-auto">
              Have a question, need help, or want to explore a partnership? We&apos;d love to hear from you.
            </p>
          </ScrollReveal>

          <div className="grid lg:grid-cols-5 gap-8">
            {/* Contact methods */}
            <div className="lg:col-span-2 space-y-4">
              {contactMethods.map((method, i) => (
                <ScrollReveal key={method.title} delay={i * 80}>
                  <a href={method.href} className="block glass-card glass-card-hover rounded-2xl p-5 group">
                    <div className="flex items-start gap-4">
                      <div className="w-11 h-11 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                        {method.icon}
                      </div>
                      <div>
                        <h3 className="font-display font-bold text-sm text-slate-900">{method.title}</h3>
                        <p className="text-xs text-slate-400 mt-0.5">{method.description}</p>
                        <p className="text-sm font-semibold text-emerald-600 mt-2">{method.action}</p>
                      </div>
                    </div>
                  </a>
                </ScrollReveal>
              ))}
            </div>

            {/* Contact form */}
            <ScrollReveal delay={100} className="lg:col-span-3">
              <div className="glass-card rounded-2xl p-8 shadow-xl shadow-slate-200/50">

                {status === 'success' ? (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4">
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round">
                        <path d="M9 12l2 2 4-4M22 12a10 10 0 11-20 0 10 10 0 0120 0z" />
                      </svg>
                    </div>
                    <h2 className="font-display font-bold text-xl text-slate-900 mb-2">Message sent!</h2>
                    <p className="text-slate-500 text-sm mb-6">
                      Thanks for reaching out. We&apos;ve sent a confirmation to <strong>{form.email}</strong> and will reply within 24 hours.
                    </p>
                    <button
                      onClick={() => { setStatus('idle'); setForm({ name: '', email: '', subject: 'General inquiry', message: '' }) }}
                      className="btn-secondary text-sm"
                    >
                      Send another message
                    </button>
                  </div>
                ) : (
                  <>
                    <h2 className="font-display font-bold text-xl text-slate-900 mb-6">Send us a message</h2>

                    <form onSubmit={handleSubmit} className="space-y-4">
                      <div className="grid sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-sm font-medium text-slate-700 mb-1.5">Name</label>
                          <input
                            type="text"
                            name="name"
                            value={form.name}
                            onChange={handleChange}
                            required
                            placeholder="Your name"
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 placeholder:text-slate-400 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
                          <input
                            type="email"
                            name="email"
                            value={form.email}
                            onChange={handleChange}
                            required
                            placeholder="you@company.com"
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 placeholder:text-slate-400 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1.5">Subject</label>
                        <select
                          name="subject"
                          value={form.subject}
                          onChange={handleChange}
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all appearance-none cursor-pointer"
                        >
                          <option>General inquiry</option>
                          <option>Technical support</option>
                          <option>Sales / Enterprise</option>
                          <option>Partnership</option>
                          <option>Bug report</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1.5">Message</label>
                        <textarea
                          name="message"
                          value={form.message}
                          onChange={handleChange}
                          required
                          rows={5}
                          placeholder="How can we help?"
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 placeholder:text-slate-400 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all resize-none"
                        />
                      </div>

                      {status === 'error' && (
                        <p className="text-sm text-red-500 bg-red-50 rounded-xl px-4 py-3">{errorMsg}</p>
                      )}

                      <button type="submit" disabled={status === 'loading'} className="btn-primary text-sm disabled:opacity-60 disabled:cursor-not-allowed">
                        {status === 'loading' ? (
                          <>
                            <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" opacity="0.2" /><path d="M21 12a9 9 0 00-9-9" /></svg>
                            Sending…
                          </>
                        ) : (
                          <>
                            Send Message
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z" /></svg>
                          </>
                        )}
                      </button>
                    </form>
                  </>
                )}
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  )
}
