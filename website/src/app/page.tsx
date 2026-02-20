import Navbar from '@/components/Navbar'
import Hero from '@/components/Hero'
import TrustBar from '@/components/TrustBar'
import ScrollReveal from '@/components/ScrollReveal'
import Features from '@/components/Features'
import DeepDives from '@/components/DeepDives'
import HowItWorks from '@/components/HowItWorks'
import Comparison from '@/components/Comparison'
import Templates from '@/components/Templates'
import Testimonials from '@/components/Testimonials'
import Pricing from '@/components/Pricing'
import FAQ from '@/components/FAQ'
import CTA from '@/components/CTA'
import Footer from '@/components/Footer'

function ProblemSolution() {
  return (
    <section className="py-20 lg:py-28 bg-white">
      <div className="max-w-4xl mx-auto px-6 lg:px-8">
        <ScrollReveal>
          <p className="text-2xl sm:text-3xl lg:text-4xl font-display font-bold text-slate-800 leading-snug tracking-tight text-center text-balance">
            Whether you&apos;re analyzing{' '}
            <span className="text-gradient">sales data</span>, cleaning up{' '}
            <span className="text-gradient">messy spreadsheets</span>, or building{' '}
            <span className="text-gradient">reports from scratch</span>, SheetMind delivers
            AI&#8209;powered actions directly inside your Google Sheet — so you can{' '}
            <span className="underline decoration-emerald-300 decoration-2 underline-offset-4">
              stop copying data into ChatGPT
            </span>{' '}
            and start working 10x faster.
          </p>
        </ScrollReveal>
      </div>
    </section>
  )
}

export default function Home() {
  return (
    <main className="min-h-screen">
      <Navbar />
      <Hero />
      <TrustBar />
      <ProblemSolution />
      <Features />
      <DeepDives />
      <HowItWorks />
      <Comparison />
      <Templates />
      <Testimonials />
      <Pricing />
      <FAQ />
      <CTA />
      <Footer />
    </main>
  )
}
