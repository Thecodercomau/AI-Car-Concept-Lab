const form = document.getElementById('conceptForm')
const emptyState = document.getElementById('emptyState')
const loadingState = document.getElementById('loadingState')
const resultState = document.getElementById('resultState')
 
const bindText = (id, value) => { document.getElementById(id).textContent = value }
const listInto = (id, items) => {
  document.getElementById(id).innerHTML = items.map(item => `<li>${escapeHtml(item)}</li>`).join('')
}
const tagsInto = (id, items) => {
  document.getElementById(id).innerHTML = items.map(item => `<span class="tag">${escapeHtml(item)}</span>`).join('')
}
const escapeHtml = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
 
form?.addEventListener('submit', async (event) => {
  event.preventDefault()
  toggleStates('loading')
  const payload = Object.fromEntries(new FormData(form).entries())
  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await response.json()
    if (!response.ok || !data.ok) throw new Error(data.error || 'Something went wrong.')
    renderConcept(data.concept)
    toggleStates('result')
  } catch (error) {
    toggleStates('empty')
    alert(error.message)
  }
})
 
function toggleStates(mode) {
  emptyState.classList.toggle('hidden', mode !== 'empty')
  loadingState.classList.toggle('hidden', mode !== 'loading')
  resultState.classList.toggle('hidden', mode !== 'result')
}
 
function renderConcept(concept) {
  bindText('carName', concept.name)
  bindText('tagline', concept.tagline)
  bindText('retailPrice', concept.retail_price)
  bindText('description', concept.description)
  bindText('powertrain', concept.powertrain)
  bindText('cockpitTheme', concept.cockpit_theme)
  bindText('targetDriver', concept.target_driver)
  listInto('materials', concept.materials)
  listInto('features', concept.features)
  tagsInto('styleTags', concept.style_tags)
  document.getElementById('conceptImage').src = concept.image_url
  renderColorwayButtons(concept.colorways)
  renderCarSvg(concept.colorways[0], concept.name)
}
 
function renderColorwayButtons(colorways) {
  const mount = document.getElementById('swatchButtons')
  mount.innerHTML = ''
  colorways.forEach((cw, index) => {
    const btn = document.createElement('button')
    btn.type = 'button'
    btn.className = `swatch-btn ${index === 0 ? 'active' : ''}`
    btn.textContent = cw.name
    btn.addEventListener('click', () => {
      document.querySelectorAll('.swatch-btn').forEach(node => node.classList.remove('active'))
      btn.classList.add('active')
      renderCarSvg(cw)
    })
    mount.appendChild(btn)
  })
}
 
function renderCarSvg(cw, name = '') {
  const mount = document.getElementById('carSvgMount')
  mount.innerHTML = `
  <svg viewBox="0 0 780 420" role="img" aria-label="${escapeHtml(name || cw.name)} colorway preview">
    <defs>
      <linearGradient id="bodyFill" x1="0" x2="1">
        <stop offset="0%" stop-color="${cw.body}"/>
        <stop offset="100%" stop-color="${shade(cw.body, 32)}"/>
      </linearGradient>
      <linearGradient id="accentFill" x1="0" x2="1">
        <stop offset="0%" stop-color="${cw.accent}"/>
        <stop offset="100%" stop-color="${shade(cw.accent, 18)}"/>
      </linearGradient>
    </defs>
    <rect width="780" height="420" rx="28" fill="#0d1220"/>
    <ellipse cx="390" cy="336" rx="250" ry="24" fill="${alpha(cw.accent, .18)}"/>
    <path d="M128 264 Q176 176 314 160 L468 146 Q576 147 642 223 L684 263 L660 292 L598 292 Q582 239 530 236 Q480 238 458 292 L276 292 Q254 238 204 236 Q151 239 132 292 L98 292 Q75 292 83 270 Z" fill="url(#bodyFill)" stroke="${shade(cw.body, 52)}" stroke-width="4"/>
    <path d="M285 168 L362 132 Q437 118 516 128 L582 214 L352 214 Z" fill="${alpha(cw.cabin, .86)}"/>
    <path d="M170 248 L102 260" stroke="url(#accentFill)" stroke-width="8" stroke-linecap="round"/>
    <path d="M614 247 L674 256" stroke="#fff2b0" stroke-width="8" stroke-linecap="round"/>
    <path d="M323 158 Q416 135 526 146" stroke="${alpha(cw.accent, .95)}" stroke-width="6" stroke-linecap="round"/>
    <circle cx="208" cy="290" r="43" fill="${cw.wheels}"/>
    <circle cx="208" cy="290" r="22" fill="${shade(cw.wheels, 70)}"/>
    <circle cx="528" cy="290" r="43" fill="${cw.wheels}"/>
    <circle cx="528" cy="290" r="22" fill="${shade(cw.wheels, 70)}"/>
    <text x="40" y="52" fill="#dbeafe" font-size="24" font-family="Inter, Arial" font-weight="700">${escapeHtml(cw.name)}</text>
    <text x="40" y="82" fill="#95a4c6" font-size="14" font-family="Inter, Arial">Body · ${cw.body} · Accent · ${cw.accent}</text>
  </svg>`
}
 
function shade(hex, amount) {
  const clean = hex.replace('#', '')
  const num = parseInt(clean, 16)
  const r = Math.min(255, Math.max(0, (num >> 16) + amount))
  const g = Math.min(255, Math.max(0, ((num >> 8) & 255) + amount))
  const b = Math.min(255, Math.max(0, (num & 255) + amount))
  return `#${[r,g,b].map(v => v.toString(16).padStart(2, '0')).join('')}`
}
 
function alpha(hex, opacity) {
  const clean = hex.replace('#', '')
  const num = parseInt(clean, 16)
  const r = num >> 16
  const g = (num >> 8) & 255
  const b = num & 255
  return `rgba(${r}, ${g}, ${b}, ${opacity})`
}
