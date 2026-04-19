import { useState } from 'react'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

export default function AdaptiveRegimen() {
  const today = new Date()
  const initDate = new Date(today.getFullYear(), today.getMonth()+3, today.getDate())
  const [selected, setSelected] = useState(initDate)
  const [month, setMonth] = useState(initDate.getMonth())
  const [year,  setYear]  = useState(initDate.getFullYear())

  const T    = Math.max(0, (selected - today) / (365.25*24*3600*1000))
  const days = Math.max(0, Math.round((selected - today) / (24*3600*1000)))

  const firstDay    = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month+1, 0).getDate()
  const cells = [...Array(firstDay).fill(null), ...Array.from({length:daysInMonth},(_,i)=>i+1)]

  const prevMonth = () => month===0 ? (setMonth(11), setYear(y=>y-1)) : setMonth(m=>m-1)
  const nextMonth = () => month===11 ? (setMonth(0),  setYear(y=>y+1)) : setMonth(m=>m+1)

  const pick = d => {
    if (!d) return
    const date = new Date(year, month, d)
    if (date <= today) return
    setSelected(date)
  }

  return (
    <div className="bg-charcoal border border-white/10 rounded-3xl p-6 flex flex-col gap-4 min-h-[280px]">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-widest text-cream/40">EXPIRY DATE</span>
        <span className="font-mono text-[10px] text-clay">T = {T.toFixed(3)}y</span>
      </div>

      <div className="flex items-center justify-between">
        <button onClick={prevMonth} className="text-cream/40 hover:text-cream px-2">‹</button>
        <span className="font-mono text-xs text-cream">{MONTHS[month]} {year}</span>
        <button onClick={nextMonth} className="text-cream/40 hover:text-cream px-2">›</button>
      </div>

      <div className="grid grid-cols-7 gap-0.5">
        {['S','M','T','W','T','F','S'].map((d,i) => (
          <div key={i} className="text-center font-mono text-[8px] text-cream/25 pb-1">{d}</div>
        ))}
        {cells.map((d, i) => {
          const date   = d ? new Date(year, month, d) : null
          const isSel  = d && selected.getDate()===d && selected.getMonth()===month && selected.getFullYear()===year
          const isPast = date && date <= today
          return (
            <button key={i} onClick={() => pick(d)}
                    className={`text-center font-mono text-[10px] py-1 rounded-md transition-all ${
                      !d        ? 'invisible' :
                      isSel     ? 'bg-clay text-white' :
                      isPast    ? 'text-cream/15 cursor-not-allowed' :
                                  'text-cream/55 hover:bg-white/10 hover:text-cream'
                    }`}>
              {d}
            </button>
          )
        })}
      </div>

      <div className="mt-auto pt-2 border-t border-white/10">
        <div className="font-mono text-[10px] text-cream/45">{days} days · T = {T.toFixed(4)} years</div>
        <div className="font-mono text-[9px] text-cream/25 mt-0.5">
          {selected.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'})}
        </div>
      </div>
    </div>
  )
}
