(() => {
  const HF_CHAT_COMPLETIONS_URL = 'https://router.huggingface.co/v1/chat/completions'
  const HF_MODEL = 'Qwen/Qwen2.5-7B-Instruct'
  const CONCEPT_SCHEMA = `{
  "name": "2-4 word creative car name",
  "tagline": "punchy tagline max 10 words",
  "description": "2-3 sentence cinematic concept description",
  "materials": ["mat1", "mat2", "mat3"],
  "colorways": [
    {"name": "Launch Spec", "body": "#RRGGBB", "accent": "#RRGGBB", "wheels": "#RRGGBB", "cabin": "#RRGGBB"}
  ],
  "features": ["feat1", "feat2", "feat3", "feat4"],
  "powertrain": "power system description",
  "cockpit_theme": "cockpit mood and interface idea",
  "target_driver": "who this concept is for",
  "retail_price": "$XXX,XXX",
  "style_tags": ["tag1", "tag2", "tag3"]
}`

  const form = document.getElementById('conceptForm')
  const emptyState = document.getElementById('emptyState')
  const loadingState = document.getElementById('loadingState')
  const resultState = document.getElementById('resultState')
  const formError = document.getElementById('formError')

  const bindText = (id, value) => { document.getElementById(id).textContent = value || '' }
  const escHtml = (value) => String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

  const listInto = (id, items) => {
    document.getElementById(id).innerHTML = (items || []).map(item => `<li>${escHtml(item)}</li>`).join('')
  }

  const tagsInto = (id, items) => {
    document.getElementById(id).innerHTML = (items || []).map(item => `<span class="tag">${escHtml(item)}</span>`).join('')
  }

  form?.addEventListener('submit', async (event) => {
    event.preventDefault()
    const submitButton = form.querySelector('button[type="submit"]')
    if (submitButton?.disabled) return
    if (submitButton) submitButton.disabled = true
    formError.textContent = ''
    toggleStates('loading')
    try {
      const formData = new FormData(form)
      const prefs = Object.fromEntries(formData.entries())
      const hfToken = prefs.hf_token
      delete prefs.hf_token
      const captchaToken = prefs['h-captcha-response']
      delete prefs['h-captcha-response']

      const captchaResponse = await fetch('/verify-captcha', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 'h-captcha-response': captchaToken || '' }),
      })
      const captchaData = await captchaResponse.json().catch(() => null)
      if (!captchaResponse.ok || !captchaData?.success) {
        throw new Error(captchaData?.error || 'CAPTCHA verification failed.')
      }

      let concept = null
      if (hfToken) {
        const hfResponse = await fetch(HF_CHAT_COMPLETIONS_URL, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${hfToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: HF_MODEL,
            messages: [
              {
                role: 'system',
                content: 'You are an automotive concept designer. Return only a valid JSON object. Do not include markdown.',
              },
              {
                role: 'user',
                content: `Create a distinct futuristic car concept from this brief:
Style: ${prefs.style}
Primary color: ${prefs.primary_color}
Accent color: ${prefs.accent_color}
Material: ${prefs.material}
Occasion: ${prefs.occasion}
Inspiration: ${prefs.inspiration}

Follow this JSON shape exactly, with exactly 3 colorways and valid #RRGGBB color values:
${CONCEPT_SCHEMA}`,
              },
            ],
            temperature: 0.85,
            max_tokens: 1200,
          }),
        })
        const hfData = await hfResponse.json().catch(() => null)
        if (!hfResponse.ok) {
          throw new Error(`Hugging Face request failed (${hfResponse.status}). Check your token and Inference Providers access.`)
        }

        const content = hfData?.choices?.[0]?.message?.content
        if (typeof content !== 'string' || !content.trim()) {
          throw new Error('Hugging Face returned an empty response. Please try again.')
        }
        concept = parseConceptJson(content)
      }

      const saveResponse = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(concept ? { ...prefs, concept } : prefs),
      })
      const data = await saveResponse.json().catch(() => null)
      if (!saveResponse.ok || !data?.success) throw new Error(data?.error || 'Could not save the generated concept.')
      renderConcept(data.concept)
      toggleStates('result')
      window.hcaptcha?.reset()
    } catch (error) {
      toggleStates('empty')
      formError.textContent = error instanceof Error ? error.message : 'Could not generate the concept.'
      window.hcaptcha?.reset()
    } finally {
      if (submitButton) submitButton.disabled = false
    }
  })

  function parseConceptJson(content) {
    const cleaned = content.trim()
      .replace(/^```(?:json)?\s*/i, '')
      .replace(/\s*```$/, '')
    const jsonStart = cleaned.indexOf('{')
    const jsonEnd = cleaned.lastIndexOf('}')
    if (jsonStart < 0 || jsonEnd < jsonStart) {
      throw new Error('Hugging Face returned a response that was not JSON. Please try again.')
    }
    try {
      return JSON.parse(cleaned.slice(jsonStart, jsonEnd + 1))
    } catch {
      throw new Error('Hugging Face returned invalid JSON. Please try again.')
    }
  }

  function toggleStates(mode) {
    emptyState.classList.toggle('hidden', mode !== 'empty')
    loadingState.classList.toggle('hidden', mode !== 'loading')
    resultState.classList.toggle('hidden', mode !== 'result')
  }

  function renderConcept(concept) {
    const c = concept
    bindText('carName', c.name)
    bindText('tagline', c.tagline)
    bindText('retailPrice', c.retail_price)
    bindText('description', c.description)
    bindText('powertrain', c.powertrain)
    bindText('cockpitTheme', c.cockpit_theme)
    bindText('targetDriver', c.target_driver)
    listInto('materials', c.materials)
    listInto('features', c.features)
    tagsInto('styleTags', c.style_tags)
    const img = document.getElementById('conceptImage')
    img.onerror = () => {
      img.onerror = null
      img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(carSvgMarkup(c.colorways?.[0] || {}, c.name))}`
      img.alt = `${c.name} colorway preview (AI render unavailable)`
    }
    img.src = c.image_url
    img.alt = `${c.name} concept render`
    renderColorwayButtons(c.colorways, c.name)
    renderCarSvg(c.colorways?.[0] || {}, c.name)
  }

  function renderColorwayButtons(colorways, name) {
    const mount = document.getElementById('swatchButtons')
    mount.innerHTML = ''
    ;(colorways || []).forEach((cw, index) => {
      const btn = document.createElement('button')
      btn.type = 'button'
      btn.className = `swatch-btn ${index === 0 ? 'active' : ''}`
      btn.textContent = cw.name
      btn.addEventListener('click', () => {
        document.querySelectorAll('.swatch-btn').forEach(node => node.classList.remove('active'))
        btn.classList.add('active')
        renderCarSvg(cw, name)
      })
      mount.appendChild(btn)
    })
  }

  function renderCarSvg(cw, name = '') {
    const mount = document.getElementById('carSvgMount')
    mount.innerHTML = carSvgMarkup(cw, name)
  }

  function carSvgMarkup(cw, name = '') {
    return `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 780 420" role="img" aria-label="${escHtml(name || cw.name || 'Car concept')} colorway preview">
      <defs>
        <linearGradient id="bodyFill" x1="0" x2="1">
          <stop offset="0%" stop-color="${cw.body || '#1d4ed8'}"/>
          <stop offset="100%" stop-color="${shade(cw.body || '#1d4ed8', 32)}"/>
        </linearGradient>
        <linearGradient id="accentFill" x1="0" x2="1">
          <stop offset="0%" stop-color="${cw.accent || '#f97316'}"/>
          <stop offset="100%" stop-color="${shade(cw.accent || '#f97316', 18)}"/>
        </linearGradient>
      </defs>
      <rect width="780" height="420" rx="28" fill="#0d1220"/>
      <ellipse cx="390" cy="336" rx="250" ry="24" fill="${alpha(cw.accent || '#f97316', .18)}"/>
      <path d="M128 264 Q176 176 314 160 L468 146 Q576 147 642 223 L684 263 L660 292 L598 292 Q582 239 530 236 Q480 238 458 292 L276 292 Q254 238 204 236 Q151 239 132 292 L98 292 Q75 292 83 270 Z" fill="url(#bodyFill)" stroke="${shade(cw.body || '#1d4ed8', 52)}" stroke-width="4"/>
      <path d="M285 168 L362 132 Q437 118 516 128 L582 214 L352 214 Z" fill="${alpha(cw.cabin || '#d9dce5', .86)}"/>
      <path d="M170 248 L102 260" stroke="url(#accentFill)" stroke-width="8" stroke-linecap="round"/>
      <path d="M614 247 L674 256" stroke="#fff2b0" stroke-width="8" stroke-linecap="round"/>
      <path d="M323 158 Q416 135 526 146" stroke="${alpha(cw.accent || '#f97316', .95)}" stroke-width="6" stroke-linecap="round"/>
      <circle cx="208" cy="290" r="43" fill="${cw.wheels || '#1b1e28'}"/>
      <circle cx="208" cy="290" r="22" fill="${shade(cw.wheels || '#1b1e28', 70)}"/>
      <circle cx="528" cy="290" r="43" fill="${cw.wheels || '#1b1e28'}"/>
      <circle cx="528" cy="290" r="22" fill="${shade(cw.wheels || '#1b1e28', 70)}"/>
      <text x="40" y="52" fill="#dbeafe" font-size="24" font-family="Inter, Arial" font-weight="700">${escHtml(cw.name || 'Launch Spec')}</text>
      <text x="40" y="82" fill="#95a4c6" font-size="14" font-family="Inter, Arial">Body · ${escHtml(cw.body || '#1d4ed8')} · Accent · ${escHtml(cw.accent || '#f97316')}</text>
    </svg>`
  }

  function shade(hex, amount) {
    const clean = (hex || '#000000').replace('#', '')
    const num = parseInt(clean, 16)
    const r = Math.min(255, Math.max(0, (num >> 16) + amount))
    const g = Math.min(255, Math.max(0, ((num >> 8) & 255) + amount))
    const b = Math.min(255, Math.max(0, (num & 255) + amount))
    return `#${[r, g, b].map(v => v.toString(16).padStart(2, '0')).join('')}`
  }

  function alpha(hex, opacity) {
    const clean = (hex || '#000000').replace('#', '')
    const num = parseInt(clean, 16)
    const r = num >> 16
    const g = (num >> 8) & 255
    const b = num & 255
    return `rgba(${r}, ${g}, ${b}, ${opacity})`
  }
})()
