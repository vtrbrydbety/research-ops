(async () => {
  // ResearchOps — FROZEN HTML V3.6 → editable Figma prototype generator · HTML Exact
  // Source SHA-256: f47a38b52028db84cb588574d4d8306901af0ed62f8035b87a06ea551c5da74d
  // No network requests. No product semantics are redefined here.

  // Frozen HTML V3.6 design tokens — do not silently redesign these.
  const C = {
    canvas: '#F6F7F9',
    canvasTop: '#F9FAFB',
    canvasBottom: '#F4F5F7',
    surface: '#FFFFFF',
    surface2: '#F9FAFB',
    text: '#15171A',
    textStrong: '#101828',
    muted: '#69707A',
    mutedStrong: '#667085',
    subtle: '#9AA0A8',
    border: '#E5E7EB',
    borderStrong: '#D8DCE2',
    primary: '#111827',
    accent: '#2563EB',
    accentSoft: '#EFF6FF',
    nextActionSoft: '#F8FBFF',
    ready: '#166534',
    readySoft: '#EDF9F1',
    warning: '#9A6700',
    warningSoft: '#FFF7E6',
    blocked: '#991B1B',
    blockedSoft: '#FEF2F2',
    unknown: '#475467',
    unknownSoft: '#F2F4F7',
    acquisition: '#475467',
    acquisitionSoft: '#EEF2F6'
  }

  function rgb(hex) {
    const s = hex.replace('#', '')
    return {
      r: parseInt(s.slice(0, 2), 16) / 255,
      g: parseInt(s.slice(2, 4), 16) / 255,
      b: parseInt(s.slice(4, 6), 16) / 255
    }
  }
  const solid = (hex, opacity = 1) => ({ type: 'SOLID', color: rgb(hex), opacity })
  const rgba = (hex, a = 1) => ({ ...rgb(hex), a })
  const softShadow = {
    type: 'DROP_SHADOW',
    color: rgba('#0F172A', 0.05),
    offset: { x: 0, y: 8 },
    radius: 24,
    spread: 0,
    visible: true,
    blendMode: 'NORMAL'
  }
  const cardShadow = {
    type: 'DROP_SHADOW',
    color: rgba('#0F172A', 0.07),
    offset: { x: 0, y: 18 },
    radius: 50,
    spread: 0,
    visible: true,
    blendMode: 'NORMAL'
  }
  const buttonShadow = {
    type: 'DROP_SHADOW',
    color: rgba('#0F172A', 0.14),
    offset: { x: 0, y: 10 },
    radius: 24,
    spread: 0,
    visible: true,
    blendMode: 'NORMAL'
  }
  const drawerShadow = {
    type: 'DROP_SHADOW',
    color: rgba('#0F172A', 0.14),
    offset: { x: -18, y: 0 },
    radius: 48,
    spread: 0,
    visible: true,
    blendMode: 'NORMAL'
  }
  function canvasFills() {
    return [
      { type:'GRADIENT_RADIAL', gradientStops:[{position:0,color:rgba('#2563EB',0.06)},{position:1,color:rgba('#2563EB',0)}], gradientTransform:[[0.52,0,0.18],[0,0.52,0]] },
      { type:'GRADIENT_LINEAR', gradientStops:[{position:0,color:rgba(C.canvasTop,1)},{position:0.42,color:rgba(C.canvas,1)},{position:1,color:rgba(C.canvasBottom,1)}], gradientTransform:[[0,1,0],[-1,0,1]] }
    ]
  }

  const regular = { family: 'Inter', style: 'Regular' }
  const semi = { family: 'Inter', style: 'Semi Bold' }
  await Promise.all([figma.loadFontAsync(regular), figma.loadFontAsync(semi)])
  await figma.loadAllPagesAsync()

  function setAuto(node, direction = 'VERTICAL', gap = 0, padding = 0) {
    node.layoutMode = direction
    node.primaryAxisSizingMode = 'AUTO'
    node.counterAxisSizingMode = 'AUTO'
    node.itemSpacing = gap
    node.paddingTop = padding
    node.paddingRight = padding
    node.paddingBottom = padding
    node.paddingLeft = padding
  }

  function box(name, opts = {}) {
    const f = figma.createFrame()
    f.name = name
    setAuto(f, opts.direction || 'VERTICAL', opts.gap ?? 0, opts.padding ?? 0)
    f.fills = [solid(opts.fill || C.surface, opts.fillOpacity ?? 1)]
    f.cornerRadius = opts.radius ?? 12
    if (opts.shadow === 'card') f.effects = [cardShadow]
    else if (opts.shadow === 'soft') f.effects = [softShadow]
    else if (opts.shadow === 'drawer') f.effects = [drawerShadow]
    else if (opts.shadow === 'button') f.effects = [buttonShadow]
    else f.effects = []
    if (opts.stroke !== false) {
      f.strokes = [solid(opts.stroke || C.border)]
      f.strokeWeight = opts.strokeWeight ?? 1
    } else {
      f.strokes = []
    }
    if (opts.width) {
      f.resize(opts.width, Math.max(f.height, 1))
      if ((opts.direction || 'VERTICAL') === 'VERTICAL') f.counterAxisSizingMode = 'FIXED'
      else f.primaryAxisSizingMode = 'FIXED'
    }
    if (opts.height) {
      f.resize(f.width, opts.height)
      if ((opts.direction || 'VERTICAL') === 'VERTICAL') f.primaryAxisSizingMode = 'FIXED'
      else f.counterAxisSizingMode = 'FIXED'
    }
    return f
  }

  function txt(str, size = 14, weight = 'Regular', color = C.text, width = null, align = 'LEFT') {
    const t = figma.createText()
    t.fontName = weight === 'Semi Bold' ? semi : regular
    t.characters = str
    t.fontSize = size
    t.fills = [solid(color)]
    t.textAlignHorizontal = align
    t.lineHeight = { unit: 'PERCENT', value: 145 }
    if (width) {
      t.resize(width, Math.max(t.height, 1))
      t.textAutoResize = 'HEIGHT'
    } else {
      t.textAutoResize = 'WIDTH_AND_HEIGHT'
    }
    return t
  }

  function divider(width) {
    const r = figma.createRectangle()
    r.name = 'Divider'
    r.resize(width, 1)
    r.fills = [solid(C.border)]
    return r
  }

  function spacerGrow() {
    const f = figma.createFrame()
    f.name = 'Spacer'
    f.resize(1, 1)
    f.layoutGrow = 1
    f.fills = []
    f.strokes = []
    return f
  }

  function fixedSpacer(height, width = 1) {
    const f = figma.createFrame()
    f.name = `Spacer / ${height}`
    f.resize(width, height)
    f.fills = []
    f.strokes = []
    return f
  }

  function nativeLockIcon() {
    const f = figma.createFrame()
    f.name = 'Lock icon'
    f.resize(28, 28)
    f.fills = [solid(C.unknownSoft)]
    f.strokes = []
    f.cornerRadius = 9

    const shackle = figma.createRectangle()
    shackle.name = 'Shackle'
    shackle.resize(12, 11)
    shackle.x = 8
    shackle.y = 5
    shackle.fills = []
    shackle.strokes = [solid(C.mutedStrong)]
    shackle.strokeWeight = 1.5
    shackle.cornerRadius = 6

    const body = figma.createRectangle()
    body.name = 'Lock body'
    body.resize(16, 12)
    body.x = 6
    body.y = 12
    body.fills = [solid(C.mutedStrong)]
    body.strokes = []
    body.cornerRadius = 3

    const keyhole = figma.createEllipse()
    keyhole.name = 'Keyhole'
    keyhole.resize(2.5, 2.5)
    keyhole.x = 12.75
    keyhole.y = 16
    keyhole.fills = [solid('#FFFFFF')]
    keyhole.strokes = []

    f.appendChild(shackle)
    f.appendChild(body)
    f.appendChild(keyhole)
    return f
  }

  function spinnerIcon() {
    const f = figma.createFrame()
    f.name = 'Spinner'
    f.resize(16, 16)
    f.fills = []
    f.strokes = []

    const ring = figma.createEllipse()
    ring.name = 'Spinner ring'
    ring.resize(16, 16)
    ring.x = 0
    ring.y = 0
    ring.fills = []
    ring.strokes = [solid(C.borderStrong)]
    ring.strokeWeight = 2

    const dot = figma.createEllipse()
    dot.name = 'Spinner accent'
    dot.resize(4, 4)
    dot.x = 6
    dot.y = 0
    dot.fills = [solid(C.accent)]
    dot.strokes = []

    f.appendChild(ring)
    f.appendChild(dot)
    return f
  }

  function chip(label, bg = C.unknownSoft, fg = C.unknown, stroke = null) {
    const f = box(`Chip / ${label}`, { direction: 'HORIZONTAL', gap: 4, padding: 8, fill: bg, stroke: stroke || bg, radius: 999 })
    f.paddingTop = 5
    f.paddingBottom = 5
    f.appendChild(txt(label, 11, 'Semi Bold', fg))
    return f
  }

  function button(label, kind = 'secondary', width = null) {
    const primary = kind === 'primary'
    const ghost = kind === 'secondary' || kind === 'ghost'
    const f = box(`Button / ${label}`, {
      direction: 'HORIZONTAL',
      gap: 8,
      padding: primary ? 16 : 10,
      fill: primary ? C.primary : C.surface,
      fillOpacity: primary ? 1 : 0.76,
      stroke: primary ? C.primary : C.border,
      radius: primary ? 12 : 999,
      shadow: primary ? 'button' : null
    })
    f.paddingTop = primary ? 12 : 8
    f.paddingBottom = primary ? 12 : 8
    f.primaryAxisAlignItems = 'CENTER'
    f.counterAxisAlignItems = 'CENTER'
    if (width) {
      f.resize(width, f.height)
      f.primaryAxisSizingMode = 'FIXED'
    }
    f.appendChild(txt(label, primary ? 13 : 11, 'Semi Bold', primary ? '#FFFFFF' : C.mutedStrong))
    return f
  }

  function textAction(label, muted = false) {
    const f = box(`Text Action / ${label}`, {
      direction: 'HORIZONTAL', gap: 0, padding: 0,
      fill: C.surface, fillOpacity: 0, stroke: false, radius: 0
    })
    f.appendChild(txt(label, 10, 'Semi Bold', muted ? C.mutedStrong : C.accent))
    return f
  }

  function iconBadge(label, bg = C.accentSoft, fg = C.accent) {
    const f = box(`Icon / ${label}`, { width: 34, height: 34, direction: 'HORIZONTAL', fill: bg, stroke: bg, radius: 9 })
    f.primaryAxisAlignItems = 'CENTER'
    f.counterAxisAlignItems = 'CENTER'
    f.appendChild(txt(label, 11, 'Semi Bold', fg))
    return f
  }

  function statusStyle(status) {
    if (status === 'Ready') return [C.readySoft, C.ready]
    if (status === 'Warning') return [C.warningSoft, C.warning]
    if (status === 'Blocked') return [C.blockedSoft, C.blocked]
    return [C.unknownSoft, C.unknown]
  }
  function statusChip(status) {
    const [bg, fg] = statusStyle(status)
    return chip(status, bg, fg)
  }
  function acquisitionChip(state) { return chip(state, C.acquisitionSoft, C.acquisition) }
  function verificationChip(state) {
    if (state === 'Corroborated') return chip(state, C.readySoft, C.ready)
    if (state === 'Unverifiable') return chip(state, C.blockedSoft, C.blocked)
    return chip(state, C.unknownSoft, C.unknown)
  }

  function field(label,value,width=820,multiline=false,focused=false){
    const wrap=box(`Field / ${label||'Value'}`,{width,gap:8,fill:C.surface,fillOpacity:0,stroke:false,radius:0});if(label)wrap.appendChild(txt(label,12,'Semi Bold',C.text));const input=box('Input shell',{width,gap:6,padding:15,fill:C.surface,stroke:focused?'#AABEF2':'#DCE4F4',radius:14});input.fills=[{type:'GRADIENT_LINEAR',gradientStops:[{position:0,color:rgba('#FFFFFF',1)},{position:1,color:rgba('#FAFBFF',0.96)}],gradientTransform:[[0,1,0],[-1,0,1]]}];input.effects=focused?[{type:'DROP_SHADOW',color:rgba('#4F7CFF',0.08),offset:{x:0,y:0},radius:4,spread:2,visible:true,blendMode:'NORMAL'},{type:'DROP_SHADOW',color:rgba('#4A5A9C',0.06),offset:{x:0,y:12},radius:30,spread:0,visible:true,blendMode:'NORMAL'}]:[softShadow];input.appendChild(txt(value,13,'Regular',C.text,width-32));if(multiline)input.paddingBottom=18;wrap.appendChild(input);return wrap
  }

  function sectionHeader(step,title,body,width=820){
    const row=box(`Section / ${step}`,{width,direction:'HORIZONTAL',gap:12,fill:C.surface,fillOpacity:0,stroke:false,radius:0});row.counterAxisAlignItems='MIN';const badge=box(`Step / ${step}`,{width:30,height:30,direction:'HORIZONTAL',fill:C.primary,stroke:false,radius:10});badge.effects=[{type:'DROP_SHADOW',color:rgba('#5C5CFF',0.16),offset:{x:0,y:8},radius:18,spread:0,visible:true,blendMode:'NORMAL'}];badge.primaryAxisAlignItems='CENTER';badge.counterAxisAlignItems='CENTER';badge.appendChild(txt(step,12,'Semi Bold','#FFFFFF'));row.appendChild(badge);const copy=box('Copy',{gap:4,fill:C.surface,fillOpacity:0,stroke:false,radius:0});copy.layoutGrow=1;copy.appendChild(txt(title,17,'Semi Bold',C.text,width-70));copy.appendChild(txt(body,12,'Regular',C.muted,width-70));row.appendChild(copy);return row
  }

  function mainFlowHeight(name, requested) {
    return /^(01|02|03|04|05|06|07|08) ·/.test(name) ? 1020 : requested
  }

  function shellBase(name, requestedHeight = 980) {
    const height = mainFlowHeight(name, requestedHeight)
    const frame = box(name,{width:1440,height,gap:0,padding:0,fill:C.canvas,stroke:false,radius:0})
    frame.fills=canvasFills()
    frame.clipsContent=true
    frame.counterAxisAlignItems='CENTER'

    const nav=box('Top bar',{width:1440,height:72,direction:'HORIZONTAL',gap:12,padding:28,fill:C.surface,fillOpacity:0.88,stroke:false,radius:0})
    nav.primaryAxisSizingMode='FIXED'
    nav.counterAxisSizingMode='FIXED'
    nav.counterAxisAlignItems='CENTER'
    nav.effects=[{type:'BACKGROUND_BLUR',radius:18,visible:true}]

    const orb=box('Brand orb',{width:36,height:36,direction:'HORIZONTAL',fill:C.primary,stroke:false,radius:12})
    orb.effects=[{type:'DROP_SHADOW',color:rgba('#0F172A',0.14),offset:{x:0,y:8},radius:20,spread:0,visible:true,blendMode:'NORMAL'}]
    orb.primaryAxisAlignItems='CENTER'
    orb.counterAxisAlignItems='CENTER'
    orb.appendChild(txt('RO',13,'Semi Bold','#FFFFFF'))
    nav.appendChild(orb)
    nav.appendChild(txt('ResearchOps',16,'Semi Bold',C.text))
    frame.appendChild(nav)

    const workspace=box('Workspace',{width:1320,gap:24,padding:28,fill:C.canvas,fillOpacity:0,stroke:false,radius:0})
    workspace.paddingTop=34
    workspace.paddingBottom=72
    workspace.counterAxisSizingMode='FIXED'
    workspace.counterAxisAlignItems='CENTER'
    frame.appendChild(workspace)
    return {frame,content:workspace}
  }

  function bareScreen(name, height = 980) {
    return shellBase(name, height)
  }

  function screen(name, title, subtitle, tag = '', height = 980) {
    const s = shellBase(name, height)
    const head=box('Page header',{width:1264,gap:8,fill:C.canvas,fillOpacity:0,stroke:false,radius:0})
    head.appendChild(txt(title,38,'Semi Bold',C.text,840))
    if(subtitle) head.appendChild(txt(subtitle,15,'Regular',C.muted,760))
    s.content.appendChild(head)
    return s
  }

  function gateCard(gate, reason, width = 1320) {
    let fg = C.text, bg = '#FFFFFF', stroke = C.border
    if (gate === 'PROCEED') { fg = C.ready; stroke = '#CFE8D6' }
    if (gate === 'PAUSE') { fg = C.blocked; stroke = '#F1CACA' }
    const f = box(`Overall Gate / ${gate}`, { width, gap: 14, padding: 20, fill: bg, stroke, radius: 20, shadow: 'soft' })
    const top = box('Gate header', { width: width - 40, direction: 'HORIZONTAL', gap: 10, fill: bg, stroke: false, radius: 0 })
    const left = box('Gate value', { gap: 4, fill: bg, stroke: false, radius: 0 })
    left.layoutGrow = 1
    left.appendChild(txt('OVERALL GATE', 10, 'Semi Bold', C.subtle))
    left.appendChild(txt(gate, 26, 'Semi Bold', fg))
    top.appendChild(left)
    if (gate === 'PROCEED') top.appendChild(chip('Ready to continue', C.readySoft, C.ready))
    if (gate === 'PAUSE') top.appendChild(chip('Blocking evidence found', C.blockedSoft, C.blocked))
    f.appendChild(top)
    f.appendChild(divider(width - 40))
    const why = box('Reason', { width: width - 40, gap: 4, fill: bg, stroke: false, radius: 0 })
    why.appendChild(txt('REASON', 10, 'Semi Bold', C.subtle))
    why.appendChild(txt(reason, 13, 'Regular', C.text, width - 40))
    f.appendChild(why)
    return f
  }

  function dimensionCard(id, name, status, explanation, impact, width = 438) {
    const f = box(`Dimension Card / ${id} / ${status}`, { width, gap: 12, padding: 16, fill: C.surface, stroke: C.border, radius: 17, shadow: 'soft' })
    const top = box('Header', { width: width - 32, direction: 'HORIZONTAL', gap: 10, fill: C.surface, stroke: false, radius: 0 })
    const title = box('Title', { gap: 3, fill: C.surface, stroke: false, radius: 0 })
    title.layoutGrow = 1
    title.appendChild(txt(id, 10, 'Semi Bold', C.subtle))
    title.appendChild(txt(name, 14, 'Semi Bold', C.text, width - 145))
    top.appendChild(title)
    top.appendChild(statusChip(status))
    f.appendChild(top)
    f.appendChild(txt(explanation, 12, 'Regular', C.muted, width - 32))
    f.appendChild(txt(`Gate impact · ${impact}`, 10, 'Regular', C.subtle, width - 32))
    const details = textAction('View details →')
    f.appendChild(details)
    return { frame: f, details }
  }

  function findingCard(data, width = 1060) {
    const f = box(`Finding / ${data.type}`, { width, gap: 11, padding: 16, fill: C.surface, stroke: C.border, radius: 14 })
    f.appendChild(txt(data.condition, 10, 'Semi Bold', C.subtle))
    f.appendChild(txt(data.title, 15, 'Semi Bold', C.text, width - 32))
    f.appendChild(txt(data.summary, 12, 'Regular', C.muted, width - 32))
    const tags = box('Finding tags', { width: width - 32, direction: 'HORIZONTAL', gap: 7, fill: C.surface, stroke: false, radius: 0 })
    tags.layoutWrap = 'WRAP'
    tags.appendChild(chip(`Finding type · ${data.type}`, C.unknownSoft, C.unknown))
    if (data.critical) tags.appendChild(chip('Gate-critical', C.warningSoft, C.warning))
    tags.appendChild(chip('Evidence · Available', C.unknownSoft, C.unknown))
    f.appendChild(tags)
    const foot = box('Finding actions', { width: width - 32, direction: 'HORIZONTAL', gap: 10, fill: C.surface, stroke: false, radius: 0 })
    foot.appendChild(txt(data.impact, 10, 'Regular', C.subtle))
    foot.appendChild(spacerGrow())
    const feedback = textAction('Give feedback', true)
    const evidence = textAction('View evidence →')
    foot.appendChild(feedback)
    foot.appendChild(evidence)
    f.appendChild(foot)
    return { frame: f, feedback, evidence }
  }

  function keyValue(label, value, width = 760) {
    const row = box(`KV / ${label}`, { width, direction: 'HORIZONTAL', gap: 12, padding: 12, fill: C.surface, stroke: C.border, radius: 0 })
    const l = txt(label.toUpperCase(), 9, 'Semi Bold', C.subtle, 130)
    const v = txt(value, 11, 'Regular', C.text, width - 170)
    row.appendChild(l)
    row.appendChild(v)
    return row
  }

  function evidencePanel(name, data, opts = {}) {
    const s = screen(name, data.title, 'Inspect the evidence, its source and location, then return to the judgment.', 'EVIDENCE DETAIL', 900)
    const panel = box('Evidence drawer', { width: 500, gap: 15, padding: 22, fill: C.surface, stroke: false, radius: 0, shadow: 'drawer' })
    const vrow = box('Verification', { width: 456, direction: 'HORIZONTAL', gap: 10, fill: C.surface, stroke: false, radius: 0 })
    vrow.appendChild(txt('Verification status', 11, 'Semi Bold', C.muted))
    vrow.appendChild(spacerGrow())
    vrow.appendChild(verificationChip(data.verification))
    panel.appendChild(vrow)
    panel.appendChild(divider(456))
    panel.appendChild(txt('EVIDENCE SUMMARY', 9, 'Semi Bold', C.subtle))
    panel.appendChild(txt(data.summary, 12, 'Regular', C.text, 456))
    panel.appendChild(divider(456))
    panel.appendChild(txt('SOURCE', 9, 'Semi Bold', C.subtle))
    panel.appendChild(txt(data.source, 12, 'Regular', C.text, 456))
    const meta = box('Source meta', { width: 456, direction: 'HORIZONTAL', gap: 8, fill: C.surface, stroke: false, radius: 0 })
    const loc = box('Location', { width: 224, gap: 4, padding: 10, fill: C.surface2, stroke: C.border, radius: 10 })
    loc.appendChild(txt('LOCATION', 8, 'Semi Bold', C.subtle))
    loc.appendChild(txt(data.location, 10, 'Regular', C.muted, 204))
    meta.appendChild(loc)
    const mt = box('Material Type', { width: 224, gap: 4, padding: 10, fill: C.surface2, stroke: C.border, radius: 10 })
    mt.appendChild(txt('MATERIAL TYPE', 8, 'Semi Bold', C.subtle))
    mt.appendChild(txt(data.materialType, 10, 'Regular', C.muted, 204))
    meta.appendChild(mt)
    panel.appendChild(meta)
    if (data.conflict) {
      const c = box('Conflict note', { width: 456, gap: 5, padding: 11, fill: C.surface2, stroke: C.border, radius: 10 })
      c.appendChild(txt('CONFLICT NOTE', 8, 'Semi Bold', C.subtle))
      c.appendChild(txt(data.conflict, 10, 'Regular', C.muted, 432))
      panel.appendChild(c)
    }
    if (data.compare) {
      const compare = box('Conflicting sources', { width: 456, direction: 'HORIZONTAL', gap: 8, fill: C.surface, stroke: false, radius: 0 })
      data.compare.forEach((item, i) => {
        const c = box(`Source ${i + 1}`, { width: 224, gap: 5, padding: 10, fill: C.surface2, stroke: C.border, radius: 10 })
        c.appendChild(txt(i === 0 ? 'SOURCE A' : 'SOURCE B', 8, 'Semi Bold', C.subtle))
        c.appendChild(txt(item.title, 10, 'Semi Bold', C.text, 204))
        c.appendChild(txt(item.copy, 9, 'Regular', C.muted, 204))
        compare.appendChild(c)
      })
      panel.appendChild(compare)
    }
    const actions = box('Evidence actions', { width: 456, direction: 'HORIZONTAL', gap: 10, fill: C.surface, stroke: false, radius: 0 })
    const feedback = textAction('Feedback on evidence', true)
    actions.appendChild(feedback)
    actions.appendChild(spacerGrow())
    let openSource = null
    if (data.sourceAvailable) {
      openSource = button('Open source ↗', 'primary')
      actions.appendChild(openSource)
    }
    panel.appendChild(actions)
    const drawerRow = box('Drawer presentation', { width: 1264, direction: 'HORIZONTAL', gap: 0, fill: C.canvas, fillOpacity: 0, stroke: false, radius: 0 })
    drawerRow.appendChild(spacerGrow())
    drawerRow.appendChild(panel)
    s.content.appendChild(drawerRow)
    return { ...s, feedback, openSource }
  }

  function feedbackPanel(name, contextLabel, contextTitle) {
    const s = screen(name, contextLabel, 'Feedback changes the Finding / Evidence context, not the Dimension Status or Overall Gate directly.', 'FEEDBACK', 860)
    const panel = box('Shared Feedback Panel', { width: 440, gap: 14, padding: 22, fill: C.surface, stroke: false, radius: 0, shadow: 'drawer' })
    panel.appendChild(txt(contextLabel.toUpperCase(), 9, 'Semi Bold', C.subtle))
    panel.appendChild(txt(contextTitle, 20, 'Semi Bold', C.text, 396))
    panel.appendChild(txt('Confirm, question, correct, or add evidence. Reassessment only propagates from the affected object when required.', 11, 'Regular', C.muted, 396))
    const opts = box('Feedback options', { width: 396, direction: 'HORIZONTAL', gap: 8, fill: C.surface, stroke: false, radius: 0 })
    opts.layoutWrap = 'WRAP'
    ;['Confirm', 'Question', 'Correct', 'Add Evidence'].forEach(v => opts.appendChild(button(v, 'secondary')))
    panel.appendChild(opts)
    panel.appendChild(field('Feedback note', 'Describe what should be questioned, corrected, or added…', 396, true))
    const note = box('Reassessment note', { width: 396, gap: 4, padding: 11, fill: C.surface2, stroke: false, radius: 10 })
    note.appendChild(txt('If the underlying judgment changes', 10, 'Semi Bold', C.text))
    note.appendChild(txt('Feedback → affected Finding → related Dimension → Readiness Result / Gate when necessary.', 10, 'Regular', C.muted, 372))
    panel.appendChild(note)
    const submit = button('Submit feedback', 'primary', 396)
    panel.appendChild(submit)
    const drawerRow = box('Drawer presentation', { width: 1264, direction: 'HORIZONTAL', gap: 0, fill: C.canvas, fillOpacity: 0, stroke: false, radius: 0 })
    drawerRow.appendChild(spacerGrow())
    drawerRow.appendChild(panel)
    s.content.appendChild(drawerRow)
    return { ...s, submit }
  }

  function modeCard(title, body, active = false, width = 192) {
    const f = box(`Environment mode / ${title}`, {
      width, gap: 6, padding: 15,
      fill: active ? C.accentSoft : C.surface,
      fillOpacity: active ? 1 : 0.74,
      stroke: active ? '#9EB7EF' : C.border,
      radius: 16,
      shadow: active ? 'soft' : null
    })
    f.appendChild(txt(title, 13, 'Semi Bold', C.textStrong, width - 30))
    f.appendChild(txt(body, 11, 'Regular', C.muted, width - 30))
    return f
  }

  function signalCard(name, state, summary, width = 652) {
    const f = box(`Signal / ${name}`, { width, gap: 9, padding: 14, fill: C.surface, fillOpacity: 0.74, stroke: C.border, radius: 14 })
    const top = box('Header', { width: width - 30, direction: 'HORIZONTAL', gap: 10, fill: C.surface, stroke: false, radius: 0 })
    top.appendChild(txt(name, 13, 'Semi Bold', C.text))
    top.appendChild(spacerGrow())
    top.appendChild(statusChip(state))
    f.appendChild(top)
    f.appendChild(txt(summary, 11, 'Regular', C.muted, width - 30))
    const details = textAction('View details →')
    f.appendChild(details)
    return { frame: f, details }
  }

  function stateFrame(name, title, state, copy, rows = [], actions = [], opts = {}) {
    const s = screen(name, title, copy, opts.tag || 'STATE VARIANT', opts.height || 820)
    const card = box('State card', { width: 820, gap: 14, padding: 22, fill: C.surface, stroke: C.border, radius: 18 })
    const top = box('State header', { width: 776, direction: 'HORIZONTAL', gap: 10, fill: C.surface, stroke: false, radius: 0 })
    top.appendChild(txt(opts.kicker || 'ACQUISITION STATE', 9, 'Semi Bold', C.subtle))
    top.appendChild(spacerGrow())
    top.appendChild(opts.business ? statusChip(state) : acquisitionChip(state))
    card.appendChild(top)
    if (opts.boundary) {
      const b = box('Boundary', { width: 776, gap: 5, padding: 11, fill: C.surface2, stroke: false, radius: 10 })
      b.appendChild(txt(opts.boundary, 10, 'Regular', C.muted, 752))
      card.appendChild(b)
    }
    if (rows.length) {
      const list = box('State details', { width: 776, gap: 0, fill: C.surface, stroke: C.border, radius: 12 })
      rows.forEach((r, idx) => {
        const row = box(`Row / ${r[0]}`, { width: 774, direction: 'HORIZONTAL', gap: 10, padding: 12, fill: C.surface, stroke: false, radius: 0 })
        const left = box('Copy', { gap: 3, fill: C.surface, stroke: false, radius: 0 })
        left.layoutGrow = 1
        left.appendChild(txt(r[0], 11, 'Semi Bold', C.text, 560))
        if (r[1]) left.appendChild(txt(r[1], 9, 'Regular', C.subtle, 560))
        row.appendChild(left)
        if (r[2]) row.appendChild(txt(r[2], 9, 'Semi Bold', r[2] === 'Available' ? C.ready : C.muted))
        list.appendChild(row)
        if (idx < rows.length - 1) list.appendChild(divider(774))
      })
      card.appendChild(list)
    }
    const actionRow = box('Actions', { width: 776, direction: 'HORIZONTAL', gap: 9, fill: C.surface, stroke: false, radius: 0 })
    const nodes = []
    actions.forEach((a, i) => {
      const b = button(a, i === actions.length - 1 ? 'primary' : 'secondary')
      actionRow.appendChild(b)
      nodes.push(b)
    })
    if (actions.length) card.appendChild(actionRow)
    s.content.appendChild(card)
    return { ...s, actionNodes: nodes }
  }

  function owningPage(node) {
    let p = node
    while (p && p.type !== 'PAGE') p = p.parent
    return p || null
  }

  function topLevelFrame(node) {
    let n = node
    while (n && n.parent && n.parent.type !== 'PAGE') n = n.parent
    return n && n.type === 'FRAME' ? n : null
  }

  async function navigateOnClick(node, destination, navigation = 'NAVIGATE') {
    if (!node || !destination) return false

    const sourcePage = owningPage(node)
    const destinationPage = owningPage(destination)
    const sourceFrame = topLevelFrame(node)
    const destinationFrame = topLevelFrame(destination)

    // Figma NAVIGATE requires a different top-level Frame on the same Page.
    if (
      navigation === 'NAVIGATE' &&
      (
        !sourcePage ||
        !destinationPage ||
        sourcePage.id !== destinationPage.id ||
        !sourceFrame ||
        !destinationFrame ||
        sourceFrame.id === destinationFrame.id ||
        destination.id !== destinationFrame.id
      )
    ) {
      console.warn(
        'Skipped invalid prototype navigation:',
        node.name,
        '→',
        destination.name,
        sourcePage ? sourcePage.name : 'no source page',
        '→',
        destinationPage ? destinationPage.name : 'no destination page'
      )
      return false
    }

    await node.setReactionsAsync([{
      trigger: { type: 'ON_CLICK' },
      actions: [{
        type: 'NODE', destinationId: destination.id, navigation,
        transition: { type: 'DISSOLVE', easing: { type: 'EASE_OUT' }, duration: 0.18 },
        preserveScrollPosition: false
      }]
    }])
    return true
  }
  async function backOnClick(node) {
    if (!node) return
    await node.setReactionsAsync([{ trigger: { type: 'ON_CLICK' }, actions: [{ type: 'BACK' }] }])
  }

  async function urlOnClick(node, url) {
    if (!node || !url) return false
    await node.setReactionsAsync([{
      trigger: { type: 'ON_CLICK' },
      actions: [{ type: 'URL', url }]
    }])
    return true
  }
  async function hotspot(node, destination) {
    const r = figma.createRectangle()
    r.name = 'Prototype Hotspot / Continue'
    r.resize(node.width, node.height)
    r.fills = [solid('#FFFFFF', 0)]
    r.strokes = []
    node.appendChild(r)
    r.x = 0; r.y = 0
    await navigateOnClick(r, destination)
    return r
  }

  function pageByName(name) {
    return figma.root.children.find(p => p.type === 'PAGE' && p.name === name) || null
  }

  function clearPage(page) {
    ;[...page.children].forEach(n => n.remove())
  }

  function containsLegacyCoverSignature(node) {
    if (!node || !('findOne' in node)) return false
    return !!node.findOne(n => n.type === 'TEXT' && (
      n.characters.includes('ResearchOps · Clickable Figma Prototype') ||
      n.characters.includes('Frozen source SHA-256') ||
      n.characters.includes('FROZEN · V3.6')
    ))
  }

  function isLegacyResearchOpsNode(node) {
    const name = node.name || ''
    if (name.startsWith('ResearchOps FROZEN V3.6 /')) return true
    if (node.getPluginData && node.getPluginData('researchops-frozen-source') === 'V3.6') return true
    if ((name === 'Cover' || name === '00_Cover' || name === '00 · Cover') && containsLegacyCoverSignature(node)) return true
    return false
  }

  function cleanupLegacyResearchOps() {
    const emptyLegacyPages = []
    const outputNames = new Set(['01_Prototype','02_Components','03_Variants_Reference'])
    for (const page of [...figma.root.children]) {
      if (page.type !== 'PAGE' || outputNames.has(page.name)) continue
      let removed = false
      for (const child of [...page.children]) {
        if (isLegacyResearchOpsNode(child)) { child.remove(); removed = true }
      }
      const legacyPageName = page.name === 'Cover' || page.name === '00_Cover' || page.name === '00 · Cover' || page.name.startsWith('ResearchOps FROZEN V3.6 /')
      if ((removed || legacyPageName) && page.children.length === 0) emptyLegacyPages.push(page)
    }
    return emptyLegacyPages
  }

  function createOrReusePage(name) {
    let p = pageByName(name)
    if (!p) { p = figma.createPage(); p.name = name }
    return p
  }

  const emptyLegacyPages = cleanupLegacyResearchOps()
  const prototypePage = createOrReusePage('01_Prototype')
  const componentsPage = createOrReusePage('02_Components')
  const variantsPage = createOrReusePage('03_Variants_Reference')
  clearPage(prototypePage); clearPage(componentsPage); clearPage(variantsPage)
  figma.root.insertChild(0, prototypePage)
  figma.root.insertChild(1, componentsPage)
  figma.root.insertChild(2, variantsPage)
  await figma.setCurrentPageAsync(prototypePage)
  for (const p of emptyLegacyPages) if (p.parent && p !== prototypePage && p !== componentsPage && p !== variantsPage) p.remove()

  function area(page, offsetX = 0, offsetY = 0) {
    return { page, offsetX, offsetY }
  }

  function place(container, node, x, y) {
    const parent = container.page || container
    parent.appendChild(node)
    node.x = x + (container.offsetX || 0)
    node.y = y + (container.offsetY || 0)
    node.setPluginData('researchops-frozen-source', 'V3.6')
    node.setPluginData('researchops-generator', 'html-exact-v36')
    return node
  }

  // -------------------------------------------------------------------------
  // 01 — Main clickable flow
  // -------------------------------------------------------------------------
  const mainSection = area(prototypePage, 0, 0)

  // Task Setup — Frozen HTML specific builder
  const setup = screen(
    '01 · Task Setup',
    'What are you trying to reproduce?',
    'Provide your goal, one reliable target entry, and how you want to supply the environment information needed for this assessment.',
    'TASK SETUP',
    1020
  )
  place(mainSection, setup.frame, 60, 90)

  const setupBody = box('Setup body', {
    width:1264,direction:'HORIZONTAL',gap:22,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })

  const setupMain = box('Main form', {
    width:882,gap:0,padding:26,
    fill:C.surface,fillOpacity:0.94,stroke:'#FFFFFF',
    radius:28,shadow:'card'
  })

  // Section 01
  setupMain.appendChild(sectionHeader('01','Reproduction goal','What decision should this assessment help you make?',830))
  setupMain.appendChild(fixedSpacer(15,830))
  setupMain.appendChild(field('', 'Decide whether it is worth starting the FGI reproduction now.', 830, true, true))
  setupMain.appendChild(fixedSpacer(8,830))
  setupMain.appendChild(txt('+ Add context or constraints · Optional',11,'Semi Bold',C.muted,830))
  setupMain.appendChild(fixedSpacer(24,830))
  setupMain.appendChild(divider(830))
  setupMain.appendChild(fixedSpacer(24,830))

  // Section 02
  setupMain.appendChild(sectionHeader('02','Target','Provide one reliable entry. ResearchOps can resolve related materials after you continue.',830))
  setupMain.appendChild(fixedSpacer(15,830))
  const targetRow = box('Target entry',{
    width:830,direction:'HORIZONTAL',gap:0,
    fill:C.surface,stroke:'#DCE4F4',radius:14
  })
  const type = box('Target type',{
    width:160,direction:'HORIZONTAL',padding:14,
    fill:C.surface,fillOpacity:0,stroke:false,radius:0
  })
  type.appendChild(txt('Repository ▾',12,'Semi Bold',C.text))
  targetRow.appendChild(type)
  const targetDivider = figma.createRectangle()
  targetDivider.name='Target type divider'
  targetDivider.resize(1,44)
  targetDivider.fills=[solid(C.border)]
  targetDivider.strokes=[]
  targetRow.appendChild(targetDivider)
  const targetValue = box('Target value',{
    width:669,direction:'HORIZONTAL',padding:16,
    fill:C.surface,fillOpacity:0,stroke:false,radius:0
  })
  targetValue.paddingTop=14
  targetValue.paddingBottom=14
  targetValue.appendChild(txt('https://github.com/aseuteurideu/FGI',12,'Regular',C.text,637))
  targetRow.appendChild(targetValue)
  setupMain.appendChild(targetRow)
  setupMain.appendChild(fixedSpacer(24,830))
  setupMain.appendChild(divider(830))
  setupMain.appendChild(fixedSpacer(24,830))

  // Section 03
  setupMain.appendChild(sectionHeader('03','Reproduction environment','Choose how ResearchOps should understand the environment you actually plan to use.',830))
  setupMain.appendChild(fixedSpacer(15,830))

  const modeRow = box('Environment modes',{
    width:830,direction:'HORIZONTAL',gap:10,
    fill:C.surface,fillOpacity:0,stroke:false,radius:0
  })
  modeRow.layoutWrap='WRAP'
  modeRow.counterAxisSpacing=10
  modeRow.appendChild(modeCard('Read-only detection','Inspect agreed facts after authorization.',true,410))
  modeRow.appendChild(modeCard('Snapshot','Upload an existing environment snapshot.',false,410))
  modeRow.appendChild(modeCard('Manual input','Paste or describe known environment facts.',false,410))
  modeRow.appendChild(modeCard('Not now','Continue without environment details.',false,410))
  setupMain.appendChild(modeRow)

  setupMain.appendChild(fixedSpacer(13,830))
  const authInfo = box('Authorization required',{
    width:830,direction:'HORIZONTAL',gap:10,padding:12,
    fill:C.surface2,stroke:C.border,radius:12
  })
  authInfo.appendChild(iconBadge('i',C.unknownSoft,C.mutedStrong))
  const authCopy = box('Copy',{gap:3,fill:C.surface2,stroke:false,radius:0})
  authCopy.layoutGrow=1
  authCopy.appendChild(txt('Authorization required',11,'Semi Bold',C.text))
  authCopy.appendChild(txt('No environment data is read until you approve read-only access.',10,'Regular',C.muted,760))
  authInfo.appendChild(authCopy)
  setupMain.appendChild(authInfo)

  setupMain.appendChild(fixedSpacer(20,830))
  const setupActions = box('Actions',{
    width:830,direction:'HORIZONTAL',gap:8,
    fill:C.surface,fillOpacity:0,stroke:false,radius:0
  })
  setupActions.appendChild(spacerGrow())
  const setupContinue = button('Continue to authorization →','primary')
  setupActions.appendChild(setupContinue)
  setupMain.appendChild(setupActions)

  setupBody.appendChild(setupMain)

  // Aside
  const setupSide = box('Aside',{
    width:360,gap:14,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  const get = box('What you’ll get',{
    width:360,gap:10,padding:18,
    fill:C.surface,fillOpacity:0.94,stroke:false,radius:20,shadow:'soft'
  })
  get.appendChild(txt('What you’ll get',13,'Semi Bold',C.text))
  get.appendChild(txt('✓ Structured readiness status\n✓ Findings linked to inspectable evidence\n✓ An Overall Gate and first Next Action',11,'Regular',C.text,324))
  setupSide.appendChild(get)

  const safety = box('Read-only decision support',{
    width:360,direction:'HORIZONTAL',gap:10,padding:15,
    fill:C.surface2,stroke:C.border,radius:12
  })
  safety.counterAxisAlignItems='CENTER'
  safety.appendChild(nativeLockIcon())
  const safetyCopy = box('Safety copy',{gap:3,fill:C.surface2,stroke:false,radius:0})
  safetyCopy.appendChild(txt('Read-only decision support',11,'Semi Bold',C.text))
  safetyCopy.appendChild(txt('No installs, environment changes, file writes, or training execution.',10,'Regular',C.muted,284))
  safety.appendChild(safetyCopy)
  setupSide.appendChild(safety)

  setupBody.appendChild(setupSide)
  setup.content.appendChild(setupBody)

  // Target Identified — Frozen HTML specific builder
  const identified = bareScreen('02 · Target Identified', 1020)
  place(mainSection, identified.frame, 1540, 90)

  const idCard = box('Target identified card',{
    width:760,gap:0,padding:22,
    fill:C.surface,stroke:C.border,radius:22
  })
  idCard.effects=[{
    type:'DROP_SHADOW',
    color:rgba('#0F172A',0.05),
    offset:{x:0,y:12},
    radius:34,
    spread:0,
    visible:true,
    blendMode:'NORMAL'
  }]

  const idTop = box('Header',{
    width:716,direction:'HORIZONTAL',gap:14,
    fill:C.surface,stroke:false,radius:0
  })
  const idHeadCopy = box('Header copy',{gap:0,fill:C.surface,stroke:false,radius:0})
  idHeadCopy.layoutGrow=1
  idHeadCopy.appendChild(txt('TARGET RESOLUTION',9,'Semi Bold',C.subtle))
  idHeadCopy.appendChild(fixedSpacer(5,1))
  idHeadCopy.appendChild(txt('Target identified',26,'Semi Bold',C.textStrong,560))
  idTop.appendChild(idHeadCopy)
  idTop.appendChild(chip('Identified',C.readySoft,C.ready))
  idCard.appendChild(idTop)

  idCard.appendChild(fixedSpacer(10,716))
  idCard.appendChild(txt(
    'ResearchOps resolved the submitted entry into a target that can be used for the readiness assessment.',
    11,'Regular',C.mutedStrong,650
  ))

  idCard.appendChild(fixedSpacer(16,716))
  const idMeta = box('Resolved target metadata',{
    width:716,gap:0,
    fill:C.surface,stroke:C.border,radius:15
  })
  idMeta.clipsContent=true
  idMeta.appendChild(keyValue('Target','aseuteurideu/FGI',716))
  idMeta.appendChild(keyValue('Resolved as','Repository · resolution status: Identified',716))
  idMeta.appendChild(keyValue('Source entry','https://github.com/aseuteurideu/FGI',716))
  idMeta.appendChild(keyValue(
    'Materials summary',
    'Primary target resolved from the submitted entry. Related public materials will be linked during the assessment when available.',
    716
  ))
  idCard.appendChild(idMeta)

  idCard.appendChild(fixedSpacer(17,716))
  const idActions = box('Actions',{
    width:716,direction:'HORIZONTAL',gap:10,
    fill:C.surface,stroke:false,radius:0
  })
  const idBack = button('← Back to Task Setup','secondary')
  const idContinue = button('Continue →','primary')
  idActions.appendChild(idBack)
  idActions.appendChild(spacerGrow())
  idActions.appendChild(idContinue)
  idCard.appendChild(idActions)

  identified.content.appendChild(idCard)

  // Authorization
  const auth = screen('03 · Read-only Authorization', 'Review read-only access', 'Confirm what ResearchOps may inspect before it reads any environment information.', 'READ-ONLY ACCESS', 920)
  place(mainSection, auth.frame, 3020, 90)
  const authCard = box('Authorization card', { width: 940, gap: 0, padding: 26, fill: C.surface, fillOpacity: 0.94, stroke: false, radius: 28, shadow: 'card' })
  const authModeRow = box('Environment acquisition mode', { width:888,direction:'HORIZONTAL',gap:12,fill:C.surface,fillOpacity:0,stroke:false,radius:0 })
  authModeRow.counterAxisAlignItems='CENTER'
  authModeRow.appendChild(chip('Read-only detection', C.readySoft, C.ready))
  authModeRow.appendChild(spacerGrow())
  authModeRow.appendChild(txt('Environment acquisition mode',10,'Regular',C.mutedStrong))
  authCard.appendChild(authModeRow)
  authCard.appendChild(fixedSpacer(16,888))
  authCard.appendChild(divider(888))
  authCard.appendChild(fixedSpacer(18,888))
  const scopes = box('Scope', { width: 888, direction: 'HORIZONTAL', gap: 12, fill: C.surface, fillOpacity:0, stroke: false, radius: 0 })
  const can = box('Can inspect', { width: 438, gap: 8, padding: 17, fill: C.surface, fillOpacity: 0.76, stroke: C.border, radius: 18 })
  can.appendChild(txt('ResearchOps can inspect', 13, 'Semi Bold', C.text)); can.appendChild(txt('✓ OS / Python / Framework\n✓ CUDA / Driver\n✓ GPU / VRAM\n✓ Available disk', 12, 'Regular', C.mutedStrong, 404)); scopes.appendChild(can)
  const wont = box('Will not', { width: 438, gap: 8, padding: 17, fill: C.surface, fillOpacity: 0.76, stroke: C.border, radius: 18 })
  wont.appendChild(txt('ResearchOps will not', 13, 'Semi Bold', C.text)); wont.appendChild(txt('× Install packages\n× Modify environment\n× Write / delete / overwrite files\n× Start training or reproduction', 12, 'Regular', C.mutedStrong, 404)); scopes.appendChild(wont)
  authCard.appendChild(scopes)
  authCard.appendChild(fixedSpacer(14,888))
  authCard.appendChild(txt('Prefer not to authorize direct inspection? Use Snapshot or Manual Input instead.', 11, 'Regular', C.muted, 888))
  authCard.appendChild(fixedSpacer(18,888))
  const authRow = box('Auth actions', { width: 888, direction: 'HORIZONTAL', gap: 8, fill: C.surface, fillOpacity:0, stroke: false, radius: 0 })
  const authBack = button('← Back', 'secondary'); const useSnapshot = button('Use snapshot instead', 'secondary'); const useManual = button('Manual input', 'secondary'); const noEnv = button('Continue without environment data', 'secondary'); const deny = button("Don't authorize", 'secondary'); const allow = button('Authorize read-only access →', 'primary')
  ;[authBack,useSnapshot,useManual,noEnv].forEach(b => authRow.appendChild(b)); authRow.appendChild(spacerGrow()); authRow.appendChild(deny); authRow.appendChild(allow)
  authCard.appendChild(authRow); auth.content.appendChild(authCard)

  // Processing — Frozen HTML specific builder
  const processing = bareScreen('04 · Processing', 1020)
  place(mainSection, processing.frame, 4500, 90)

  // HTML: .processing-wrap { max-width:820px; margin:72px auto 0; }
  processing.content.appendChild(fixedSpacer(72,1264))

  const proc = box('Processing card',{
    width:820,gap:0,padding:30,
    fill:C.surface,fillOpacity:0.94,stroke:'#FFFFFF',radius:24
  })
  proc.effects=[cardShadow,{type:'BACKGROUND_BLUR',radius:22,visible:true}]

  const procIcon = box('Processing icon',{
    width:42,height:42,direction:'HORIZONTAL',
    fill:C.primary,stroke:false,radius:14
  })
  procIcon.primaryAxisAlignItems='CENTER'
  procIcon.counterAxisAlignItems='CENTER'
  procIcon.appendChild(txt('✦',16,'Semi Bold','#FFFFFF'))
  proc.appendChild(procIcon)

  proc.appendChild(fixedSpacer(16,760))
  proc.appendChild(txt('Building your readiness assessment',22,'Semi Bold',C.textStrong,760))
  proc.appendChild(fixedSpacer(7,760))
  proc.appendChild(txt(
    'ResearchOps is combining the authorized environment facts with the resolved target materials.',
    12,'Regular',C.mutedStrong,760
  ))

  proc.appendChild(fixedSpacer(22,760))

  const processingRows = [
    ['Reading authorized environment facts','Processing'],
    ['Reviewing linked target materials','Processing'],
    ['Building readiness findings and Gate','Processing']
  ]

  processingRows.forEach(([label,state],i)=>{
    if(i>0) proc.appendChild(divider(760))
    const row = box(`Processing row ${i+1}`,{
      width:760,direction:'HORIZONTAL',gap:16,
      fill:C.surface,fillOpacity:0,stroke:false,radius:0
    })
    row.paddingTop=12
    row.paddingBottom=12
    row.counterAxisAlignItems='CENTER'

    const left = box('Processing row left',{
      direction:'HORIZONTAL',gap:10,
      fill:C.surface,fillOpacity:0,stroke:false,radius:0
    })
    left.counterAxisAlignItems='CENTER'
    left.appendChild(spinnerIcon())
    left.appendChild(txt(label,12,'Semi Bold',C.text,520))
    row.appendChild(left)
    row.appendChild(spacerGrow())
    row.appendChild(txt(state,10,'Semi Bold',C.mutedStrong))
    proc.appendChild(row)
  })

  processing.content.appendChild(proc)

  // 05 Readiness Overview — Frozen HTML specific builder
  const overview = bareScreen('05 · Readiness Overview · CONDITIONAL PROCEED', 1020)
  place(mainSection, overview.frame, 5980, 90)
  overview.frame.overflowDirection = 'VERTICAL'

  const overviewWrap = box('Overview wrap',{
    width:1180,gap:0,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })

  const overviewHead = box('Overview head',{
    width:1180,direction:'HORIZONTAL',gap:20,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  overviewHead.counterAxisAlignItems='MIN'
  overviewHead.appendChild(txt('Readiness Overview',31,'Semi Bold',C.text,820))
  overviewHead.appendChild(spacerGrow())
  const overviewBack = button('← Back to Task Setup','secondary')
  overviewHead.appendChild(overviewBack)
  overviewWrap.appendChild(overviewHead)
  overviewWrap.appendChild(fixedSpacer(18,1180))

  overviewWrap.appendChild(
    gateCard('CONDITIONAL PROCEED','Dataset access permission is not confirmed.',1180)
  )
  overviewWrap.appendChild(fixedSpacer(16,1180))

  const dims = box('Dimension grid',{
    width:1180,direction:'HORIZONTAL',gap:12,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  const od1 = dimensionCard('RD-01','Data & Access Readiness','Unknown','A gate-critical dataset access condition is still unresolved.','Prevents full PROCEED',385)
  const od2 = dimensionCard('RD-02','Environment & Dependency Readiness','Warning','The environment is usable for assessment, with a known compatibility risk that needs validation.','Non-blocking risk',385)
  const od3 = dimensionCard('RD-03','Weights & Configuration Readiness','Ready','Required checkpoint and configuration relationships are sufficiently identified for the current assessment.','No current blocker',385)
  dims.appendChild(od1.frame)
  dims.appendChild(od2.frame)
  dims.appendChild(od3.frame)
  overviewWrap.appendChild(dims)

  overviewWrap.appendChild(fixedSpacer(16,1180))
  const low = box('Overview lower',{
    width:1180,gap:12,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })

  const issue = box('Key issue',{
    width:1180,gap:6,padding:17,
    fill:C.surface,stroke:C.border,radius:18
  })
  issue.appendChild(txt('KEY ISSUE',9,'Semi Bold',C.subtle))
  issue.appendChild(txt('Dataset access permission is not confirmed',15,'Semi Bold',C.textStrong,1146))
  issue.appendChild(txt('This unresolved condition is currently preventing a full PROCEED decision.',11,'Regular',C.mutedStrong,1146))
  issue.appendChild(chip('Gate-critical Unknown',C.surface2,C.mutedStrong,C.border))
  low.appendChild(issue)

  const next = box('First Next Action',{
    width:1180,gap:6,padding:17,
    fill:C.nextActionSoft,stroke:'#D9E4FF',radius:18
  })
  next.appendChild(chip('First Next Action','#EAF2FF','#1D4ED8'))
  next.appendChild(txt('Confirm whether dataset access can be obtained',15,'Semi Bold',C.textStrong,1146))
  next.appendChild(txt('Verify access before moving to higher-cost reproduction work.',11,'Regular',C.mutedStrong,1146))
  next.appendChild(txt('Action type · Resolve Gate-critical Unknown',9,'Regular',C.subtle))
  low.appendChild(next)
  overviewWrap.appendChild(low)

  overviewWrap.appendChild(fixedSpacer(16,1180))
  const sigHead = box('Signals section head',{
    width:1180,direction:'HORIZONTAL',gap:10,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  sigHead.appendChild(txt('Additional signals',12,'Semi Bold',C.text))
  sigHead.appendChild(spacerGrow())
  sigHead.appendChild(txt('Supporting context, not core Dimensions',10,'Regular',C.subtle))
  overviewWrap.appendChild(sigHead)
  overviewWrap.appendChild(fixedSpacer(9,1180))

  const sigRow = box('Signal row',{
    width:1180,direction:'HORIZONTAL',gap:10,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  const rs = signalCard('Resource Constraint','Unknown','Available resource facts are known, but the project’s explicit minimum requirements are not fully confirmed.',585)
  const es = signalCard('Evaluation Conflict','Warning','A paper-code evaluation setting difference may affect result comparability.',585)
  sigRow.appendChild(rs.frame)
  sigRow.appendChild(es.frame)
  overviewWrap.appendChild(sigRow)
  overviewWrap.appendChild(fixedSpacer(72,1180))
  overview.content.appendChild(overviewWrap)

  // 06 Dimension Detail — Frozen HTML specific builder
  const detail = bareScreen('06 · Dimension Detail · RD-01 Unknown', 1020)
  place(mainSection, detail.frame, 7460, 90)

  const detailWrap = box('Dimension detail wrap',{
    width:1080,gap:0,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })

  const detailHead = box('Dimension detail head',{
    width:1080,direction:'HORIZONTAL',gap:18,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  detailHead.counterAxisAlignItems='MIN'
  const detailHeadCopy = box('Dimension title',{
    gap:0,fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  detailHeadCopy.layoutGrow=1
  detailHeadCopy.appendChild(txt('RD-01',10,'Semi Bold',C.subtle))
  detailHeadCopy.appendChild(fixedSpacer(5,1))
  detailHeadCopy.appendChild(txt('Data & Access Readiness',28,'Semi Bold',C.textStrong,820))
  detailHead.appendChild(detailHeadCopy)
  const detailBack = button('← Back to Overview','secondary')
  detailHead.appendChild(detailBack)
  detailWrap.appendChild(detailHead)
  detailWrap.appendChild(fixedSpacer(18,1080))

  const summary = box('Dimension summary',{
    width:1080,gap:12,padding:18,
    fill:C.surface,stroke:C.border,radius:14
  })
  const st = box('Status line',{
    width:1044,direction:'HORIZONTAL',gap:12,
    fill:C.surface,stroke:false,radius:0
  })
  st.appendChild(statusChip('Unknown'))
  st.appendChild(txt('Dataset access cannot be confirmed with the evidence currently available.',12,'Regular',C.text,820))
  summary.appendChild(st)
  summary.appendChild(txt('GATE IMPACT',9,'Semi Bold',C.subtle))
  summary.appendChild(txt('Prevents full PROCEED until the access condition is resolved.',11,'Regular',C.muted,1044))
  detailWrap.appendChild(summary)

  detailWrap.appendChild(fixedSpacer(16,1080))
  detailWrap.appendChild(txt('Key Finding',12,'Semi Bold','#344054',1080))
  detailWrap.appendChild(fixedSpacer(9,1080))

  const finding = findingCard({
    condition:'Condition · Dataset access',
    title:'Dataset access permission is not confirmed',
    summary:'Available sources do not establish whether the required dataset can be accessed under the user’s actual reproduction conditions.',
    type:'Unknown',
    critical:true,
    impact:'Gate impact · Prevents full PROCEED'
  },1080)
  detailWrap.appendChild(finding.frame)

  detailWrap.appendChild(fixedSpacer(16,1080))
  detailWrap.appendChild(txt('Related Next Action',12,'Semi Bold','#344054',1080))
  detailWrap.appendChild(fixedSpacer(9,1080))

  const rel = box('Related Next Action card',{
    width:1080,gap:5,padding:16,
    fill:C.nextActionSoft,stroke:'#D9E4FF',radius:17
  })
  rel.appendChild(txt('Confirm whether dataset access can be obtained',14,'Semi Bold',C.text,1048))
  rel.appendChild(txt('Resolve Gate-critical Unknown',9,'Regular',C.muted))
  detailWrap.appendChild(rel)
  detail.content.appendChild(detailWrap)

  // 07 Evidence Detail — clone Dimension Detail + fixed overlay drawer
  const evidenceFrame = detail.frame.clone()
  evidenceFrame.name = '07 · Evidence Detail · RD-01'
  place(mainSection, evidenceFrame, 8940, 90)

  const evidenceBackdrop = figma.createRectangle()
  evidenceBackdrop.name = 'Evidence backdrop'
  evidenceBackdrop.resize(1440,1020)
  evidenceBackdrop.fills = [solid('#0F172A',0.22)]
  evidenceBackdrop.strokes = []
  evidenceFrame.appendChild(evidenceBackdrop)
  evidenceBackdrop.layoutPositioning = 'ABSOLUTE'
  evidenceBackdrop.x = 0
  evidenceBackdrop.y = 0

  const evidenceDrawer = box('Evidence drawer',{
    width:500,height:1020,gap:0,padding:22,
    fill:C.surface,stroke:false,radius:0,shadow:'drawer'
  })
  evidenceFrame.appendChild(evidenceDrawer)
  evidenceDrawer.layoutPositioning = 'ABSOLUTE'
  evidenceDrawer.x = 940
  evidenceDrawer.y = 0

  const evHead = box('Evidence head',{
    width:456,direction:'HORIZONTAL',gap:14,
    fill:C.surface,stroke:false,radius:0
  })
  evHead.counterAxisAlignItems='MIN'
  const evHeadCopy = box('Evidence head copy',{gap:0,fill:C.surface,stroke:false,radius:0})
  evHeadCopy.layoutGrow=1
  evHeadCopy.appendChild(txt('EVIDENCE DETAIL',9,'Semi Bold',C.subtle))
  evHeadCopy.appendChild(fixedSpacer(5,1))
  evHeadCopy.appendChild(txt('Dataset access evidence',18,'Semi Bold',C.textStrong,350))
  evHead.appendChild(evHeadCopy)
  const evidenceBack = textAction('Close',true)
  evHead.appendChild(evidenceBack)
  evidenceDrawer.appendChild(evHead)
  evidenceDrawer.appendChild(fixedSpacer(15,456))
  evidenceDrawer.appendChild(divider(456))
  evidenceDrawer.appendChild(fixedSpacer(15,456))

  const vrow = box('Verification',{
    width:456,direction:'HORIZONTAL',gap:10,
    fill:C.surface,stroke:false,radius:0
  })
  vrow.appendChild(txt('Verification status',11,'Semi Bold',C.muted))
  vrow.appendChild(spacerGrow())
  vrow.appendChild(verificationChip('Located Only'))
  evidenceDrawer.appendChild(vrow)

  evidenceDrawer.appendChild(fixedSpacer(15,456))
  evidenceDrawer.appendChild(divider(456))
  evidenceDrawer.appendChild(fixedSpacer(15,456))
  evidenceDrawer.appendChild(txt('EVIDENCE SUMMARY',9,'Semi Bold',C.subtle))
  evidenceDrawer.appendChild(fixedSpacer(6,456))
  evidenceDrawer.appendChild(txt(
    'Project materials identify the dataset dependency, but they do not establish whether the current user has permission or access under the intended reproduction conditions.',
    12,'Regular',C.text,456
  ))

  evidenceDrawer.appendChild(fixedSpacer(15,456))
  evidenceDrawer.appendChild(divider(456))
  evidenceDrawer.appendChild(fixedSpacer(15,456))
  evidenceDrawer.appendChild(txt('SOURCE',9,'Semi Bold',C.subtle))
  evidenceDrawer.appendChild(fixedSpacer(6,456))
  evidenceDrawer.appendChild(txt('Project documentation + user access context',12,'Regular',C.text,456))
  evidenceDrawer.appendChild(fixedSpacer(10,456))

  const evMeta = box('Source meta',{
    width:456,direction:'HORIZONTAL',gap:8,
    fill:C.surface,stroke:false,radius:0
  })
  const evLoc = box('Location',{
    width:224,gap:4,padding:10,
    fill:C.surface2,stroke:C.border,radius:10
  })
  evLoc.appendChild(txt('LOCATION',8,'Semi Bold',C.subtle))
  evLoc.appendChild(txt('Dataset / setup references and current user-provided access facts',10,'Regular',C.muted,204))
  evMeta.appendChild(evLoc)

  const evType = box('Material Type',{
    width:224,gap:4,padding:10,
    fill:C.surface2,stroke:C.border,radius:10
  })
  evType.appendChild(txt('MATERIAL TYPE',8,'Semi Bold',C.subtle))
  evType.appendChild(txt('Repository / User Context',10,'Regular',C.muted,204))
  evMeta.appendChild(evType)
  evidenceDrawer.appendChild(evMeta)

  evidenceDrawer.appendChild(fixedSpacer(16,456))
  const evActions = box('Evidence actions',{
    width:456,direction:'HORIZONTAL',gap:10,
    fill:C.surface,stroke:false,radius:0
  })
  const evidenceFeedbackAction = textAction('Feedback on evidence',true)
  const evidenceOpenSource = button('Open source ↗','primary')
  evActions.appendChild(evidenceFeedbackAction)
  evActions.appendChild(spacerGrow())
  evActions.appendChild(evidenceOpenSource)
  evidenceDrawer.appendChild(evActions)

  const evidence = {
    frame:evidenceFrame,
    content:evidenceFrame,
    feedback:evidenceFeedbackAction,
    openSource:evidenceOpenSource
  }

  // 08 Finding Feedback — clone Dimension Detail + fixed overlay panel
  const feedbackFrame = detail.frame.clone()
  feedbackFrame.name = '08 · Shared Feedback · Finding'
  place(mainSection, feedbackFrame, 10420, 90)

  const feedbackBackdrop = figma.createRectangle()
  feedbackBackdrop.name = 'Feedback backdrop'
  feedbackBackdrop.resize(1440,1020)
  feedbackBackdrop.fills = [solid('#0F172A',0.22)]
  feedbackBackdrop.strokes = []
  feedbackFrame.appendChild(feedbackBackdrop)
  feedbackBackdrop.layoutPositioning = 'ABSOLUTE'
  feedbackBackdrop.x = 0
  feedbackBackdrop.y = 0

  const feedbackDrawer = box('Shared Feedback Panel',{
    width:440,height:1020,gap:0,padding:22,
    fill:C.surface,stroke:false,radius:0,shadow:'drawer'
  })
  feedbackFrame.appendChild(feedbackDrawer)
  feedbackDrawer.layoutPositioning = 'ABSOLUTE'
  feedbackDrawer.x = 1000
  feedbackDrawer.y = 0

  const fbHead = box('Feedback head',{
    width:396,direction:'HORIZONTAL',gap:12,
    fill:C.surface,stroke:false,radius:0
  })
  fbHead.counterAxisAlignItems='MIN'
  const fbHeadCopy = box('Feedback head copy',{gap:0,fill:C.surface,stroke:false,radius:0})
  fbHeadCopy.layoutGrow=1
  fbHeadCopy.appendChild(txt('FINDING FEEDBACK',9,'Semi Bold',C.subtle))
  fbHeadCopy.appendChild(fixedSpacer(5,1))
  fbHeadCopy.appendChild(txt('Dataset access permission is not confirmed',20,'Semi Bold',C.text,305))
  fbHead.appendChild(fbHeadCopy)
  const feedbackBack = textAction('Close',true)
  fbHead.appendChild(feedbackBack)
  feedbackDrawer.appendChild(fbHead)
  feedbackDrawer.appendChild(fixedSpacer(15,396))
  feedbackDrawer.appendChild(divider(396))
  feedbackDrawer.appendChild(fixedSpacer(15,396))

  feedbackDrawer.appendChild(txt(
    'Feedback applies to this Finding and its evidence. It does not directly edit the Dimension status or Overall Gate.',
    11,'Regular',C.muted,396
  ))
  feedbackDrawer.appendChild(fixedSpacer(15,396))

  const fbOptions = box('Feedback options',{
    width:396,direction:'HORIZONTAL',gap:8,
    fill:C.surface,stroke:false,radius:0
  })
  fbOptions.layoutWrap='WRAP'
  ;['Confirm','Question','Correct','Add Evidence'].forEach(v=>{
    fbOptions.appendChild(button(v,'secondary'))
  })
  feedbackDrawer.appendChild(fbOptions)

  feedbackDrawer.appendChild(fixedSpacer(15,396))
  feedbackDrawer.appendChild(field(
    'Feedback note',
    'Describe what should be questioned, corrected, or added…',
    396,
    true
  ))
  feedbackDrawer.appendChild(fixedSpacer(12,396))

  const reassessment = box('Reassessment note',{
    width:396,gap:4,padding:11,
    fill:C.surface2,stroke:false,radius:10
  })
  reassessment.appendChild(txt('If the underlying judgment changes',10,'Semi Bold',C.text))
  reassessment.appendChild(txt(
    'Feedback → affected Finding → related Dimension → Readiness Result / Gate when necessary.',
    10,'Regular',C.muted,372
  ))
  feedbackDrawer.appendChild(reassessment)

  feedbackDrawer.appendChild(fixedSpacer(14,396))
  const feedbackSubmit = button('Submit feedback','primary',396)
  feedbackDrawer.appendChild(feedbackSubmit)

  const feedback = {
    frame:feedbackFrame,
    content:feedbackFrame,
    submit:feedbackSubmit
  }

  // -------------------------------------------------------------------------
  // 02 — Supporting views / branches
  // -------------------------------------------------------------------------
  // All prototype-supporting frames use the same 1440 × 1020 viewport
  // as the main clickable flow. Modal / Drawer states preserve their
  // underlying page context instead of becoming invented standalone screens.
  const supportSection = area(prototypePage, 0, 1320)

  function overlayBackdrop(name, opacity = 0.22) {
    const r = figma.createRectangle()
    r.name = name
    r.resize(1440,1020)
    r.fills = [solid('#0F172A',opacity)]
    r.strokes = []
    return r
  }

  function fixedRightPanel(name, width, padding, shadow = 'drawer') {
    const f = box(name,{
      width,height:1020,gap:0,padding,
      fill:C.surface,stroke:false,radius:0,shadow
    })
    return f
  }

  function signalDrawerOverlay(baseFrame, name, title, state, type) {
    const frame = baseFrame.clone()
    frame.name = name
    frame.resize(1440,1020)
    frame.clipsContent = true
    frame.overflowDirection = 'NONE'

    const backdrop = overlayBackdrop('Signal drawer backdrop',0.22)
    frame.appendChild(backdrop)
    backdrop.layoutPositioning='ABSOLUTE'
    backdrop.x=0
    backdrop.y=0

    const drawer = fixedRightPanel('Additional Signal drawer',460,24)
    frame.appendChild(drawer)
    drawer.layoutPositioning='ABSOLUTE'
    drawer.x=980
    drawer.y=0

    const inner = 412

    const head = box('Drawer head',{
      width:inner,direction:'HORIZONTAL',gap:14,
      fill:C.surface,stroke:false,radius:0
    })
    head.counterAxisAlignItems='MIN'
    const hc = box('Drawer title copy',{gap:0,fill:C.surface,stroke:false,radius:0})
    hc.layoutGrow=1
    hc.appendChild(txt('ADDITIONAL SIGNAL',9,'Semi Bold',C.subtle))
    hc.appendChild(fixedSpacer(5,1))
    hc.appendChild(txt(title,19,'Semi Bold',C.textStrong,320))
    head.appendChild(hc)
    const close = button('Close','secondary')
    head.appendChild(close)
    drawer.appendChild(head)
    drawer.appendChild(fixedSpacer(16,inner))
    drawer.appendChild(divider(inner))

    function section(label, value, valueNode=null) {
      drawer.appendChild(fixedSpacer(16,inner))
      drawer.appendChild(txt(label.toUpperCase(),9,'Semi Bold',C.subtle))
      drawer.appendChild(fixedSpacer(6,inner))
      if (valueNode) drawer.appendChild(valueNode)
      else drawer.appendChild(txt(value,12,'Regular',C.text,inner))
      drawer.appendChild(fixedSpacer(16,inner))
      drawer.appendChild(divider(inner))
    }

    section('Status','',statusChip(state))

    if(type==='resource'){
      section(
        'Summary',
        'Current resource facts are available, but the repository does not provide enough explicit minimum requirements to make a reliable comparison.'
      )

      const table = box('Resource items',{
        width:inner,gap:0,
        fill:C.surface,stroke:C.border,radius:12
      })
      table.clipsContent=true

      const rows = [
        ['RESOURCE','CURRENT','REQUIRED',true],
        ['GPU / VRAM','Known','Not confirmed',false],
        ['Disk','Known','Not confirmed',false],
        ['Time budget','Provided','Not explicitly stated',false]
      ]
      rows.forEach((r,idx)=>{
        const row=box(`Resource row ${idx}`,{
          width:410,direction:'HORIZONTAL',gap:8,padding:10,
          fill:r[3]?C.surface2:C.surface,stroke:false,radius:0
        })
        const col1=txt(r[0],r[3]?9:10,r[3]?'Semi Bold':'Semi Bold',r[3]?C.subtle:C.mutedStrong,104)
        const col2=txt(r[1],r[3]?9:10,r[3]?'Semi Bold':'Regular',r[3]?C.subtle:C.text,126)
        const col3=txt(r[2],r[3]?9:10,r[3]?'Semi Bold':'Regular',r[3]?C.subtle:C.text,140)
        row.appendChild(col1);row.appendChild(col2);row.appendChild(col3)
        table.appendChild(row)
        if(idx<rows.length-1) table.appendChild(divider(410))
      })
      section('Resource items','',table)

      section(
        'Gate impact',
        'Can contribute to CONDITIONAL PROCEED, but does not justify Resource Blocked without an explicit minimum requirement plus a confirmed shortfall.'
      )
    } else {
      section('Conflict type','Paper-Code Setting')
      section(
        'Summary',
        'The paper and repository appear to use different evaluation settings. The difference is relevant to comparability but is not independently blocking the reproduction.'
      )
      section(
        'Gate impact',
        'Evaluation Warning may support CONDITIONAL PROCEED, but it does not independently produce a P0 Blocked state.'
      )
    }

    drawer.appendChild(fixedSpacer(16,inner))
    drawer.appendChild(txt('EVIDENCE',9,'Semi Bold',C.subtle))
    drawer.appendChild(fixedSpacer(6,inner))
    const evidence = textAction('View related evidence →')
    drawer.appendChild(evidence)

    return {frame,close,evidence}
  }

  function evidenceDrawerOverlay(baseFrame, name, data) {
    const frame = baseFrame.clone()
    frame.name = name
    frame.resize(1440,1020)
    frame.clipsContent = true
    frame.overflowDirection = 'NONE'

    const backdrop = overlayBackdrop('Evidence backdrop',0.22)
    frame.appendChild(backdrop)
    backdrop.layoutPositioning='ABSOLUTE'
    backdrop.x=0
    backdrop.y=0

    const drawer = fixedRightPanel('Evidence drawer',500,22)
    frame.appendChild(drawer)
    drawer.layoutPositioning='ABSOLUTE'
    drawer.x=940
    drawer.y=0
    const inner=456

    const head = box('Evidence head',{
      width:inner,direction:'HORIZONTAL',gap:14,
      fill:C.surface,stroke:false,radius:0
    })
    head.counterAxisAlignItems='MIN'
    const hc=box('Evidence head copy',{gap:0,fill:C.surface,stroke:false,radius:0})
    hc.layoutGrow=1
    hc.appendChild(txt('EVIDENCE DETAIL',9,'Semi Bold',C.subtle))
    hc.appendChild(fixedSpacer(5,1))
    hc.appendChild(txt(data.title,19,'Semi Bold',C.textStrong,350))
    head.appendChild(hc)
    const close=button('Close','secondary')
    head.appendChild(close)
    drawer.appendChild(head)

    drawer.appendChild(fixedSpacer(15,inner))
    drawer.appendChild(divider(inner))
    drawer.appendChild(fixedSpacer(15,inner))

    const vr=box('Verification row',{
      width:inner,direction:'HORIZONTAL',gap:10,
      fill:C.surface,stroke:false,radius:0
    })
    vr.appendChild(txt('Verification status',11,'Semi Bold',C.muted))
    vr.appendChild(spacerGrow())
    vr.appendChild(verificationChip(data.verification))
    drawer.appendChild(vr)

    drawer.appendChild(fixedSpacer(15,inner))
    drawer.appendChild(divider(inner))
    drawer.appendChild(fixedSpacer(15,inner))
    drawer.appendChild(txt('EVIDENCE SUMMARY',9,'Semi Bold',C.subtle))
    drawer.appendChild(fixedSpacer(6,inner))
    drawer.appendChild(txt(data.summary,12,'Regular',C.text,inner))

    drawer.appendChild(fixedSpacer(15,inner))
    drawer.appendChild(divider(inner))
    drawer.appendChild(fixedSpacer(15,inner))
    drawer.appendChild(txt('SOURCE',9,'Semi Bold',C.subtle))
    drawer.appendChild(fixedSpacer(6,inner))
    drawer.appendChild(txt(data.source,12,'Regular',C.text,inner))
    drawer.appendChild(fixedSpacer(10,inner))

    const meta=box('Source meta',{
      width:inner,direction:'HORIZONTAL',gap:8,
      fill:C.surface,stroke:false,radius:0
    })
    const loc=box('Location',{
      width:224,gap:4,padding:10,
      fill:C.surface2,stroke:C.border,radius:10
    })
    loc.appendChild(txt('LOCATION',8,'Semi Bold',C.subtle))
    loc.appendChild(txt(data.location,10,'Regular',C.muted,204))
    meta.appendChild(loc)
    const mt=box('Material Type',{
      width:224,gap:4,padding:10,
      fill:C.surface2,stroke:C.border,radius:10
    })
    mt.appendChild(txt('MATERIAL TYPE',8,'Semi Bold',C.subtle))
    mt.appendChild(txt(data.materialType,10,'Regular',C.muted,204))
    meta.appendChild(mt)
    drawer.appendChild(meta)

    if(data.conflict){
      drawer.appendChild(fixedSpacer(14,inner))
      const conflict=box('Conflict note',{
        width:inner,gap:5,padding:11,
        fill:C.surface2,stroke:C.border,radius:10
      })
      conflict.appendChild(txt('CONFLICT NOTE',8,'Semi Bold',C.subtle))
      conflict.appendChild(txt(data.conflict,10,'Regular',C.muted,432))
      drawer.appendChild(conflict)
    }

    if(data.compare){
      drawer.appendChild(fixedSpacer(10,inner))
      const compare=box('Conflicting sources',{
        width:inner,direction:'HORIZONTAL',gap:8,
        fill:C.surface,stroke:false,radius:0
      })
      data.compare.forEach((item,i)=>{
        const c=box(i===0?'Source A':'Source B',{
          width:224,gap:5,padding:10,
          fill:C.surface2,stroke:C.border,radius:10
        })
        c.appendChild(txt(i===0?'SOURCE A':'SOURCE B',8,'Semi Bold',C.subtle))
        c.appendChild(txt(item.title,10,'Semi Bold',C.text,204))
        c.appendChild(txt(item.copy,9,'Regular',C.muted,204))
        compare.appendChild(c)
      })
      drawer.appendChild(compare)
    }

    drawer.appendChild(fixedSpacer(16,inner))
    const actions=box('Evidence actions',{
      width:inner,direction:'HORIZONTAL',gap:10,
      fill:C.surface,stroke:false,radius:0
    })
    const feedback=textAction('Feedback on evidence',true)
    actions.appendChild(feedback)
    actions.appendChild(spacerGrow())
    let openSource=null
    if(data.sourceUrl){
      openSource=button('Open source ↗','primary')
      actions.appendChild(openSource)
    }
    drawer.appendChild(actions)

    return {frame,close,feedback,openSource}
  }

  function feedbackOverlay(baseFrame, name, contextTitle, context='evidence') {
    const frame=baseFrame.clone()
    frame.name=name
    frame.resize(1440,1020)
    frame.clipsContent=true
    frame.overflowDirection='NONE'

    const backdrop=overlayBackdrop('Feedback backdrop',0.22)
    frame.appendChild(backdrop)
    backdrop.layoutPositioning='ABSOLUTE'
    backdrop.x=0
    backdrop.y=0

    const panel=fixedRightPanel('Shared Feedback Panel',440,22)
    frame.appendChild(panel)
    panel.layoutPositioning='ABSOLUTE'
    panel.x=1000
    panel.y=0
    const inner=396

    const head=box('Feedback head',{
      width:inner,direction:'HORIZONTAL',gap:12,
      fill:C.surface,stroke:false,radius:0
    })
    head.counterAxisAlignItems='MIN'
    const hc=box('Feedback head copy',{gap:0,fill:C.surface,stroke:false,radius:0})
    hc.layoutGrow=1
    hc.appendChild(txt(context==='evidence'?'EVIDENCE FEEDBACK':'FINDING FEEDBACK',9,'Semi Bold',C.subtle))
    hc.appendChild(fixedSpacer(5,1))
    hc.appendChild(txt(contextTitle,20,'Semi Bold',C.textStrong,300))
    head.appendChild(hc)
    const close=button('Close','secondary')
    head.appendChild(close)
    panel.appendChild(head)

    panel.appendChild(fixedSpacer(15,inner))
    panel.appendChild(divider(inner))
    panel.appendChild(fixedSpacer(15,inner))

    const copy=context==='evidence'
      ? 'Feedback applies to this Evidence. It does not directly edit the Finding, Dimension status, or Overall Gate.'
      : 'Feedback applies to this Finding and its evidence. It does not directly edit the Dimension status or Overall Gate.'
    panel.appendChild(txt(copy,11,'Regular',C.muted,inner))
    panel.appendChild(fixedSpacer(15,inner))

    const opts=box('Feedback options',{
      width:inner,direction:'HORIZONTAL',gap:8,
      fill:C.surface,stroke:false,radius:0
    })
    opts.layoutWrap='WRAP'
    ;['Confirm','Question','Correct','Add Evidence'].forEach(v=>opts.appendChild(button(v,'secondary')))
    panel.appendChild(opts)

    panel.appendChild(fixedSpacer(15,inner))
    panel.appendChild(field('Feedback note','Describe what should be questioned, corrected, or added…',inner,true))
    panel.appendChild(fixedSpacer(12,inner))

    const reassessment=box('Reassessment note',{
      width:inner,gap:4,padding:11,
      fill:C.surface2,stroke:false,radius:10
    })
    reassessment.appendChild(txt('If the underlying judgment changes',10,'Semi Bold',C.text))
    reassessment.appendChild(txt(
      'Feedback → affected Finding → related Dimension → Readiness Result / Gate when necessary.',
      10,'Regular',C.muted,372
    ))
    panel.appendChild(reassessment)

    panel.appendChild(fixedSpacer(14,inner))
    const submit=button('Submit feedback','primary',inner)
    panel.appendChild(submit)

    return {frame,close,submit}
  }

  function buildFrozenDimensionState(name,id,title,status,statusCopy,gateImpact,findingData,nextAction,nextType) {
    const s=bareScreen(name,1020)

    const wrap=box('Dimension detail wrap',{
      width:1080,gap:0,
      fill:C.canvas,fillOpacity:0,stroke:false,radius:0
    })

    const head=box('Dimension detail head',{
      width:1080,direction:'HORIZONTAL',gap:18,
      fill:C.canvas,fillOpacity:0,stroke:false,radius:0
    })
    head.counterAxisAlignItems='MIN'
    const hc=box('Dimension title',{gap:0,fill:C.canvas,fillOpacity:0,stroke:false,radius:0})
    hc.layoutGrow=1
    hc.appendChild(txt(id,10,'Semi Bold',C.subtle))
    hc.appendChild(fixedSpacer(5,1))
    hc.appendChild(txt(title,28,'Semi Bold',C.textStrong,820))
    head.appendChild(hc)
    const back=button('← Back to Overview','secondary')
    head.appendChild(back)
    wrap.appendChild(head)
    wrap.appendChild(fixedSpacer(18,1080))

    const summary=box('Dimension summary',{
      width:1080,gap:12,padding:18,
      fill:C.surface,stroke:C.border,radius:18
    })
    const sr=box('Status line',{
      width:1044,direction:'HORIZONTAL',gap:12,
      fill:C.surface,stroke:false,radius:0
    })
    sr.appendChild(statusChip(status))
    sr.appendChild(txt(statusCopy,12,'Regular',C.text,820))
    summary.appendChild(sr)
    summary.appendChild(txt('GATE IMPACT',9,'Semi Bold',C.subtle))
    summary.appendChild(txt(gateImpact,11,'Regular',C.muted,1044))
    wrap.appendChild(summary)

    wrap.appendChild(fixedSpacer(16,1080))
    wrap.appendChild(txt('Key Finding',12,'Semi Bold','#344054',1080))
    wrap.appendChild(fixedSpacer(9,1080))
    const finding=findingCard(findingData,1080)
    wrap.appendChild(finding.frame)

    wrap.appendChild(fixedSpacer(16,1080))
    wrap.appendChild(txt('Related Next Action',12,'Semi Bold','#344054',1080))
    wrap.appendChild(fixedSpacer(9,1080))
    const na=box('Related Next Action card',{
      width:1080,gap:5,padding:16,
      fill:C.nextActionSoft,stroke:'#D9E4FF',radius:17
    })
    na.appendChild(txt(nextAction,14,'Semi Bold',C.text,1048))
    na.appendChild(txt(nextType,9,'Regular',C.muted))
    wrap.appendChild(na)

    s.content.appendChild(wrap)
    return {...s,finding,back}
  }

  // -------------------------------------------------------------------------
  // A. Target Pending Confirmation — same viewport + Frozen amber notice
  // -------------------------------------------------------------------------
  const targetConfirm=screen(
    'Supporting · Target Pending Confirmation',
    'Confirm the target',
    'ResearchOps found more than one plausible match for the entry you provided.',
    'TARGET CONFIRMATION',
    1020
  )
  place(supportSection,targetConfirm.frame,60,100)

  const tc=box('Target confirmation card',{
    width:900,gap:0,padding:22,
    fill:C.surface,fillOpacity:0.94,stroke:false,radius:24,shadow:'soft'
  })

  const warn=box('Uncertainty reason',{
    width:856,gap:5,padding:13,
    fill:'#FFFAF0',stroke:false,radius:12
  })
  const warnBar=figma.createRectangle()
  warnBar.name='Amber left rule'
  warnBar.resize(3,54)
  warnBar.fills=[solid('#D98B22')]
  warnBar.strokes=[]
  warn.appendChild(warnBar)
  warnBar.layoutPositioning='ABSOLUTE'
  warnBar.x=0
  warnBar.y=0
  warn.appendChild(txt(
    'The title alone is not specific enough to identify one target with confidence. Choose the intended match, add a more specific entry, or defer confirmation.',
    11,'Regular','#6B5A3A',824
  ))
  tc.appendChild(warn)
  tc.appendChild(fixedSpacer(14,856))

  function candidate(label,name,source,active=false){
    const c=box(`Candidate / ${label}`,{
      width:856,gap:4,padding:12,
      fill:active?C.accentSoft:C.surface,
      stroke:active?'#9EB7EF':C.border,
      radius:14
    })
    c.appendChild(txt(label.toUpperCase(),9,'Semi Bold',C.subtle))
    c.appendChild(txt(name,12,'Semi Bold',C.text,826))
    c.appendChild(txt(source,10,'Regular',C.muted,826))
    return c
  }
  tc.appendChild(candidate('Candidate A · Paper','Provided paper title','Primary match from the submitted title.',true))
  tc.appendChild(fixedSpacer(9,856))
  tc.appendChild(candidate('Candidate B · Related project','Related project / repository match','A related material with a similar title or project identity.'))
  tc.appendChild(fixedSpacer(16,856))

  const tcActions=box('Actions',{
    width:856,direction:'HORIZONTAL',gap:8,
    fill:C.surface,stroke:false,radius:0
  })
  const tcSupp=button('Supplement entry','secondary')
  const tcSkip=button('Continue without confirming','secondary')
  const tcConfirmBtn=button('Confirm selected target →','primary')
  tcActions.appendChild(tcSupp)
  tcActions.appendChild(tcSkip)
  tcActions.appendChild(spacerGrow())
  tcActions.appendChild(tcConfirmBtn)
  tc.appendChild(tcActions)
  targetConfirm.content.appendChild(tc)

  // -------------------------------------------------------------------------
  // B. Skip Target Confirmation — Target Confirmation underlay + modal
  // -------------------------------------------------------------------------
  const skipFrame=targetConfirm.frame.clone()
  skipFrame.name='Supporting · Skip Target Confirmation Modal'
  skipFrame.resize(1440,1020)
  skipFrame.clipsContent=true
  place(supportSection,skipFrame,1540,100)

  const skipBackdrop=overlayBackdrop('Skip confirmation backdrop',0.28)
  skipFrame.appendChild(skipBackdrop)
  skipBackdrop.layoutPositioning='ABSOLUTE'
  skipBackdrop.x=0
  skipBackdrop.y=0

  const sm=box('Skip confirmation modal',{
    width:460,gap:0,padding:20,
    fill:C.surface,stroke:C.border,radius:16,shadow:'card'
  })
  sm.appendChild(txt('TARGET CONFIRMATION',9,'Semi Bold',C.subtle))
  sm.appendChild(fixedSpacer(6,420))
  sm.appendChild(txt('Continue without confirming?',19,'Semi Bold',C.textStrong,420))
  sm.appendChild(fixedSpacer(8,420))
  sm.appendChild(txt(
    'ResearchOps will continue using the currently available target mapping without confirming which candidate is the intended target.',
    11,'Regular',C.muted,420
  ))
  sm.appendChild(fixedSpacer(12,420))
  const smw=box('Warning',{
    width:420,gap:4,padding:10,
    fill:C.surface2,stroke:C.border,radius:10
  })
  smw.appendChild(txt(
    'This may produce a partially constrained assessment because some findings or evidence could be associated with the wrong target material.',
    10,'Regular',C.muted,396
  ))
  sm.appendChild(smw)
  sm.appendChild(fixedSpacer(14,420))
  const sma=box('Actions',{
    width:420,direction:'HORIZONTAL',gap:8,
    fill:C.surface,stroke:false,radius:0
  })
  const smBack=button('Go back','secondary')
  const smGo=button('Confirm and continue →','primary')
  sma.appendChild(smBack)
  sma.appendChild(spacerGrow())
  sma.appendChild(smGo)
  sm.appendChild(sma)
  skipFrame.appendChild(sm)
  sm.layoutPositioning='ABSOLUTE'
  sm.x=490
  sm.y=280
  const skip={frame:skipFrame}

  // -------------------------------------------------------------------------
  // C. Authorization Denied — one 760px card, no external Hero
  // -------------------------------------------------------------------------
  const denied=bareScreen('Supporting · Authorization Denied',1020)
  place(supportSection,denied.frame,3020,100)

  const deniedCard=box('Authorization Denied card',{
    width:760,gap:0,padding:22,
    fill:C.surface,stroke:C.border,radius:22,shadow:'soft'
  })
  const deniedHead=box('Header',{
    width:716,direction:'HORIZONTAL',gap:14,
    fill:C.surface,stroke:false,radius:0
  })
  deniedHead.counterAxisAlignItems='MIN'
  const dhc=box('Header copy',{gap:0,fill:C.surface,stroke:false,radius:0})
  dhc.layoutGrow=1
  dhc.appendChild(txt('ENVIRONMENT ACCESS',9,'Semi Bold',C.subtle))
  dhc.appendChild(fixedSpacer(5,1))
  dhc.appendChild(txt('Read-only access not authorized',26,'Semi Bold',C.textStrong,540))
  deniedHead.appendChild(dhc)
  deniedHead.appendChild(acquisitionChip('Authorization Denied'))
  deniedCard.appendChild(deniedHead)
  deniedCard.appendChild(fixedSpacer(10,716))
  deniedCard.appendChild(txt(
    'ResearchOps did not read any environment information. You can provide the same context through another supported input path.',
    11,'Regular',C.mutedStrong,650
  ))
  deniedCard.appendChild(fixedSpacer(15,716))
  const boundary=box('Boundary',{
    width:716,gap:5,padding:11,
    fill:C.surface2,stroke:false,radius:11
  })
  boundary.appendChild(txt(
    'Authorization Denied is not Environment Blocked and does not directly assign RD-02 a Blocked status.',
    10,'Regular',C.muted,692
  ))
  deniedCard.appendChild(boundary)
  deniedCard.appendChild(fixedSpacer(17,716))
  const deniedActions=box('Actions',{
    width:716,direction:'HORIZONTAL',gap:8,
    fill:C.surface,stroke:false,radius:0
  })
  const deniedReview=button('← Review access again','secondary')
  const deniedSnapshot=button('Use snapshot instead','secondary')
  const deniedManual=button('Manual input','secondary')
  const deniedNoEnv=button('Continue without environment data →','primary')
  deniedActions.appendChild(deniedReview)
  deniedActions.appendChild(deniedSnapshot)
  deniedActions.appendChild(deniedManual)
  deniedActions.appendChild(spacerGrow())
  deniedActions.appendChild(deniedNoEnv)
  deniedCard.appendChild(deniedActions)
  denied.content.appendChild(deniedCard)
  denied.actionNodes=[deniedReview,deniedSnapshot,deniedManual,deniedNoEnv]

  // -------------------------------------------------------------------------
  // D. Resource / Evaluation Signal Drawers — Overview underlay + fixed drawer
  // -------------------------------------------------------------------------
  const resourceView=signalDrawerOverlay(
    overview.frame,
    'Supporting · Resource Constraint Drawer',
    'Resource Constraint',
    'Unknown',
    'resource'
  )
  place(supportSection,resourceView.frame,4500,100)

  const evaluationView=signalDrawerOverlay(
    overview.frame,
    'Supporting · Evaluation Conflict Drawer',
    'Evaluation Conflict',
    'Warning',
    'evaluation'
  )
  place(supportSection,evaluationView.frame,5980,100)

  const rvEvidence=resourceView.evidence
  const evEvidence=evaluationView.evidence

  // -------------------------------------------------------------------------
  // E. Resource / Conflict Evidence — preserve signal drawer context below
  // -------------------------------------------------------------------------
  const resourceEvidence=evidenceDrawerOverlay(
    resourceView.frame,
    'Supporting · Resource Evidence',
    {
      title:'Resource constraint evidence',
      verification:'Located Only',
      summary:'Current resource facts are available, while explicit minimum project requirements are not sufficiently established for a reliable shortfall comparison.',
      source:'Current resource facts + project requirement sources',
      location:'User Context / repository setup and requirement references',
      materialType:'User Context / Repository',
      sourceUrl:''
    }
  )
  place(supportSection,resourceEvidence.frame,7460,100)

  const conflictEvidence=evidenceDrawerOverlay(
    evaluationView.frame,
    'Supporting · Conflict Evidence',
    {
      title:'Conflicting setup evidence',
      verification:'Located Only',
      summary:'Two located sources support different interpretations of the same setup condition. The conflict is preserved for review rather than silently resolved.',
      source:'Multiple conflicting sources',
      location:'Published setup description / repository setup documentation',
      materialType:'Paper / Repository',
      conflict:'The sources disagree. ResearchOps has not selected either source as authoritative.',
      compare:[
        {
          title:'Paper setup description',
          copy:'The published setup describes one environment or evaluation configuration.'
        },
        {
          title:'Repository setup description',
          copy:'The repository material indicates a different environment or evaluation configuration.'
        }
      ],
      sourceUrl:''
    }
  )
  place(supportSection,conflictEvidence.frame,8940,100)

  // -------------------------------------------------------------------------
  // F. Evidence Feedback — Evidence Drawer remains visible underneath
  // -------------------------------------------------------------------------
  const evidenceFeedback=feedbackOverlay(
    evidence.frame,
    'Supporting · Shared Feedback · Evidence',
    'Dataset access evidence',
    'evidence'
  )
  place(supportSection,evidenceFeedback.frame,10420,100)

  // -------------------------------------------------------------------------
  // G. Additional Dimension Detail states — reuse corrected Frozen template
  // -------------------------------------------------------------------------
  const blockedDetail=buildFrozenDimensionState(
    'Supporting · RD-01 Blocked',
    'RD-01',
    'Data & Access Readiness',
    'Blocked',
    'Explicit negative evidence shows the required dataset access is unavailable for the current reproduction path.',
    'This blocking condition triggers the current PAUSE decision.',
    {
      condition:'Condition · Required dataset access',
      title:'Required dataset access is explicitly unavailable',
      summary:'The current reproduction path has a confirmed negative access result for a required dataset condition.',
      type:'Fact',
      critical:true,
      impact:'Gate impact · Triggers PAUSE'
    },
    'Resolve or replace the blocked access path',
    'Resolve Blocker'
  )
  place(supportSection,blockedDetail.frame,60,1180)

  const warningDetail=buildFrozenDimensionState(
    'Supporting · RD-02 Warning',
    'RD-02',
    'Environment & Dependency Readiness',
    'Warning',
    'The environment is usable for assessment, but one compatibility risk still needs validation.',
    'Adds a non-blocking risk to the current CONDITIONAL PROCEED decision.',
    {
      condition:'Condition · Environment compatibility',
      title:'A version compatibility risk still needs validation',
      summary:'The available environment facts differ from the project’s documented setup in a way that may matter, but current evidence does not establish a hard incompatibility.',
      type:'Inference',
      critical:false,
      impact:'Gate impact · Non-blocking Warning'
    },
    'Validate the environment against the documented dependency setup',
    'Mitigate Warning'
  )
  place(supportSection,warningDetail.frame,1540,1180)

  const readyDetail=buildFrozenDimensionState(
    'Supporting · RD-03 Ready',
    'RD-03',
    'Weights & Configuration Readiness',
    'Ready',
    'Required checkpoint and configuration relationships are sufficiently identified for the current assessment.',
    'No current blocker from weights or configuration.',
    {
      condition:'Condition · Checkpoint and configuration mapping',
      title:'Checkpoint and configuration relationships are sufficiently identified',
      summary:'The available project materials provide a usable mapping between the required checkpoint and the configuration needed for the current reproduction path.',
      type:'Fact',
      critical:false,
      impact:'Gate impact · No current blocker'
    },
    'Run a minimum configuration validation before higher-cost reproduction work',
    'Minimum Validation'
  )
  place(supportSection,readyDetail.frame,3020,1180)

  // -------------------------------------------------------------------------
  // 03 — State variants / Reference-only
  // -------------------------------------------------------------------------
  const stateSection = area(variantsPage, 0, 0)

  function referenceVariantScreen(name, width) {
    const s = bareScreen(name,1020)
    const card = box('Variant card',{
      width,gap:0,padding:22,
      fill:C.surface,stroke:C.border,radius:22,shadow:'soft'
    })
    s.content.appendChild(card)
    return { ...s, card }
  }

  function variantHeader(card, innerWidth, kicker, title, tag) {
    const head=box('Variant header',{
      width:innerWidth,direction:'HORIZONTAL',gap:14,
      fill:C.surface,stroke:false,radius:0
    })
    head.counterAxisAlignItems='MIN'

    const copy=box('Variant title copy',{
      gap:0,fill:C.surface,stroke:false,radius:0
    })
    copy.layoutGrow=1
    copy.appendChild(txt(kicker.toUpperCase(),9,'Semi Bold',C.subtle))
    copy.appendChild(fixedSpacer(5,1))
    copy.appendChild(txt(title,24,'Semi Bold',C.textStrong,innerWidth-170))
    head.appendChild(copy)
    head.appendChild(acquisitionChip(tag))
    card.appendChild(head)
    return head
  }

  function variantActions(card, innerWidth, labels) {
    card.appendChild(fixedSpacer(17,innerWidth))
    const row=box('Variant actions',{
      width:innerWidth,direction:'HORIZONTAL',gap:9,
      fill:C.surface,stroke:false,radius:0
    })
    const nodes=[]
    labels.forEach((label,i)=>{
      const b=button(label,i===labels.length-1?'primary':'ghost')
      if(i===labels.length-1 && labels.length>1) row.appendChild(spacerGrow())
      row.appendChild(b)
      nodes.push(b)
    })
    card.appendChild(row)
    return nodes
  }

  function stateList(innerWidth, rows) {
    const list=box('State details',{
      width:innerWidth,gap:0,
      fill:C.surface,stroke:C.border,radius:12
    })
    list.clipsContent=true

    rows.forEach((r,idx)=>{
      const row=box(`State row / ${r[0]}`,{
        width:innerWidth-2,direction:'HORIZONTAL',gap:10,padding:12,
        fill:C.surface,stroke:false,radius:0
      })
      const left=box('Row copy',{gap:3,fill:C.surface,stroke:false,radius:0})
      left.layoutGrow=1
      left.appendChild(txt(r[0],11,'Semi Bold',C.textStrong,innerWidth-180))
      if(r[1]) left.appendChild(txt(r[1],9,'Regular',C.subtle,innerWidth-180))
      row.appendChild(left)
      if(r[2]){
        row.appendChild(txt(
          r[2],9,'Semi Bold',
          r[2]==='Available'?C.ready:C.mutedStrong
        ))
      }
      list.appendChild(row)
      if(idx<rows.length-1) list.appendChild(divider(innerWidth-2))
    })
    return list
  }

  // -------------------------------------------------------------------------
  // A. Partial Result — one 760px card, no external Hero
  // -------------------------------------------------------------------------
  const partial=referenceVariantScreen('Variant · Partial Result',760)
  place(stateSection,partial.frame,60,100)
  variantHeader(partial.card,716,'Acquisition state','Partial result available','Partial Result')
  partial.card.appendChild(fixedSpacer(10,716))
  partial.card.appendChild(txt(
    'Some assessment inputs are available, while one acquisition step is still incomplete. ResearchOps has not converted the incomplete acquisition into a readiness Warning, Unknown, or Blocked status.',
    11,'Regular',C.mutedStrong,716
  ))
  partial.card.appendChild(fixedSpacer(13,716))
  const partialBoundary=box('Acquisition boundary',{
    width:716,gap:5,padding:11,
    fill:C.surface2,stroke:false,radius:10
  })
  partialBoundary.appendChild(txt(
    'This is a processing / acquisition state, not a business readiness status.',
    10,'Regular',C.muted,692
  ))
  partial.card.appendChild(partialBoundary)
  partial.card.appendChild(fixedSpacer(13,716))
  partial.card.appendChild(stateList(716,[
    ['Target materials','Primary target and linked materials currently available to the assessment.','Available'],
    ['Environment context','Environment facts available from the selected input path.','Available'],
    ['Additional material review','One linked material review has not finished yet.','Still processing']
  ]))
  partial.actionNodes=variantActions(
    partial.card,716,
    ['← Back to Task Setup','Continue processing →']
  )

  // -------------------------------------------------------------------------
  // B. Acquisition Failure — one 760px card, no external Hero
  // -------------------------------------------------------------------------
  const failure=referenceVariantScreen('Variant · Acquisition Failure',760)
  place(stateSection,failure.frame,1540,100)
  variantHeader(failure.card,716,'Acquisition state','Environment acquisition failed','Acquisition Failure')
  failure.card.appendChild(fixedSpacer(10,716))
  failure.card.appendChild(txt(
    'ResearchOps could not complete the selected environment acquisition step. No readiness status has been assigned from this technical failure.',
    11,'Regular',C.mutedStrong,716
  ))
  failure.card.appendChild(fixedSpacer(13,716))
  const failureBoundary=box('Acquisition boundary',{
    width:716,gap:5,padding:11,
    fill:C.surface2,stroke:false,radius:10
  })
  failureBoundary.appendChild(txt(
    'Acquisition Failure is not Environment Blocked and does not by itself produce Warning, Blocked, or PAUSE.',
    10,'Regular',C.muted,692
  ))
  failure.card.appendChild(failureBoundary)
  failure.card.appendChild(fixedSpacer(13,716))

  const failureDetail=box('Failure detail',{
    width:716,gap:0,
    fill:C.surface,stroke:C.border,radius:12
  })
  failureDetail.clipsContent=true

  const failed=box('What failed',{
    width:714,gap:3,padding:12,
    fill:C.surface,stroke:false,radius:0
  })
  failed.appendChild(txt('WHAT FAILED',9,'Semi Bold',C.subtle))
  failed.appendChild(txt('Read-only environment acquisition',11,'Semi Bold',C.textStrong,690))
  failed.appendChild(txt(
    'The requested environment facts could not be retrieved.',
    9,'Regular',C.muted,690
  ))
  failureDetail.appendChild(failed)
  failureDetail.appendChild(divider(714))

  const recovery=box('Recovery',{
    width:714,gap:3,padding:12,
    fill:C.surface,stroke:false,radius:0
  })
  recovery.appendChild(txt('RECOVERY',9,'Semi Bold',C.subtle))
  recovery.appendChild(txt(
    'Retry the same path or use another supported input mode.',
    11,'Semi Bold',C.textStrong,690
  ))
  failureDetail.appendChild(recovery)
  failure.card.appendChild(failureDetail)
  failure.actionNodes=variantActions(
    failure.card,716,
    ['Use snapshot instead','Manual input','Retry →']
  )

  // -------------------------------------------------------------------------
  // C. Conflict — one 820px card + preserved two-source rule
  // -------------------------------------------------------------------------
  const conflict=referenceVariantScreen('Variant · Conflict',820)
  place(stateSection,conflict.frame,3020,100)
  variantHeader(conflict.card,776,'Acquisition state','Conflicting evidence found','Conflict')
  conflict.card.appendChild(fixedSpacer(10,776))
  conflict.card.appendChild(txt(
    'ResearchOps found two available sources that support different interpretations of the same setup condition.',
    11,'Regular',C.mutedStrong,776
  ))
  conflict.card.appendChild(fixedSpacer(13,776))
  const conflictBoundary=box('Conflict boundary',{
    width:776,gap:5,padding:11,
    fill:C.surface2,stroke:false,radius:10
  })
  conflictBoundary.appendChild(txt(
    'Conflict is an acquisition / analysis state. It is not itself a Readiness Warning, Unknown, Blocked, or PAUSE decision.',
    10,'Regular',C.muted,752
  ))
  conflict.card.appendChild(conflictBoundary)
  conflict.card.appendChild(fixedSpacer(13,776))

  const sources=box('Conflicting sources',{
    width:776,direction:'HORIZONTAL',gap:10,
    fill:C.surface,stroke:false,radius:0
  })
  const sourceA=box('Source A',{
    width:383,gap:5,padding:12,
    fill:C.surface2,stroke:C.border,radius:12
  })
  sourceA.appendChild(txt('SOURCE A',9,'Semi Bold',C.subtle))
  sourceA.appendChild(txt('Paper setup description',11,'Semi Bold',C.textStrong,359))
  sourceA.appendChild(txt(
    'The published setup describes one environment or evaluation configuration.',
    10,'Regular',C.muted,359
  ))
  sourceA.appendChild(txt('Material · Paper',9,'Regular',C.subtle))
  sources.appendChild(sourceA)

  const sourceB=box('Source B',{
    width:383,gap:5,padding:12,
    fill:C.surface2,stroke:C.border,radius:12
  })
  sourceB.appendChild(txt('SOURCE B',9,'Semi Bold',C.subtle))
  sourceB.appendChild(txt('Repository setup description',11,'Semi Bold',C.textStrong,359))
  sourceB.appendChild(txt(
    'The repository material indicates a different environment or evaluation configuration.',
    10,'Regular',C.muted,359
  ))
  sourceB.appendChild(txt('Material · Repository',9,'Regular',C.subtle))
  sources.appendChild(sourceB)
  conflict.card.appendChild(sources)

  conflict.card.appendChild(fixedSpacer(12,776))
  const conflictRule=box('Conflict rule',{
    width:776,gap:5,padding:11,
    fill:C.surface2,stroke:C.border,radius:10
  })
  conflictRule.appendChild(txt(
    'Both sources remain visible. ResearchOps does not silently choose one source or collapse the disagreement into a single conclusion.',
    10,'Regular',C.mutedStrong,752
  ))
  conflict.card.appendChild(conflictRule)
  conflict.actionNodes=variantActions(
    conflict.card,776,
    ['← Back to Task Setup','Review available evidence →']
  )

  // -------------------------------------------------------------------------
  // D. Gate Not Available Yet — one 800px card; not a fourth Gate
  // -------------------------------------------------------------------------
  const gateNA=referenceVariantScreen('Variant · Gate Not Available Yet',800)
  place(stateSection,gateNA.frame,4500,100)

  const gateHead=box('Gate availability header',{
    width:756,direction:'HORIZONTAL',gap:14,
    fill:C.surface,stroke:false,radius:0
  })
  gateHead.counterAxisAlignItems='MIN'
  const gateHeadCopy=box('Gate availability title',{
    gap:0,fill:C.surface,stroke:false,radius:0
  })
  gateHeadCopy.layoutGrow=1
  gateHeadCopy.appendChild(txt('OVERALL GATE',9,'Semi Bold',C.subtle))
  gateHeadCopy.appendChild(fixedSpacer(5,1))
  gateHeadCopy.appendChild(txt('Not Available Yet',24,'Semi Bold',C.textStrong,570))
  gateHead.appendChild(gateHeadCopy)
  gateHead.appendChild(acquisitionChip('Gate unavailable'))
  gateNA.card.appendChild(gateHead)

  gateNA.card.appendChild(fixedSpacer(10,756))
  gateNA.card.appendChild(txt(
    'ResearchOps does not yet have enough completed readiness findings to reliably aggregate an Overall Gate.',
    11,'Regular',C.mutedStrong,756
  ))
  gateNA.card.appendChild(fixedSpacer(13,756))
  const gateBoundary=box('Gate availability boundary',{
    width:756,gap:5,padding:11,
    fill:C.surface2,stroke:false,radius:10
  })
  gateBoundary.appendChild(txt(
    '“Not Available Yet” is not a fourth Gate value and must not be interpreted as Gate = Unknown.',
    10,'Regular',C.muted,732
  ))
  gateNA.card.appendChild(gateBoundary)
  gateNA.card.appendChild(fixedSpacer(13,756))
  gateNA.card.appendChild(stateList(756,[
    ['RD-01 · Data & Access Readiness','A usable dimension result is already available.','Available'],
    ['RD-02 · Environment & Dependency Readiness','Required acquisition / analysis is not complete yet.','Still processing'],
    ['RD-03 · Weights & Configuration Readiness','A usable dimension result is already available.','Available']
  ]))
  gateNA.actionNodes=variantActions(
    gateNA.card,756,
    ['← Back to Task Setup','Continue processing →']
  )

  // -------------------------------------------------------------------------
  // E. Blocked / PAUSE — 900px Frozen Overview layout
  // -------------------------------------------------------------------------
  const pause=bareScreen('Variant · Blocked / PAUSE',1020)
  place(stateSection,pause.frame,60,1160)

  const pauseWrap=box('PAUSE overview wrap',{
    width:900,gap:0,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  const pauseHead=box('PAUSE overview head',{
    width:900,direction:'HORIZONTAL',gap:18,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  pauseHead.counterAxisAlignItems='MIN'
  pauseHead.appendChild(txt('Readiness Overview',31,'Semi Bold',C.textStrong,650))
  pauseHead.appendChild(spacerGrow())
  const pauseBack=button('← Back to Task Setup','ghost')
  pauseHead.appendChild(pauseBack)
  pauseWrap.appendChild(pauseHead)
  pauseWrap.appendChild(fixedSpacer(18,900))

  pauseWrap.appendChild(gateCard(
    'PAUSE',
    'A required data-access condition is explicitly unavailable under the current reproduction path.',
    900
  ))
  pauseWrap.appendChild(fixedSpacer(16,900))

  const pd=box('Dimensions',{
    width:900,direction:'HORIZONTAL',gap:12,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  const pd1=dimensionCard(
    'RD-01','Data & Access Readiness','Blocked',
    'Explicit negative evidence shows the required dataset access is unavailable for the current reproduction path.',
    'Triggers PAUSE',292
  )
  const pd2=dimensionCard(
    'RD-02','Environment & Dependency Readiness','Warning',
    'A compatibility risk is known, but current evidence does not establish a hard environment blocker.',
    'Non-blocking risk',292
  )
  const pd3=dimensionCard(
    'RD-03','Weights & Configuration Readiness','Ready',
    'Required checkpoint and configuration relationships are sufficiently identified for the current assessment.',
    'No current blocker',292
  )
  pd.appendChild(pd1.frame);pd.appendChild(pd2.frame);pd.appendChild(pd3.frame)
  pauseWrap.appendChild(pd)

  pauseWrap.appendChild(fixedSpacer(16,900))
  const pl=box('PAUSE lower',{
    width:900,direction:'HORIZONTAL',gap:12,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  const blocker=box('Key Blocker',{
    width:444,gap:6,padding:17,
    fill:C.surface,stroke:'#EFC2C2',radius:18
  })
  blocker.appendChild(txt('KEY BLOCKER',9,'Semi Bold',C.subtle))
  blocker.appendChild(txt('Required dataset access is not available',14,'Semi Bold',C.textStrong,410))
  blocker.appendChild(txt(
    'Blocking evidence · The required access condition has an explicit negative result for the current reproduction path.',
    10,'Regular',C.blocked,410
  ))
  pl.appendChild(blocker)

  const pa=box('First Next Action',{
    width:444,gap:6,padding:17,
    fill:C.nextActionSoft,stroke:'#D9E4FF',radius:18
  })
  pa.appendChild(txt('FIRST NEXT ACTION',9,'Semi Bold',C.accent))
  pa.appendChild(txt('Resolve or replace the blocked access path',14,'Semi Bold',C.textStrong,410))
  pa.appendChild(txt('Action type · Resolve Blocker',9,'Regular',C.subtle))
  pl.appendChild(pa)
  pauseWrap.appendChild(pl)
  pause.content.appendChild(pauseWrap)

  // -------------------------------------------------------------------------
  // F. Ready / PROCEED — 900px Frozen Overview layout
  // -------------------------------------------------------------------------
  const proceed=bareScreen('Variant · Ready / PROCEED',1020)
  place(stateSection,proceed.frame,1540,1160)

  const proceedWrap=box('PROCEED overview wrap',{
    width:900,gap:0,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  const proceedHead=box('PROCEED overview head',{
    width:900,direction:'HORIZONTAL',gap:18,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  proceedHead.counterAxisAlignItems='MIN'
  proceedHead.appendChild(txt('Readiness Overview',31,'Semi Bold',C.textStrong,650))
  proceedHead.appendChild(spacerGrow())
  const proceedBack=button('← Back to Task Setup','ghost')
  proceedHead.appendChild(proceedBack)
  proceedWrap.appendChild(proceedHead)
  proceedWrap.appendChild(fixedSpacer(18,900))

  proceedWrap.appendChild(gateCard(
    'PROCEED',
    'All three core readiness dimensions are supported by sufficient positive evidence, with no material resource or priority evaluation conflict affecting the current path.',
    900
  ))
  proceedWrap.appendChild(fixedSpacer(16,900))

  const prd=box('Dimensions',{
    width:900,direction:'HORIZONTAL',gap:12,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  const pr1=dimensionCard(
    'RD-01','Data & Access Readiness','Ready',
    'Required data and access conditions are sufficiently supported for the current validation path.',
    'No current blocker',292
  )
  const pr2=dimensionCard(
    'RD-02','Environment & Dependency Readiness','Ready',
    'Available environment facts are sufficiently aligned with documented dependency requirements for the current validation path.',
    'No current blocker',292
  )
  const pr3=dimensionCard(
    'RD-03','Weights & Configuration Readiness','Ready',
    'Required checkpoint and configuration relationships are sufficiently identified for the intended validation path.',
    'No current blocker',292
  )
  prd.appendChild(pr1.frame);prd.appendChild(pr2.frame);prd.appendChild(pr3.frame)
  proceedWrap.appendChild(prd)

  proceedWrap.appendChild(fixedSpacer(16,900))
  const prl=box('PROCEED lower',{
    width:900,direction:'HORIZONTAL',gap:12,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  const prs=box('Readiness Summary',{
    width:444,gap:6,padding:17,
    fill:C.surface,stroke:C.border,radius:18
  })
  prs.appendChild(txt('READINESS SUMMARY',9,'Semi Bold',C.subtle))
  prs.appendChild(txt(
    'No current gate-critical blocker or unresolved core readiness gap',
    14,'Semi Bold',C.textStrong,410
  ))
  prs.appendChild(txt(
    'Positive evidence remains inspectable even when the current status is Ready.',
    10,'Regular',C.mutedStrong,410
  ))
  prl.appendChild(prs)

  const pra=box('First Next Action',{
    width:444,gap:6,padding:17,
    fill:C.nextActionSoft,stroke:'#D9E4FF',radius:18
  })
  pra.appendChild(txt('FIRST NEXT ACTION',9,'Semi Bold',C.accent))
  pra.appendChild(txt(
    'Run the minimum validation before higher-cost reproduction work',
    14,'Semi Bold',C.textStrong,410
  ))
  pra.appendChild(txt('Action type · Minimum Validation',9,'Regular',C.subtle))
  prl.appendChild(pra)
  proceedWrap.appendChild(prl)
  proceed.content.appendChild(proceedWrap)

  // -------------------------------------------------------------------------
  // 04 — Component Library
  // -------------------------------------------------------------------------
  ;[
    partial,
    failure,
    conflict,
    gateNA
  ].forEach(v => {
    v.actionNodes.forEach(n => {
      n.name = `Reference Action · ${n.name.replace('Button / ', '')}`
      n.setPluginData('prototype-behavior', 'reference-only-no-cross-page-navigation')
    })
  })

  ;[
    pd1.details, pd2.details, pd3.details,
    pr1.details, pr2.details, pr3.details
  ].forEach(n => {
    n.name = `Reference Action · ${n.name}`
    n.setPluginData('prototype-behavior', 'reference-only-no-cross-page-navigation')
  })

  const compSection = componentsPage

  // -------------------------------------------------------------------------
  // 02_Components — clean Auto Layout library
  // -------------------------------------------------------------------------
  function libraryGroup(title, width, children) {
    const g=box(`Library Group / ${title}`,{
      width,gap:16,padding:20,
      fill:C.surface2,stroke:C.border,radius:20
    })
    g.appendChild(txt(title,17,'Semi Bold',C.textStrong,width-40))
    children.forEach(node=>g.appendChild(node))
    return g
  }

  function exactPillComponent(name, propName, propValue, label, bg, fg) {
    const c=figma.createComponent()
    c.name=`${propName}=${propValue}`
    setAuto(c,'HORIZONTAL',4,8)
    c.paddingTop=5
    c.paddingBottom=5
    c.cornerRadius=999
    c.fills=[solid(bg)]
    c.strokes=[solid(bg)]
    c.appendChild(txt(label,9,'Semi Bold',fg))
    return c
  }

  function libraryTextActionComponent(label='View details →', muted=false) {
    const c=figma.createComponent()
    c.name=`Tone=${muted?'Muted':'Default'}`
    setAuto(c,'HORIZONTAL',0,0)
    c.fills=[]
    c.strokes=[]
    c.appendChild(txt(label,10,'Semi Bold',muted?C.mutedStrong:C.accent))
    return c
  }

  function exactDimensionComponent(status, copy, impact) {
    const c=figma.createComponent()
    c.name=`Status=${status}`
    setAuto(c,'VERTICAL',12,16)
    c.resize(430,c.height)
    c.counterAxisSizingMode='FIXED'
    c.cornerRadius=17
    c.fills=[solid(C.surface)]
    c.strokes=[solid(C.border)]
    c.effects=[softShadow]

    const top=box('Header',{
      width:398,direction:'HORIZONTAL',gap:10,
      fill:C.surface,stroke:false,radius:0
    })
    const title=box('Title',{gap:4,fill:C.surface,stroke:false,radius:0})
    title.layoutGrow=1
    title.appendChild(txt('RD-XX',9,'Semi Bold',C.subtle))
    title.appendChild(txt('Dimension Name',13,'Semi Bold',C.textStrong,285))
    top.appendChild(title)

    const [bg,fg]=statusStyle(status)
    const st=box(`Status / ${status}`,{
      direction:'HORIZONTAL',gap:4,padding:8,
      fill:bg,stroke:bg,radius:999
    })
    st.paddingTop=5
    st.paddingBottom=5
    st.appendChild(txt(status,9,'Semi Bold',fg))
    top.appendChild(st)
    c.appendChild(top)

    c.appendChild(txt(copy,11,'Regular',C.muted,398))
    c.appendChild(txt(`Gate impact · ${impact}`,9,'Regular',C.subtle,398))
    c.appendChild(txt('View details →',10,'Semi Bold',C.accent))
    return c
  }

  function exactSignalComponent(name,state) {
    const c=figma.createComponent()
    c.name=`Type=${name}`
    setAuto(c,'VERTICAL',9,14)
    c.resize(520,c.height)
    c.counterAxisSizingMode='FIXED'
    c.cornerRadius=14
    c.fills=[solid(C.surface,0.74)]
    c.strokes=[solid(C.border)]

    const top=box('Header',{
      width:492,direction:'HORIZONTAL',gap:10,
      fill:C.surface,fillOpacity:0,stroke:false,radius:0
    })
    top.appendChild(txt(name,11,'Semi Bold','#344054'))
    top.appendChild(spacerGrow())

    const [bg,fg]=statusStyle(state)
    const st=box(`Signal status / ${state}`,{
      direction:'HORIZONTAL',gap:4,padding:7,
      fill:bg,stroke:bg,radius:999
    })
    st.paddingTop=5
    st.paddingBottom=5
    st.appendChild(txt(state,9,'Semi Bold',fg))
    top.appendChild(st)
    c.appendChild(top)

    c.appendChild(txt('Supporting context summary.',10,'Regular',C.muted,492))
    c.appendChild(txt('View details →',10,'Semi Bold',C.accent))
    return c
  }

  function exactGateComponent(gate) {
    const c=figma.createComponent()
    c.name=`Gate=${gate}`
    setAuto(c,'VERTICAL',0,20)
    c.resize(620,c.height)
    c.counterAxisSizingMode='FIXED'
    c.cornerRadius=20
    c.fills=[solid(C.surface)]
    c.strokes=[solid(
      gate==='PROCEED' ? '#CFE8D6' :
      gate==='PAUSE' ? '#F1CACA' : C.border
    )]
    c.effects=[softShadow]
    c.appendChild(txt('OVERALL GATE',10,'Semi Bold',C.mutedStrong))
    c.appendChild(fixedSpacer(6,580))
    const valueColor=
      gate==='PROCEED' ? C.ready :
      gate==='PAUSE' ? C.blocked : C.textStrong
    c.appendChild(txt(gate,gate==='CONDITIONAL PROCEED'?24:26,'Semi Bold',valueColor,580))
    c.appendChild(fixedSpacer(14,580))
    c.appendChild(divider(580))
    c.appendChild(fixedSpacer(14,580))
    c.appendChild(txt('REASON',10,'Semi Bold',C.mutedStrong))
    c.appendChild(fixedSpacer(4,580))
    c.appendChild(txt('Gate reason appears here.',13,'Regular','#344054',580))
    return c
  }

  // ---- Component sets ------------------------------------------------------

  const statusComponents=[]
  ;['Ready','Warning','Blocked','Unknown'].forEach(s=>{
    const [bg,fg]=statusStyle(s)
    const c=exactPillComponent('Status Chip','Status',s,s,bg,fg)
    compSection.appendChild(c)
    statusComponents.push(c)
  })
  const statusSet=figma.combineAsVariants(statusComponents,compSection)
  statusSet.name='Status Chip'
  statusSet.layoutMode='HORIZONTAL'
  statusSet.primaryAxisSizingMode='AUTO'
  statusSet.counterAxisSizingMode='AUTO'
  statusSet.itemSpacing=10
  statusSet.paddingTop=18;statusSet.paddingRight=18;statusSet.paddingBottom=18;statusSet.paddingLeft=18

  const verificationComponents=[]
  ;[
    ['Located Only',C.unknownSoft,C.unknown],
    ['Corroborated',C.readySoft,C.ready],
    ['Unverifiable',C.blockedSoft,C.blocked]
  ].forEach(([s,bg,fg])=>{
    const c=exactPillComponent('Verification Status','Verification',s,s,bg,fg)
    compSection.appendChild(c)
    verificationComponents.push(c)
  })
  const verificationSet=figma.combineAsVariants(verificationComponents,compSection)
  verificationSet.name='Verification Status Chip'
  verificationSet.layoutMode='HORIZONTAL'
  verificationSet.primaryAxisSizingMode='AUTO'
  verificationSet.counterAxisSizingMode='AUTO'
  verificationSet.itemSpacing=10
  verificationSet.paddingTop=18;verificationSet.paddingRight=18;verificationSet.paddingBottom=18;verificationSet.paddingLeft=18

  const acquisitionTags=[]
  ;['Partial Result','Acquisition Failure','Conflict'].forEach(s=>{
    const c=exactPillComponent(
      'Acquisition State Tag','Acquisition',s,s,
      s==='Partial Result'?C.unknownSoft:C.acquisitionSoft,
      C.acquisition
    )
    compSection.appendChild(c)
    acquisitionTags.push(c)
  })
  const acquisitionTagSet=figma.combineAsVariants(acquisitionTags,compSection)
  acquisitionTagSet.name='Acquisition State Tag'
  acquisitionTagSet.layoutMode='HORIZONTAL'
  acquisitionTagSet.primaryAxisSizingMode='AUTO'
  acquisitionTagSet.counterAxisSizingMode='AUTO'
  acquisitionTagSet.itemSpacing=10
  acquisitionTagSet.paddingTop=18;acquisitionTagSet.paddingRight=18;acquisitionTagSet.paddingBottom=18;acquisitionTagSet.paddingLeft=18

  const processingComponent=figma.createComponent()
  processingComponent.name='Processing Row'
  setAuto(processingComponent,'HORIZONTAL',10,12)
  processingComponent.resize(520,processingComponent.height)
  processingComponent.counterAxisSizingMode='FIXED'
  processingComponent.cornerRadius=10
  processingComponent.fills=[solid(C.surface2)]
  processingComponent.strokes=[solid(C.border)]
  processingComponent.counterAxisAlignItems='CENTER'
  processingComponent.appendChild(spinnerIcon())
  processingComponent.appendChild(txt('Reading authorized environment facts',12,'Semi Bold','#344054',350))
  processingComponent.appendChild(spacerGrow())
  processingComponent.appendChild(txt('Processing',10,'Semi Bold',C.mutedStrong))
  compSection.appendChild(processingComponent)

  const gateComponents=[]
  ;['PROCEED','CONDITIONAL PROCEED','PAUSE'].forEach(g=>{
    const c=exactGateComponent(g)
    compSection.appendChild(c)
    gateComponents.push(c)
  })
  const gateSet=figma.combineAsVariants(gateComponents,compSection)
  gateSet.name='Overall Gate'
  gateSet.layoutMode='VERTICAL'
  gateSet.primaryAxisSizingMode='AUTO'
  gateSet.counterAxisSizingMode='AUTO'
  gateSet.itemSpacing=10
  gateSet.paddingTop=18;gateSet.paddingRight=18;gateSet.paddingBottom=18;gateSet.paddingLeft=18

  const gateAvailability=figma.createComponent()
  gateAvailability.name='State=Not Available Yet'
  setAuto(gateAvailability,'VERTICAL',8,20)
  gateAvailability.resize(620,gateAvailability.height)
  gateAvailability.counterAxisSizingMode='FIXED'
  gateAvailability.cornerRadius=20
  gateAvailability.fills=[solid(C.surface)]
  gateAvailability.strokes=[solid(C.border)]
  gateAvailability.effects=[softShadow]
  gateAvailability.appendChild(txt('OVERALL GATE',10,'Semi Bold',C.mutedStrong))
  gateAvailability.appendChild(txt('Not Available Yet',20,'Semi Bold',C.textStrong,580))
  gateAvailability.appendChild(txt('Availability state only — not a fourth Gate value.',11,'Regular',C.muted,580))
  compSection.appendChild(gateAvailability)

  const dimComponents=[]
  ;[
    ['Ready','Sufficient positive evidence supports the current condition.','No current blocker'],
    ['Warning','A known risk needs validation but is not yet blocking.','Non-blocking risk'],
    ['Blocked','Explicit negative evidence proves a necessary condition is not met.','Triggers PAUSE'],
    ['Unknown','Missing / conflicting / insufficient evidence prevents reliable judgment.','May prevent full PROCEED']
  ].forEach(([s,copy,impact])=>{
    const c=exactDimensionComponent(s,copy,impact)
    compSection.appendChild(c)
    dimComponents.push(c)
  })
  const dimSet=figma.combineAsVariants(dimComponents,compSection)
  dimSet.name='Readiness Dimension Card'
  dimSet.layoutMode='HORIZONTAL'
  dimSet.layoutWrap='WRAP'
  dimSet.primaryAxisSizingMode='FIXED'
  dimSet.counterAxisSizingMode='AUTO'
  dimSet.resize(940,dimSet.height)
  dimSet.itemSpacing=12
  dimSet.counterAxisSpacing=12
  dimSet.paddingTop=18;dimSet.paddingRight=18;dimSet.paddingBottom=18;dimSet.paddingLeft=18

  const primaryButton=figma.createComponent()
  primaryButton.name='Type=Primary'
  setAuto(primaryButton,'HORIZONTAL',8,16)
  primaryButton.paddingTop=12;primaryButton.paddingBottom=12
  primaryButton.cornerRadius=12
  primaryButton.fills=[solid(C.primary)]
  primaryButton.strokes=[]
  primaryButton.effects=[buttonShadow]
  primaryButton.appendChild(txt('Primary action',13,'Semi Bold','#FFFFFF'))
  compSection.appendChild(primaryButton)

  const secondaryButton=figma.createComponent()
  secondaryButton.name='Type=Secondary'
  setAuto(secondaryButton,'HORIZONTAL',8,16)
  secondaryButton.paddingTop=12;secondaryButton.paddingBottom=12
  secondaryButton.cornerRadius=12
  secondaryButton.fills=[solid(C.surface,0.75)]
  secondaryButton.strokes=[solid(C.border)]
  secondaryButton.appendChild(txt('Secondary action',13,'Semi Bold','#344054'))
  compSection.appendChild(secondaryButton)

  const ghostButton=figma.createComponent()
  ghostButton.name='Type=Ghost'
  setAuto(ghostButton,'HORIZONTAL',4,10)
  ghostButton.paddingTop=8;ghostButton.paddingBottom=8
  ghostButton.cornerRadius=999
  ghostButton.fills=[solid(C.surface,0.72)]
  ghostButton.strokes=[solid(C.border)]
  ghostButton.appendChild(txt('Ghost action',11,'Semi Bold',C.mutedStrong))
  compSection.appendChild(ghostButton)

  const buttonSet=figma.combineAsVariants([primaryButton,secondaryButton,ghostButton],compSection)
  buttonSet.name='Button'
  buttonSet.layoutMode='HORIZONTAL'
  buttonSet.primaryAxisSizingMode='AUTO'
  buttonSet.counterAxisSizingMode='AUTO'
  buttonSet.itemSpacing=10
  buttonSet.paddingTop=18;buttonSet.paddingRight=18;buttonSet.paddingBottom=18;buttonSet.paddingLeft=18

  const taDefault=libraryTextActionComponent('View details →',false)
  const taMuted=libraryTextActionComponent('Feedback on evidence',true)
  compSection.appendChild(taDefault);compSection.appendChild(taMuted)
  const textActionSet=figma.combineAsVariants([taDefault,taMuted],compSection)
  textActionSet.name='Text Action'
  textActionSet.layoutMode='VERTICAL'
  textActionSet.primaryAxisSizingMode='AUTO'
  textActionSet.counterAxisSizingMode='AUTO'
  textActionSet.itemSpacing=12
  textActionSet.paddingTop=18;textActionSet.paddingRight=18;textActionSet.paddingBottom=18;textActionSet.paddingLeft=18

  const signalComponents=[]
  ;[['Resource Constraint','Unknown'],['Evaluation Conflict','Warning']].forEach(([name,state])=>{
    const c=exactSignalComponent(name,state)
    compSection.appendChild(c)
    signalComponents.push(c)
  })
  const signalSet=figma.combineAsVariants(signalComponents,compSection)
  signalSet.name='Context Signal Card'
  signalSet.layoutMode='VERTICAL'
  signalSet.primaryAxisSizingMode='AUTO'
  signalSet.counterAxisSizingMode='AUTO'
  signalSet.itemSpacing=10
  signalSet.paddingTop=18;signalSet.paddingRight=18;signalSet.paddingBottom=18;signalSet.paddingLeft=18

  // ---- Reference cards -----------------------------------------------------

  const acquisitionRef=box('Acquisition state semantics reference',{
    width:760,gap:8,padding:16,fill:C.surface,stroke:C.border,radius:12
  })
  acquisitionRef.appendChild(txt('ACQUISITION STATE · FROZEN SEMANTICS',10,'Semi Bold',C.subtle))
  acquisitionRef.appendChild(txt(
    'Empty · Reference only; do not present as a business readiness status.\nProcessing · Use spinner / processing row, not a generic status chip.\nPartial Result · Neutral acquisition tag.\nAcquisition Failure · Neutral acquisition tag; not Blocked.\nConflict · Neutral acquisition tag; not Warning / Blocked.',
    11,'Regular',C.text,720
  ))

  const nextRef=box('Next Action priority reference',{
    width:760,gap:8,padding:16,fill:C.surface,stroke:C.border,radius:12
  })
  nextRef.appendChild(txt('NEXT ACTION · FROZEN PRIORITY',10,'Semi Bold',C.subtle))
  nextRef.appendChild(txt(
    '1. Resolve Blocker\n2. Resolve Gate-critical Unknown\n3. Mitigate Warning\n4. Minimum Validation\n5. Higher-cost Reproduction',
    12,'Regular',C.text,720
  ))
  nextRef.appendChild(txt(
    'Higher-cost Reproduction is advice only; it is not an automatic execution CTA.',
    10,'Regular',C.muted,720
  ))

  const feedbackRef=box('Feedback options reference',{
    width:760,gap:9,padding:16,fill:C.surface,stroke:C.border,radius:12
  })
  feedbackRef.appendChild(txt('FEEDBACK / CORRECTION',10,'Semi Bold',C.subtle))
  const fbr=box('Options',{direction:'HORIZONTAL',gap:7,fill:C.surface,stroke:false,radius:0})
  ;['Confirm','Question','Correct','Add Evidence'].forEach(v=>{
    const item=box(`Feedback option / ${v}`,{
      direction:'HORIZONTAL',gap:4,padding:10,
      fill:C.unknownSoft,stroke:C.unknownSoft,radius:999
    })
    item.paddingTop=8;item.paddingBottom=8
    item.appendChild(txt(v,11,'Semi Bold',C.unknown))
    fbr.appendChild(item)
  })
  feedbackRef.appendChild(fbr)
  feedbackRef.appendChild(txt(
    'Feedback targets Finding / Evidence; it never hand-edits Dimension Status or Overall Gate.',
    10,'Regular',C.muted,720
  ))

  const safetyRef=box('Read-only Safety Boundary',{
    width:760,gap:8,padding:16,fill:C.surface2,stroke:C.border,radius:12
  })
  safetyRef.appendChild(txt('READ-ONLY SAFETY BOUNDARY',10,'Semi Bold',C.subtle))
  safetyRef.appendChild(txt(
    'No install · no environment modification · no file delete / overwrite · no training / reproduction execution',
    11,'Regular',C.text,720
  ))

  // ---- Clean library layout ------------------------------------------------

  const root=box('Component Library Layout',{
    width:2760,gap:34,padding:0,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  place(compSection,root,80,70)

  const header=box('Component library header',{
    width:2760,gap:7,padding:0,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  header.appendChild(txt('Component Library',32,'Semi Bold',C.textStrong))
  header.appendChild(txt(
    'Editable local components mapped to Frozen HTML V3.6. Components and semantic references are separated for implementation clarity.',
    13,'Regular',C.muted,1200
  ))
  root.appendChild(header)

  const mainLabel=txt('COMPONENTS',11,'Semi Bold',C.subtle)
  root.appendChild(mainLabel)

  const columns=box('Component columns',{
    width:2760,direction:'HORIZONTAL',gap:28,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })

  const colA=box('Column A',{
    width:720,gap:28,padding:0,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  colA.appendChild(libraryGroup('Business Status',720,[statusSet]))
  colA.appendChild(libraryGroup('Verification Status',720,[verificationSet]))
  colA.appendChild(libraryGroup('Acquisition State',720,[acquisitionTagSet,processingComponent]))
  columns.appendChild(colA)

  const colB=box('Column B',{
    width:720,gap:28,padding:0,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  colB.appendChild(libraryGroup('Overall Gate',720,[gateSet,gateAvailability]))
  colB.appendChild(libraryGroup('Actions',720,[buttonSet,textActionSet]))
  columns.appendChild(colB)

  const colC=box('Column C',{
    width:1264,gap:28,padding:0,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  colC.appendChild(libraryGroup('Readiness Dimension Card',1264,[dimSet]))
  colC.appendChild(libraryGroup('Context Signal Card',1264,[signalSet]))
  columns.appendChild(colC)

  root.appendChild(columns)

  root.appendChild(fixedSpacer(10,2760))
  root.appendChild(txt('REFERENCE / DOCUMENTATION',11,'Semi Bold',C.subtle))

  const refRow1=box('Reference row 1',{
    width:2760,direction:'HORIZONTAL',gap:28,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  refRow1.appendChild(acquisitionRef)
  refRow1.appendChild(nextRef)
  refRow1.appendChild(spacerGrow())
  root.appendChild(refRow1)

  const refRow2=box('Reference row 2',{
    width:2760,direction:'HORIZONTAL',gap:28,
    fill:C.canvas,fillOpacity:0,stroke:false,radius:0
  })
  refRow2.appendChild(feedbackRef)
  refRow2.appendChild(safetyRef)
  refRow2.appendChild(spacerGrow())
  root.appendChild(refRow2)

  // -------------------------------------------------------------------------
    // Prototype interactions
  // -------------------------------------------------------------------------
  await navigateOnClick(setupContinue, identified.frame)
  await navigateOnClick(idBack, setup.frame)
  await navigateOnClick(idContinue, auth.frame)
  await navigateOnClick(authBack, identified.frame)
  await navigateOnClick(useSnapshot, setup.frame)
  await navigateOnClick(useManual, setup.frame)
  await navigateOnClick(noEnv, processing.frame)
  await navigateOnClick(deny, denied.frame)
  await navigateOnClick(allow, processing.frame)
  await hotspot(processing.frame, overview.frame)

  await navigateOnClick(overviewBack, setup.frame)
  await navigateOnClick(od1.details, detail.frame)
  await navigateOnClick(od2.details, warningDetail.frame)
  await navigateOnClick(od3.details, readyDetail.frame)
  await navigateOnClick(rs.details, resourceView.frame)
  await navigateOnClick(es.details, evaluationView.frame)

  await navigateOnClick(detailBack, overview.frame)
  await navigateOnClick(finding.evidence, evidence.frame)
  await navigateOnClick(finding.feedback, feedback.frame)

  await navigateOnClick(evidence.feedback, evidenceFeedback.frame)
  if (evidence.openSource) {
    await urlOnClick(evidence.openSource, 'https://github.com/aseuteurideu/FGI')
  }
  await navigateOnClick(evidenceBack, detail.frame)
  await navigateOnClick(feedback.submit, detail.frame)
  await navigateOnClick(feedbackBack, detail.frame)

  await navigateOnClick(tcSupp, setup.frame)
  await navigateOnClick(tcSkip, skip.frame)
  await navigateOnClick(tcConfirmBtn, identified.frame)
  await navigateOnClick(smBack, targetConfirm.frame)
  await navigateOnClick(smGo, auth.frame)

  await navigateOnClick(denied.actionNodes[0], auth.frame)
  await navigateOnClick(denied.actionNodes[1], setup.frame)
  await navigateOnClick(denied.actionNodes[2], setup.frame)
  await navigateOnClick(denied.actionNodes[3], processing.frame)

  await navigateOnClick(resourceView.close, overview.frame)
  await navigateOnClick(evaluationView.close, overview.frame)
  await navigateOnClick(rvEvidence, resourceEvidence.frame)
  await navigateOnClick(evEvidence, conflictEvidence.frame)

  await navigateOnClick(resourceEvidence.close, resourceView.frame)
  await navigateOnClick(conflictEvidence.close, evaluationView.frame)
  await navigateOnClick(resourceEvidence.feedback, evidenceFeedback.frame)
  await navigateOnClick(conflictEvidence.feedback, evidenceFeedback.frame)

  await navigateOnClick(evidenceFeedback.close, evidence.frame)
  await navigateOnClick(evidenceFeedback.submit, evidence.frame)

  // 03_Variants_Reference is intentionally reference-only.
  // Figma NAVIGATE cannot cross Pages, so no reactions are attached here.
  // The equivalent clickable destinations live on 01_Prototype.

  await figma.setCurrentPageAsync(prototypePage)
  figma.currentPage.selection = [setup.frame]
  figma.viewport.scrollAndZoomIntoView([setup.frame, identified.frame, auth.frame, processing.frame, overview.frame, detail.frame, evidence.frame, feedback.frame])
  figma.notify('ResearchOps V3.6 Final Unified generated: Prototype, Components and Variants Reference all aligned to the completed Frozen HTML audit.', { timeout: 6000 })
  figma.closePlugin()
})().catch((err) => {
  console.error(err)
  figma.notify(`ResearchOps generator failed: ${err && err.message ? err.message : String(err)}`, { error: true, timeout: 8000 })
  figma.closePlugin()
})
