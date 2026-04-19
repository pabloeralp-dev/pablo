import { useEffect, useState } from 'react'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', fn)
    return () => window.removeEventListener('scroll', fn)
  }, [])

  return (
    <nav className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 flex items-center justify-between px-6 py-3 rounded-full transition-all duration-300 w-[90%] max-w-4xl ${
      scrolled ? 'bg-charcoal/90 backdrop-blur-md border border-white/10' : 'bg-transparent'
    }`}>
      <span className="font-mono text-sm tracking-widest text-cream">BS PRICER_</span>
      <div className="hidden md:flex items-center gap-8 text-sm text-cream/60">
        {[['#pricer','Pricer'],['#greeks','Greeks'],['#payoff','Payoff'],['#iv-solver','IV Solver']].map(([href,label]) => (
          <a key={href} href={href} className="hover:text-cream transition-colors">{label}</a>
        ))}
      </div>
      <a href="#pricer" className="hidden md:block bg-clay text-white text-sm px-5 py-2 rounded-full hover:bg-clay/80 transition-colors">
        Price Now
      </a>
    </nav>
  )
}
