import DiagnosticShuffler   from './DiagnosticShuffler'
import TelemetryTypewriter  from './TelemetryTypewriter'
import AdaptiveRegimen      from './AdaptiveRegimen'

export default function Features() {
  return (
    <section id="greeks" className="bg-moss rounded-t-5xl py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <p className="font-mono text-xs tracking-[0.3em] text-clay mb-4">QUANTITATIVE ANALYTICS</p>
          <h2 className="font-serif text-5xl md:text-6xl text-cream font-light">The Full Greeks Suite.</h2>
          <p className="mt-4 text-cream/45 max-w-xl mx-auto text-sm leading-relaxed">
            Delta. Gamma. Vega. Theta. Rho. Every sensitivity measure computed in real time,
            following market conventions throughout.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <DiagnosticShuffler />
          <TelemetryTypewriter />
          <AdaptiveRegimen />
        </div>
      </div>
    </section>
  )
}
