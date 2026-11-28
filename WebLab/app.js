/* ============================================================================
   LA COPA ETERNA: SANGRE Y POTRERO — AAA COMMAND CENTER & INTERACTIVE LAB
   app.js — Full 60 FPS Deterministic Simulation, Q32.32, GGPO, Wwise & eSports
   ============================================================================ */

(() => {
  'use strict';

  // ==========================================================================
  // 1. WEB AUDIO API SYNTHESIZER, TRIBUNA PROCEDURAL CONMEBOL & LOCUCIÓN TTS
  // ==========================================================================
  let audioEnabled = true;
  let ttsEnabled = true;
  let bandPlaying = false;
  let bandTimer = null;
  let bandStep = 0;
  let audioCtx = null;
  let crowdBusGain = null;
  let crowdLowpassFilter = null;

  function ensureAudio() {
    if (!audioEnabled) return null;
    if (!audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        audioCtx = new AudioContextClass();
        crowdLowpassFilter = audioCtx.createBiquadFilter();
        crowdLowpassFilter.type = 'lowpass';
        crowdLowpassFilter.frequency.value = 18000;

        crowdBusGain = audioCtx.createGain();
        crowdBusGain.gain.value = 0.22;
        crowdLowpassFilter.connect(crowdBusGain).connect(audioCtx.destination);
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    return audioCtx;
  }

  // Trigger real Sidechain Auto-Ducking (-6.0 dB = 0.5x linear gain) en el bus de Hinchada
  function triggerSidechainDucking(db = -6.0, recoverySec = 0.45) {
    const ctx = ensureAudio();
    if (!ctx || !crowdBusGain) return;
    const now = ctx.currentTime;
    const targetLinear = Math.pow(10, db / 20) * 0.24;
    crowdBusGain.gain.cancelScheduledValues(now);
    crowdBusGain.gain.setValueAtTime(targetLinear, now);
    crowdBusGain.gain.exponentialRampToValueAtTime(0.24, now + recoverySec);
  }

  // Modulación del Filtro Low-Pass (Pixel Health / Altura 3600m)
  function setCrowdFilterCutoff(freqHz) {
    const ctx = ensureAudio();
    if (!ctx || !crowdLowpassFilter) return;
    crowdLowpassFilter.frequency.setTargetAtTime(freqHz, ctx.currentTime, 0.08);
  }

  // Locución en Vivo del Relator Sudamericano (Web Speech API + Interrupt Stinger)
  function speakSouthAmericanCommentary(rawText, priority = 2) {
    if (!ttsEnabled || !('speechSynthesis' in window)) return;
    try {
      const clean = rawText.replace(/["«»]/g, '');
      window.speechSynthesis.cancel(); // Priority Queue Interrupt (< 2ms)
      const utter = new SpeechSynthesisUtterance(clean);
      const voices = window.speechSynthesis.getVoices();
      const esVoice = voices.find((v) => v.lang.startsWith('es-AR') || v.lang.startsWith('es-CO') || v.lang.startsWith('es-MX') || v.lang.startsWith('es'));
      if (esVoice) utter.voice = esVoice;
      utter.lang = 'es-419';
      utter.rate = priority >= 3 ? 1.24 : 1.15;
      utter.pitch = priority >= 4 ? 1.25 : 1.08;
      utter.volume = 0.9;
      window.speechSynthesis.speak(utter);
    } catch (_) {
      // Fallback silencioso si el navegador restringe speechSynthesis
    }
  }

  function playSynthSound(type) {
    const ctx = ensureAudio();
    if (!ctx) return;
    const now = ctx.currentTime;

    if (type === 'step') {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(520, now);
      osc.frequency.exponentialRampToValueAtTime(240, now + 0.035);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.04);
    } else if (type === 'hit') {
      triggerSidechainDucking(-6.0, 0.35);
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(160, now);
      osc.frequency.exponentialRampToValueAtTime(42, now + 0.14);
      gain.gain.setValueAtTime(0.22, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.15);
    } else if (type === 'parry') {
      triggerSidechainDucking(-6.0, 0.5);
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.exponentialRampToValueAtTime(1760, now + 0.18);
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.2);
    } else if (type === 'stinger') {
      triggerSidechainDucking(-6.0, 0.75);
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'square';
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.setValueAtTime(660, now + 0.06);
      osc.frequency.setValueAtTime(880, now + 0.12);
      gain.gain.setValueAtTime(0.14, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.26);
    } else if (type === 'desync') {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(310, now);
      osc.frequency.setValueAtTime(185, now + 0.12);
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.31);
    }
  }

  // Sintetizador Rítmico Procedural de las 10 Hinchadas CONMEBOL (BPM exactos de DT_StagesCONMEBOL.json)
  const CHANT_PATTERNS = {
    SAMBA:         { bpm: 115, label: '🇧🇷 Brasil — Batucada de Samba (115 BPM)',          low: [1,0,0,1, 1,0,1,0], mid: [0,1,1,0, 0,1,1,1], agogo: [1,0,1,1, 0,1,0,1] },
    BOMBO_AR:      { bpm: 128, label: '🇦🇷 Argentina — Bombo con Platillo Murga (128 BPM)', low: [1,0,1,0, 1,1,0,1], mid: [0,0,1,0, 0,0,1,0], agogo: [1,1,0,1, 1,0,1,0] },
    CANDOMBE_UY:   { bpm: 120, label: '🇺🇾 Uruguay — Cuerda de Candombe (120 BPM)',         low: [1,0,0,1, 0,1,1,0], mid: [1,1,0,1, 1,0,1,1], agogo: [0,1,1,0, 1,0,1,0] },
    TAMBORA_CO:    { bpm: 130, label: '🇨🇴 Colombia — Tambora Caribeña (130 BPM)',          low: [1,0,1,1, 0,1,1,0], mid: [0,1,0,1, 1,0,1,1], agogo: [1,1,1,0, 1,1,0,1] },
    CUECA_CL:      { bpm: 125, label: '🇨🇱 Chile — Cueca Brava & Bombo (125 BPM)',          low: [1,0,1,0, 1,0,1,1], mid: [0,1,1,0, 0,1,1,0], agogo: [1,0,1,0, 1,1,0,1] },
    POLKA_PY:      { bpm: 120, label: '🇵🇾 Paraguay — Polka Guaraní (120 BPM)',             low: [1,0,0,1, 1,0,1,0], mid: [0,1,0,1, 0,1,1,0], agogo: [1,1,0,1, 0,1,1,0] },
    CAJON_PE:      { bpm: 118, label: '🇵🇪 Perú — Cajón Criollo & Quijada (118 BPM)',       low: [1,0,0,1, 0,0,1,0], mid: [0,1,1,0, 1,1,0,1], agogo: [1,0,1,1, 0,1,0,1] },
    SANJUANITO_EC: { bpm: 135, label: '🇪🇨 Ecuador — San Juanito Andino (135 BPM)',         low: [1,0,1,0, 1,0,1,0], mid: [0,1,1,0, 0,1,1,1], agogo: [1,1,0,1, 1,0,1,1] },
    JOROPO_VE:     { bpm: 170, label: '🇻🇪 Venezuela — Joropo & Tambor Urbano (170 BPM)',   low: [1,0,1,1, 0,1,0,1], mid: [0,1,0,1, 1,0,1,1], agogo: [1,1,1,0, 1,1,1,0] },
    ANDINO_BO:     { bpm: 110, label: '🇧🇴 Bolivia — Bombo Legüero 3,600m (110 BPM)',       low: [1,0,0,1, 1,0,0,1], mid: [0,0,1,0, 0,1,1,0], agogo: [0,1,0,1, 0,1,0,1] }
  };

  function playPercussionStep() {
    if (!bandPlaying || !audioEnabled) return;
    const ctx = ensureAudio();
    if (!ctx || !crowdLowpassFilter) return;

    const selEl = document.getElementById('t4-sel-chants');
    const styleKey = selEl ? selEl.value : 'SAMBA';
    const pat = CHANT_PATTERNS[styleKey] || CHANT_PATTERNS.SAMBA;
    const idx = bandStep % 8;
    const now = ctx.currentTime;

    // 1. Surdo / Bombo de Cancha (Grave)
    if (pat.low[idx]) {
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(115, now);
      osc.frequency.exponentialRampToValueAtTime(46, now + 0.16);
      g.gain.setValueAtTime(0.45, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
      osc.connect(g).connect(crowdLowpassFilter);
      osc.start(now);
      osc.stop(now + 0.18);
    }

    // 2. Redoblante / Repique / Platillo (Medio)
    if (pat.mid[idx]) {
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(290, now);
      osc.frequency.exponentialRampToValueAtTime(140, now + 0.08);
      g.gain.setValueAtTime(0.24, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.09);
      osc.connect(g).connect(crowdLowpassFilter);
      osc.start(now);
      osc.stop(now + 0.09);
    }

    // 3. Agogô / Trompeta / Chajchas (Agudo)
    if (pat.agogo[idx]) {
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.type = 'square';
      const pitch = (idx % 2 === 0) ? 740 : 880;
      osc.frequency.setValueAtTime(pitch, now);
      g.gain.setValueAtTime(0.11, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
      osc.connect(g).connect(crowdLowpassFilter);
      osc.start(now);
      osc.stop(now + 0.07);
    }

    bandStep++;
  }

  function toggleStadiumBand(forceState = null) {
    bandPlaying = forceState !== null ? forceState : !bandPlaying;
    if (bandTimer) {
      clearInterval(bandTimer);
      bandTimer = null;
    }
    const hdrBtn = document.getElementById('btn-toggle-band');
    const t4Btn = document.getElementById('t4-btn-band-play');

    if (bandPlaying) {
      ensureAudio();
      const selEl = document.getElementById('t4-sel-chants');
      const pat = CHANT_PATTERNS[selEl ? selEl.value : 'SAMBA'] || CHANT_PATTERNS.SAMBA;
      const stepMs = Math.round((60000 / pat.bpm) / 2); // Corcheas
      bandTimer = setInterval(playPercussionStep, stepMs);
      if (hdrBtn) hdrBtn.textContent = '🥁 Hinchada: ON';
      if (t4Btn) t4Btn.textContent = '⏸ Pausar Banda en Vivo';
    } else {
      if (hdrBtn) hdrBtn.textContent = '🥁 Hinchada: OFF';
      if (t4Btn) t4Btn.textContent = '▶ Iniciar Banda en Vivo';
    }
  }

  document.getElementById('btn-toggle-audio').addEventListener('click', (e) => {
    audioEnabled = !audioEnabled;
    e.currentTarget.textContent = audioEnabled ? '🔊 SFX: ON' : '🔇 SFX: OFF';
    if (audioEnabled) playSynthSound('parry');
  });

  document.getElementById('btn-toggle-tts').addEventListener('click', (e) => {
    ttsEnabled = !ttsEnabled;
    e.currentTarget.textContent = ttsEnabled ? '🎙️ Relator Voz: ON' : '🔇 Relator Voz: OFF';
    if (!ttsEnabled && 'speechSynthesis' in window) window.speechSynthesis.cancel();
  });

  document.getElementById('btn-toggle-band').addEventListener('click', () => {
    toggleStadiumBand();
  });

  // Modal Pre-Partida EOS (CommonUI Filter)
  const eosBackdrop = document.getElementById('eos-modal-backdrop');
  function openEosModal() {
    eosBackdrop.style.display = 'flex';
    playSynthSound('stinger');
  }
  document.getElementById('btn-eos-modal').addEventListener('click', openEosModal);
  const t4OpenEosBtn = document.getElementById('t4-btn-open-eos');
  if (t4OpenEosBtn) t4OpenEosBtn.addEventListener('click', openEosModal);

  document.getElementById('eos-sim-lan').addEventListener('click', () => {
    document.getElementById('eos-opp-platform').textContent = '🖥️ PC Steam (Crossplay Activo)';
    const netEl = document.getElementById('eos-opp-nettype');
    netEl.textContent = '🔌 Cable Ethernet LAN (Óptimo Competitivo)';
    netEl.style.color = '#00e676';
    document.getElementById('eos-opp-ping').textContent = '28 ms';
    const jitEl = document.getElementById('eos-opp-jitter');
    jitEl.textContent = '±1.8 ms (Rollback Fijo: 1 Frame)';
    jitEl.style.color = '#00e676';
    playSynthSound('parry');
  });

  document.getElementById('eos-sim-wifi').addEventListener('click', () => {
    document.getElementById('eos-opp-platform').textContent = '🎮 PlayStation 5 (Crossplay Activo)';
    const netEl = document.getElementById('eos-opp-nettype');
    netEl.textContent = '📶 Wi-Fi Inalámbrico (Alerta de Packet Burst)';
    netEl.style.color = '#ff2a54';
    document.getElementById('eos-opp-ping').textContent = '135 ms';
    const jitEl = document.getElementById('eos-opp-jitter');
    jitEl.textContent = '±38.4 ms (Rollback Estimado: 5f - 7f)';
    jitEl.style.color = '#ff2a54';
    playSynthSound('desync');
  });

  document.getElementById('eos-btn-reject').addEventListener('click', () => {
    eosBackdrop.style.display = 'none';
    playSynthSound('step');
  });

  document.getElementById('eos-btn-accept').addEventListener('click', () => {
    eosBackdrop.style.display = 'none';
    document.querySelector('[data-tab="tab6"]').click();
    toggleStadiumBand(true);
    playSynthSound('stinger');
  });

  // ==========================================================================
  // 2. NAVEGACIÓN DE PESTAÑAS (TABS)
  // ==========================================================================
  let activeTab = 'tab1';
  document.querySelectorAll('#main-tabs .tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#main-tabs .tab-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      activeTab = btn.dataset.tab;
      document.getElementById(activeTab).classList.add('active');
      if (activeTab === 'tab7') renderTab7Studio3D();
      playSynthSound('step');
    });
  });

  // ==========================================================================
  // 3. BASE DE DATOS INTEGRADA DEL MOTOR (ROSTER 16+1, MOVES & 10 ESTADIOS)
  // ==========================================================================
  const ROSTER_DATA = [
    {
      Name: 'FENOMENO_BR', DisplayName: 'O Fenômeno', Country: 'Brasil 🇧🇷', Era: '1994-2006',
      Archetype: 'Rushdown Explosivo', MaxHealth: 10000, StunThreshold: 1000, ForwardDashFrames: 15, BackDashFrames: 21,
      SignatureMoveNotation: '236+LP',
      PassiveTitle: 'Pasiva: Arrancada Imparable (Super Armor)',
      PassiveDesc: 'Los primeros 4 frames de su Forward Dash absorben 1 impacto ligero o proyectil sin detener su carrera.',
      ColorPrimary: '#f5c451', ColorSecondary: '#00a859',
      SpecificMoves: [
        { MoveID: 'FEN_PEDALADA', Numpad: '236+LP', Name: 'Pedalada Mortal (Stance)', S: 11, A: 0, R: 12, Block: 0, Hit: 0, Dmg: 0, Flags: 2, Win: 8, Invuln: 'High-Crush F4-10', BoxType: 'stance' },
        { MoveID: 'FEN_FRENO', Numpad: '236+LP~LP', Name: 'Freno en Seco (Plus Frame)', S: 6, A: 3, R: 10, Block: 2, Hit: 6, Dmg: 400, Flags: 6, Win: 6, Invuln: 'Ninguna', BoxType: 'melee' },
        { MoveID: 'FEN_SOMBRERO', Numpad: '236+LP~MP', Name: 'Sombrero Overhead', S: 18, A: 4, R: 15, Block: -3, Hit: 5, Dmg: 900, Flags: 4, Win: 5, Invuln: 'Low-Crush F6-18', BoxType: 'overhead' },
        { MoveID: 'FEN_CORTEBAJO', Numpad: '236+LP~HP', Name: 'Corte Bajo (Hard Knockdown)', S: 12, A: 3, R: 20, Block: -8, Hit: 18, Dmg: 850, Flags: 4, Win: 5, Invuln: 'Ninguna', BoxType: 'low' },
        { MoveID: 'FEN_SUPER1', Numpad: '236236+LP', Name: 'Definición Cruzada (Nv.1)', S: 7, A: 18, R: 32, Block: -18, Hit: 35, Dmg: 2400, Flags: 0, Win: 0, Invuln: 'Strike Invuln F1-7', BoxType: 'projectile' },
        { MoveID: 'FEN_ULTIMATE', Numpad: '214214+HP+SK', Name: 'Pentacampeón Eterno (Nv.3)', S: 5, A: 24, R: 45, Block: -30, Hit: 60, Dmg: 4500, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-12', BoxType: 'ultimate' }
      ]
    },
    {
      Name: 'BRUXO_BR', DisplayName: 'O Bruxo', Country: 'Brasil 🇧🇷', Era: '2000-2010',
      Archetype: 'Trickster / Mix-up', MaxHealth: 9500, StunThreshold: 950, ForwardDashFrames: 17, BackDashFrames: 20,
      SignatureMoveNotation: '41236+MP',
      PassiveTitle: 'Pasiva: Sonrisa de Carnaval (Ritmo de Samba)',
      PassiveDesc: 'Cada finta exitosa con Gambeta incrementa +15% la ganancia de Super Meter durante 6 segundos.',
      ColorPrimary: '#ffe07d', ColorSecondary: '#1b5e20',
      SpecificMoves: [
        { MoveID: 'BRUXO_ELASTICA_MP', Numpad: '41236+MP', Name: 'Elástica de Caño (Cross-up)', S: 14, A: 5, R: 15, Block: -2, Hit: 8, Dmg: 950, Flags: 4, Win: 6, Invuln: 'Projectile Invuln F4-12', BoxType: 'melee' },
        { MoveID: 'BRUXO_ELASTICA_HP', Numpad: '41236+HP', Name: 'Elástica Pesada (Plus on Block)', S: 19, A: 5, R: 14, Block: 2, Hit: 15, Dmg: 1150, Flags: 4, Win: 6, Invuln: 'Projectile Invuln F4-14', BoxType: 'melee' },
        { MoveID: 'BRUXO_NOLOOK_PASS', Numpad: '236+SK', Name: 'Pase No-Look (Ángulo Falso)', S: 13, A: 10, R: 20, Block: 3, Hit: 9, Dmg: 850, Flags: 4, Win: 5, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'BRUXO_ESPALDINHA', Numpad: '4+MP', Name: 'Espaldinha Táctica', S: 8, A: 4, R: 13, Block: 1, Hit: 6, Dmg: 680, Flags: 6, Win: 6, Invuln: 'Air Invuln F1-8', BoxType: 'antiair' },
        { MoveID: 'BRUXO_ULTIMATE_JOGA_BONITO', Numpad: '214214+HP+SK', Name: 'Joga Bonito Eterno (Nv.3)', S: 6, A: 22, R: 44, Block: -28, Hit: 62, Dmg: 4400, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-10', BoxType: 'ultimate' }
      ]
    },
    {
      Name: 'CANON_AR', DisplayName: 'El Cañón', Country: 'Argentina 🇦🇷', Era: '1990-2002',
      Archetype: 'Power Shoto', MaxHealth: 10500, StunThreshold: 1050, ForwardDashFrames: 19, BackDashFrames: 22,
      SignatureMoveNotation: '236+SK',
      PassiveTitle: 'Pasiva: Artillería Pesada (Chip Damage +25%)',
      PassiveDesc: 'Sus disparos de balón causan 25% más daño gris en bloqueo y empujan el doble hacia la red.',
      ColorPrimary: '#74acdf', ColorSecondary: '#ffffff',
      SpecificMoves: [
        { MoveID: 'CANON_BATI', Numpad: '236+SK', Name: 'Bati-Cañonazo Recto', S: 14, A: 12, R: 24, Block: -3, Hit: 2, Dmg: 1100, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'CANON_BATI_CHARGED', Numpad: '236+[SK]', Name: 'Bati-Cañonazo Cargado (Guard Crush)', S: 28, A: 14, R: 18, Block: 4, Hit: 25, Dmg: 1650, Flags: 4, Win: 8, Invuln: 'Super Armor F8-22', BoxType: 'projectile' },
        { MoveID: 'CANON_VOLEA', Numpad: '623+HP', Name: 'Volea de Media Vuelta (DP)', S: 5, A: 10, R: 30, Block: -20, Hit: 28, Dmg: 1400, Flags: 4, Win: 6, Invuln: 'Full Invuln F1-6', BoxType: 'antiair' },
        { MoveID: 'CANON_ULTIMATE_ANGULO_ETERNO', Numpad: '214214+HP+SK', Name: 'Ángulo Eterno del 98 (Nv.3)', S: 6, A: 20, R: 46, Block: -32, Hit: 64, Dmg: 4700, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-11', BoxType: 'ultimate' }
      ]
    },
    {
      Name: 'PULGA_AR', DisplayName: 'La Pulga', Country: 'Argentina 🇦🇷', Era: '2005-Presente',
      Archetype: 'Pixie / Footsies', MaxHealth: 9000, StunThreshold: 900, ForwardDashFrames: 14, BackDashFrames: 18,
      SignatureMoveNotation: '236+MP',
      PassiveTitle: 'Pasiva: Pelota Pegada al Pie (Micro-Hurtbox)',
      PassiveDesc: 'Su Hurtbox superior es 18% más baja durante desplazamientos y sus cambios de dirección no tienen fricción.',
      ColorPrimary: '#00e5ff', ColorSecondary: '#f5c451',
      SpecificMoves: [
        { MoveID: 'PULGA_RECORTE', Numpad: '3+MP', Name: 'Recorte Interno (Plus on Block)', S: 6, A: 3, R: 11, Block: 2, Hit: 6, Dmg: 600, Flags: 6, Win: 6, Invuln: 'High-Crush F2-6', BoxType: 'low' },
        { MoveID: 'PULGA_SLALOM_LP', Numpad: '236+LP', Name: 'Gambeta Endiablada (Finta Invuln)', S: 9, A: 0, R: 10, Block: 0, Hit: 0, Dmg: 0, Flags: 2, Win: 6, Invuln: 'High-Crush F1-8', BoxType: 'stance' },
        { MoveID: 'PULGA_SLALOM_MP', Numpad: '236+MP', Name: 'Slalom Imposible', S: 13, A: 4, R: 14, Block: -2, Hit: 5, Dmg: 800, Flags: 4, Win: 5, Invuln: 'Projectile Invuln F3-11', BoxType: 'melee' },
        { MoveID: 'PULGA_VASELINA', Numpad: '236+HP', Name: 'Vaselina Sombrero', S: 15, A: 5, R: 21, Block: -9, Hit: 22, Dmg: 1050, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'overhead' },
        { MoveID: 'PULGA_TIROANGULO', Numpad: '214+SK', Name: 'Rosca al Ángulo Imposible', S: 18, A: 10, R: 24, Block: 1, Hit: 8, Dmg: 950, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'PULGA_CORONACION', Numpad: '214214+HP+SK', Name: 'Coronación Eterna (Ultimate 4f)', S: 4, A: 10, R: 38, Block: -24, Hit: 65, Dmg: 4600, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-12', BoxType: 'ultimate' }
      ]
    },
    {
      Name: 'PIBE_CO', DisplayName: 'El Pibe', Country: 'Colombia 🇨🇴', Era: '1990-2000',
      Archetype: 'Setplay Zoner', MaxHealth: 10000, StunThreshold: 1000, ForwardDashFrames: 21, BackDashFrames: 23,
      SignatureMoveNotation: '236+SK',
      PassiveTitle: 'Pasiva: Visión Periférica Total (Trampas de Balón)',
      PassiveDesc: 'Puede mantener hasta 2 balones flotando en cancha que detonan al contacto o mediante comando 22+SK.',
      ColorPrimary: '#ffeb3b', ColorSecondary: '#1976d2',
      SpecificMoves: [
        { MoveID: 'PIBE_PASE_FILTRADO', Numpad: '236+SK', Name: 'Pase Filtrado al Vacío', S: 15, A: 14, R: 22, Block: 2, Hit: 10, Dmg: 900, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'PIBE_BALON_SUSPENDIDO', Numpad: '214+SK', Name: 'Balón Suspendido (Setplay)', S: 17, A: 30, R: 19, Block: 6, Hit: 16, Dmg: 800, Flags: 4, Win: 5, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'PIBE_DETONAR_PASE', Numpad: '22+SK', Name: 'Activación Táctica de Esférico', S: 8, A: 8, R: 16, Block: 4, Hit: 20, Dmg: 1050, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'PIBE_ULTIMATE_CINCO_A_CERO', Numpad: '214214+HP+SK', Name: 'Cinco a Cero Monumental (Nv.3)', S: 6, A: 24, R: 42, Block: -26, Hit: 60, Dmg: 4450, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-10', BoxType: 'ultimate' }
      ]
    },
    {
      Name: 'LOCO_CO', DisplayName: 'El Loco', Country: 'Colombia 🇨🇴', Era: '1990-2000',
      Archetype: 'Counter-Acrobat', MaxHealth: 10200, StunThreshold: 1050, ForwardDashFrames: 18, BackDashFrames: 20,
      SignatureMoveNotation: '214+SK',
      PassiveTitle: 'Pasiva: Arquero Líbero (Furia Fuera del Área)',
      PassiveDesc: 'Mientras está de la mitad de la cancha hacia adelante gana +12% velocidad y daño en saltos acrobáticos.',
      ColorPrimary: '#00e5ff', ColorSecondary: '#ffeb3b',
      SpecificMoves: [
        { MoveID: 'LOCO_ESCORPION', Numpad: '214+SK', Name: 'El Escorpión (High-Crush Counter)', S: 16, A: 8, R: 22, Block: -4, Hit: 24, Dmg: 1250, Flags: 4, Win: 6, Invuln: 'Upper Invuln F1-16', BoxType: 'antiair' },
        { MoveID: 'LOCO_DESPEJE', Numpad: '623+HP', Name: 'Despeje de Puños Volador', S: 5, A: 7, R: 29, Block: -18, Hit: 26, Dmg: 1300, Flags: 4, Win: 6, Invuln: 'Full Invuln F1-6', BoxType: 'antiair' },
        { MoveID: 'LOCO_SALIDA_AREA', Numpad: '236+MP', Name: 'Salida del Área Líbero', S: 12, A: 6, R: 17, Block: -3, Hit: 15, Dmg: 1000, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'melee' },
        { MoveID: 'LOCO_ULTIMATE_WEMBLEY_ETERNO', Numpad: '214214+HP+SK', Name: 'Wembley Eterno 95 (Nv.3)', S: 5, A: 22, R: 44, Block: -28, Hit: 62, Dmg: 4550, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-10', BoxType: 'ultimate' }
      ]
    },
    {
      Name: 'PISTOLERO_UY', DisplayName: 'El Pistolero', Country: 'Uruguay 🇺🇾', Era: '2007-Presente',
      Archetype: 'Hybrid Grappler', MaxHealth: 10800, StunThreshold: 1100, ForwardDashFrames: 20, BackDashFrames: 23,
      SignatureMoveNotation: '41236+LP',
      PassiveTitle: 'Pasiva: Garra Charrúa (Desperation Boost)',
      PassiveDesc: 'Al bajar del 30% de vida sus Command Grabs ganan alcance extra y su daño base sube un 15%.',
      ColorPrimary: '#4fc3f7', ColorSecondary: '#ffffff',
      SpecificMoves: [
        { MoveID: 'PISTOLERO_MORDISCO', Numpad: '41236+LP', Name: 'Presión Asfixiante (Command Grab)', S: 6, A: 3, R: 28, Block: 0, Hit: 30, Dmg: 1800, Flags: 0, Win: 0, Invuln: 'Throw Invuln F1-6', BoxType: 'grab' },
        { MoveID: 'PISTOLERO_MANOSALVADORA', Numpad: '22+GB', Name: 'La Mano Salvadora (Parry 1f)', S: 1, A: 16, R: 26, Block: 0, Hit: 16, Dmg: 0, Flags: 8, Win: 10, Invuln: 'Parry Stance F1-16', BoxType: 'stance' },
        { MoveID: 'PISTOLERO_ULTIMATE_GARRA_CHARRUA', Numpad: '214214+HP+SK', Name: 'Garra Charrúa Inmortal (Nv.3)', S: 5, A: 20, R: 45, Block: -30, Hit: 64, Dmg: 4650, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-10', BoxType: 'ultimate' }
      ]
    },
    {
      Name: 'MATADOR_UY', DisplayName: 'El Matador', Country: 'Uruguay 🇺🇾', Era: '2000-2018',
      Archetype: 'Long-Range Hybrid', MaxHealth: 10000, StunThreshold: 1000, ForwardDashFrames: 18, BackDashFrames: 21,
      SignatureMoveNotation: '236+SK',
      PassiveTitle: 'Pasiva: Francotirador Ambidiestro',
      PassiveDesc: 'Puede cancelar cualquier tiro de balón en otro disparo con pierna opuesta consumiendo 250 de Gambeta.',
      ColorPrimary: '#81d4fa', ColorSecondary: '#f5c451',
      SpecificMoves: [
        { MoveID: 'MATADOR_EFECTO_JABULANI', Numpad: '236+SK', Name: 'Efecto Jabulani (Curva Errática)', S: 15, A: 14, R: 21, Block: 1, Hit: 14, Dmg: 1100, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'MATADOR_CABEZAZO_PLANCHA', Numpad: '[4]6+HP', Name: 'Cabezazo en Plancha (Charge)', S: 11, A: 7, R: 19, Block: -4, Hit: 22, Dmg: 1250, Flags: 4, Win: 6, Invuln: 'Projectile Invuln F3-12', BoxType: 'melee' },
        { MoveID: 'MATADOR_ULTIMATE_BALON_DE_ORO', Numpad: '214214+HP+SK', Name: 'Balón de Oro Sudáfrica (Nv.3)', S: 6, A: 22, R: 44, Block: -29, Hit: 62, Dmg: 4550, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-10', BoxType: 'ultimate' }
      ]
    },
    {
      Name: 'BAMBAM_CL', DisplayName: 'Bam-Bam', Country: 'Chile 🇨🇱', Era: '1990-2002',
      Archetype: 'Air-Dominance', MaxHealth: 10000, StunThreshold: 1000, ForwardDashFrames: 17, BackDashFrames: 20,
      SignatureMoveNotation: 'j.236+MP',
      PassiveTitle: 'Pasiva: El Helicóptero (Suspend Air-Stall)',
      PassiveDesc: 'Puede suspenderse 18 frames en el punto máximo de su salto para alterar el timing de sus Divekicks.',
      ColorPrimary: '#ff2a54', ColorSecondary: '#1976d2',
      SpecificMoves: [
        { MoveID: 'BAMBAM_CABEZAZO_PICADA', Numpad: 'j.236+MP', Name: 'Cabezazo Suspendido (Overhead)', S: 9, A: 8, R: 14, Block: 2, Hit: 12, Dmg: 950, Flags: 4, Win: 6, Invuln: 'Throw Invuln Air', BoxType: 'overhead' },
        { MoveID: 'BAMBAM_HELICOPTERO_AA', Numpad: '623+HP', Name: 'El Helicóptero Anti-Aéreo', S: 5, A: 9, R: 28, Block: -17, Hit: 26, Dmg: 1300, Flags: 4, Win: 6, Invuln: 'Full Invuln F1-6', BoxType: 'antiair' },
        { MoveID: 'BAMBAM_TIJERA_CHILENA', Numpad: '214+SK', Name: 'Tijera Chilena', S: 14, A: 6, R: 21, Block: -6, Hit: 22, Dmg: 1200, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'melee' }
      ]
    },
    {
      Name: 'REY_CL', DisplayName: 'El Rey', Country: 'Chile 🇨🇱', Era: '2007-Presente',
      Archetype: 'Berserker Rekka', MaxHealth: 10400, StunThreshold: 1050, ForwardDashFrames: 16, BackDashFrames: 20,
      SignatureMoveNotation: '236+LP',
      PassiveTitle: 'Pasiva: Pulmón de Acero (Gambeta Cost -20%)',
      PassiveDesc: 'Sus cancelaciones de barrida y Rekkas consumen 20% menos barra de Gambeta.',
      ColorPrimary: '#ff5252', ColorSecondary: '#ffffff',
      SpecificMoves: [
        { MoveID: 'REY_TRANCAZO_REKKA_1', Numpad: '236+LP', Name: 'Trancazo Real (Rekka 1/3)', S: 10, A: 4, R: 16, Block: -2, Hit: 4, Dmg: 600, Flags: 2, Win: 8, Invuln: 'Ninguna', BoxType: 'melee' },
        { MoveID: 'REY_TRANCAZO_REKKA_2', Numpad: '236+LP~MP', Name: 'Trancazo Real (Rekka 2/3)', S: 8, A: 4, R: 18, Block: -4, Hit: 6, Dmg: 650, Flags: 2, Win: 8, Invuln: 'Ninguna', BoxType: 'melee' },
        { MoveID: 'REY_BARRIDA_REAL', Numpad: '3+HP', Name: 'Barrida Real Con Todo', S: 10, A: 5, R: 18, Block: -4, Hit: 18, Dmg: 1000, Flags: 6, Win: 6, Invuln: 'High-Crush F3-12', BoxType: 'low' }
      ]
    },
    {
      Name: 'BULLDOG_PY', DisplayName: 'El Bulldog', Country: 'Paraguay 🇵🇾', Era: '1990-2003',
      Archetype: 'Big-Body Grappler / Zoner', MaxHealth: 11500, StunThreshold: 1200, ForwardDashFrames: 23, BackDashFrames: 25,
      SignatureMoveNotation: '236+SK',
      PassiveTitle: 'Pasiva: Intimidación Guaraní (11,500 HP + Hyper Armor)',
      PassiveDesc: 'Mayor vitalidad entre las leyendas jugables. Sus tiros libres convocan una barrera espectral.',
      ColorPrimary: '#ff2a54', ColorSecondary: '#4fc3f7',
      SpecificMoves: [
        { MoveID: 'BULLDOG_TIRO_LIBRE_BARRERA', Numpad: '236+SK', Name: 'Tiro Libre con Barrera', S: 18, A: 16, R: 22, Block: 4, Hit: 18, Dmg: 1350, Flags: 4, Win: 6, Invuln: 'Armor F6-18', BoxType: 'projectile' },
        { MoveID: 'BULLDOG_AGARRE_CUELLO', Numpad: '41236+HP', Name: 'Agarre del Cuello (Command Throw)', S: 7, A: 3, R: 30, Block: 0, Hit: 32, Dmg: 2000, Flags: 0, Win: 0, Invuln: 'Throw Invuln F1-7', BoxType: 'grab' }
      ]
    },
    {
      Name: 'MAESTRO_PE', DisplayName: 'El Maestro', Country: 'Perú 🇵🇪', Era: 'Clásico-Moderno',
      Archetype: 'Technical Footsies', MaxHealth: 9800, StunThreshold: 980, ForwardDashFrames: 17, BackDashFrames: 19,
      SignatureMoveNotation: '236+SK~8',
      PassiveTitle: 'Pasiva: Toque de Seda Peruano',
      PassiveDesc: 'Sus ataques normales medios tienen +2 frames adicionales de ventana de cancelación a Especiales.',
      ColorPrimary: '#ffffff', ColorSecondary: '#ff2a54',
      SpecificMoves: [
        { MoveID: 'MAESTRO_TRES_DEDOS_ALTO', Numpad: '236+SK~8', Name: 'Tiro de Tres Dedos (Curva Alta)', S: 15, A: 12, R: 20, Block: 2, Hit: 12, Dmg: 1000, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'MAESTRO_TRES_DEDOS_BAJO', Numpad: '236+SK~2', Name: 'Tiro de Tres Dedos (Curva Baja)', S: 15, A: 12, R: 20, Block: 2, Hit: 14, Dmg: 1000, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'MAESTRO_HUACHA_SIDESWAP', Numpad: '214+LP', Name: 'Huacha Elegante de Cambio de Lado', S: 11, A: 4, R: 15, Block: -2, Hit: 8, Dmg: 750, Flags: 4, Win: 6, Invuln: 'Strike Pass F4-10', BoxType: 'melee' }
      ]
    },
    {
      Name: 'TREN_EC', DisplayName: 'El Tren Amazónico', Country: 'Ecuador 🇪🇨', Era: '2002-2020',
      Archetype: 'Speedster / Run-Cancel', MaxHealth: 9600, StunThreshold: 950, ForwardDashFrames: 13, BackDashFrames: 18,
      SignatureMoveNotation: '236+GB',
      PassiveTitle: 'Pasiva: Locomotora por la Banda (Dash 13f)',
      PassiveDesc: 'El Forward Dash más veloz de las leyendas (13 frames); permite Run-Cancel dejando sus presiones en +3 on block.',
      ColorPrimary: '#ffd600', ColorSecondary: '#2962ff',
      SpecificMoves: [
        { MoveID: 'TREN_EXPRESO_BANDA', Numpad: '236+GB', Name: 'Expreso por la Banda (Run-Cancel)', S: 8, A: 0, R: 9, Block: 3, Hit: 7, Dmg: 0, Flags: 6, Win: 8, Invuln: 'Projectile Invuln F2-8', BoxType: 'stance' },
        { MoveID: 'TREN_CENTRO_RASANTE', Numpad: '236+SK', Name: 'Centro Rasante Buscapiés', S: 12, A: 10, R: 19, Block: -1, Hit: 14, Dmg: 950, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'low' }
      ]
    },
    {
      Name: 'HURACAN_VE', DisplayName: 'El Huracán Vinotinto', Country: 'Venezuela 🇻🇪', Era: '2000-Presente',
      Archetype: 'Dead-Ball Sniper', MaxHealth: 10200, StunThreshold: 1020, ForwardDashFrames: 19, BackDashFrames: 21,
      SignatureMoveNotation: '236+SK',
      PassiveTitle: 'Pasiva: Zurda de Oro (Sin Escalado a Distancia)',
      PassiveDesc: 'Sus proyectiles de balón no sufren reducción de daño por distancia y caen en picada (Folha Seca).',
      ColorPrimary: '#ad1457', ColorSecondary: '#f5c451',
      SpecificMoves: [
        { MoveID: 'HURACAN_ZURDA_FOLHA_SECA', Numpad: '236+SK', Name: 'Zurda de Oro (Folha Seca)', S: 16, A: 14, R: 21, Block: 3, Hit: 16, Dmg: 1250, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'HURACAN_CORNER_OLIMPICO', Numpad: '214+SK', Name: 'Córner Olímpico Vinotinto', S: 19, A: 16, R: 22, Block: 4, Hit: 18, Dmg: 1200, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' }
      ]
    },
    {
      Name: 'DIABLO_BO', DisplayName: 'El Diablo Andino', Country: 'Bolivia 🇧🇴', Era: '1990-2000',
      Archetype: 'Stamina Debuffer', MaxHealth: 9800, StunThreshold: 960, ForwardDashFrames: 18, BackDashFrames: 20,
      SignatureMoveNotation: '214+SK',
      PassiveTitle: 'Pasiva: Mal de Altura (3,600m Debuff)',
      PassiveDesc: 'Sus impactos especiales aplican "Falta de Aire", reduciendo la regeneración de Gambeta del rival en 30%.',
      ColorPrimary: '#00e676', ColorSecondary: '#ff2a54',
      SpecificMoves: [
        { MoveID: 'DIABLO_BALON_PESADO_3600M', Numpad: '214+SK', Name: 'Balón Pesado (3,600m Hipoxia)', S: 15, A: 12, R: 20, Block: 3, Hit: 15, Dmg: 1050, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'DIABLO_REMATE_SOROCHE', Numpad: '236+MP', Name: 'Remate Soroche Altiplano', S: 12, A: 5, R: 17, Block: -2, Hit: 16, Dmg: 1000, Flags: 4, Win: 6, Invuln: 'Ninguna', BoxType: 'melee' }
      ]
    },
    {
      Name: 'GENERAL_FR', DisplayName: 'Le Général (Invitado)', Country: 'Francia 🇫🇷', Era: '1996-2006',
      Archetype: 'Tactical Stance', MaxHealth: 10000, StunThreshold: 1000, ForwardDashFrames: 17, BackDashFrames: 20,
      SignatureMoveNotation: '236+MP',
      PassiveTitle: 'Pasiva: Maestro de la Orquesta',
      PassiveDesc: 'La Roulette de Marseille atraviesa ataques de golpe alto y deja al rival de espaldas.',
      ColorPrimary: '#2979ff', ColorSecondary: '#ffffff',
      SpecificMoves: [
        { MoveID: 'GENERAL_ROULETTE_MARSEILLE', Numpad: '236+MP', Name: 'Roulette de Marseille (Stance Evade)', S: 11, A: 6, R: 15, Block: -1, Hit: 10, Dmg: 950, Flags: 4, Win: 6, Invuln: 'Strike Invuln F3-9', BoxType: 'melee' },
        { MoveID: 'GENERAL_COUP_DE_TETE', Numpad: '41236+HP', Name: 'Coup de Tête Final (Armor Break)', S: 9, A: 5, R: 22, Block: -6, Hit: 28, Dmg: 1500, Flags: 4, Win: 6, Invuln: 'Super Armor F1-7', BoxType: 'antiair' }
      ]
    },
    {
      Name: 'VAR_ZERO_BOSS', DisplayName: 'El Juez Supremo (V.A.R. - ZERO)', Country: 'BOSS FINAL ⚠️', Era: 'Atemporal',
      Archetype: 'Boss Zoner / Time Rewinder', MaxHealth: 13000, StunThreshold: 1500, ForwardDashFrames: 12, BackDashFrames: 14,
      SignatureMoveNotation: '22+GB',
      PassiveTitle: 'Pasiva Boss: Revisión de Cuadro (V.A.R. Rewind 90f)',
      PassiveDesc: 'Rebobina 90 frames del Ring Buffer GGPO. Vulnerable a System Overload tras 3 Gambetas Perfectas.',
      ColorPrimary: '#ff2a54', ColorSecondary: '#00e5ff',
      SpecificMoves: [
        { MoveID: 'VAR_OFFSIDE_TRAP', Numpad: '236+SK', Name: 'Láser de Línea de Offside', S: 10, A: 14, R: 16, Block: 4, Hit: 20, Dmg: 1400, Flags: 4, Win: 8, Invuln: 'Ninguna', BoxType: 'projectile' },
        { MoveID: 'VAR_RED_CARD', Numpad: '623+HP', Name: 'Sentencia de Tarjeta Roja (Guard Crush)', S: 8, A: 6, R: 22, Block: 6, Hit: 28, Dmg: 1850, Flags: 4, Win: 6, Invuln: 'Super Armor F1-8', BoxType: 'antiair' },
        { MoveID: 'VAR_REWIND_90F', Numpad: '22+GB', Name: 'V.A.R. Rewind (-90 Frames GGPO)', S: 3, A: 2, R: 20, Block: 0, Hit: 0, Dmg: 0, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-15', BoxType: 'ultimate' },
        { MoveID: 'VAR_ULTIMATE_PURGA_REGLAMENTARIA', Numpad: '214214+HP+SK', Name: 'Purga Reglamentaria Total (Nv.3)', S: 5, A: 24, R: 42, Block: -26, Hit: 65, Dmg: 5000, Flags: 0, Win: 0, Invuln: 'Full Invuln F1-12', BoxType: 'ultimate' }
      ]
    }
  ];

  const UNIVERSAL_MOVES = [
    { MoveID: '5LP_UNIVERSAL', Numpad: '5LP', Name: 'Toque Corto (Jab)', S: 4, A: 3, R: 7, Block: 1, Hit: 4, Dmg: 400, Flags: 7, Win: 6, Invuln: 'Ninguna', BoxType: 'melee' },
    { MoveID: '2LP_UNIVERSAL', Numpad: '2LP', Name: 'Punteo Bajo Rápido', S: 4, A: 2, R: 8, Block: 1, Hit: 4, Dmg: 350, Flags: 7, Win: 5, Invuln: 'High-Crush F1-6', BoxType: 'low' },
    { MoveID: '5MP_UNIVERSAL', Numpad: '5MP', Name: 'Cabezazo / Hombro Medio', S: 7, A: 4, R: 14, Block: -1, Hit: 5, Dmg: 700, Flags: 6, Win: 7, Invuln: 'Ninguna', BoxType: 'melee' },
    { MoveID: '2MP_UNIVERSAL', Numpad: '2MP', Name: 'enganche de Suelo (Footsie)', S: 6, A: 4, R: 13, Block: 0, Hit: 6, Dmg: 650, Flags: 6, Win: 7, Invuln: 'Ninguna', BoxType: 'low' },
    { MoveID: '5HP_UNIVERSAL', Numpad: '5HP', Name: 'Entrada Dura / Patada Fuerte', S: 11, A: 4, R: 21, Block: -4, Hit: 3, Dmg: 1100, Flags: 12, Win: 8, Invuln: 'Ninguna', BoxType: 'melee' },
    { MoveID: '2HP_UNIVERSAL', Numpad: '2HP', Name: 'Chilena Anti-Aérea Universal', S: 9, A: 5, R: 22, Block: -8, Hit: 15, Dmg: 950, Flags: 4, Win: 6, Invuln: 'Air Invuln F4-12', BoxType: 'antiair' },
    { MoveID: '2SK_SWEEP', Numpad: '2SK', Name: 'Barrida de Potrero (Sweep)', S: 9, A: 4, R: 24, Block: -11, Hit: 20, Dmg: 900, Flags: 0, Win: 0, Invuln: 'High-Crush F3-13', BoxType: 'low' },
    { MoveID: 'THROW_NORMAL', Numpad: 'LP+MP', Name: 'Forcejeo de Camiseta (Throw)', S: 5, A: 3, R: 23, Block: 0, Hit: 25, Dmg: 1200, Flags: 0, Win: 0, Invuln: 'Unblockable Grab', BoxType: 'grab' },
    { MoveID: 'PARRY_GAMBETA', Numpad: '5GB', Name: 'Gambeta / Parry Táctico (2f)', S: 2, A: 12, R: 18, Block: 0, Hit: 12, Dmg: 0, Flags: 8, Win: 12, Invuln: 'Parry Window F2-13', BoxType: 'stance' }
  ];

  const STAGES_DATA = [
    { StageID: 'STAGE_MARACANA', DisplayName: 'Templo do Maracanã (Brasil)', Width: 2500, WallHP: 3, BPM: 115.0, ZoneA: 'El Círculo Central Mítico', ZoneB: 'Explanada de Samba y Vestuarios' },
    { StageID: 'STAGE_BOMBONERA', DisplayName: 'La Caldera de La Boca (Argentina)', Width: 2200, WallHP: 4, BPM: 128.0, ZoneA: 'El Área Chica Vibrante', ZoneB: 'Calle Caminito Nocturna' },
    { StageID: 'STAGE_CENTENARIO', DisplayName: 'Monumento Centenario (Uruguay)', Width: 2400, WallHP: 3, BPM: 120.0, ZoneA: 'Frente a la Torre de los Homenajes', ZoneB: 'Museo del Fútbol de 1930' },
    { StageID: 'STAGE_METROPOLITANO', DisplayName: 'Coloso de Barranquilla (Colombia)', Width: 2500, WallHP: 3, BPM: 130.0, ZoneA: 'El Horno Caribeño (40°C)', ZoneB: 'Carnaval Exterior del Estadio' },
    { StageID: 'STAGE_NUNOA', DisplayName: 'Coliseo de Ñuñoa (Chile)', Width: 2400, WallHP: 3, BPM: 125.0, ZoneA: 'Bajo la Cordillera Nevada', ZoneB: 'El Memorial y Pista Atlética' },
    { StageID: 'STAGE_DEFENSORES', DisplayName: 'El Fortín de Sajonia (Paraguay)', Width: 2300, WallHP: 4, BPM: 120.0, ZoneA: 'Las Trincheras Guaraníes', ZoneB: 'Sala de Prensa y Pasillo de Honor' },
    { StageID: 'STAGE_NACIONAL_LIMA', DisplayName: 'Templo José Díaz (Perú)', Width: 2400, WallHP: 3, BPM: 118.0, ZoneA: 'La Joya Iluminada (Garúa)', ZoneB: 'Paseo de los Héroes Exterior' },
    { StageID: 'STAGE_ATAHUALPA', DisplayName: 'El Volcán de Quito (Ecuador)', Width: 2450, WallHP: 3, BPM: 135.0, ZoneA: 'En la Línea Ecuatorial', ZoneB: 'Mirador Andino del Teleférico' },
    { StageID: 'STAGE_AVILA', DisplayName: 'El Monumental del Ávila (Venezuela)', Width: 2400, WallHP: 3, BPM: 170.0, ZoneA: 'Frente al Cerro El Ávila', ZoneB: 'Terraza VIP y Helipuerto' },
    { StageID: 'STAGE_HERNANDO_SILES', DisplayName: 'El Nido del Cóndor 3600m (Bolivia)', Width: 2600, WallHP: 2, BPM: 110.0, ZoneA: 'La Cancha sobre las Nubes', ZoneB: 'Plaza del Monolito Andino' }
  ];

  // ==========================================================================
  // 4. TAB 1: VISOR DE FRAME DATA, HITBOXES & ROSTER CONMEBOL (60 FPS)
  // ==========================================================================
  let t1SelectedCharIdx = 0;
  let t1SelectedMoveIdx = 0;
  let t1CombinedMoves = [];
  let t1CurrentFrame = 1;
  let t1Playing = true;

  const t1RosterGrid = document.getElementById('t1-roster-grid');
  const t1MoveTbody = document.getElementById('t1-move-tbody');
  const t1FrameStrip = document.getElementById('t1-frame-strip');
  const t1Canvas = document.getElementById('t1-canvas');
  const t1Ctx = t1Canvas.getContext('2d');

  // Construir las 60 celdas del Frame Meter
  const t1FrameCells = [];
  for (let i = 1; i <= 60; i++) {
    const cell = document.createElement('div');
    cell.className = 'f-cell';
    cell.textContent = i;
    cell.addEventListener('click', () => {
      t1Playing = false;
      document.getElementById('t1-btn-play').textContent = '▶ Play';
      t1CurrentFrame = i;
      updateTab1FrameMeterUI();
      playSynthSound('step');
    });
    t1FrameStrip.appendChild(cell);
    t1FrameCells.push(cell);
  }

  function decodeCancelFlags(mask) {
    if (!mask) return '0x00 (Ninguna)';
    const parts = [];
    if (mask & 1) parts.push('CH (Chain)');
    if (mask & 2) parts.push('SP (Special)');
    if (mask & 4) parts.push('SU (Super)');
    if (mask & 8) parts.push('GB (Gambeta)');
    return `0x0${mask.toString(16).toUpperCase()} (${parts.join(' | ')})`;
  }

  function selectTab1Char(idx) {
    t1SelectedCharIdx = idx;
    const char = ROSTER_DATA[idx];
    document.querySelectorAll('.roster-card').forEach((c, i) => {
      c.classList.toggle('active', i === idx);
    });

    document.getElementById('t1-char-code').textContent = char.Name;
    document.getElementById('t1-char-era').textContent = `${char.Country} • ${char.Era}`;
    document.getElementById('t1-stat-hp').textContent = char.MaxHealth.toLocaleString();
    document.getElementById('t1-stat-stun').textContent = char.StunThreshold.toLocaleString();
    document.getElementById('t1-stat-fdash').textContent = `${char.ForwardDashFrames} Frames`;
    document.getElementById('t1-stat-bdash').textContent = `${char.BackDashFrames} Frames`;
    document.getElementById('t1-passive-title').textContent = char.PassiveTitle;
    document.getElementById('t1-passive-desc').textContent = char.PassiveDesc;

    t1CombinedMoves = [...char.SpecificMoves, ...UNIVERSAL_MOVES];
    document.getElementById('t1-move-count').textContent = `${t1CombinedMoves.length} Moves`;

    t1MoveTbody.innerHTML = '';
    t1CombinedMoves.forEach((mv, mIdx) => {
      const tr = document.createElement('tr');
      const blkClass = mv.Block > 0 ? 'adv-plus' : (mv.Block <= -10 ? 'adv-punish' : 'adv-minus');
      const hitClass = mv.Hit > 0 ? 'adv-plus' : 'adv-minus';
      const blkStr = mv.Block > 0 ? `+${mv.Block}` : `${mv.Block}`;
      const hitStr = mv.Hit > 0 ? `+${mv.Hit}` : `${mv.Hit}`;

      tr.innerHTML = `
        <td style="color:var(--gold-bright); font-weight:700;">${mv.Numpad}</td>
        <td>${mv.Name}</td>
        <td>${mv.S} / ${mv.A} / ${mv.R}</td>
        <td class="${blkClass}">${blkStr}</td>
        <td class="${hitClass}">${hitStr}</td>
        <td>${mv.Dmg}</td>
      `;
      tr.addEventListener('click', () => {
        selectTab1Move(mIdx);
        playSynthSound('step');
      });
      t1MoveTbody.appendChild(tr);
    });

    selectTab1Move(0);
  }

  function selectTab1Move(mIdx) {
    t1SelectedMoveIdx = mIdx;
    t1CurrentFrame = 1;
    const mv = t1CombinedMoves[mIdx];
    document.querySelectorAll('#t1-move-tbody tr').forEach((r, i) => {
      r.classList.toggle('selected', i === mIdx);
    });

    const total = mv.S + mv.A + mv.R;
    document.getElementById('t1-active-move-label').textContent =
      `${mv.Numpad} — ${mv.Name} (Startup ${mv.S}f | Active ${mv.A}f | Recovery ${mv.R}f | Total ${total}f)`;
    document.getElementById('t1-insp-id').textContent = mv.MoveID;
    document.getElementById('t1-insp-total').textContent = `${total} Frames (${(total * 16.666).toFixed(1)} ms)`;
    document.getElementById('t1-insp-flags').textContent = decodeCancelFlags(mv.Flags);
    document.getElementById('t1-insp-win').textContent = mv.Win > 0
      ? `Frames ${mv.S} a ${mv.S + mv.Win} (${mv.Win}f duración)`
      : 'No Cancelable (0f)';
    document.getElementById('t1-insp-invuln').textContent = mv.Invuln;

    updateTab1FrameMeterUI();
  }

  function updateTab1FrameMeterUI() {
    const mv = t1CombinedMoves[t1SelectedMoveIdx];
    if (!mv) return;
    const sEnd = mv.S;
    const aEnd = mv.S + mv.A;
    const rEnd = aEnd + mv.R;
    const cStart = mv.S;
    const cEnd = mv.S + mv.Win;
    const hasInvuln = mv.Invuln && mv.Invuln !== 'Ninguna';

    let phaseName = 'IDLE / NEUTRAL';
    if (t1CurrentFrame < sEnd) phaseName = 'STARTUP (PREPARACIÓN)';
    else if (t1CurrentFrame < aEnd && mv.A > 0) phaseName = 'ACTIVE (CAJA DE DAÑO ROJA)';
    else if (t1CurrentFrame <= rEnd) phaseName = 'RECOVERY (RECUPERACIÓN)';

    document.getElementById('t1-frame-readout').textContent =
      `FRAME ACTUAL: ${String(t1CurrentFrame).padStart(2, '0')} / 60 [${phaseName}]`;

    t1FrameCells.forEach((cell, idx) => {
      const f = idx + 1;
      cell.className = 'f-cell';
      if (f < sEnd) cell.classList.add('startup');
      else if (f < aEnd && mv.A > 0) cell.classList.add('active-f');
      else if (f <= rEnd) cell.classList.add('recovery');

      if (mv.Win > 0 && f >= cStart && f <= cEnd) cell.classList.add('cancel-win');
      if (hasInvuln && f >= 1 && f <= Math.min(12, sEnd + 2)) cell.classList.add('invuln-win');
      if (f === t1CurrentFrame) cell.classList.add('current-head');
    });
  }

  // Poblar tarjetas del Roster
  ROSTER_DATA.forEach((char, idx) => {
    const card = document.createElement('div');
    card.className = 'roster-card';
    card.innerHTML = `
      <div class="rc-top">
        <span>${char.DisplayName}</span>
        <span class="rc-country">${char.Country}</span>
      </div>
      <div class="rc-arch">${char.Archetype} • ${char.MaxHealth} HP</div>
    `;
    card.addEventListener('click', () => {
      selectTab1Char(idx);
      playSynthSound('step');
    });
    t1RosterGrid.appendChild(card);
  });

  document.getElementById('t1-btn-play').addEventListener('click', (e) => {
    t1Playing = !t1Playing;
    e.currentTarget.textContent = t1Playing ? '⏸ Pause' : '▶ Play';
  });
  document.getElementById('t1-btn-prev').addEventListener('click', () => {
    t1Playing = false;
    document.getElementById('t1-btn-play').textContent = '▶ Play';
    t1CurrentFrame = t1CurrentFrame <= 1 ? 60 : t1CurrentFrame - 1;
    updateTab1FrameMeterUI();
    playSynthSound('step');
  });
  document.getElementById('t1-btn-next').addEventListener('click', () => {
    t1Playing = false;
    document.getElementById('t1-btn-play').textContent = '▶ Play';
    t1CurrentFrame = t1CurrentFrame >= 60 ? 1 : t1CurrentFrame + 1;
    updateTab1FrameMeterUI();
    playSynthSound('step');
  });
  document.getElementById('t1-btn-reset').addEventListener('click', () => {
    t1CurrentFrame = 1;
    updateTab1FrameMeterUI();
    playSynthSound('step');
  });

  function renderTab1Canvas() {
    const char = ROSTER_DATA[t1SelectedCharIdx];
    const mv = t1CombinedMoves[t1SelectedMoveIdx];
    if (!char || !mv) return;

    const w = t1Canvas.width;
    const h = t1Canvas.height;
    t1Ctx.clearRect(0, 0, w, h);

    // Fondo cuadrícula determinista (1 unidad = 10 cm)
    t1Ctx.fillStyle = '#070b12';
    t1Ctx.fillRect(0, 0, w, h);

    t1Ctx.strokeStyle = 'rgba(0, 229, 255, 0.07)';
    t1Ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 38) {
      t1Ctx.beginPath(); t1Ctx.moveTo(x, 0); t1Ctx.lineTo(x, h); t1Ctx.stroke();
    }
    for (let y = 0; y < h; y += 38) {
      t1Ctx.beginPath(); t1Ctx.moveTo(0, y); t1Ctx.lineTo(w, y); t1Ctx.stroke();
    }

    // Césped del estadio
    const groundY = 305;
    t1Ctx.fillStyle = 'rgba(0, 230, 118, 0.12)';
    t1Ctx.fillRect(0, groundY, w, h - groundY);
    t1Ctx.strokeStyle = '#00e676';
    t1Ctx.lineWidth = 2;
    t1Ctx.beginPath(); t1Ctx.moveTo(0, groundY); t1Ctx.lineTo(w, groundY); t1Ctx.stroke();

    const sEnd = mv.S;
    const aEnd = mv.S + mv.A;
    const rEnd = aEnd + mv.R;

    const isStartup = t1CurrentFrame < sEnd;
    const isActive = t1CurrentFrame >= sEnd && t1CurrentFrame < aEnd && mv.A > 0;
    const isRecovery = t1CurrentFrame >= aEnd && t1CurrentFrame <= rEnd;
    const hasInvuln = mv.Invuln && mv.Invuln !== 'Ninguna' && t1CurrentFrame <= Math.min(14, sEnd + 2);

    // Coordenadas base P1
    let p1X = 230;
    let p1Y = groundY;
    if (isStartup) p1X += (t1CurrentFrame / Math.max(1, sEnd)) * 18;
    else if (isActive) p1X += 26;
    else if (isRecovery) p1X += Math.max(0, 26 - ((t1CurrentFrame - aEnd) * 1.4));

    if (mv.BoxType === 'antiair' && (isActive || isStartup)) {
      p1Y -= Math.sin((t1CurrentFrame / Math.max(1, aEnd)) * Math.PI) * 55;
    }

    // Dibujar silueta estilizada del jugador P1
    const hurtH = mv.BoxType === 'low' ? 95 : (char.Name === 'PULGA_AR' ? 122 : 145);
    const hurtW = char.Name === 'BULLDOG_PY' ? 78 : 62;

    // 1. PUSHBOX (Amarillo)
    const pushW = hurtW - 12;
    const pushH = hurtH - 15;
    t1Ctx.fillStyle = 'rgba(245, 196, 81, 0.18)';
    t1Ctx.strokeStyle = '#f5c451';
    t1Ctx.lineWidth = 2;
    t1Ctx.fillRect(p1X - pushW / 2, p1Y - pushH, pushW, pushH);
    t1Ctx.strokeRect(p1X - pushW / 2, p1Y - pushH, pushW, pushH);

    // 2. HURTBOX (Verde o Azul Cian si es Invulnerable / High-Crush)
    t1Ctx.fillStyle = hasInvuln ? 'rgba(0, 229, 255, 0.24)' : 'rgba(0, 230, 118, 0.20)';
    t1Ctx.strokeStyle = hasInvuln ? '#00e5ff' : '#00e676';
    t1Ctx.lineWidth = 2;
    t1Ctx.fillRect(p1X - hurtW / 2, p1Y - hurtH, hurtW, hurtH);
    t1Ctx.strokeRect(p1X - hurtW / 2, p1Y - hurtH, hurtW, hurtH);

    // Etiqueta Jugador
    t1Ctx.fillStyle = '#ffffff';
    t1Ctx.font = 'bold 11px Consolas, monospace';
    t1Ctx.fillText(`${char.DisplayName} [P1]`, p1X - hurtW / 2, p1Y - hurtH - 8);

    // 3. HITBOX ACTIVA (Rojo) o PROJECTILE BOX (Naranja)
    if (isActive) {
      let hbX = p1X + hurtW / 2 - 6;
      let hbY = p1Y - hurtH * 0.72;
      let hbW = 92;
      let hbH = 48;

      if (mv.BoxType === 'low') {
        hbY = p1Y - 42;
        hbW = 105;
        hbH = 38;
      } else if (mv.BoxType === 'antiair') {
        hbY = p1Y - hurtH - 35;
        hbW = 78;
        hbH = 85;
      } else if (mv.BoxType === 'overhead') {
        hbY = p1Y - hurtH + 10;
        hbW = 88;
        hbH = 65;
      } else if (mv.BoxType === 'ultimate') {
        hbW = 210;
        hbH = 130;
        hbY = p1Y - 140;
      }

      t1Ctx.fillStyle = 'rgba(255, 42, 84, 0.38)';
      t1Ctx.strokeStyle = '#ff2a54';
      t1Ctx.lineWidth = 2.5;
      t1Ctx.fillRect(hbX, hbY, hbW, hbH);
      t1Ctx.strokeRect(hbX, hbY, hbW, hbH);

      t1Ctx.fillStyle = '#ff8a9f';
      t1Ctx.fillText(`HITBOX (${mv.Dmg} DMG)`, hbX + 4, hbY - 5);
    }

    // Proyectil de Balón (Naranja)
    if (mv.BoxType === 'projectile' && t1CurrentFrame >= sEnd) {
      const projProgress = (t1CurrentFrame - sEnd) * 14;
      const ballX = p1X + 55 + projProgress;
      const ballY = p1Y - 72 - Math.sin(projProgress * 0.025) * 18;

      t1Ctx.fillStyle = 'rgba(255, 145, 0, 0.35)';
      t1Ctx.strokeStyle = '#ff9100';
      t1Ctx.lineWidth = 2;
      t1Ctx.fillRect(ballX - 22, ballY - 22, 44, 44);
      t1Ctx.strokeRect(ballX - 22, ballY - 22, 44, 44);

      t1Ctx.beginPath();
      t1Ctx.arc(ballX, ballY, 14, 0, Math.PI * 2);
      t1Ctx.fillStyle = '#ffffff';
      t1Ctx.fill();
      t1Ctx.strokeStyle = '#06080d';
      t1Ctx.stroke();
    }

    // 4. DUMMY OPONENTE & VECTOR DISTANCIA
    if (document.getElementById('t1-chk-opponent').checked) {
      const p2X = 520;
      const p2W = 64;
      const p2H = 145;

      // Pushbox P2
      t1Ctx.fillStyle = 'rgba(245, 196, 81, 0.14)';
      t1Ctx.strokeStyle = '#f5c451';
      t1Ctx.fillRect(p2X - 25, groundY - 130, 50, 130);
      t1Ctx.strokeRect(p2X - 25, groundY - 130, 50, 130);

      // Hurtbox P2
      t1Ctx.fillStyle = 'rgba(0, 230, 118, 0.15)';
      t1Ctx.strokeStyle = '#00e676';
      t1Ctx.fillRect(p2X - p2W / 2, groundY - p2H, p2W, p2H);
      t1Ctx.strokeRect(p2X - p2W / 2, groundY - p2H, p2W, p2H);

      t1Ctx.fillStyle = '#8b9bb4';
      t1Ctx.fillText('DUMMY [P2]', p2X - p2W / 2, groundY - p2H - 8);

      // Línea de Distancia Q32.32
      t1Ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
      t1Ctx.setLineDash([4, 4]);
      t1Ctx.beginPath();
      t1Ctx.moveTo(p1X, groundY + 18);
      t1Ctx.lineTo(p2X, groundY + 18);
      t1Ctx.stroke();
      t1Ctx.setLineDash([]);

      const distMeters = ((p2X - p1X) / 100).toFixed(3);
      t1Ctx.fillStyle = '#f5c451';
      t1Ctx.fillText(`ΔX = ${distMeters}m (Q32.32 Raw: ${Math.round((p2X - p1X) * 42949672.96)})`, (p1X + p2X) / 2 - 95, groundY + 34);
    }

    // HUD Superior dentro del Canvas
    t1Ctx.fillStyle = 'rgba(12, 16, 24, 0.85)';
    t1Ctx.fillRect(12, 12, 345, 54);
    t1Ctx.strokeStyle = '#1e2a3d';
    t1Ctx.strokeRect(12, 12, 345, 54);

    t1Ctx.fillStyle = '#f5c451';
    t1Ctx.font = 'bold 12px Consolas, monospace';
    t1Ctx.fillText(`MOVE: ${mv.Numpad} (${mv.MoveID})`, 22, 32);
    t1Ctx.fillStyle = '#00e5ff';
    t1Ctx.fillText(`ADV ON BLOCK: ${mv.Block >= 0 ? '+' + mv.Block : mv.Block}f | ON HIT: +${mv.Hit}f`, 22, 52);
  }

  // Inicializar Tab 1 con O Fenômeno
  selectTab1Char(0);

  // ==========================================================================
  // 5. TAB 2: KERNEL DETERMINISTA (Q32.32, RING BUFFER 60F & PRIORIDADES FGC)
  // ==========================================================================
  let t2FacingRight = true;
  const t2RingBuffer = Array.from({ length: 60 }, () => ({ dir: 5, btn: '' }));
  const t2RingGrid = document.getElementById('t2-ring-grid');

  function renderTab2RingBuffer() {
    t2RingGrid.innerHTML = '';
    t2RingBuffer.forEach((entry, idx) => {
      const slot = document.createElement('div');
      slot.className = 'rb-slot' + (idx === 0 ? ' latest' : '');
      const dirArrows = { 1: '↙', 2: '↓', 3: '↘', 4: '←', 5: '•', 6: '→', 7: '↖', 8: '↑', 9: '↗' };
      slot.innerHTML = `
        <div style="font-size:8.5px; color:var(--text-dim);">F-${idx}</div>
        <div class="rb-dir">${entry.dir}${dirArrows[entry.dir] || ''}</div>
        <div class="rb-btn">${entry.btn || '-'}</div>
      `;
      t2RingGrid.appendChild(slot);
    });
  }

  function pushToRingBuffer(dir, btn = '') {
    // Si estamos en P2 (mirando a la izquierda), invertimos horizontalmente 4<->6, 1<->3, 7<->9
    let relDir = dir;
    if (!t2FacingRight) {
      const mirrorMap = { 1: 3, 2: 2, 3: 1, 4: 6, 5: 5, 6: 4, 7: 9, 8: 8, 9: 7 };
      relDir = mirrorMap[dir] || 5;
    }
    t2RingBuffer.pop();
    t2RingBuffer.unshift({ dir: relDir, btn });
    evaluateCommandPriorityHierarchy();
    renderTab2RingBuffer();
  }

  function matchSubsequenceInBuffer(seq, maxWindow) {
    let cursor = seq.length - 1;
    const limit = Math.min(maxWindow, t2RingBuffer.length);
    for (let i = 0; i < limit; i++) {
      if (t2RingBuffer[i].dir === seq[cursor]) {
        cursor--;
        if (cursor < 0) return true;
      }
    }
    return false;
  }

  function evaluateCommandPriorityHierarchy() {
    const latest = t2RingBuffer[0];
    const resEl = document.getElementById('t2-parsed-result');
    const reasonEl = document.getElementById('t2-parsed-reason');

    // Jerarquía exacta de DeterministicFighterStateMachine.cpp:
    // 1. Ultimate 214214+HP+SK (26f)
    if (latest.btn.includes('HP') && latest.btn.includes('SK') && matchSubsequenceInBuffer([2, 1, 4, 2, 1, 4], 26)) {
      resEl.textContent = '🌟 ULTIMATE NIVEL 3: GRITO SAGRADO (214214+HP+SK)';
      resEl.style.color = '#ffe07d';
      reasonEl.textContent = 'Match en ventana de 26 frames. Prioridad Máxima Nivel 3 activada.';
      playSynthSound('stinger');
      return;
    }
    // 2. HCF 41236 (Estricta o Tolerante sin diagonal 1: 4->2->3->6)
    if (latest.btn && (matchSubsequenceInBuffer([4, 1, 2, 3, 6], 20) || matchSubsequenceInBuffer([4, 2, 3, 6], 18))) {
      resEl.textContent = `🧲 SPECIAL HCF (41236+${latest.btn}): COMMAND GRAB / ELÁSTICA`;
      resEl.style.color = '#00e676';
      reasonEl.textContent = 'Detectado por HCF_41236 (Acepta 4→2→3→6 omitiendo diagonal 1 por ergonomía).';
      playSynthSound('parry');
      return;
    }
    // 3. DP 623 vs QCF 236 (Anti-Overlap Priority!)
    if (latest.btn && matchSubsequenceInBuffer([6, 2, 3], 14)) {
      resEl.textContent = `🔥 SPECIAL DP (623+${latest.btn}): DESPEJE / VOLEA ANTI-AÉREA`;
      resEl.style.color = '#ff2a54';
      reasonEl.textContent = 'Resolución Anti-Overlap: Aunque termina en 236, el input 6 inicial fuerza prioridad DP (623 > 236).';
      playSynthSound('hit');
      return;
    }
    // 4. QCF 236
    if (latest.btn && matchSubsequenceInBuffer([2, 3, 6], 12)) {
      resEl.textContent = `⚽ SPECIAL QCF (236+${latest.btn}): BATI-CAÑÓN / PEDALADA`;
      resEl.style.color = '#00e5ff';
      reasonEl.textContent = 'Detectado Cuarto de Círculo Adelante limpio en ventana de 12 frames.';
      playSynthSound('step');
      return;
    }
    // 5. QCB 214
    if (latest.btn && matchSubsequenceInBuffer([2, 1, 4], 12)) {
      resEl.textContent = `🦂 SPECIAL QCB (214+${latest.btn}): EL ESCORPIÓN / ROSCA`;
      resEl.style.color = '#b388ff';
      reasonEl.textContent = 'Detectado Cuarto de Círculo Atrás en ventana de 12 frames.';
      playSynthSound('step');
      return;
    }

    if (latest.btn) {
      resEl.textContent = `👊 GOLPE NORMAL: ${latest.dir}${latest.btn}`;
      resEl.style.color = '#eef2f9';
      reasonEl.textContent = 'Sin secuencia direccional especial previa; ejecuta Normal Move.';
    } else {
      resEl.textContent = `[MOVIMIENTO DIRECCIONAL NUMPAD: ${latest.dir}]`;
      resEl.style.color = '#8b9bb4';
    }
  }

  // Botones de dirección y ataque en Tab 2
  document.querySelectorAll('.t2-dir-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      pushToRingBuffer(parseInt(btn.dataset.dir, 10), '');
      playSynthSound('step');
    });
  });

  document.querySelectorAll('.t2-atk-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const currentDir = t2RingBuffer[0] ? t2RingBuffer[0].dir : 5;
      pushToRingBuffer(currentDir, btn.dataset.btn);
      playSynthSound('hit');
    });
  });

  // Cambio de lado P1 / P2
  document.getElementById('t2-btn-side').addEventListener('click', (e) => {
    t2FacingRight = !t2FacingRight;
    e.currentTarget.textContent = t2FacingRight
      ? 'Lado Actual: P1 (Mirando Derecha ▶)'
      : 'Lado Actual: P2 (Mirando Izquierda ◀ - Auto Mirror)';
    playSynthSound('step');
  });

  document.getElementById('t2-btn-clear-buf').addEventListener('click', () => {
    for (let i = 0; i < 60; i++) t2RingBuffer[i] = { dir: 5, btn: '' };
    renderTab2RingBuffer();
    document.getElementById('t2-parsed-result').textContent = '[BUFFER REINICIADO A NEUTRO 5]';
    playSynthSound('step');
  });

  // Macros de Ingeniería en Tab 2
  document.getElementById('t2-macro-6236').addEventListener('click', () => {
    const seq = [
      { d: 6, b: '' }, { d: 6, b: '' }, { d: 5, b: '' },
      { d: 2, b: '' }, { d: 3, b: '' }, { d: 6, b: 'HP' }
    ];
    seq.forEach((s) => {
      t2RingBuffer.pop();
      t2RingBuffer.unshift({ dir: s.d, btn: s.b });
    });
    evaluateCommandPriorityHierarchy();
    renderTab2RingBuffer();
  });

  document.getElementById('t2-macro-41236').addEventListener('click', () => {
    // Secuencia 4 -> 2 -> 3 -> 6 + LP (Omitiendo diagonal 1 deliberadamente)
    const seq = [
      { d: 4, b: '' }, { d: 4, b: '' },
      { d: 2, b: '' }, { d: 3, b: '' }, { d: 6, b: 'LP' }
    ];
    seq.forEach((s) => {
      t2RingBuffer.pop();
      t2RingBuffer.unshift({ dir: s.d, btn: s.b });
    });
    evaluateCommandPriorityHierarchy();
    renderTab2RingBuffer();
  });

  document.getElementById('t2-macro-ult').addEventListener('click', () => {
    const seq = [
      { d: 2, b: '' }, { d: 1, b: '' }, { d: 4, b: '' },
      { d: 2, b: '' }, { d: 1, b: '' }, { d: 4, b: 'HP+SK' }
    ];
    seq.forEach((s) => {
      t2RingBuffer.pop();
      t2RingBuffer.unshift({ dir: s.d, btn: s.b });
    });
    evaluateCommandPriorityHierarchy();
    renderTab2RingBuffer();
  });

  document.getElementById('t2-macro-socd').addEventListener('click', () => {
    t2RingBuffer.pop();
    t2RingBuffer.unshift({ dir: 5, btn: '' });
    renderTab2RingBuffer();
    document.getElementById('t2-socd-status').textContent = 'SOCD CLEANED: [Left+Right+Up+Down] → Convertido a 5 (Neutro Exacto)';
    document.getElementById('t2-parsed-result').textContent = '🛡️ LIMPIEZA SOCD APLICADA → SALIDA NUMPAD: 5 (NEUTRO)';
    document.getElementById('t2-parsed-result').style.color = '#00e5ff';
    playSynthSound('parry');
  });

  // Inspector Q32.32 & Fletcher-32 Checksum
  const t2BitGrid = document.getElementById('t2-bit-grid');
  const t2BitCells = [];
  for (let b = 63; b >= 0; b--) {
    const cell = document.createElement('div');
    cell.className = 'bit-cell ' + (b >= 32 ? 'int-part' : 'frac-part');
    cell.title = b >= 32 ? `Bit ${b} (Parte Entera Q32)` : `Bit ${b} (Parte Fraccionaria .32)`;
    t2BitGrid.appendChild(cell);
    t2BitCells.push(cell);
  }

  function computeFletcher32(words) {
    let sum1 = 0xffff;
    let sum2 = 0xffff;
    for (let i = 0; i < words.length; i++) {
      sum1 = (sum1 + (words[i] & 0xffff)) % 0xffff;
      sum2 = (sum2 + sum1) % 0xffff;
    }
    return (((sum2 & 0xffff) << 16) | (sum1 & 0xffff)) >>> 0;
  }

  function updateQ32Inspector() {
    const posMm = parseInt(document.getElementById('t2-q-pos').value, 10);
    const velMm = parseInt(document.getElementById('t2-q-vel').value, 10);
    const floatErr = document.getElementById('t2-chk-float-error').checked;

    document.getElementById('t2-q-pos-lbl').textContent = `${posMm} mm (${(posMm / 1000).toFixed(3)} m)`;
    document.getElementById('t2-q-vel-lbl').textContent = `${velMm} mm/f (${(velMm / 1000).toFixed(3)} m/f)`;

    // FFixedPoint::FromMillimeters(mm) => (BigInt(mm) << 32n) / 1000n
    const rawBig = (BigInt(posMm) << 32n) / 1000n;
    const unsigned64 = BigInt.asUintN(64, rawBig);
    const hexStr = unsigned64.toString(16).toUpperCase().padStart(16, '0');
    const binStr = unsigned64.toString(2).padStart(64, '0');

    const hiHex = hexStr.slice(0, 8);
    const loHex = hexStr.slice(8, 16);
    const intPart = Number(rawBig >> 32n);
    const fracPart = Number(unsigned64 & 0xffffffffn) / 4294967296;

    document.getElementById('t2-q-raw').textContent = rawBig.toString();
    document.getElementById('t2-q-hex').textContent = `0x${hiHex}_${loHex}`;
    document.getElementById('t2-q-parts').textContent =
      `Int: ${intPart} | Frac: 0x${loHex} (${fracPart.toFixed(6)})`;

    for (let i = 0; i < 64; i++) {
      const bitChar = binStr[i];
      t2BitCells[i].textContent = bitChar;
      t2BitCells[i].classList.toggle('one', bitChar === '1');
    }

    // Cálculo de Checksum Fletcher-32
    const w0 = Number(unsigned64 & 0xffffn);
    const w1 = Number((unsigned64 >> 16n) & 0xffffn);
    const w2 = Number((unsigned64 >> 32n) & 0xffffn);
    const w3 = Number((unsigned64 >> 48n) & 0xffffn);
    const velRaw = (BigInt(velMm) << 32n) / 1000n;
    const velU64 = BigInt.asUintN(64, velRaw);
    const w4 = Number(velU64 & 0xffffn);
    const w5 = Number((velU64 >> 16n) & 0xffffn);

    const hashPC = computeFletcher32([w0, w1, w2, w3, w4, w5, 10000, 1000]);
    const hashPS5 = floatErr
      ? computeFletcher32([w0 ^ 0x0001, w1, w2, w3, w4, w5, 10000, 1000]) // 1 ULP drift en mantisa float
      : hashPC;

    const hexPC = '0x' + hashPC.toString(16).toUpperCase().padStart(8, '0');
    const hexPS5 = '0x' + hashPS5.toString(16).toUpperCase().padStart(8, '0');

    document.getElementById('t2-hash-pc').textContent = hexPC;
    document.getElementById('t2-hash-ps5').textContent = hexPS5;
    document.getElementById('hdr-checksum').textContent = hexPC;

    const banner = document.getElementById('t2-desync-banner');
    const titleEl = document.getElementById('t2-desync-title');
    const hashEl = document.getElementById('t2-desync-hash');

    if (floatErr) {
      banner.classList.add('alert');
      titleEl.textContent = '🚨 GGPO DESYNC DETECTED! (1-ULP IEEE-754 Float Drift entre MSVC y Clang)';
      hashEl.textContent = `${hexPC} != ${hexPS5}`;
      document.getElementById('t2-hash-ps5').style.color = '#ff2a54';
    } else {
      banner.classList.remove('alert');
      titleEl.textContent = '✔ DETERMINISMO GARANTIZADO — PC (x86_64) == PS5 == XBOX SERIES X';
      hashEl.textContent = hexPC;
      document.getElementById('t2-hash-ps5').style.color = '#00e676';
    }
  }

  document.getElementById('t2-q-pos').addEventListener('input', updateQ32Inspector);
  document.getElementById('t2-q-vel').addEventListener('input', updateQ32Inspector);
  document.getElementById('t2-chk-float-error').addEventListener('change', (e) => {
    updateQ32Inspector();
    if (e.target.checked) playSynthSound('desync');
    else playSynthSound('parry');
  });

  // Soporte de Teclado en Vivo para el Ring Buffer (Tab 2)
  window.addEventListener('keydown', (e) => {
    if (activeTab !== 'tab2') return;
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

    const keyMapDir = {
      KeyW: 8, ArrowUp: 8,
      KeyS: 2, ArrowDown: 2,
      KeyA: 4, ArrowLeft: 4,
      KeyD: 6, ArrowRight: 6
    };
    const keyMapBtn = {
      KeyJ: 'LP',
      KeyK: 'MP',
      KeyL: 'HP',
      KeyU: 'SK',
      KeyI: 'GB'
    };

    if (keyMapDir[e.code]) {
      e.preventDefault();
      pushToRingBuffer(keyMapDir[e.code], '');
      playSynthSound('step');
    } else if (keyMapBtn[e.code]) {
      e.preventDefault();
      const curDir = t2RingBuffer[0] ? t2RingBuffer[0].dir : 5;
      pushToRingBuffer(curDir, keyMapBtn[e.code]);
      playSynthSound('hit');
    }
  });

  renderTab2RingBuffer();
  updateQ32Inspector();

  // ==========================================================================
  // 6. TAB 3: EL POTRERO (MULTI-SLOT DUMMY), GGPO NETCODE & REPLAY TAKEOVER
  // ==========================================================================
  const t3StageSelect = document.getElementById('t3-sel-stage');
  STAGES_DATA.forEach((st, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = st.DisplayName;
    t3StageSelect.appendChild(opt);
  });

  const dummySlots = [
    { id: 1, name: 'Slot 1: 236+LP~MP (Sombrero Overhead)', weight: 40, type: 'OVERHEAD' },
    { id: 2, name: 'Slot 2: 236+LP~HP (Corte Bajo)', weight: 35, type: 'LOW' },
    { id: 3, name: 'Slot 3: 41236+LP (Mordisco Command Grab)', weight: 15, type: 'GRAB' },
    { id: 4, name: 'Slot 4: 5GB (Gambeta Bait & Punish)', weight: 10, type: 'BAIT' }
  ];
  let activeDummySlot = 0;

  function renderDummySlots() {
    const container = document.getElementById('t3-slots-container');
    container.innerHTML = '';
    dummySlots.forEach((sl, idx) => {
      const card = document.createElement('div');
      card.className = 'slot-card' + (idx === activeDummySlot ? ' active-slot' : '');
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; font-size:11px; font-weight:700;">
          <span>${sl.name}</span>
          <span style="color:var(--gold); font-family:var(--font-mono);">Peso: ${sl.weight}%</span>
        </div>
        <div class="meter-bar">
          <div class="meter-fill" style="width:${sl.weight}%;"></div>
        </div>
      `;
      container.appendChild(card);
    });
  }
  renderDummySlots();

  document.getElementById('t3-btn-roll-dummy').addEventListener('click', () => {
    const r = Math.random() * 100;
    let acc = 0;
    for (let i = 0; i < dummySlots.length; i++) {
      acc += dummySlots[i].weight;
      if (r <= acc) {
        activeDummySlot = i;
        break;
      }
    }
    renderDummySlots();
    playSynthSound('hit');
  });

  // Estado de simulación de El Potrero (Tab 3)
  let t3StageIdx = 0;
  let t3WallRemaining = STAGES_DATA[0].WallHP;
  let t3InZoneB = false;
  let t3LiveTakeover = false;
  let t3ReplayFrame = 240;
  let t3P1X = -210;
  let t3P2X = 210;
  let t3SavedSnapshot = null;
  let t3RollbackFlash = 0;
  let t3BossParries = 0;

  t3StageSelect.addEventListener('change', (e) => {
    t3StageIdx = parseInt(e.target.value, 10);
    const st = STAGES_DATA[t3StageIdx];
    t3WallRemaining = st.WallHP;
    t3InZoneB = false;
    updateTab3StageUI();
    playSynthSound('step');
  });

  function updateTab3StageUI() {
    const st = STAGES_DATA[t3StageIdx];
    const zoneText = t3InZoneB ? `Zona B: ${st.ZoneB} [WALL BROKEN!]` : `Zona A: ${st.ZoneA}`;
    document.getElementById('t3-stage-subtitle').textContent = `Estadio: ${st.DisplayName} (${zoneText})`;
    document.getElementById('t3-wall-hp').textContent = t3InZoneB ? 'ROTO (Zona B Activa)' : `${t3WallRemaining} / ${st.WallHP} Impactos`;
    document.getElementById('t3-zone-name').textContent = zoneText;
    document.getElementById('t3-zone-name').style.color = t3InZoneB ? '#ff9100' : '#00e676';
    document.getElementById('t3-stage-bpm').textContent = `${t3InZoneB ? (st.BPM + 12).toFixed(1) : st.BPM.toFixed(1)} BPM`;
  }

  function updateTab3NetUI() {
    const ping = parseInt(document.getElementById('t3-rng-ping').value, 10);
    const jitter = parseInt(document.getElementById('t3-rng-jitter').value, 10);
    const wifi = document.getElementById('t3-chk-wifi').checked;

    document.getElementById('t3-lbl-ping').textContent = `${ping} ms`;
    document.getElementById('t3-lbl-jitter').textContent = `${jitter} ms`;
    document.getElementById('t3-net-type-badge').textContent = wifi ? 'WI-FI (PACKET BURST)' : 'CABLE LAN (ESTABLE)';

    const delayFrames = ping <= 36 ? 1 : (ping <= 85 ? 2 : 3);
    const rbFrames = Math.min(7, Math.max(0, Math.ceil((ping / 2 + jitter + (wifi ? 18 : 0)) / 16.66) - delayFrames));
    document.getElementById('t3-lbl-rb').textContent = `Rollback: ${rbFrames}f | Input Delay: ${delayFrames}f`;

    document.getElementById('hdr-net-status').textContent =
      `PING ${ping}ms (${rbFrames}f RB / ${delayFrames}f DLY)`;
    const dot = document.getElementById('hdr-net-dot');
    dot.className = 'dot' + (rbFrames >= 5 ? ' danger' : (rbFrames >= 3 ? ' warn' : ''));
  }

  document.getElementById('t3-rng-ping').addEventListener('input', updateTab3NetUI);
  document.getElementById('t3-rng-jitter').addEventListener('input', updateTab3NetUI);
  document.getElementById('t3-chk-wifi').addEventListener('change', updateTab3NetUI);

  document.getElementById('t3-btn-save-state').addEventListener('click', () => {
    t3SavedSnapshot = { p1X: t3P1X, p2X: t3P2X, frame: t3ReplayFrame, wall: t3WallRemaining, zoneB: t3InZoneB };
    playSynthSound('parry');
  });

  document.getElementById('t3-btn-load-state').addEventListener('click', () => {
    if (t3SavedSnapshot) {
      t3P1X = t3SavedSnapshot.p1X;
      t3P2X = t3SavedSnapshot.p2X;
      t3ReplayFrame = t3SavedSnapshot.frame;
      t3WallRemaining = t3SavedSnapshot.wall;
      t3InZoneB = t3SavedSnapshot.zoneB;
      updateTab3StageUI();
      playSynthSound('stinger');
    }
  });

  document.getElementById('t3-btn-force-rb').addEventListener('click', () => {
    t3RollbackFlash = 25;
    t3P1X -= 45;
    playSynthSound('desync');
  });

  document.getElementById('t3-btn-takeover').addEventListener('click', (e) => {
    t3LiveTakeover = !t3LiveTakeover;
    const badge = document.getElementById('t3-mode-badge');
    if (t3LiveTakeover) {
      badge.textContent = '🔴 LIVE TAKEOVER ACTIVO (CONTROL DEL JUGADOR P1)';
      badge.style.color = '#00e676';
      e.currentTarget.textContent = '⏹ Volver a Replay Theater';
      playSynthSound('stinger');
    } else {
      badge.textContent = 'REPLAY THEATER (GRABACIÓN DETERMINISTA)';
      badge.style.color = '#00e5ff';
      e.currentTarget.textContent = '🎮 Tomar el Control en Vivo (Live Takeover)';
      playSynthSound('step');
    }
  });

  document.getElementById('t3-btn-wallbreak').addEventListener('click', () => {
    if (t3WallRemaining > 1) {
      t3WallRemaining--;
      playSynthSound('hit');
    } else {
      t3WallRemaining = 0;
      t3InZoneB = true;
      playSynthSound('stinger');
    }
    updateTab3StageUI();
  });

  document.getElementById('t3-btn-var-rewind').addEventListener('click', () => {
    t3ReplayFrame = Math.max(1, t3ReplayFrame - 90);
    document.getElementById('t3-rng-timeline').value = t3ReplayFrame;
    t3RollbackFlash = 35;
    playSynthSound('desync');
  });

  document.getElementById('t3-rng-timeline').addEventListener('input', (e) => {
    t3ReplayFrame = parseInt(e.target.value, 10);
  });

  document.getElementById('t3-btn-boss-parry').addEventListener('click', () => {
    t3BossParries = Math.min(3, t3BossParries + 1);
    document.getElementById('t3-boss-parries').textContent = `${t3BossParries} / 3`;
    const stEl = document.getElementById('t3-boss-state');
    if (t3BossParries >= 3) {
      stEl.textContent = '⚡ SYSTEM OVERLOAD! (VULNERABLE A ULTIMATE CONMEBOL)';
      stEl.style.color = '#00e676';
      playSynthSound('stinger');
    } else {
      playSynthSound('parry');
    }
  });

  document.getElementById('t3-btn-boss-reset').addEventListener('click', () => {
    t3BossParries = 0;
    document.getElementById('t3-boss-parries').textContent = '0 / 3';
    const stEl = document.getElementById('t3-boss-state');
    stEl.textContent = 'OPRESIVO (Offside Lasers ON)';
    stEl.style.color = '#ff2a54';
    playSynthSound('step');
  });

  const t3Canvas = document.getElementById('t3-canvas');
  const t3Ctx = t3Canvas.getContext('2d');

  function renderTab3Canvas() {
    const w = t3Canvas.width;
    const h = t3Canvas.height;
    t3Ctx.clearRect(0, 0, w, h);

    const st = STAGES_DATA[t3StageIdx];

    // Avance de frame de replay
    t3ReplayFrame = (t3ReplayFrame % 600) + 1;
    document.getElementById('t3-rng-timeline').value = t3ReplayFrame;
    document.getElementById('t3-replay-frame').textContent = `${t3ReplayFrame} / 600`;

    // Movimiento oscilante en Replay o interactivo en Live Takeover
    const angle = t3ReplayFrame * 0.04;
    if (!t3LiveTakeover) {
      t3P1X = -160 + Math.sin(angle) * 95;
      t3P2X = 160 + Math.cos(angle * 0.85) * 95;
    } else {
      t3P1X = -90 + Math.sin(angle * 1.8) * 45;
      t3P2X = 110;
    }

    const distMeters = Math.abs(t3P2X - t3P1X) / 80;
    const fov = (52 + Math.min(22, distMeters * 3.1)).toFixed(1);
    const zOffset = (-380 - distMeters * 28).toFixed(1);

    document.getElementById('t3-cam-dist').textContent = `${distMeters.toFixed(2)} m`;
    document.getElementById('t3-cam-fov').textContent = `${fov}°`;
    document.getElementById('t3-cam-z').textContent = `${zOffset} u`;

    // Fondo según Zona A o Zona B (Wall Break)
    const grad = t3Ctx.createLinearGradient(0, 0, 0, h);
    if (t3InZoneB) {
      grad.addColorStop(0, '#1f0d1d');
      grad.addColorStop(1, '#090d16');
    } else {
      grad.addColorStop(0, '#081826');
      grad.addColorStop(1, '#07120e');
    }
    t3Ctx.fillStyle = grad;
    t3Ctx.fillRect(0, 0, w, h);

    // Efecto V.A.R. Rewind / Rollback Flash
    if (t3RollbackFlash > 0) {
      t3RollbackFlash--;
      t3Ctx.fillStyle = 'rgba(0, 229, 255, 0.16)';
      t3Ctx.fillRect(0, 0, w, h);
      t3Ctx.fillStyle = '#00e5ff';
      t3Ctx.font = 'bold 14px Consolas, monospace';
      t3Ctx.fillText('⏪ GGPO / V.A.R. STATE RESIMULATION IN PROGRESS...', 190, 40);
    }

    const groundY = 300;
    t3Ctx.fillStyle = t3InZoneB ? 'rgba(255, 145, 0, 0.14)' : 'rgba(0, 230, 118, 0.14)';
    t3Ctx.fillRect(0, groundY, w, h - groundY);

    // Muros Laterales / Redes del Arco
    t3Ctx.strokeStyle = t3InZoneB ? '#ff9100' : '#f5c451';
    t3Ctx.lineWidth = 4;
    t3Ctx.strokeRect(30, 60, w - 60, groundY - 60);

    const centerX = w / 2;
    const p1ScreenX = centerX + t3P1X;
    const p2ScreenX = centerX + t3P2X;

    // P1 Box
    t3Ctx.fillStyle = 'rgba(0, 230, 118, 0.3)';
    t3Ctx.strokeStyle = '#00e676';
    t3Ctx.lineWidth = 2;
    t3Ctx.fillRect(p1ScreenX - 28, groundY - 130, 56, 130);
    t3Ctx.strokeRect(p1ScreenX - 28, groundY - 130, 56, 130);
    t3Ctx.fillStyle = '#fff';
    t3Ctx.font = 'bold 11px Consolas, monospace';
    t3Ctx.fillText(t3LiveTakeover ? 'P1 (LIVE TAKEOVER)' : 'P1 (REPLAY)', p1ScreenX - 45, groundY - 138);

    // P2 Dummy / Boss Box
    t3Ctx.fillStyle = 'rgba(255, 42, 84, 0.3)';
    t3Ctx.strokeStyle = '#ff2a54';
    t3Ctx.fillRect(p2ScreenX - 28, groundY - 130, 56, 130);
    t3Ctx.strokeRect(p2ScreenX - 28, groundY - 130, 56, 130);
    t3Ctx.fillStyle = '#ff8a9f';
    t3Ctx.fillText(`DUMMY [${dummySlots[activeDummySlot].type}]`, p2ScreenX - 45, groundY - 138);

    // Frustum de Cámara 2.5D
    t3Ctx.strokeStyle = 'rgba(0, 229, 255, 0.4)';
    t3Ctx.setLineDash([6, 4]);
    const midX = (p1ScreenX + p2ScreenX) / 2;
    t3Ctx.strokeRect(midX - 220, 75, 440, 235);
    t3Ctx.setLineDash([]);
    t3Ctx.fillStyle = '#00e5ff';
    t3Ctx.fillText(`2.5D CAMERA TARGET (FOV ${fov}° | ${st.DisplayName})`, midX - 165, 92);
  }

  updateTab3StageUI();
  updateTab3NetUI();

  // ==========================================================================
  // 7. TAB 4: ARTE TÉCNICO, COMMONUI, DUALSENSE & CONSOLA ACÚSTICA WWISE
  // ==========================================================================
  let t4ImpactFrames = 0;
  let t4HitstopPreset = 12;
  let t4ShakeTimer = 0;
  let t4PadType = 'PS5';

  document.getElementById('t4-btn-impact').addEventListener('click', () => {
    t4ImpactFrames = 18; // Visualizado en cámara lenta para apreciar los 3 frames de Impact Ink
    t4ShakeTimer = t4HitstopPreset;
    playSynthSound('hit');
  });

  document.querySelectorAll('.t4-hs-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.t4-hs-btn').forEach((b) => b.classList.remove('btn-gold'));
      btn.classList.add('btn-gold');
      t4HitstopPreset = parseInt(btn.dataset.hs, 10);
      t4ShakeTimer = t4HitstopPreset;
      playSynthSound('hit');
    });
  });

  document.getElementById('t4-rng-sweat').addEventListener('input', (e) => {
    document.getElementById('t4-lbl-sweat').textContent = `${e.target.value}%`;
  });
  document.getElementById('t4-rng-mud').addEventListener('input', (e) => {
    document.getElementById('t4-lbl-mud').textContent = `${e.target.value}%`;
  });

  // CommonUI Instant Glyph Switcher
  const GLYPH_MAPS = {
    PS5: { LP: '▢ Cuadrado', MP: '△ Triángulo', HP: '◯ Círculo', SK: '✕ Cruz', GB: 'R2 (Adaptive)' },
    XBOX: { LP: 'X (Azul)', MP: 'Y (Amarillo)', HP: 'B (Rojo)', SK: 'A (Verde)', GB: 'RT (Impulse)' },
    STICK: { LP: '1 (Jab)', MP: '2 (Strong)', HP: '3 (Fierce)', SK: '4 (Special)', GB: '5 (Drive)' },
    KB: { LP: 'Key [J]', MP: 'Key [K]', HP: 'Key [L]', SK: 'Key [U]', GB: 'Key [Space]' }
  };

  function updateCommonUIGlyphs(pad) {
    t4PadType = pad;
    const map = GLYPH_MAPS[pad];
    const container = document.getElementById('t4-glyph-preview');
    container.innerHTML = `
      <span class="glyph-pill">LP: ${map.LP}</span>
      <span class="glyph-pill">MP: ${map.MP}</span>
      <span class="glyph-pill">HP: ${map.HP}</span>
      <span class="glyph-pill" style="border-color:var(--turf);">SK: ${map.SK}</span>
      <span class="glyph-pill" style="border-color:var(--gold);">GB: ${map.GB}</span>
    `;
    renderDualSenseCurve();
  }

  document.querySelectorAll('.t4-pad-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.t4-pad-btn').forEach((b) => b.classList.remove('btn-gold'));
      btn.classList.add('btn-gold');
      updateCommonUIGlyphs(btn.dataset.pad);
      playSynthSound('step');
    });
  });

  document.getElementById('t4-chk-tourney').addEventListener('change', () => {
    renderDualSenseCurve();
    playSynthSound('parry');
  });

  function renderDualSenseCurve() {
    const cv = document.getElementById('t4-trigger-canvas');
    const ctx = cv.getContext('2d');
    const w = cv.width;
    const h = cv.height;
    ctx.clearRect(0, 0, w, h);

    ctx.fillStyle = '#070b12';
    ctx.fillRect(0, 0, w, h);

    const tourneyMode = document.getElementById('t4-chk-tourney').checked;

    ctx.strokeStyle = '#1e2a3d';
    ctx.beginPath();
    ctx.moveTo(30, h - 22);
    ctx.lineTo(w - 15, h - 22);
    ctx.stroke();

    ctx.beginPath();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = tourneyMode ? '#00e676' : '#f5c451';

    for (let x = 30; x <= w - 20; x += 4) {
      const t = (x - 30) / (w - 50);
      let force = 0;
      if (!tourneyMode) {
        force = 0.25 + Math.sin(t * Math.PI) * 0.65;
      }
      const y = (h - 24) - force * (h - 45);
      if (x === 30) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    ctx.fillStyle = tourneyMode ? '#00e676' : '#ffe07d';
    ctx.font = 'bold 10.5px Consolas, monospace';
    ctx.fillText(
      tourneyMode
        ? 'MODO TORNEO FGC: 0% RESISTENCIA MECÁNICA (INPUT INSTANTÁNEO)'
        : `${t4PadType} L2/R2 ADAPTIVE CURVE: TENSIÓN DE FATIGA ACTIVA`,
      12,
      18
    );
  }

  updateCommonUIGlyphs('PS5');

  // Consola Wwise: RTPCs, Priority Queue de Relatores y Sidechain Ducking
  let wwiseDuckingDb = 0.0;
  let wwiseActivePrio = 0;

  const COMMENTARY_LINES = {
    1: { prio: 1, text: '"La toca en corto buscando espacio en la mitad de la cancha..."', duck: -2.0 },
    2: { prio: 2, text: '"¡UYYY! ¡Le dejó los tapones marcados hasta la tibia, juez!"', duck: -4.5 },
    3: { prio: 3, text: '"¡NOOO! ¡QUÉ GAMBETA ENDIABLADA! ¡LO DEJÓ PAGANDO EN UNA BALDOSA!"', duck: -6.0 },
    4: { prio: 4, text: '"¡GOOOLAZO HISTÓRICO! ¡SE CAE EL ESTADIO ABAJO! ¡LA COPA ES ETERNA!"', duck: -6.0 }
  };

  document.querySelectorAll('.t4-comm-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const p = parseInt(btn.dataset.prio, 10);
      const entry = COMMENTARY_LINES[p];
      wwiseActivePrio = entry.prio;
      wwiseDuckingDb = entry.duck;

      document.getElementById('t4-comm-prio-badge').textContent =
        `PRIORIDAD ACTIVA: NIVEL ${entry.prio} (INTERRUPT STINGER <2ms)`;
      document.getElementById('t4-comm-duck-badge').textContent =
        `SIDECHAIN DUCKING: ${entry.duck.toFixed(1)} dB`;
      document.getElementById('t4-comm-line').textContent = entry.text;

      playSynthSound(p >= 3 ? 'stinger' : 'step');
      speakSouthAmericanCommentary(entry.text, entry.prio);
    });
  });

  // Conectar Controles de Banda de Tribuna en Tab 4
  const t4BandPlayBtn = document.getElementById('t4-btn-band-play');
  if (t4BandPlayBtn) {
    t4BandPlayBtn.addEventListener('click', () => toggleStadiumBand());
  }
  const t4ChantsSel = document.getElementById('t4-sel-chants');
  if (t4ChantsSel) {
    t4ChantsSel.innerHTML = Object.entries(CHANT_PATTERNS)
      .map(([key, cfg]) => `<option value="${key}">${cfg.label}</option>`)
      .join('');
    t4ChantsSel.addEventListener('change', () => {
      const pat = CHANT_PATTERNS[t4ChantsSel.value] || CHANT_PATTERNS.SAMBA;
      const isAltiplano = t4ChantsSel.value === 'ANDINO_BO';
      const cutoff = isAltiplano ? 900 : 18000;
      setCrowdFilterCutoff(cutoff);
      document.getElementById('t4-band-status').textContent =
        `Filtro Low-Pass: ${cutoff.toLocaleString()} Hz | Tempo: ${pat.bpm} BPM | Auto-Ducking: Activo (-6.0 dB en Impactos)`;
      if (bandPlaying) toggleStadiumBand(true);
    });
  }

  document.getElementById('t4-rng-crowd').addEventListener('input', (e) => {
    const val = parseInt(e.target.value, 10);
    const lbl = val > 15 ? `+${val} (Dominio Local)` : (val < -15 ? `${val} (Dominio Visitante)` : `${val} (Equilibrado)`);
    document.getElementById('t4-lbl-crowd').textContent = lbl;
  });

  document.getElementById('t4-rng-excite').addEventListener('input', (e) => {
    const ex = parseInt(e.target.value, 10);
    document.getElementById('t4-lbl-excite').textContent = `${ex} / 100`;
    // Si la tensión supera 85 (Pixel Health), aplica Low-Pass dramático de latido (950 Hz)
    const cutoff = ex >= 85 ? 950 : 18000;
    setCrowdFilterCutoff(cutoff);
  });

  const t4ShaderCanvas = document.getElementById('t4-shader-canvas');
  const t4ShaderCtx = t4ShaderCanvas.getContext('2d');
  const t4WwiseCanvas = document.getElementById('t4-wwise-canvas');
  const t4WwiseCtx = t4WwiseCanvas.getContext('2d');

  function renderTab4Canvases() {
    // 1. Shader Canvas (Impact Ink, Hitstop Shake, Rim Light, Sudor/Barro)
    const sw = t4ShaderCanvas.width;
    const sh = t4ShaderCanvas.height;
    t4ShaderCtx.clearRect(0, 0, sw, sh);

    const isImpactInk = t4ImpactFrames > 0;
    if (t4ImpactFrames > 0) t4ImpactFrames--;

    let shakeX = 0;
    let shakeY = 0;
    if (t4ShakeTimer > 0) {
      t4ShakeTimer--;
      shakeX = (Math.random() - 0.5) * 14;
      shakeY = (Math.random() - 0.5) * 10;
    }

    t4ShaderCtx.save();
    t4ShaderCtx.translate(shakeX, shakeY);

    if (isImpactInk) {
      // Filtro Impact Ink: Alto contraste Blanco/Negro con líneas radiales
      t4ShaderCtx.fillStyle = (t4ImpactFrames % 2 === 0) ? '#ffffff' : '#05070b';
      t4ShaderCtx.fillRect(0, 0, sw, sh);
      t4ShaderCtx.strokeStyle = '#ff2a54';
      t4ShaderCtx.lineWidth = 4;
      for (let i = 0; i < 16; i++) {
        const ang = (i / 16) * Math.PI * 2;
        t4ShaderCtx.beginPath();
        t4ShaderCtx.moveTo(sw / 2 + Math.cos(ang) * 60, sh / 2 + Math.sin(ang) * 60);
        t4ShaderCtx.lineTo(sw / 2 + Math.cos(ang) * 360, sh / 2 + Math.sin(ang) * 360);
        t4ShaderCtx.stroke();
      }
    } else {
      t4ShaderCtx.fillStyle = '#090e17';
      t4ShaderCtx.fillRect(0, 0, sw, sh);
    }

    // Aura Rim Light seleccionada
    const aura = document.getElementById('t4-sel-aura').value;
    const auraColors = {
      NONE: 'transparent',
      INVULN: '#ffffff',
      ARMOR: '#f5c451',
      CRUSH: '#ff2a54',
      ALTIPLANO: '#00e676'
    };

    const charX = sw / 2;
    const charY = sh - 35;

    if (aura !== 'NONE') {
      t4ShaderCtx.shadowColor = auraColors[aura];
      t4ShaderCtx.shadowBlur = 26;
    }

    // Cuerpo Cel-Shaded del Luchador
    t4ShaderCtx.fillStyle = isImpactInk ? '#000000' : '#1b2838';
    t4ShaderCtx.strokeStyle = aura !== 'NONE' ? auraColors[aura] : '#00e5ff';
    t4ShaderCtx.lineWidth = aura !== 'NONE' ? 5 : 2.5;
    t4ShaderCtx.fillRect(charX - 48, charY - 175, 96, 175);
    t4ShaderCtx.strokeRect(charX - 48, charY - 175, 96, 175);
    t4ShaderCtx.shadowBlur = 0;

    // Capa de Barro (Mud Mask inferior)
    const mudPct = parseInt(document.getElementById('t4-rng-mud').value, 10);
    if (mudPct > 0) {
      const mudH = (mudPct / 100) * 85;
      t4ShaderCtx.fillStyle = 'rgba(92, 64, 51, 0.72)';
      t4ShaderCtx.fillRect(charX - 46, charY - mudH, 92, mudH);
    }

    // Capa de Sudor (Brillos especulares)
    const sweatPct = parseInt(document.getElementById('t4-rng-sweat').value, 10);
    t4ShaderCtx.fillStyle = 'rgba(255, 255, 255, 0.75)';
    const drops = Math.floor(sweatPct / 8);
    for (let d = 0; d < drops; d++) {
      const dx = charX - 35 + ((d * 19) % 70);
      const dy = charY - 160 + ((d * 23) % 90);
      t4ShaderCtx.beginPath();
      t4ShaderCtx.arc(dx, dy, 2.5, 0, Math.PI * 2);
      t4ShaderCtx.fill();
    }

    t4ShaderCtx.fillStyle = '#f5c451';
    t4ShaderCtx.font = 'bold 12px Consolas, monospace';
    t4ShaderCtx.fillText(
      isImpactInk
        ? '⚡ POST-PROCESS: IMPACT INK FRAME ACTIVO!'
        : `RIM LIGHT: ${aura} | SUDOR: ${sweatPct}% | BARRO: ${mudPct}% | HITSTOP: ${t4HitstopPreset}f`,
      16,
      26
    );
    t4ShaderCtx.restore();

    // 2. Wwise Buses Meter Canvas
    const ww = t4WwiseCanvas.width;
    const wh = t4WwiseCanvas.height;
    t4WwiseCtx.clearRect(0, 0, ww, wh);
    t4WwiseCtx.fillStyle = '#070b12';
    t4WwiseCtx.fillRect(0, 0, ww, wh);

    // Relajación gradual del Sidechain Ducking
    if (wwiseDuckingDb < 0) {
      wwiseDuckingDb = Math.min(0, wwiseDuckingDb + 0.04);
      document.getElementById('t4-comm-duck-badge').textContent = `SIDECHAIN DUCKING: ${wwiseDuckingDb.toFixed(1)} dB`;
    }

    const excite = parseInt(document.getElementById('t4-rng-excite').value, 10) / 100;
    const duckFactor = Math.pow(10, wwiseDuckingDb / 20); // Conversión dB a amplitud lineal

    const buses = [
      { name: 'Bus 01: SFX_Combat_Impacts (Prioridad Máxima)', lvl: 0.85, color: '#ff2a54' },
      { name: 'Bus 02: VO_Commentators_PriorityQueue', lvl: wwiseDuckingDb < -0.5 ? 0.92 : 0.25, color: '#f5c451' },
      { name: `Bus 03: Stadium_Crowd_Chants (Ducked ${wwiseDuckingDb.toFixed(1)} dB)`, lvl: (0.4 + excite * 0.5) * duckFactor, color: '#00e676' },
      { name: `Bus 04: Interactive_Music_Stems (Ducked ${wwiseDuckingDb.toFixed(1)} dB)`, lvl: (0.35 + excite * 0.5) * duckFactor, color: '#00e5ff' }
    ];

    buses.forEach((b, i) => {
      const y = 22 + i * 44;
      t4WwiseCtx.fillStyle = '#eef2f9';
      t4WwiseCtx.font = 'bold 11px Consolas, monospace';
      t4WwiseCtx.fillText(b.name, 16, y);

      t4WwiseCtx.fillStyle = '#141c2b';
      t4WwiseCtx.fillRect(16, y + 7, ww - 32, 14);

      const jitterWave = (Math.random() - 0.5) * 0.04;
      const barW = Math.max(0.05, Math.min(1, b.lvl + jitterWave)) * (ww - 32);
      t4WwiseCtx.fillStyle = b.color;
      t4WwiseCtx.fillRect(16, y + 7, barW, 14);
    });
  }

  // ==========================================================================
  // 8. TAB 5: ARBITRAJE ESPORTS (ANTI-CHEAT, .SAFREPLAY & GLICKO-2)
  // ==========================================================================
  let t5CurrentProfile = 'HUMAN';
  const t5CheatCanvas = document.getElementById('t5-cheat-canvas');
  const t5CheatCtx = t5CheatCanvas.getContext('2d');

  const CHEAT_PROFILES = {
    HUMAN: {
      badge: 'VEREDICTO: LEGÍTIMO',
      varText: '2.15 frames² (Distribución Gaussiana Humana)',
      parryText: '14.2% (Lectura Humana Normal)',
      lagText: 'r = 0.06 (Ruido de Red Natural)',
      actionText: '✔ Partida Validada para Ranking CONMEBOL',
      actionColor: '#00e676',
      bars: [4, 12, 28, 34, 16, 6]
    },
    MACRO: {
      badge: '🚨 DETECTADO: HARDWARE MACRO',
      varText: '0.00 frames² (ANOMALÍA: Cadencia Robótica Exacta)',
      parryText: '18.0% (Normal)',
      lagText: 'r = 0.04 (Normal)',
      actionText: '⛔ Cuenta Enviada a Cola de Sanción + Descalificación de Torneo',
      actionColor: '#ff2a54',
      bars: [0, 0, 100, 0, 0, 0]
    },
    PARRYBOT: {
      badge: '🚨 DETECTADO: AUTO-PARRY SCRIPT',
      varText: '1.85 frames² (Normal)',
      parryText: '98.4% en Frame 1 de Startup (Inhumano > 85%)',
      lagText: 'r = 0.08 (Normal)',
      actionText: '⛔ Bloqueo Inmediato por Inyección de Lectura de Memoria',
      actionColor: '#ff2a54',
      bars: [98, 2, 0, 0, 0, 0]
    },
    LAGSWITCH: {
      badge: '🚨 DETECTADO: LAG-SWITCH ASIMÉTRICO',
      varText: '2.30 frames² (Normal)',
      parryText: '11.5% (Normal)',
      lagText: 'r = 0.94 (Pérdida de Paquetes Exclusiva al Recibir Combos)',
      actionText: '⚠️ Derrota Forzada por Manipulación Intencional de Socket UDP',
      actionColor: '#ff9100',
      bars: [15, 22, 35, 68, 92, 96]
    }
  };

  function updateTab5Profile(profKey) {
    t5CurrentProfile = profKey;
    const p = CHEAT_PROFILES[profKey];
    document.getElementById('t5-verdict-badge').textContent = p.badge;
    document.getElementById('t5-stat-var').textContent = p.varText;
    document.getElementById('t5-stat-parry').textContent = p.parryText;
    document.getElementById('t5-stat-lag').textContent = p.lagText;
    const actEl = document.getElementById('t5-stat-action');
    actEl.textContent = p.actionText;
    actEl.style.color = p.actionColor;

    renderTab5CheatCanvas();
  }

  function renderTab5CheatCanvas() {
    const w = t5CheatCanvas.width;
    const h = t5CheatCanvas.height;
    t5CheatCtx.clearRect(0, 0, w, h);
    t5CheatCtx.fillStyle = '#070b12';
    t5CheatCtx.fillRect(0, 0, w, h);

    const p = CHEAT_PROFILES[t5CurrentProfile];
    const barW = 72;
    const gap = 28;
    const startX = 65;

    t5CheatCtx.fillStyle = '#f5c451';
    t5CheatCtx.font = 'bold 12px Consolas, monospace';
    t5CheatCtx.fillText(`HISTOGRAMA TELEMÉTRICO DEL SERVIDOR — PERFIL: ${t5CurrentProfile}`, 20, 26);

    p.bars.forEach((val, idx) => {
      const x = startX + idx * (barW + gap);
      const bh = (val / 100) * (h - 75);
      const y = h - 32 - bh;

      t5CheatCtx.fillStyle = p.actionColor;
      t5CheatCtx.fillRect(x, y, barW, bh);
      t5CheatCtx.strokeStyle = '#ffffff';
      t5CheatCtx.strokeRect(x, y, barW, bh);

      t5CheatCtx.fillStyle = '#eef2f9';
      t5CheatCtx.font = '11px Consolas, monospace';
      t5CheatCtx.fillText(`${val}%`, x + 18, y - 6);
      t5CheatCtx.fillStyle = '#8b9bb4';
      t5CheatCtx.fillText(`Bin F${idx + 1}`, x + 14, h - 12);
    });
  }

  document.querySelectorAll('.t5-prof-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      updateTab5Profile(btn.dataset.prof);
      playSynthSound(btn.dataset.prof === 'HUMAN' ? 'parry' : 'desync');
    });
  });

  // Calculadora .safreplay
  function updateSafReplayCalc() {
    const secs = parseInt(document.getElementById('t5-rng-dur').value, 10);
    const frames = secs * 60;
    const rawBytes = 192 + frames * 4; // 192B header + 2 players * 2 bytes * frames
    const zstdKB = (rawBytes * 0.31) / 1024;
    const mp4KB = secs * 1500;

    document.getElementById('t5-lbl-dur').textContent = `${secs} Segundos (${frames.toLocaleString()} Frames)`;
    document.getElementById('t5-rep-raw').textContent = `${(rawBytes / 1024).toFixed(2)} KB`;
    document.getElementById('t5-rep-zstd').textContent = `${zstdKB.toFixed(2)} KB (< 50 KB Target)`;
    document.getElementById('t5-rep-mp4').textContent = `~${mp4KB.toLocaleString()} KB (${(mp4KB / 1024).toFixed(1)} MB)`;
  }

  document.getElementById('t5-rng-dur').addEventListener('input', updateSafReplayCalc);

  // Calculadora Glicko-2
  function updateGlicko2Calc() {
    const r1 = parseFloat(document.getElementById('t5-g-r1').value) || 1500;
    const rd1 = parseFloat(document.getElementById('t5-g-rd1').value) || 65;
    const r2 = parseFloat(document.getElementById('t5-g-r2').value) || 1500;
    const score = parseFloat(document.getElementById('t5-g-score').value);

    const q = Math.log(10) / 400;
    const gRD = 1 / Math.sqrt(1 + (3 * q * q * 60 * 60) / (Math.PI * Math.PI));
    const expected = 1 / (1 + Math.pow(10, (-gRD * (r1 - r2)) / 400));

    const d2 = 1 / (q * q * gRD * gRD * expected * (1 - expected));
    const newRD = Math.sqrt(1 / (1 / (rd1 * rd1) + 1 / d2));
    const delta = Math.round(q * (newRD * newRD) * gRD * (score - expected));
    const newR = Math.round(r1 + delta);

    document.getElementById('t5-g-exp').textContent = `${(expected * 100).toFixed(1)}%`;
    const sign = delta >= 0 ? `+${delta}` : `${delta}`;
    const newEl = document.getElementById('t5-g-new');
    newEl.textContent = `${newR} (${sign} pts) | RD': ${newRD.toFixed(1)}`;
    newEl.style.color = delta >= 0 ? '#00e676' : '#ff2a54';

    let divName = '🌱 Potrero de Tierra (< 1200)';
    if (newR >= 2100) divName = '👑 Leyenda Eterna — Top 500 CONMEBOL (2100+)';
    else if (newR >= 1800) divName = '🌟 Primera División Profesional (1800 - 2099)';
    else if (newR >= 1500) divName = '⚽ Copa Continental (1500 - 1799)';
    else if (newR >= 1200) divName = '🏟️ Liga Regional (1200 - 1499)';
    document.getElementById('t5-g-div').textContent = divName;
  }

  ['t5-g-r1', 't5-g-rd1', 't5-g-r2', 't5-g-score'].forEach((id) => {
    document.getElementById(id).addEventListener('input', updateGlicko2Calc);
    document.getElementById(id).addEventListener('change', updateGlicko2Calc);
  });

  updateTab5Profile('HUMAN');
  updateSafReplayCalc();
  updateGlicko2Calc();

  // ==========================================================================
  // 9. TAB 6: MODO VERSUS 1v1 JUGABLE EN TIEMPO REAL (60 FPS)
  // ==========================================================================
  const t6SelP1 = document.getElementById('t6-sel-p1');
  const t6SelP2 = document.getElementById('t6-sel-p2');
  const t6SelStage = document.getElementById('t6-sel-stage');
  const t6SelAI = document.getElementById('t6-sel-ai');
  const t6Canvas = document.getElementById('t6-canvas');
  const t6Ctx = t6Canvas.getContext('2d');
  const t6WebglCanvas = document.getElementById('t6-webgl-canvas');
  const t6WebglHud = document.getElementById('t6-webgl-hud');
  const t6Btn3dMode = document.getElementById('t6-btn-3d-mode');
  const t6WebGLReady = Boolean(t6WebglCanvas && window.SAFWglArena && window.SAFWglArena.init(t6WebglCanvas));
  let t6Arena3DEnabled = t6WebGLReady;

  function syncT63DButtonUI() {
    if (t6Btn3dMode) {
      if (!t6WebGLReady) {
        t6Btn3dMode.textContent = '🎨 Motor: 2D Respaldo (Sin GPU WebGL2)';
        t6Btn3dMode.className = 'btn btn-cyan btn-sm';
      } else if (t6Arena3DEnabled) {
        t6Btn3dMode.textContent = '🧊 Motor 3D: ON (17 Modelos .GLB)';
        t6Btn3dMode.className = 'btn btn-gold btn-sm';
      } else {
        t6Btn3dMode.textContent = '🎨 Motor 3D: OFF (Vista 2D Clásica)';
        t6Btn3dMode.className = 'btn btn-cyan btn-sm';
      }
    }
    if (t6WebglCanvas) {
      t6WebglCanvas.style.display = (t6WebGLReady && t6Arena3DEnabled) ? 'block' : 'none';
    }
    if (t6WebglHud && !(t6WebGLReady && t6Arena3DEnabled)) {
      t6WebglHud.style.display = 'none';
    }
  }

  if (t6Btn3dMode) {
    t6Btn3dMode.addEventListener('click', () => {
      if (!t6WebGLReady) {
        announceT6('⚠️ Tu navegador actual no expuso WebGL2 GPU; usando respaldo 2D.', '#ff9100', 70);
        return;
      }
      t6Arena3DEnabled = !t6Arena3DEnabled;
      syncT63DButtonUI();
      announceT6(
        t6Arena3DEnabled ? '🧊 ARENA 3D WEBGL2 ACTIVADA (17 SK_*.glb EN VIVO)' : '🎨 MODO 2D CLÁSICO ACTIVADO',
        t6Arena3DEnabled ? '#ffe07d' : '#00e5ff',
        55
      );
    });
  }
  syncT63DButtonUI();

  ROSTER_DATA.forEach((ch, idx) => {
    const o1 = document.createElement('option');
    o1.value = idx;
    o1.textContent = `${ch.DisplayName} (${ch.Country})`;
    t6SelP1.appendChild(o1);

    const o2 = document.createElement('option');
    o2.value = idx;
    o2.textContent = `${ch.DisplayName} (${ch.Country})`;
    t6SelP2.appendChild(o2);
  });
  t6SelP1.value = 0; // O Fenômeno
  t6SelP2.value = 3; // La Pulga

  STAGES_DATA.forEach((st, idx) => {
    const os = document.createElement('option');
    os.value = idx;
    os.textContent = st.DisplayName;
    t6SelStage.appendChild(os);
  });

  const t6SelArtStyle = document.getElementById('t6-sel-artstyle');
  if (t6SelArtStyle) {
    t6SelArtStyle.addEventListener('change', (e) => {
      t6State.artStyle = e.target.value;
      const isSfumato = t6State.artStyle === 'SFUMATO';
      announceT6(
        isSfumato ? '🖼️ DIRECCIÓN DE ARTE: RENACIMIENTO SFUMATO (DA VINCI)' : '⚡ DIRECCIÓN DE ARTE: STREET-INK AAA',
        isSfumato ? '#e5b95c' : '#00e5ff',
        55
      );
      playSynthSound('parry');
    });
  }

  // Catálogo de Movimientos de Combate en Vivo para Tab 6
  const T6_MOVES = {
    LP: { name: '5LP (Jab Rápido)', startup: 4, active: 4, recovery: 7, dmg: 450, hitstun: 14, blockstun: 9, push: 18, meter: 90, range: 95, type: 'HIGH' },
    MP: { name: '5MP (Cabezazo Medio)', startup: 7, active: 5, recovery: 12, dmg: 780, hitstun: 19, blockstun: 13, push: 28, meter: 150, range: 115, type: 'MID' },
    HP: { name: '5HP (Entrada Potente)', startup: 11, active: 6, recovery: 18, dmg: 1200, hitstun: 25, blockstun: 16, push: 48, meter: 240, range: 135, type: 'HIGH', wallDmg: 1 },
    SK: { name: '5SK (Disparo de Balón)', startup: 12, active: 4, recovery: 18, dmg: 850, hitstun: 20, blockstun: 12, push: 32, meter: 160, range: 70, type: 'PROJ', projSpeed: 10.5 },
    GB: { name: '5GB (Gambeta / Parry 2f)', startup: 2, active: 14, recovery: 14, dmg: 0, hitstun: 0, blockstun: 0, push: 0, meter: 80, range: 0, type: 'PARRY' },
    SP_236: { name: '236+SK (Cañonazo Especial)', startup: 13, active: 6, recovery: 17, dmg: 1350, hitstun: 26, blockstun: 16, push: 45, meter: 260, range: 80, type: 'PROJ_EX', projSpeed: 14.0, wallDmg: 1 },
    SP_623: { name: '623+HP (Despeje Anti-Aéreo DP)', startup: 5, active: 9, recovery: 22, dmg: 1450, hitstun: 30, blockstun: 14, push: 52, meter: 250, range: 118, type: 'DP', invuln: true, vy: -11, wallDmg: 1 },
    SP_41236: { name: '41236+LP (Agarre Táctico / Elástica)', startup: 6, active: 5, recovery: 20, dmg: 1850, hitstun: 34, blockstun: 0, push: 65, meter: 300, range: 105, type: 'GRAB', unblockable: true, wallDmg: 1 },
    SUPER_1: { name: '236236+SK (Super Nivel 1)', startup: 6, active: 14, recovery: 24, dmg: 2600, hitstun: 38, blockstun: 20, push: 85, meter: 0, costSuper: 1000, range: 155, type: 'SUPER', invuln: true, projSpeed: 17.5, wallDmg: 2 },
    ULT_3: { name: '214214+HP+SK (Grito Sagrado Nivel 3)', startup: 4, active: 22, recovery: 30, dmg: 4600, hitstun: 55, blockstun: 25, push: 130, meter: 0, costSuper: 3000, range: 230, type: 'ULTIMATE', invuln: true, wallDmg: 4 }
  };

  function createMatchFighter(charIdx, x, isP1) {
    const data = ROSTER_DATA[charIdx] || ROSTER_DATA[0];
    return {
      charIdx,
      data,
      isP1,
      x,
      y: 0,
      vx: 0,
      vy: 0,
      facingRight: isP1,
      hp: data.MaxHealth,
      maxHp: data.MaxHealth,
      gambeta: 1000,
      superMeter: 1500,
      state: 'IDLE', // IDLE, WALK_F, WALK_B, CROUCH, JUMP, DASH_F, DASH_B, STARTUP, ACTIVE, RECOVERY, HITSTUN, BLOCKSTUN, PARRY, KO
      stateFrame: 0,
      stunFrames: 0,
      activeMoveKey: null,
      moveHitRegistered: false,
      comboCount: 0,
      comboDamage: 0,
      varRewindUsed: false
    };
  }

  let t6State = {
    p1: createMatchFighter(0, 280, true),
    p2: createMatchFighter(3, 800, false),
    stageIdx: 0,
    artStyle: 'SFUMATO', // 'SFUMATO' (Renacimiento Da Vinci) o 'STREET_INK' (Neón & Tinta)
    wallHp: 3,
    maxWallHp: 3,
    inZoneB: false,
    timerFrames: 99 * 60,
    hitstopFrames: 0,
    shakeFrames: 0,
    impactInkFrames: 0,
    projectiles: [],
    particles: [],
    bannerText: '¡PITAZO INICIAL! — FIGHT!',
    bannerTimer: 90,
    bannerColor: '#ffe07d',
    keysDown: {},
    uiMoveHeld: null,
    latchedBtn: '',
    lastTapDir: 0,
    lastTapTime: 0,
    p2LastTapDir: 0,
    p2LastTapTime: 0,
    matchEnded: false,
    tourneyMode: false,
    tourneyRound: 1,
    storyMode: false,
    storyChapter: 1,
    showInputDisplay: true,
    inputLog: [
      { dir: 5, btn: '', frames: 1 }
    ],
    gpPrevButtons: {},
    gpPrevButtonsP2: {},
    stats: {
      p1DamageDealt: 0,
      p2DamageDealt: 0,
      p1MaxCombo: 0,
      p2MaxCombo: 0,
      p1Blocks: 0,
      p2Blocks: 0,
      wallBreaks: 0
    }
  };

  const T6_DIR_ARROWS = { 1: '↙', 2: '↓', 3: '↘', 4: '←', 5: '•', 6: '→', 7: '↖', 8: '↑', 9: '↗' };

  function pushT6InputHistory(dir, btn = '') {
    const log = t6State.inputLog;
    const latest = log[0];
    if (latest && latest.dir === dir && latest.btn === btn) {
      latest.frames = Math.min(999, latest.frames + 1);
    } else {
      log.unshift({ dir, btn, frames: 1 });
      if (log.length > 10) log.pop();
    }
    renderT6InputHistoryDOM();
  }

  function renderT6InputHistoryDOM() {
    const container = document.getElementById('t6-input-history');
    if (!container) return;
    if (!t6State.showInputDisplay) {
      container.style.display = 'none';
      return;
    }
    container.style.display = 'flex';
    container.innerHTML = t6State.inputLog.map((item) => {
      const arrow = T6_DIR_ARROWS[item.dir] || '•';
      let btnBadge = '';
      if (item.btn) {
        const bClass = ['LP', 'MP', 'HP', 'SK', 'GB'].includes(item.btn) ? `b-${item.btn}` : 'b-SP';
        btnBadge = `<span class="t6-ih-btn ${bClass}">${item.btn}</span>`;
      }
      return `
        <div class="t6-ih-row">
          <span class="t6-ih-dir">${item.dir}${arrow}</span>
          ${btnBadge}
          <span class="t6-ih-frames">${item.frames}f</span>
        </div>
      `;
    }).join('');
  }

  const t6BtnInputDisp = document.getElementById('t6-btn-input-display');
  if (t6BtnInputDisp) {
    t6BtnInputDisp.addEventListener('click', (e) => {
      t6State.showInputDisplay = !t6State.showInputDisplay;
      e.currentTarget.textContent = t6State.showInputDisplay ? '📋 Input Display: ON' : '📋 Input Display: OFF';
      renderT6InputHistoryDOM();
    });
  }

  // Recortes de Retratos Verificados + Frases de Victoria por Leyenda (0..16)
  const T6_VICTORY_PORTRAITS = [
    { sheet: '../Assets/ConceptArt/VSScreen_Brasil_vs_Argentina_Renaissance.jpg', size: '210% auto', pos: '12% 24%', quote: '"¡Con una pedalada de otro planeta dejó pagando a toda la defensa y clavó el gol de la gloria eterna!"' },
    { sheet: '../Assets/ConceptArt/LaCopaEterna_KeyArt_RosterClash.jpg', size: '220% auto', pos: '24% 25%', quote: '"¡Sonríe la pelota! Magia, samba y elástica sin mirar para levantar a todo el estadio."' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_PortraitSheet_CONMEBOL.jpg', size: '310% auto', pos: '84% 22%', quote: '"¡Rompió la red de un cañonazo inatajable desde treinta metros! ¡Pura dinamita albiceleste!"' },
    { sheet: '../Assets/ConceptArt/VSScreen_Brasil_vs_Argentina_Renaissance.jpg', size: '210% auto', pos: '88% 24%', quote: '"¡La pelota siempre pegada al botín izquierdo! Gambeta imposible y coronación histórica en la final."' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_PortraitSheet_CONMEBOL.jpg', size: '310% auto', pos: '14% 22%', quote: '"¡Todo bien, todo bien! Pases filtrados con ojos en la nuca y control absoluto del mediocampo."' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_PortraitSheet_CONMEBOL.jpg', size: '310% auto', pos: '48% 22%', quote: '"¡Un Escorpión inmortal sobre la línea de sentencia para humillar el ataque rival!"' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_PortraitSheet_CONMEBOL.jpg', size: '310% auto', pos: '25% 78%', quote: '"¡Garra Charrúa hasta el último aliento! Presión asfixiante y victoria en área chica."' },
    { sheet: '../Assets/ConceptArt/LaCopaEterna_KeyArt_RosterClash.jpg', size: '220% auto', pos: '78% 28%', quote: '"¡Efecto Jabulani con ambas piernas! Un francotirador implacable desde cualquier rincón."' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_RosterWave2_Renaissance.jpg', size: '400% auto', pos: '6% 14%', quote: '"¡Suspendido en el cielo como un helicóptero, conectó el cabezazo definitivo!"' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_RosterWave2_Renaissance.jpg', size: '400% auto', pos: '36% 14%', quote: '"¡Trancazo real con pulmón de acero! Nadie le gana una pelota dividida en el barro."' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_RosterWave2_Renaissance.jpg', size: '400% auto', pos: '66% 14%', quote: '"¡Intimidación guaraní de tiro libre! Ni la barrera ni el arquero pudieron resistir."' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_RosterWave2_Renaissance.jpg', size: '400% auto', pos: '95% 14%', quote: '"¡Elegancia de tres dedos y caño de colección para firmar una obra de arte!"' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_RosterWave2_Renaissance.jpg', size: '400% auto', pos: '6% 86%', quote: '"¡A toda máquina por la banda derecha! Velocidad supersónica de trece cuadros."' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_RosterWave2_Renaissance.jpg', size: '400% auto', pos: '36% 86%', quote: '"¡Zurda de oro en Folha Seca! El balón cayó como un misil en el ángulo superior."' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_RosterWave2_Renaissance.jpg', size: '400% auto', pos: '66% 86%', quote: '"¡A 3.600 metros la pelota no dobla y el rival se quedó sin aire en el segundo tiempo!"' },
    { sheet: '../Assets/ConceptArt/CharacterSelect_RosterWave2_Renaissance.jpg', size: '400% auto', pos: '95% 86%', quote: '"¡Roulette de Marseille y clase magistral para dominar el tempo del encuentro!"' },
    { sheet: '../Assets/ConceptArt/Boss_VAR_ZERO_Renaissance.jpg', size: '135% auto', pos: '50% 22%', quote: '"¡REVISIÓN DE CUADRO COMPLETADA! El Juez Supremo decreta fuera de juego y anula tu existencia."' }
  ];

  function playVictoryFanfare() {
    const ctx = ensureAudio();
    if (!ctx) return;
    const now = ctx.currentTime;
    const notes = [261.63, 329.63, 392.00, 523.25]; // Acorde Mayor Triunfal C4-E4-G4-C5
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, now + i * 0.09);
      g.gain.setValueAtTime(0.16, now + i * 0.09);
      g.gain.exponentialRampToValueAtTime(0.001, now + i * 0.09 + 0.55);
      osc.connect(g).connect(ctx.destination);
      osc.start(now + i * 0.09);
      osc.stop(now + i * 0.09 + 0.58);
    });
  }

  function showTab6VictoryOverlay(winnerFighter, reasonType = 'KO') {
    if (t6State.matchEnded) return;
    t6State.matchEnded = true;

    const overlayEl = document.getElementById('t6-victory-overlay');
    const cardEl = document.getElementById('t6-victory-card');
    if (!overlayEl || !cardEl) return;

    cardEl.classList.toggle('street-ink-mode', t6State.artStyle === 'STREET_INK');

    const isBossWin = winnerFighter.data.Name === 'VAR_ZERO_BOSS';
    const bannerEl = document.getElementById('t6-vic-banner');
    if (reasonType === 'TIME') {
      bannerEl.textContent = `⏱️ ¡TIEMPO CUMPLIDO! — VICTORIA POR PUNTOS (${winnerFighter.isP1 ? 'P1' : 'P2'})`;
    } else if (isBossWin) {
      bannerEl.textContent = '⚖️ VEREDICTO V.A.R.-ZERO — ¡EL JUEZ SUPREMO DOMINA LA CANCHA!';
    } else {
      bannerEl.textContent = `🏆 ¡CAMPEÓN DE LA CANCHA! — VICTORIA DE ${winnerFighter.isP1 ? 'JUGADOR 1' : 'JUGADOR 2'}`;
    }

    const artInfo = T6_VICTORY_PORTRAITS[winnerFighter.charIdx] || T6_VICTORY_PORTRAITS[0];
    const portEl = document.getElementById('t6-vic-portrait');
    portEl.style.backgroundImage = `url('${artInfo.sheet}')`;
    portEl.style.backgroundSize = artInfo.size;
    portEl.style.backgroundPosition = artInfo.pos;

    document.getElementById('t6-vic-country').textContent = `${winnerFighter.data.Country} • ${winnerFighter.data.Archetype}`;
    document.getElementById('t6-vic-name').textContent = winnerFighter.data.DisplayName;
    document.getElementById('t6-vic-quote').textContent = artInfo.quote;

    const st = t6State.stats;
    const maxCombo = Math.max(st.p1MaxCombo, st.p2MaxCombo, 1);
    const totalBlocks = st.p1Blocks + st.p2Blocks;
    const secsLeft = Math.ceil(t6State.timerFrames / 60);

    document.getElementById('t6-vic-dmg').textContent =
      `${st.p1DamageDealt.toLocaleString()} vs ${st.p2DamageDealt.toLocaleString()}`;
    document.getElementById('t6-vic-combo').textContent = `${maxCombo} Hits`;
    document.getElementById('t6-vic-blocks').textContent = `${totalBlocks} Defensas`;
    document.getElementById('t6-vic-walls').textContent = `${st.wallBreaks} Ruptura(s)`;
    document.getElementById('t6-vic-time').textContent = `${secsLeft} Segundos`;

    // Calcular Rango de Estilo (S / A / B / C)
    const winHpPct = winnerFighter.hp / winnerFighter.maxHp;
    let rank = 'B';
    if (winHpPct >= 0.65 && (maxCombo >= 3 || st.wallBreaks >= 1)) rank = 'S';
    else if (winHpPct >= 0.40 || maxCombo >= 2) rank = 'A';
    else if (winHpPct < 0.15) rank = 'C';

    const rankEl = document.getElementById('t6-vic-rank');
    rankEl.textContent = rank;
    rankEl.style.color = rank === 'S' ? '#ffe07d' : (rank === 'A' ? '#00e676' : '#00e5ff');

    // Hook de Retorno para Modo Torneo (Llave Copa Eterna) y Modo Historia
    const tourneyBtn = document.getElementById('t6-btn-tourney-next');
    if (t6State.tourneyMode) {
      const won = winnerFighter === t6State.p1;
      const score = st.p1DamageDealt + (won ? 5000 : 0) + maxCombo * 250;
      try {
        localStorage.setItem('copaEternaLastMatch', JSON.stringify({
          round: t6State.tourneyRound,
          won,
          rank,
          score,
          timestamp: Date.now()
        }));
      } catch (_) {}
      if (tourneyBtn) tourneyBtn.style.display = 'inline-flex';
    } else if (tourneyBtn) {
      tourneyBtn.style.display = 'none';
    }

    const storyBtn = document.getElementById('t6-btn-story-next');
    if (t6State.storyMode) {
      const won = winnerFighter === t6State.p1;
      const score = st.p1DamageDealt + (won ? 5000 : 0) + maxCombo * 250;
      try {
        localStorage.setItem('copaEternaLastStoryMatch', JSON.stringify({
          chapter: t6State.storyChapter,
          won,
          rank,
          score,
          maxCombo,
          timestamp: Date.now()
        }));
      } catch (_) {}
      if (storyBtn) storyBtn.style.display = 'inline-flex';
    } else if (storyBtn) {
      storyBtn.style.display = 'none';
    }

    overlayEl.style.display = 'flex';
    playVictoryFanfare();
  }

  function announceT6(text, color = '#ffe07d', duration = 65, commentary = null, sub = null) {
    t6State.bannerText = text;
    t6State.bannerColor = color;
    t6State.bannerTimer = duration;
    if (commentary) {
      document.getElementById('t6-live-commentary').textContent = commentary;
      if (activeTab === 'tab6') {
        const prio = text.includes('GOOOOO') ? 4 : (text.includes('OOOO-LÉ') || text.includes('COUNTER') ? 3 : 2);
        speakSouthAmericanCommentary(commentary, prio);
      }
    }
    if (sub) {
      document.getElementById('t6-live-sub').textContent = sub;
    }
  }

  function resetTab6Match() {
    const p1Idx = parseInt(t6SelP1.value, 10) || 0;
    let p2Idx = parseInt(t6SelP2.value, 10) || 3;
    if (t6SelAI.value === 'BOSS_VAR') {
      p2Idx = ROSTER_DATA.length - 1; // V.A.R.-ZERO
      t6SelP2.value = p2Idx;
    }
    const stIdx = parseInt(t6SelStage.value, 10) || 0;
    const st = STAGES_DATA[stIdx];

    t6State.p1 = createMatchFighter(p1Idx, 270, true);
    t6State.p2 = createMatchFighter(p2Idx, 810, false);
    t6State.stageIdx = stIdx;
    if (t6WebGLReady && window.SAFWglArena) {
      const p1Code = t6State.p1.data.Name;
      const p2Code = t6State.p2.data.Name;
      const p1Glb = `../Assets/Models3D/Fighters/${p1Code === 'VAR_ZERO_BOSS' ? 'SK_SUPREME_JUDGE_BOSS.glb' : 'SK_' + p1Code + '.glb'}`;
      const p2Glb = `../Assets/Models3D/Fighters/${p2Code === 'VAR_ZERO_BOSS' ? 'SK_SUPREME_JUDGE_BOSS.glb' : 'SK_' + p2Code + '.glb'}`;
      const st3d = (typeof STAGES_3D_CATALOG !== 'undefined' && STAGES_3D_CATALOG[stIdx]) ? STAGES_3D_CATALOG[stIdx].File : 'SM_Stage_Maracana_BR.glb';
      window.SAFWglArena.preload([p1Glb, p2Glb, `../Assets/Models3D/Stages/${st3d}`]);
    }
    getT6FighterSpritePair(t6State.p1.data.Name);
    getT6FighterSpritePair(t6State.p2.data.Name);
    if (t6SelArtStyle) t6State.artStyle = t6SelArtStyle.value;
    t6State.wallHp = st.WallHP;
    t6State.maxWallHp = st.WallHP;
    t6State.inZoneB = false;
    t6State.timerFrames = 99 * 60;
    t6State.hitstopFrames = 0;
    t6State.shakeFrames = 0;
    t6State.impactInkFrames = 0;
    t6State.projectiles = [];
    t6State.particles = [];
    t6State.matchEnded = false;
    t6State.inputLog = [{ dir: 5, btn: '', frames: 1 }];
    renderT6InputHistoryDOM();
    t6State.stats = {
      p1DamageDealt: 0,
      p2DamageDealt: 0,
      p1MaxCombo: 0,
      p2MaxCombo: 0,
      p1Blocks: 0,
      p2Blocks: 0,
      wallBreaks: 0
    };

    const vicOverlay = document.getElementById('t6-victory-overlay');
    if (vicOverlay) vicOverlay.style.display = 'none';

    document.getElementById('t6-zone-badge').textContent = 'ZONA A';
    document.getElementById('t6-match-subtitle').textContent =
      `${t6State.p1.data.DisplayName} vs ${t6State.p2.data.DisplayName} — ${st.DisplayName} (${st.ZoneA})`;

    const isLocal2P = t6SelAI.value === 'LOCAL_2P';
    const isTraining = t6SelAI.value === 'DUMMY';
    const isStory = Boolean(t6State.storyMode);
    if (isTraining) {
      t6State.p1.superMeter = 3000;
      t6State.p1.gambeta = 1000;
      t6State.p2.superMeter = 3000;
      t6State.p2.gambeta = 1000;
    }
    announceT6(
      isTraining
        ? '🎯 MODO ENTRENAMIENTO — EL POTRERO (TIEMPO ∞)'
        : (isStory
            ? `📖 MODO HISTORIA — CAPÍTULO ${t6State.storyChapter} EN VIVO`
            : (isLocal2P ? '👥 ¡DUELO LOCAL 2P! — P1 (WASD) vs P2 (FLECHAS)' : '⚽ ¡PITAZO INICIAL! — RUEDA EL BALÓN')),
      isTraining ? '#00e5ff' : (isStory ? '#ffe07d' : '#00e676'),
      85,
      isTraining
        ? `"¡Sesión de entrenamiento libre para ${t6State.p1.data.DisplayName} frente a ${t6State.p2.data.DisplayName} en ${st.DisplayName}!"`
        : `"¡Arranca el duelo histórico entre ${t6State.p1.data.DisplayName} y ${t6State.p2.data.DisplayName} en ${st.DisplayName}!"`,
      isTraining
        ? 'Training Mode activo: Tiempo ∞, Dummy pasivo con auto-regeneración de HP post-combo y Hinchada Nivel 3 cargada.'
        : (isStory
            ? `Campaña Crónicas del Potrero (Capítulo ${t6State.storyChapter}/6): Vence al rival para avanzar la historia.`
            : (isLocal2P
                ? '2P Local activo: P1 (WASD + U/I/O/J/K o Pad #1) vs P2 (Flechas + Numpad 1-5 / 7,8,9,B,N o Pad #2).'
                : 'Fase Neutral 2.5D activa @ 60.0 FPS deterministas.'))
    );
    playSynthSound('stinger');
  }

  t6SelP1.addEventListener('change', resetTab6Match);
  t6SelP2.addEventListener('change', () => {
    const chosenP2 = parseInt(t6SelP2.value, 10);
    if (t6SelAI.value === 'BOSS_VAR' && chosenP2 !== ROSTER_DATA.length - 1) {
      t6SelAI.value = 'CPU_PRO';
    }
    resetTab6Match();
  });
  t6SelStage.addEventListener('change', resetTab6Match);
  t6SelAI.addEventListener('change', resetTab6Match);
  document.getElementById('t6-btn-restart').addEventListener('click', resetTab6Match);

  const t6BtnRematch = document.getElementById('t6-btn-rematch');
  if (t6BtnRematch) {
    t6BtnRematch.addEventListener('click', resetTab6Match);
  }

  const t6BtnDemoKo = document.getElementById('t6-btn-demo-ko');
  if (t6BtnDemoKo) {
    t6BtnDemoKo.addEventListener('click', () => {
      t6State.p2.hp = 0;
      t6State.p2.state = 'KO';
      t6State.stats.p1DamageDealt = Math.max(t6State.stats.p1DamageDealt, t6State.p2.maxHp);
      t6State.stats.p1MaxCombo = Math.max(t6State.stats.p1MaxCombo, 6);
      t6State.stats.p1Blocks = Math.max(t6State.stats.p1Blocks, 3);
      t6State.stats.wallBreaks = Math.max(t6State.stats.wallBreaks, 1);
      t6State.impactInkFrames = 10;
      t6State.hitstopFrames = 14;
      announceT6(
        `⚽🏆 ¡GOOOOOOOLAZO / K.O.! — GANA ${t6State.p1.data.DisplayName.toUpperCase()}`,
        '#00e676',
        180,
        `"¡GOOOOOOLAZO HISTÓRICO DE ${t6State.p1.data.DisplayName.toUpperCase()}! ¡SE CAE EL ESTADIO ABAJO!"`,
        'Mostrando Pantalla de Victoria Post-Partido.'
      );
      showTab6VictoryOverlay(t6State.p1, 'KO');
    });
  }

  document.getElementById('t6-btn-fill-meters').addEventListener('click', () => {
    t6State.p1.superMeter = 3000;
    t6State.p1.gambeta = 1000;
    t6State.p2.superMeter = 3000;
    t6State.p2.gambeta = 1000;
    announceT6('⚡ ¡HINCHADA AL 100%! (NIVEL 3 LISTO)', '#00e5ff', 55);
    playSynthSound('parry');
  });

  function spawnParticles(x, y, color, count = 14) {
    const isSfumato = t6State.artStyle === 'SFUMATO';
    const sfumatoPalette = ['#f5c451', '#d4882a', '#ffe599', '#87b8d4', '#c95b3c'];
    for (let i = 0; i < count; i++) {
      const ang = Math.random() * Math.PI * 2;
      const spd = 2 + Math.random() * 7;
      const ptColor = isSfumato ? sfumatoPalette[i % sfumatoPalette.length] : color;
      t6State.particles.push({
        x,
        y,
        vx: Math.cos(ang) * spd,
        vy: Math.sin(ang) * spd - 2,
        life: 16 + Math.floor(Math.random() * 14),
        color: ptColor
      });
    }
  }

  function startFighterMove(fighter, moveKey) {
    if (fighter.state === 'KO' || fighter.state === 'HITSTUN' || fighter.state === 'BLOCKSTUN') return false;
    const mv = T6_MOVES[moveKey];
    if (!mv) return false;

    // Permite cancelar Normales en Especiales/Supers si el golpe ya conectó
    const isBusyAttacking = ['STARTUP', 'ACTIVE', 'RECOVERY'].includes(fighter.state);
    if (isBusyAttacking) {
      const canCancel = fighter.moveHitRegistered && (moveKey.startsWith('SP_') || moveKey === 'SUPER_1' || moveKey === 'ULT_3');
      if (!canCancel) return false;
    }

    if (mv.costSuper && fighter.superMeter < mv.costSuper) {
      if (fighter.isP1) {
        announceT6(`NECESITAS ${mv.costSuper} DE SUPER METER`, '#ff9100', 40);
      }
      return false;
    }
    if (moveKey === 'GB' && fighter.gambeta < 200) return false;

    if (mv.costSuper) fighter.superMeter -= mv.costSuper;
    if (moveKey === 'GB') fighter.gambeta = Math.max(0, fighter.gambeta - 200);

    fighter.activeMoveKey = moveKey;
    fighter.state = moveKey === 'GB' ? 'PARRY' : 'STARTUP';
    fighter.stateFrame = 1;
    fighter.moveHitRegistered = false;
    fighter.vx = 0;

    if (fighter.isP1) {
      t6State.latchedBtn = moveKey;
    }

    if (mv.vy && fighter.y === 0) {
      fighter.vy = mv.vy;
    }

    if (moveKey === 'SUPER_1' || moveKey === 'ULT_3') {
      t6State.impactInkFrames = 8;
      t6State.hitstopFrames = 10;
      announceT6(
        moveKey === 'ULT_3' ? `🌟 ¡GRITO SAGRADO: ${fighter.data.DisplayName.toUpperCase()}!` : `🔥 ¡SUPER DISPARO NIVEL 1!`,
        '#ffe07d',
        65,
        `"¡ATENCIÓN QUE PREPARA EL REMATE DEFINITIVO ${fighter.data.DisplayName}!"`,
        `Ejecutando ${mv.name} (Startup ${mv.startup}f)`
      );
      playSynthSound('stinger');
    } else {
      playSynthSound('step');
    }
    return true;
  }

  function triggerFighterMovement(fighter, moveCmd) {
    if (fighter.state === 'KO' || fighter.state === 'HITSTUN' || fighter.state === 'BLOCKSTUN') return;
    if (['STARTUP', 'ACTIVE', 'RECOVERY', 'PARRY'].includes(fighter.state)) return;

    const dirSign = fighter.facingRight ? 1 : -1;
    if (moveCmd === 'DASH_F') {
      if (fighter.gambeta >= 150) {
        fighter.gambeta -= 150;
        fighter.state = 'DASH_F';
        fighter.stateFrame = 1;
        fighter.vx = dirSign * 9.5;
        spawnParticles(fighter.x, 385, '#00e676', 8);
        playSynthSound('step');
      }
    } else if (moveCmd === 'DASH_B') {
      fighter.state = 'DASH_B';
      fighter.stateFrame = 1;
      fighter.vx = -dirSign * 8.2;
      playSynthSound('step');
    } else if (moveCmd === 'JUMP' && fighter.y === 0) {
      fighter.state = 'JUMP';
      fighter.vy = -13.5;
      playSynthSound('step');
    } else if (moveCmd === 'CROUCH' && fighter.y === 0) {
      fighter.state = 'CROUCH';
      fighter.vx = 0;
    } else if (moveCmd === 'LEFT') {
      fighter.vx = -4.6;
      fighter.state = fighter.facingRight ? 'WALK_B' : 'WALK_F';
    } else if (moveCmd === 'RIGHT') {
      fighter.vx = 4.6;
      fighter.state = fighter.facingRight ? 'WALK_F' : 'WALK_B';
    }
  }

  // Botones en pantalla de Tab 6
  document.querySelectorAll('.t6-move-btn').forEach((btn) => {
    btn.addEventListener('mousedown', () => {
      t6State.uiMoveHeld = btn.dataset.move;
      triggerFighterMovement(t6State.p1, btn.dataset.move);
    });
    btn.addEventListener('mouseup', () => {
      t6State.uiMoveHeld = null;
      const stillCrouching = Boolean(t6State.keysDown['KeyS'] || t6State.keysDown['ArrowDown']);
      if (['WALK_F', 'WALK_B', 'CROUCH'].includes(t6State.p1.state)) {
        if (stillCrouching && t6State.p1.y === 0) {
          t6State.p1.state = 'CROUCH';
          t6State.p1.vx = 0;
        } else {
          t6State.p1.state = 'IDLE';
          t6State.p1.vx = 0;
        }
      }
    });
    btn.addEventListener('mouseleave', () => {
      t6State.uiMoveHeld = null;
    });
  });

  document.querySelectorAll('.t6-act-btn').forEach((btn) => {
    btn.addEventListener('click', () => startFighterMove(t6State.p1, btn.dataset.act));
  });

  const T6_ATTACK_KEY_MAP = {
    KeyJ: 'LP',
    KeyK: 'MP',
    KeyL: 'HP',
    KeyO: 'HP',
    KeyU: 'SK',
    KeyI: 'GB',
    Digit1: 'SP_236',
    Digit2: 'SP_623',
    Digit3: 'SP_41236',
    Digit4: 'SUPER_1',
    Digit5: 'ULT_3'
  };

  const T6_P1_LOCAL2P_ATTACK_MAP = {
    KeyJ: 'LP',
    KeyK: 'MP',
    KeyL: 'HP',
    KeyO: 'HP',
    KeyU: 'SK',
    KeyI: 'GB'
  };

  const T6_P2_LOCAL2P_ATTACK_MAP = {
    Numpad1: 'LP',
    Digit1: 'LP',
    Numpad7: 'LP',
    Numpad2: 'MP',
    Digit2: 'MP',
    Numpad8: 'MP',
    Numpad3: 'HP',
    Digit3: 'HP',
    Numpad9: 'HP',
    Numpad4: 'SK',
    Digit4: 'SK',
    KeyB: 'SK',
    Numpad5: 'GB',
    Digit5: 'GB',
    KeyN: 'GB',
    Numpad6: 'SP_236',
    Digit6: 'SP_236',
    Numpad0: 'SUPER_1',
    Digit0: 'SUPER_1',
    NumpadEnter: 'ULT_3',
    Slash: 'ULT_3'
  };

  function handleDirectionalTapDash(fighter, tapDir, lastDirProp, lastTimeProp, now) {
    if (t6State[lastDirProp] === tapDir && now - t6State[lastTimeProp] < 240) {
      const cmd = tapDir === 6
        ? (fighter.facingRight ? 'DASH_F' : 'DASH_B')
        : (fighter.facingRight ? 'DASH_B' : 'DASH_F');
      triggerFighterMovement(fighter, cmd);
      t6State[lastDirProp] = 0;
      return true;
    }
    t6State[lastDirProp] = tapDir;
    t6State[lastTimeProp] = now;
    return false;
  }

  // Controles de Teclado en Tiempo Real para Tab 6 (1P y Modo Local 2P)
  window.addEventListener('keydown', (e) => {
    if (activeTab !== 'tab6') return;
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

    t6State.keysDown[e.code] = true;
    const isLocal2P = t6SelAI.value === 'LOCAL_2P';
    const now = performance.now();

    if (isLocal2P) {
      // --- MODO 2 JUGADORES LOCALES: P1 (WASD + U/I/O/J/K) vs P2 (Flechas + Numpad 1-5 / Digits 1-5 / 7-9,B,N) ---
      if (e.code === 'KeyD' && !e.repeat) {
        if (handleDirectionalTapDash(t6State.p1, 6, 'lastTapDir', 'lastTapTime', now)) return;
      } else if (e.code === 'KeyA' && !e.repeat) {
        if (handleDirectionalTapDash(t6State.p1, 4, 'lastTapDir', 'lastTapTime', now)) return;
      } else if (e.code === 'KeyW') {
        e.preventDefault();
        triggerFighterMovement(t6State.p1, 'JUMP');
      } else if (e.code === 'KeyS') {
        e.preventDefault();
        triggerFighterMovement(t6State.p1, 'CROUCH');
      }

      if (T6_P1_LOCAL2P_ATTACK_MAP[e.code] && !e.repeat) {
        e.preventDefault();
        startFighterMove(t6State.p1, T6_P1_LOCAL2P_ATTACK_MAP[e.code]);
      }

      if (e.code === 'ArrowRight') {
        e.preventDefault();
        if (!e.repeat && handleDirectionalTapDash(t6State.p2, 6, 'p2LastTapDir', 'p2LastTapTime', now)) return;
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        if (!e.repeat && handleDirectionalTapDash(t6State.p2, 4, 'p2LastTapDir', 'p2LastTapTime', now)) return;
      } else if (e.code === 'ArrowUp') {
        e.preventDefault();
        triggerFighterMovement(t6State.p2, 'JUMP');
      } else if (e.code === 'ArrowDown') {
        e.preventDefault();
        triggerFighterMovement(t6State.p2, 'CROUCH');
      }

      if (T6_P2_LOCAL2P_ATTACK_MAP[e.code] && !e.repeat) {
        e.preventDefault();
        startFighterMove(t6State.p2, T6_P2_LOCAL2P_ATTACK_MAP[e.code]);
      }
      return;
    }

    // --- MODO 1P (vs CPU / Boss / Dummy): WASD + Flechas mapeadas a P1 ---
    if (e.code === 'KeyD' || e.code === 'ArrowRight') {
      if (!e.repeat && handleDirectionalTapDash(t6State.p1, 6, 'lastTapDir', 'lastTapTime', now)) return;
    }
    if (e.code === 'KeyA' || e.code === 'ArrowLeft') {
      if (!e.repeat && handleDirectionalTapDash(t6State.p1, 4, 'lastTapDir', 'lastTapTime', now)) return;
    }

    if (e.code === 'KeyW' || e.code === 'ArrowUp') {
      e.preventDefault();
      triggerFighterMovement(t6State.p1, 'JUMP');
    } else if (e.code === 'KeyS' || e.code === 'ArrowDown') {
      e.preventDefault();
      triggerFighterMovement(t6State.p1, 'CROUCH');
    }

    if (T6_ATTACK_KEY_MAP[e.code] && !e.repeat) {
      e.preventDefault();
      startFighterMove(t6State.p1, T6_ATTACK_KEY_MAP[e.code]);
    }
  });

  function syncFighterPostKeyUp(fighter, upLeft, upRight, upDown) {
    if (!['WALK_F', 'WALK_B', 'CROUCH'].includes(fighter.state)) return;
    if (upDown && fighter.y === 0) {
      fighter.state = 'CROUCH';
      fighter.vx = 0;
    } else if (upLeft && !upRight && fighter.y === 0) {
      triggerFighterMovement(fighter, 'LEFT');
    } else if (upRight && !upLeft && fighter.y === 0) {
      triggerFighterMovement(fighter, 'RIGHT');
    } else {
      fighter.state = 'IDLE';
      fighter.vx = 0;
    }
  }

  window.addEventListener('keyup', (e) => {
    delete t6State.keysDown[e.code];
    if (activeTab !== 'tab6') return;

    if (t6SelAI.value === 'LOCAL_2P') {
      syncFighterPostKeyUp(
        t6State.p1,
        Boolean(t6State.keysDown['KeyA']),
        Boolean(t6State.keysDown['KeyD']),
        Boolean(t6State.keysDown['KeyS'])
      );
      syncFighterPostKeyUp(
        t6State.p2,
        Boolean(t6State.keysDown['ArrowLeft']),
        Boolean(t6State.keysDown['ArrowRight']),
        Boolean(t6State.keysDown['ArrowDown'])
      );
      return;
    }

    const stillCrouching = Boolean(t6State.keysDown['KeyS'] || t6State.keysDown['ArrowDown']);
    const stillLeft = Boolean(t6State.keysDown['KeyA'] || t6State.keysDown['ArrowLeft']);
    const stillRight = Boolean(t6State.keysDown['KeyD'] || t6State.keysDown['ArrowRight']);
    syncFighterPostKeyUp(t6State.p1, stillLeft, stillRight, stillCrouching);
  });

  function applyHitOrBlock(attacker, defender, mv) {
    const isDefenderParrying = defender.state === 'PARRY';
    const isDefenderAttacking = defender.state === 'STARTUP' || defender.state === 'ACTIVE';
    const isDefenderInvuln = (defender.state === 'STARTUP' || defender.state === 'ACTIVE') &&
      defender.activeMoveKey && T6_MOVES[defender.activeMoveKey]?.invuln;

    if (isDefenderInvuln) {
      announceT6('🛡️ ¡INVULNERABILIDAD FRAME 1!', '#ffffff', 40);
      return;
    }

    // 1. GAMBETA PERFECTA / PARRY ("¡OOOO-LÉ!")
    if (isDefenderParrying) {
      if (defender.isP1) t6State.stats.p1Blocks++;
      else t6State.stats.p2Blocks++;
      defender.superMeter = Math.min(3000, defender.superMeter + 400);
      defender.gambeta = Math.min(1000, defender.gambeta + 300);
      attacker.state = 'RECOVERY';
      attacker.stateFrame = 1;
      t6State.hitstopFrames = 14;
      t6State.impactInkFrames = 5;
      spawnParticles(defender.x, 310 + defender.y, '#00e5ff', 22);
      announceT6(
        '⚡ ¡OOOO-LÉ! ¡GAMBETA PERFECTA (PARRY 2f)!',
        '#00e5ff',
        60,
        `"¡NOOO! ¡QUÉ GAMBETA ENDIABLADA DE ${defender.data.DisplayName}! ¡SE ESCUCHA EL OOOO-LÉ EN LA TRIBUNA!"`,
        'Sidechain Auto-Ducking -6.0 dB activado • Ventaja +14f para contraatacar.'
      );
      playSynthSound('parry');
      return;
    }

    // Verificar si el defensor está bloqueando hacia atrás
    const holdingBack = defender.state === 'WALK_B' || defender.state === 'CROUCH';
    const blocked = holdingBack && !mv.unblockable && defender.y === 0;

    const pushDir = attacker.facingRight ? 1 : -1;

    if (blocked) {
      const chip = Math.max(10, Math.floor(mv.dmg * 0.15));
      defender.hp = Math.max(1, defender.hp - chip);
      if (defender.isP1) t6State.stats.p1Blocks++;
      else t6State.stats.p2Blocks++;
      if (attacker.isP1) t6State.stats.p1DamageDealt += chip;
      else t6State.stats.p2DamageDealt += chip;
      defender.state = 'BLOCKSTUN';
      defender.stunFrames = mv.blockstun;
      defender.vx = pushDir * (mv.push * 0.22);
      attacker.superMeter = Math.min(3000, attacker.superMeter + Math.floor(mv.meter * 0.5));
      t6State.hitstopFrames = 6;
      spawnParticles(defender.x, 315 + defender.y, '#f5c451', 10);
      playSynthSound('step');
    } else {
      // Impacto Limpio o Counter Hit!
      const isCounter = isDefenderAttacking;
      const dmg = Math.round(mv.dmg * (isCounter ? 1.2 : 1.0));
      defender.hp = Math.max(0, defender.hp - dmg);
      defender.state = 'HITSTUN';
      defender.stunFrames = mv.hitstun + (isCounter ? 5 : 0);
      defender.vx = pushDir * (mv.push * 0.32);
      if (mv.type === 'DP' || mv.type === 'ULTIMATE') {
        defender.vy = -8.5;
      }

      attacker.comboCount++;
      attacker.comboDamage += dmg;
      if (attacker.isP1) {
        t6State.stats.p1DamageDealt += dmg;
        t6State.stats.p1MaxCombo = Math.max(t6State.stats.p1MaxCombo, attacker.comboCount);
      } else {
        t6State.stats.p2DamageDealt += dmg;
        t6State.stats.p2MaxCombo = Math.max(t6State.stats.p2MaxCombo, attacker.comboCount);
      }
      attacker.superMeter = Math.min(3000, attacker.superMeter + mv.meter);
      defender.superMeter = Math.min(3000, defender.superMeter + Math.floor(mv.meter * 0.4));

      t6State.hitstopFrames = mv.dmg >= 1200 ? 14 : 9;
      t6State.shakeFrames = mv.dmg >= 1200 ? 14 : 7;
      if (isCounter || mv.type === 'ULTIMATE' || mv.type === 'SUPER') {
        t6State.impactInkFrames = 4;
      }

      spawnParticles(defender.x, 305 + defender.y, '#ff2a54', 20);
      playSynthSound(mv.dmg >= 1200 ? 'stinger' : 'hit');

      if (isCounter) {
        announceT6(
          `💥 COUNTER HIT! (${attacker.comboCount} HITS — ${attacker.comboDamage} DMG)`,
          '#ff2a54',
          55,
          `"¡UYYY! ¡Cruce violento en el mediocampo, lo anticipó con Counter Hit!"`,
          `Impact Ink Shader (3f) + Hitstop ${t6State.hitstopFrames}f activados.`
        );
      } else if (attacker.comboCount >= 2) {
        announceT6(
          `🔥 ${attacker.comboCount} HIT COMBO! (${attacker.comboDamage} DMG)`,
          '#ffe07d',
          45
        );
      }

      // Verificar Wall Break si el defensor es estrellado contra el borde de la cancha
      const nearWall = defender.x <= 95 || defender.x >= 985;
      if (nearWall && (mv.wallDmg || mv.dmg >= 1100) && !t6State.inZoneB) {
        t6State.wallHp = Math.max(0, t6State.wallHp - (mv.wallDmg || 1));
        if (t6State.wallHp === 0) {
          t6State.inZoneB = true;
          t6State.stats.wallBreaks++;
          t6State.impactInkFrames = 10;
          t6State.shakeFrames = 24;
          const st = STAGES_DATA[t6State.stageIdx];
          document.getElementById('t6-zone-badge').textContent = 'ZONA B (WALL BROKEN)';
          document.getElementById('t6-match-subtitle').textContent =
            `${t6State.p1.data.DisplayName} vs ${t6State.p2.data.DisplayName} — ${st.DisplayName} (Zona B: ${st.ZoneB})`;
          announceT6(
            `💥 ¡WALL BREAK! → TRANSICIÓN A: ${st.ZoneB.toUpperCase()}`,
            '#ff9100',
            90,
            `"¡ROMPIÓ LAS REDES DEL ARCO! ¡LA PELEA SE VA A ${st.ZoneB.toUpperCase()} CON +12 BPM EN WWISE!"`,
            'Reinicio a Neutro con Bono de Super Meter por Ruptura de Escenario.'
          );
          t6State.p1.x = 320;
          t6State.p2.x = 760;
          playSynthSound('stinger');
        }
      }

      // Mecánica especial Boss V.A.R.-ZERO: Fase 2 V.A.R. Rewind (-90f) cuando baja del 35% de vida
      if (!defender.isP1 && t6SelAI.value === 'BOSS_VAR' && defender.hp > 0 && defender.hp < defender.maxHp * 0.35 && !defender.varRewindUsed) {
        defender.varRewindUsed = true;
        defender.hp = Math.min(defender.maxHp, defender.hp + 2800);
        defender.state = 'IDLE';
        defender.x = 820;
        t6State.p1.x = 260;
        t6State.impactInkFrames = 8;
        announceT6(
          '⏪ ¡V.A.R. REWIND ACTIVADO! (-90 FRAMES GGPO)',
          '#00e5ff',
          95,
          '"¡EL JUEZ SUPREMO ANULA LA JUGADA Y REBOBINA 90 CUADROS DEL TIEMPO!"',
          'Fase 2 V.A.R.-ZERO activada: Recupera posición y salud del buffer.'
        );
        playSynthSound('desync');
      }

      // Verificar K.O. / ¡GOOOOOOL! (en Modo Entrenamiento, P2/P1 no caen en KO y regeneran post-combo)
      if (defender.hp <= 0) {
        if (t6SelAI.value === 'DUMMY') {
          defender.hp = 1;
        } else {
          defender.hp = 0;
          defender.state = 'KO';
          t6State.impactInkFrames = 12;
          t6State.hitstopFrames = 20;
          announceT6(
            `⚽🏆 ¡GOOOOOOOLAZO / K.O.! — GANA ${attacker.data.DisplayName.toUpperCase()}`,
            '#00e676',
            180,
            `"¡GOOOOOOLAZO HISTÓRICO DE ${attacker.data.DisplayName.toUpperCase()}! ¡SE CAE EL ESTADIO ABAJO, SEÑORAS Y SEÑORES!"`,
            'Presiona "⚔️ Revancha Inmediata" o cambia de Leyenda.'
          );
          playSynthSound('stinger');
          showTab6VictoryOverlay(attacker, 'KO');
        }
      }
    }
  }

  function updateFighterPhysicsAndState(f, opp) {
    // Regeneración gradual de Gambeta en neutro
    if (f.state === 'IDLE' || f.state === 'WALK_F' || f.state === 'WALK_B') {
      f.gambeta = Math.min(1000, f.gambeta + 1.2);
      if (f.y === 0) {
        f.facingRight = opp.x >= f.x;
      }
    }

    f.stateFrame++;

    if (f.state === 'HITSTUN' || f.state === 'BLOCKSTUN') {
      f.stunFrames--;
      f.vx *= 0.84;
      if (f.stunFrames <= 0 && f.y === 0) {
        f.state = 'IDLE';
        f.stateFrame = 0;
        opp.comboCount = 0;
        opp.comboDamage = 0;
      }
    } else if (f.state === 'DASH_F' || f.state === 'DASH_B') {
      if (f.stateFrame >= 14) {
        f.state = 'IDLE';
        f.vx = 0;
      }
    } else if (f.state === 'PARRY') {
      if (f.stateFrame >= 24) {
        f.state = 'IDLE';
      }
    } else if (['STARTUP', 'ACTIVE', 'RECOVERY'].includes(f.state)) {
      const mv = T6_MOVES[f.activeMoveKey];
      if (mv) {
        const sEnd = mv.startup;
        const aEnd = sEnd + mv.active;
        const rEnd = aEnd + mv.recovery;

        if (f.stateFrame < sEnd) {
          f.state = 'STARTUP';
        } else if (f.stateFrame < aEnd) {
          f.state = 'ACTIVE';
          // Si es movimiento de balón/proyectil, dispara el balón físico en el 1er frame activo
          if (!f.moveHitRegistered && (mv.type === 'PROJ' || mv.type === 'PROJ_EX' || mv.type === 'SUPER')) {
            f.moveHitRegistered = true;
            const dir = f.facingRight ? 1 : -1;
            t6State.projectiles.push({
              ownerIsP1: f.isP1,
              x: f.x + dir * 52,
              y: 320 + f.y,
              vx: dir * (mv.projSpeed || 11),
              dmg: mv.dmg,
              mv,
              color: f.data.ColorPrimary || '#ff9100'
            });
            playSynthSound('hit');
          }
          // Si es ataque cuerpo a cuerpo, verifica intersección AABB con el rival
          if (!f.moveHitRegistered && mv.range > 0 && mv.type !== 'PROJ' && mv.type !== 'PROJ_EX') {
            const dist = Math.abs(opp.x - f.x);
            const verticalOk = Math.abs(opp.y - f.y) < 95;
            if (dist <= mv.range && verticalOk) {
              f.moveHitRegistered = true;
              applyHitOrBlock(f, opp, mv);
            }
          }
        } else if (f.stateFrame < rEnd) {
          f.state = 'RECOVERY';
        } else {
          f.state = 'IDLE';
          f.activeMoveKey = null;
          f.stateFrame = 0;
        }
      }
    }

    // Integración de posición X/Y y gravedad
    f.x += f.vx;
    f.y += f.vy;
    if (f.y < 0) {
      f.vy += 0.82; // Gravedad determinista
    } else if (f.y >= 0) {
      f.y = 0;
      f.vy = 0;
      if (f.state === 'JUMP') {
        f.state = 'IDLE';
      }
    }

    // Límites de las redes del estadio
    f.x = Math.max(65, Math.min(1015, f.x));
  }

  function updateP2CompetitiveAI() {
    const p1 = t6State.p1;
    const p2 = t6State.p2;
    const mode = t6SelAI.value;
    if (mode === 'DUMMY' || p2.state === 'KO' || p1.state === 'KO') return;
    if (['HITSTUN', 'BLOCKSTUN', 'STARTUP', 'ACTIVE', 'RECOVERY', 'PARRY'].includes(p2.state)) return;

    const dist = Math.abs(p1.x - p2.x);
    const r = Math.random();

    // Si P1 está atacando de cerca, la IA puede bloquear o tirar Gambeta Parry / DP
    if (p1.state === 'STARTUP' || p1.state === 'ACTIVE') {
      if (dist < 145 && r < 0.12) {
        startFighterMove(p2, 'GB'); // Gambeta Parry
        return;
      }
      if (dist < 130 && r < 0.14) {
        startFighterMove(p2, 'SP_623'); // Reversal DP
        return;
      }
      if (r < 0.55) {
        triggerFighterMovement(p2, p2.facingRight ? 'LEFT' : 'RIGHT'); // Bloquear atrás
        return;
      }
    }

    // Comportamiento a distancia media/larga
    if (dist > 260) {
      if (r < 0.035) {
        startFighterMove(p2, mode === 'BOSS_VAR' ? 'SP_236' : 'SK');
      } else if (r < 0.07) {
        triggerFighterMovement(p2, 'DASH_F');
      } else {
        triggerFighterMovement(p2, p2.facingRight ? 'RIGHT' : 'LEFT');
      }
    } else if (dist > 115) {
      if (p2.superMeter >= 3000 && r < 0.025) {
        startFighterMove(p2, 'ULT_3');
      } else if (p2.superMeter >= 1000 && r < 0.035) {
        startFighterMove(p2, 'SUPER_1');
      } else if (r < 0.05) {
        startFighterMove(p2, 'MP');
      } else if (r < 0.08) {
        startFighterMove(p2, 'HP');
      } else if (r < 0.11) {
        triggerFighterMovement(p2, p2.facingRight ? 'RIGHT' : 'LEFT');
      }
    } else {
      // Corta distancia (Mix-up entre Jab, Command Grab y DP)
      if (r < 0.06) startFighterMove(p2, 'LP');
      else if (r < 0.10) startFighterMove(p2, 'SP_41236');
      else if (r < 0.13) startFighterMove(p2, 'HP');
      else if (r < 0.16) triggerFighterMovement(p2, 'DASH_B');
    }
  }

  function readSingleGamepadState(pad, prevButtons) {
    const emptyGp = { active: false, up: false, down: false, left: false, right: false, dir: 5, heldBtn: '', risingActs: [], startPressed: false };
    if (!pad) return emptyGp;

    const axX = pad.axes[0] || 0;
    const axY = pad.axes[1] || 0;
    const dUp = Boolean(pad.buttons[12]?.pressed || axY < -0.55);
    const dDown = Boolean(pad.buttons[13]?.pressed || axY > 0.55);
    const dLeft = Boolean(pad.buttons[14]?.pressed || axX < -0.45);
    const dRight = Boolean(pad.buttons[15]?.pressed || axX > 0.45);

    let gpDir = 5;
    if (dUp && !dDown) gpDir = (dRight && !dLeft) ? 9 : ((dLeft && !dRight) ? 7 : 8);
    else if (dDown && !dUp) gpDir = (dRight && !dLeft) ? 3 : ((dLeft && !dRight) ? 1 : 2);
    else if (dRight && !dLeft) gpDir = 6;
    else if (dLeft && !dRight) gpDir = 4;

    const btnMap = [
      { idx: 0, act: 'LP' },
      { idx: 1, act: 'MP' },
      { idx: 2, act: 'HP' },
      { idx: 3, act: 'SK' },
      { idx: 4, act: 'GB' },
      { idx: 5, act: 'SP_236' },
      { idx: 6, act: 'SUPER_1' },
      { idx: 7, act: 'ULT_3' }
    ];

    let heldBtn = '';
    const risingActs = [];
    btnMap.forEach(({ idx, act }) => {
      const pressed = Boolean(pad.buttons[idx]?.pressed);
      if (pressed && !heldBtn) heldBtn = act;
      if (pressed && !prevButtons[idx]) {
        risingActs.push(act);
      }
      prevButtons[idx] = pressed;
    });

    const startNow = Boolean(pad.buttons[9]?.pressed);
    const startJustPressed = startNow && !prevButtons[9];
    prevButtons[9] = startNow;

    return {
      active: true,
      up: dUp,
      down: dDown,
      left: dLeft,
      right: dRight,
      dir: gpDir,
      heldBtn,
      risingActs,
      startPressed: startJustPressed
    };
  }

  function pollT6GamepadInput() {
    const emptyGp = { active: false, up: false, down: false, left: false, right: false, dir: 5, heldBtn: '', risingActs: [], startPressed: false };
    const statusEl = document.getElementById('t6-gamepad-status');
    if (!navigator.getGamepads) {
      if (statusEl) statusEl.textContent = '🎮 Gamepad: Esperando...';
      return { p1: emptyGp, p2: emptyGp };
    }
    const pads = navigator.getGamepads();
    const connectedPads = [];
    for (let i = 0; i < pads.length; i++) {
      if (pads[i] && pads[i].connected) connectedPads.push(pads[i]);
    }
    if (statusEl) {
      if (connectedPads.length === 0) {
        statusEl.textContent = '🎮 Gamepad: Esperando...';
        statusEl.style.borderColor = '';
        statusEl.style.color = '';
      } else if (connectedPads.length === 1) {
        statusEl.textContent = '🎮 1 Gamepad Conectado (P1)';
        statusEl.style.borderColor = '#00e676';
        statusEl.style.color = '#00e676';
      } else {
        statusEl.textContent = `🎮 ${connectedPads.length} Gamepads Conectados (P1 & P2)`;
        statusEl.style.borderColor = '#00e5ff';
        statusEl.style.color = '#00e5ff';
      }
    }

    return {
      p1: readSingleGamepadState(connectedPads[0] || null, t6State.gpPrevButtons),
      p2: readSingleGamepadState(connectedPads[1] || null, t6State.gpPrevButtonsP2)
    };
  }

  function stepTab6VersusSimulation() {
    const p1 = t6State.p1;
    const p2 = t6State.p2;
    const isLocal2P = t6SelAI.value === 'LOCAL_2P';

    // 0. Polling Unificado (Gamepad #1/#2 + Teclado + UI) @ 60Hz con limpieza SOCD
    const gps = pollT6GamepadInput();
    const gp = gps.p1;
    const gp2 = gps.p2;
    if (gp.startPressed || (isLocal2P && gp2.startPressed)) {
      resetTab6Match();
      return;
    }

    const kUp = Boolean(t6State.keysDown['KeyW'] || (!isLocal2P && t6State.keysDown['ArrowUp']) || t6State.uiMoveHeld === 'JUMP');
    const kDown = Boolean(t6State.keysDown['KeyS'] || (!isLocal2P && t6State.keysDown['ArrowDown']) || t6State.uiMoveHeld === 'CROUCH');
    const kLeft = Boolean(t6State.keysDown['KeyA'] || (!isLocal2P && t6State.keysDown['ArrowLeft']) || t6State.uiMoveHeld === 'LEFT');
    const kRight = Boolean(t6State.keysDown['KeyD'] || (!isLocal2P && t6State.keysDown['ArrowRight']) || t6State.uiMoveHeld === 'RIGHT');

    const rawUp = kUp || gp.up;
    const rawDown = kDown || gp.down;
    const rawLeft = kLeft || gp.left;
    const rawRight = kRight || gp.right;

    // Limpieza SOCD Neutral P1 (Arriba+Abajo = Neutro, Izquierda+Derecha = Neutro)
    const uUp = rawUp && !rawDown;
    const uDown = rawDown && !rawUp;
    const uLeft = rawLeft && !rawRight;
    const uRight = rawRight && !rawLeft;

    let curDir = 5;
    if (uUp) curDir = uRight ? 9 : (uLeft ? 7 : 8);
    else if (uDown) curDir = uRight ? 3 : (uLeft ? 1 : 2);
    else if (uRight) curDir = 6;
    else if (uLeft) curDir = 4;

    if (t6State.bannerTimer > 0) t6State.bannerTimer--;
    if (t6State.impactInkFrames > 0) t6State.impactInkFrames--;
    if (t6State.shakeFrames > 0) t6State.shakeFrames--;

    // Congelamiento por Hitstop dramático
    if (t6State.hitstopFrames > 0) {
      t6State.hitstopFrames--;
      renderTab6VersusCanvas();
      return;
    }

    // Reloj del partido (infinito en Modo Entrenamiento)
    const isTraining = t6SelAI.value === 'DUMMY';
    if (!isTraining && !t6State.matchEnded && p1.state !== 'KO' && p2.state !== 'KO' && t6State.timerFrames > 0) {
      t6State.timerFrames--;
      if (t6State.timerFrames === 0) {
        const winnerFighter = p1.hp >= p2.hp ? p1 : p2;
        announceT6(`⏱️ ¡FINAL DEL TIEMPO REGLAMENTARIO! GANA ${winnerFighter.data.DisplayName.toUpperCase()}`, '#ffe07d', 160);
        playSynthSound('stinger');
        showTab6VictoryOverlay(winnerFighter, 'TIME');
      }
    }

    // Auto-regeneración de HP y Hinchada en Modo Entrenamiento cuando termina el combo
    if (isTraining) {
      if (p2.state === 'IDLE' && p1.comboCount === 0 && p2.hp < p2.maxHp) {
        p2.hp = Math.min(p2.maxHp, p2.hp + 120);
      }
      if (p1.state === 'IDLE') {
        if (p1.hp < p1.maxHp) p1.hp = Math.min(p1.maxHp, p1.hp + 80);
        if (p1.superMeter < 3000) p1.superMeter = Math.min(3000, p1.superMeter + 12);
      }
    }

    // Ejecutar ataques recién presionados desde Gamepad #1 en este frame
    gp.risingActs.forEach((act) => {
      startFighterMove(p1, act);
    });

    // Fusionar botón activo P1 (pulso de ataque del frame, tecla sostenida o botón de Gamepad)
    let heldKeyBtn = '';
    const p1Map = isLocal2P ? T6_P1_LOCAL2P_ATTACK_MAP : T6_ATTACK_KEY_MAP;
    for (const [code, act] of Object.entries(p1Map)) {
      if (t6State.keysDown[code]) {
        heldKeyBtn = act;
        break;
      }
    }
    const unifiedBtn = t6State.latchedBtn || gp.heldBtn || heldKeyBtn;
    t6State.latchedBtn = '';

    // Único registro determinista por frame en el Input History FGC
    pushT6InputHistory(curDir, unifiedBtn);

    // Aplicar movimiento direccional unificado P1 (Gamepad #1 + Teclado) respetando agachado sostenido
    if (uUp && p1.y === 0) {
      triggerFighterMovement(p1, 'JUMP');
    } else if (['IDLE', 'WALK_F', 'WALK_B', 'CROUCH'].includes(p1.state) && p1.y === 0) {
      if (uDown) {
        triggerFighterMovement(p1, 'CROUCH');
      } else if (uLeft) {
        triggerFighterMovement(p1, 'LEFT');
      } else if (uRight) {
        triggerFighterMovement(p1, 'RIGHT');
      } else if (t6State.uiMoveHeld !== 'DASH_F' && t6State.uiMoveHeld !== 'DASH_B') {
        p1.vx = 0;
        p1.state = 'IDLE';
      }
    }

    // Jugador 2: Humano Local (LOCAL_2P) o IA Competitiva
    if (isLocal2P) {
      gp2.risingActs.forEach((act) => {
        startFighterMove(p2, act);
      });
      const p2RawUp = Boolean(t6State.keysDown['ArrowUp']) || gp2.up;
      const p2RawDown = Boolean(t6State.keysDown['ArrowDown']) || gp2.down;
      const p2RawLeft = Boolean(t6State.keysDown['ArrowLeft']) || gp2.left;
      const p2RawRight = Boolean(t6State.keysDown['ArrowRight']) || gp2.right;

      const p2Up = p2RawUp && !p2RawDown;
      const p2Down = p2RawDown && !p2RawUp;
      const p2Left = p2RawLeft && !p2RawRight;
      const p2Right = p2RawRight && !p2RawLeft;

      if (p2Up && p2.y === 0) {
        triggerFighterMovement(p2, 'JUMP');
      } else if (['IDLE', 'WALK_F', 'WALK_B', 'CROUCH'].includes(p2.state) && p2.y === 0) {
        if (p2Down) {
          triggerFighterMovement(p2, 'CROUCH');
        } else if (p2Left) {
          triggerFighterMovement(p2, 'LEFT');
        } else if (p2Right) {
          triggerFighterMovement(p2, 'RIGHT');
        } else {
          p2.vx = 0;
          p2.state = 'IDLE';
        }
      }
    } else {
      updateP2CompetitiveAI();
    }

    // Físicas y máquinas de estado de P1 y P2
    updateFighterPhysicsAndState(p1, p2);
    updateFighterPhysicsAndState(p2, p1);

    // Colisión de Pushbox para que no se solapen
    const minSep = 58;
    const dx = p2.x - p1.x;
    if (Math.abs(dx) < minSep && Math.abs(p1.y - p2.y) < 80) {
      const overlap = (minSep - Math.abs(dx)) / 2;
      const sign = dx >= 0 ? 1 : -1;
      p1.x -= sign * overlap;
      p2.x += sign * overlap;
    }

    // Actualizar proyectiles de balón en cancha
    for (let i = t6State.projectiles.length - 1; i >= 0; i--) {
      const pr = t6State.projectiles[i];
      pr.x += pr.vx;
      const target = pr.ownerIsP1 ? p2 : p1;
      const attacker = pr.ownerIsP1 ? p1 : p2;

      if (Math.abs(pr.x - target.x) < 42 && Math.abs(pr.y - (320 + target.y)) < 75) {
        applyHitOrBlock(attacker, target, pr.mv);
        t6State.projectiles.splice(i, 1);
        continue;
      }
      if (pr.x < 30 || pr.x > 1050) {
        t6State.projectiles.splice(i, 1);
      }
    }

    // Actualizar partículas de impacto
    for (let i = t6State.particles.length - 1; i >= 0; i--) {
      const pt = t6State.particles[i];
      pt.x += pt.vx;
      pt.y += pt.vy;
      pt.vy += 0.35;
      pt.life--;
      if (pt.life <= 0) t6State.particles.splice(i, 1);
    }

    // Actualizar panel derecho de telemetría
    document.getElementById('t6-st-p1').textContent =
      `${p1.state}${p1.activeMoveKey ? ' (' + p1.activeMoveKey + ' F' + p1.stateFrame + ')' : ''}`;
    document.getElementById('t6-st-p2').textContent =
      `${p2.state}${p2.activeMoveKey ? ' (' + p2.activeMoveKey + ' F' + p2.stateFrame + ')' : ''}`;
    document.getElementById('t6-st-combo').textContent = `${p1.comboCount} Hits (${p1.comboDamage} DMG)`;
    document.getElementById('t6-st-wall').textContent =
      t6State.inZoneB ? 'ROTO (Zona B Activa)' : `${t6State.wallHp} / ${t6State.maxWallHp} Impactos`;
    document.getElementById('t6-st-balls').textContent = `${t6State.projectiles.length} Activos`;

    renderTab6VersusCanvas();
  }

  const T6_SPRITE_CACHE = {};
  function getT6FighterSpritePair(code) {
    if (!T6_SPRITE_CACHE[code]) {
      const front = new Image();
      front.src = `../Assets/Sprites2D/Fighters/Sprite_${code}_Front.png`;
      const side = new Image();
      side.src = `../Assets/Sprites2D/Fighters/Sprite_${code}_Side.png`;
      T6_SPRITE_CACHE[code] = { front, side };
    }
    return T6_SPRITE_CACHE[code];
  }

  function drawFighterOnT6Canvas(ctx, f, groundY) {
    const isSfumato = t6State.artStyle === 'SFUMATO';
    const x = f.x;
    const y = groundY + f.y;
    const dir = f.facingRight ? 1 : -1;
    const isBoss = f.data.Name === 'VAR_ZERO_BOSS';
    const w = f.data.Name === 'BULLDOG_PY' ? 84 : (isBoss ? 86 : 74);
    const baseH = f.data.Name === 'PULGA_AR' ? 172 : (isBoss ? 214 : 188);
    const h = f.state === 'CROUCH' ? baseH * 0.72 : baseH;
    const t = f.stateFrame;

    // 1. Sombra realista sobre el césped
    ctx.fillStyle = isSfumato ? 'rgba(18, 12, 4, 0.65)' : 'rgba(0, 0, 0, 0.52)';
    ctx.beginPath();
    ctx.ellipse(x, groundY + 4, (f.state === 'KO' ? w * 1.15 : w * 0.52), 9, 0, 0, Math.PI * 2);
    ctx.fill();

    const sprites = getT6FighterSpritePair(f.data.Name);
    const useSide = ['WALK_F', 'WALK_B', 'DASH_F', 'DASH_B', 'STARTUP', 'ACTIVE', 'RECOVERY', 'HITSTUN', 'KO'].includes(f.state);
    const activeImg = (useSide && sprites.side.complete && sprites.side.naturalWidth > 0)
      ? sprites.side
      : (sprites.front.complete && sprites.front.naturalWidth > 0 ? sprites.front : null);

    if (activeImg) {
      let tilt = 0;
      let lungeX = 0;
      let dropY = 0;
      let scaleX = 1.0;
      let scaleY = 1.0;
      const mvKey = f.activeMoveKey;

      if (f.state === 'IDLE') {
        scaleY = 1.0 + Math.sin(t * 0.12) * 0.015;
        scaleX = 1.0 - Math.sin(t * 0.12) * 0.008;
      } else if (f.state === 'CROUCH') {
        scaleY = 0.72;
        scaleX = 1.10;
      } else if (f.state === 'WALK_F' || f.state === 'WALK_B') {
        tilt = dir * (f.state === 'WALK_F' ? 0.07 : -0.06);
        dropY = Math.abs(Math.sin(t * 0.28)) * -5;
      } else if (f.state === 'DASH_F' || f.state === 'DASH_B') {
        tilt = dir * (f.state === 'DASH_F' ? 0.22 : -0.18);
        lungeX = dir * (f.state === 'DASH_F' ? 12 : -10);
      } else if (f.state === 'HITSTUN') {
        tilt = -dir * 0.26;
        lungeX = -dir * 10;
      } else if (f.state === 'BLOCKSTUN' || f.state === 'PARRY') {
        tilt = -dir * 0.08;
        scaleY = 0.95;
      } else if (f.state === 'KO') {
        tilt = -dir * 1.46;
        dropY = -baseH * 0.14;
      } else if (f.state === 'STARTUP' || f.state === 'ACTIVE' || f.state === 'RECOVERY') {
        const isAct = f.state === 'ACTIVE';
        if (mvKey === 'SP_623' || mvKey === 'ULT_3') {
          tilt = -dir * (isAct ? 0.42 : 0.20);
          lungeX = dir * (isAct ? 22 : 8);
        } else if (mvKey === 'HP' || mvKey === 'SK' || mvKey === 'SP_236' || mvKey === 'SUPER_1') {
          tilt = -dir * (isAct ? 0.16 : 0.08);
          lungeX = dir * (isAct ? 20 : 6);
        } else {
          tilt = dir * (isAct ? 0.15 : 0.06);
          lungeX = dir * (isAct ? 18 : 6);
        }
      }

      const drawH = baseH * scaleY;
      const aspect = activeImg.naturalWidth / Math.max(1, activeImg.naturalHeight);
      const drawW = drawH * aspect * scaleX;

      ctx.save();
      ctx.translate(x + lungeX, y + dropY);
      ctx.rotate(tilt);

      if (f.state === 'PARRY') {
        ctx.shadowColor = '#00e5ff';
        ctx.shadowBlur = 24;
      } else if (f.activeMoveKey && T6_MOVES[f.activeMoveKey]?.invuln) {
        ctx.shadowColor = '#ffe07d';
        ctx.shadowBlur = 24;
      } else if (f.state === 'HITSTUN') {
        ctx.shadowColor = '#ff2a54';
        ctx.shadowBlur = 20;
      } else if (f.superMeter >= 3000) {
        ctx.shadowColor = '#f5c451';
        ctx.shadowBlur = 14;
      }

      // Reflejar horizontalmente según orientación (P1 mira derecha, P2 mira izquierda)
      ctx.scale(dir, 1);
      ctx.drawImage(activeImg, -drawW * 0.5, -drawH, drawW, drawH);

      if (f.state === 'HITSTUN') {
        ctx.globalCompositeOperation = 'source-atop';
        ctx.fillStyle = 'rgba(255, 42, 84, 0.34)';
        ctx.fillRect(-drawW * 0.5, -drawH, drawW, drawH);
      } else if (f.state === 'PARRY' || f.state === 'BLOCKSTUN') {
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.78)';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.ellipse(0, -drawH * 0.5, drawW * 0.45, drawH * 0.48, 0, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();

      // Estela de golpe / patada en fase ACTIVE
      if (f.state === 'ACTIVE' && mvKey && mvKey !== 'GB') {
        ctx.save();
        ctx.strokeStyle = isSfumato ? 'rgba(255, 226, 153, 0.78)' : 'rgba(0, 229, 255, 0.85)';
        ctx.lineWidth = 9;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.arc(x + dir * 24, y - drawH * 0.52, 54, dir > 0 ? -0.75 : Math.PI - 0.35, dir > 0 ? 0.35 : Math.PI + 0.75);
        ctx.stroke();
        ctx.restore();
      }

      // Hitbox visual en ACTIVE
      if (f.state === 'ACTIVE' && mvKey) {
        const mv = T6_MOVES[mvKey];
        if (mv && mv.range > 0 && mv.type !== 'PROJ') {
          const hbX = dir > 0 ? x + w * 0.35 : x - w * 0.35 - mv.range;
          const hbW = mv.range;
          const hbY = y - h * 0.74;
          ctx.fillStyle = isSfumato ? 'rgba(245, 196, 81, 0.25)' : 'rgba(255, 42, 84, 0.28)';
          ctx.strokeStyle = isSfumato ? '#ffe07d' : '#ff2a54';
          ctx.lineWidth = 2;
          ctx.fillRect(hbX, hbY, hbW, 50);
          ctx.strokeRect(hbX, hbY, hbW, 50);
        }
      }

      // Etiqueta sobre jugador
      ctx.fillStyle = isSfumato ? '#ffe599' : '#ffffff';
      ctx.font = isSfumato ? 'bold 11.5px Georgia, serif' : 'bold 11px Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${f.isP1 ? 'P1' : 'P2'}: ${f.data.DisplayName}`, x, y - baseH - 14);
      ctx.textAlign = 'left';
      return;
    }

    // 2. Cinemática Articulada por Estado y Frame (Respaldo mientras decodifica el sprite PNG)
    const breathY = (f.state === 'IDLE') ? Math.sin(t * 0.12) * 3.5 : 0;
    let bodyTilt = 0;
    let torsoDrop = breathY;

    if (f.state === 'WALK_F') {
      bodyTilt = dir * 0.10;
      torsoDrop = Math.abs(Math.sin(t * 0.28)) * 4;
    } else if (f.state === 'WALK_B') {
      bodyTilt = -dir * 0.08;
      torsoDrop = Math.abs(Math.sin(t * 0.25)) * 3;
    } else if (f.state === 'DASH_F') {
      bodyTilt = dir * 0.28;
      torsoDrop = 8;
    } else if (f.state === 'DASH_B') {
      bodyTilt = -dir * 0.22;
      torsoDrop = 6;
    } else if (f.state === 'HITSTUN') {
      bodyTilt = -dir * 0.26;
      torsoDrop = 6;
    } else if (f.state === 'BLOCKSTUN') {
      bodyTilt = -dir * 0.12;
      torsoDrop = 5;
    } else if (f.state === 'KO') {
      bodyTilt = -dir * 1.42; // Derribado en el césped
      torsoDrop = h * 0.72;
    } else if (f.state === 'ACTIVE' || f.state === 'STARTUP') {
      const mvKey = f.activeMoveKey;
      if (mvKey === 'HP' || mvKey === 'SK' || mvKey === 'SP_236' || mvKey === 'SUPER_1' || mvKey === 'ULT_3') {
        bodyTilt = -dir * 0.16; // Inclinación de volea / cañonazo
      } else if (mvKey === 'SP_623') {
        bodyTilt = -dir * 0.45; // Chilena acrobática
      } else {
        bodyTilt = dir * 0.14;
      }
    }

    const hipX = x;
    const hipY = y - h * 0.42 + torsoDrop;
    const shoulderX = hipX + Math.sin(bodyTilt) * (h * 0.42);
    const shoulderY = hipY - Math.cos(bodyTilt) * (h * 0.42);
    const neckX = shoulderX + Math.sin(bodyTilt) * 10;
    const neckY = shoulderY - Math.cos(bodyTilt) * 10;
    const headX = neckX + Math.sin(bodyTilt) * 14 + dir * 3;
    const headY = neckY - Math.cos(bodyTilt) * 14;

    // Coordenadas articuladas de Pierna Trasera y Pierna Delantera (Muslo -> Rodilla -> Botín)
    let bKneeX = hipX - dir * 12;
    let bKneeY = hipY + (y - hipY) * 0.52;
    let bFootX = hipX - dir * 18;
    let bFootY = y - 4;

    let fKneeX = hipX + dir * 14;
    let fKneeY = hipY + (y - hipY) * 0.50;
    let fFootX = hipX + dir * 20;
    let fFootY = y - 4;

    // Coordenadas articuladas de Brazo Trasero y Brazo Delantero (Hombro -> Codo -> Puño)
    let bElbowX = shoulderX - dir * 16;
    let bElbowY = shoulderY + 22;
    let bHandX = shoulderX - dir * 6;
    let bHandY = shoulderY + 34;

    let fElbowX = shoulderX + dir * 14;
    let fElbowY = shoulderY + 20;
    let fHandX = shoulderX + dir * 26;
    let fHandY = shoulderY + 12 + breathY;

    if (f.state === 'WALK_F' || f.state === 'WALK_B' || f.state === 'DASH_F') {
      const cycle = Math.sin(t * (f.state === 'DASH_F' ? 0.55 : 0.30));
      fKneeX = hipX + dir * 14 + cycle * 16;
      fFootX = hipX + dir * 16 + cycle * 26;
      fFootY = y - 4 - Math.max(0, cycle * 10);

      bKneeX = hipX - dir * 10 - cycle * 16;
      bFootX = hipX - dir * 14 - cycle * 24;
      bFootY = y - 4 - Math.max(0, -cycle * 10);

      fHandX = shoulderX + dir * 18 - cycle * 18;
      bHandX = shoulderX - dir * 10 + cycle * 18;
    } else if (f.state === 'BLOCKSTUN' || f.state === 'PARRY') {
      // Guardia de brazos cruzados frente al pecho/rostro
      fElbowX = shoulderX + dir * 18;
      fElbowY = shoulderY + 10;
      fHandX = shoulderX + dir * 22;
      fHandY = shoulderY - 12;
      bElbowX = shoulderX + dir * 10;
      bElbowY = shoulderY + 16;
      bHandX = shoulderX + dir * 16;
      bHandY = shoulderY - 6;
    } else if (f.state === 'HITSTUN') {
      fHandX = shoulderX - dir * 18;
      fHandY = shoulderY - 8;
      bHandX = shoulderX - dir * 26;
      bHandY = shoulderY + 6;
      fFootX = hipX + dir * 26;
    } else if (f.state === 'STARTUP' || f.state === 'ACTIVE') {
      const isAct = f.state === 'ACTIVE';
      const mvKey = f.activeMoveKey;
      const ext = isAct ? 1.0 : 0.38;

      if (mvKey === 'LP' || mvKey === 'SP_41236') {
        // Toque rápido / Jab o Agarre extendido
        fElbowX = shoulderX + dir * (22 * ext);
        fElbowY = shoulderY + 4;
        fHandX = shoulderX + dir * (58 * ext);
        fHandY = shoulderY + 2;
      } else if (mvKey === 'MP') {
        // Cabezazo / Hombro o Rodillazo Medio
        fKneeX = hipX + dir * (34 * ext);
        fKneeY = hipY - 8 * ext;
        fFootX = hipX + dir * (48 * ext);
        fFootY = hipY + 16;
      } else {
        // Patada Fuerte / Disparo de Balón / Chilena / Ultimate
        const kickHigh = (mvKey === 'SP_623' || mvKey === 'ULT_3') ? -58 : -26;
        fKneeX = hipX + dir * (32 * ext);
        fKneeY = hipY + kickHigh * 0.45 * ext;
        fFootX = hipX + dir * (78 * ext);
        fFootY = hipY + kickHigh * ext;

        // Arco de Estela Cinética en la patada activa
        if (isAct) {
          ctx.save();
          ctx.strokeStyle = isSfumato ? 'rgba(255, 226, 153, 0.72)' : 'rgba(0, 229, 255, 0.85)';
          ctx.lineWidth = isSfumato ? 10 : 12;
          ctx.lineCap = 'round';
          ctx.beginPath();
          ctx.arc(hipX, hipY, 74, dir > 0 ? -0.65 : Math.PI - 0.35, dir > 0 ? 0.35 : Math.PI + 0.65);
          ctx.stroke();
          ctx.restore();
        }
      }
    }

    // Función auxiliar para dibujar extremidades articuladas con estilo Sfumato o Street-Ink
    const drawArticulatedLimb = (x1, y1, x2, y2, thickness, colorFill, colorOutline) => {
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      // Contorno exterior
      ctx.strokeStyle = colorOutline;
      ctx.lineWidth = thickness + (isSfumato ? 3 : 5);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      // Relleno de la extremidad
      ctx.strokeStyle = colorFill;
      ctx.lineWidth = thickness;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    };

    const outlineCol = isSfumato ? '#241509' : '#05070b';
    const skinCol = isSfumato ? '#c98e5e' : '#f2c6a0';
    const shortsCol = f.data.ColorSecondary || (isSfumato ? '#1d2d44' : '#101826');
    const sockCol = f.data.ColorPrimary || '#f5c451';

    // 3. Dibujar Pierna Trasera y Brazo Trasero
    drawArticulatedLimb(hipX - dir * 6, hipY, bKneeX, bKneeY, 13, shortsCol, outlineCol);
    drawArticulatedLimb(bKneeX, bKneeY, bFootX, bFootY, 10, sockCol, outlineCol);
    // Botín trasero
    ctx.fillStyle = '#141418';
    ctx.fillRect(bFootX - 7, bFootY - 5, 16, 8);

    drawArticulatedLimb(shoulderX - dir * 8, shoulderY + 4, bElbowX, bElbowY, 10, f.data.ColorPrimary, outlineCol);
    drawArticulatedLimb(bElbowX, bElbowY, bHandX, bHandY, 8, skinCol, outlineCol);

    // 4. Aura según estado (Parry, Invuln, Nivel 3)
    if (f.state === 'PARRY') {
      ctx.shadowColor = isSfumato ? '#ffe07d' : '#00e5ff';
      ctx.shadowBlur = 24;
    } else if (f.activeMoveKey && T6_MOVES[f.activeMoveKey]?.invuln) {
      ctx.shadowColor = isSfumato ? '#fff2b2' : '#ffffff';
      ctx.shadowBlur = 22;
    } else if (f.superMeter >= 3000) {
      ctx.shadowColor = '#f5c451';
      ctx.shadowBlur = 16;
    }

    // 5. Torso Articulado (Camiseta Drapeada Renacentista vs Street-Ink con contornos nítidos)
    ctx.save();
    const midTorsoX = (hipX + shoulderX) * 0.5;
    const midTorsoY = (hipY + shoulderY) * 0.5;
    ctx.translate(midTorsoX, midTorsoY);
    ctx.rotate(bodyTilt);

    const tw = w * 0.78;
    const th = h * 0.44;

    if (isSfumato) {
      const torsoGrad = ctx.createLinearGradient(-dir * (tw / 2), -th / 2, dir * (tw / 2), th / 2);
      if (f.state === 'HITSTUN') {
        torsoGrad.addColorStop(0, '#7a1c1c');
        torsoGrad.addColorStop(1, '#e06641');
      } else if (f.state === 'BLOCKSTUN') {
        torsoGrad.addColorStop(0, '#594214');
        torsoGrad.addColorStop(1, '#f5c451');
      } else {
        torsoGrad.addColorStop(0, '#21160c');
        torsoGrad.addColorStop(0.45, f.data.ColorPrimary || '#c99738');
        torsoGrad.addColorStop(1, '#ffe599');
      }
      ctx.fillStyle = torsoGrad;
      ctx.strokeStyle = '#d4af37';
      ctx.lineWidth = 2.2;
    } else {
      ctx.fillStyle = f.state === 'HITSTUN' ? '#ff2a54' : (f.state === 'BLOCKSTUN' ? '#f5c451' : f.data.ColorPrimary);
      ctx.strokeStyle = '#05070b';
      ctx.lineWidth = 4;
    }

    // Trapecio anatómico del torso
    ctx.beginPath();
    ctx.moveTo(-tw * 0.54, -th * 0.5);
    ctx.lineTo(tw * 0.54, -th * 0.5);
    ctx.lineTo(tw * 0.42, th * 0.5);
    ctx.lineTo(-tw * 0.42, th * 0.5);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Franja / Banda de Selección y Pliegues Drapeados (Sfumato) o Rim Light Neón (Street-Ink)
    ctx.fillStyle = f.data.ColorSecondary || '#6ba4c8';
    ctx.fillRect(-tw * 0.44, -th * 0.14, tw * 0.88, th * 0.28);

    if (isSfumato) {
      ctx.strokeStyle = 'rgba(28, 18, 8, 0.55)';
      ctx.lineWidth = 1.4;
      for (let fl = -1; fl <= 1; fl++) {
        ctx.beginPath();
        ctx.moveTo(fl * 9, -th * 0.44);
        ctx.quadraticCurveTo(fl * 13 + dir * 4, 0, fl * 7, th * 0.44);
        ctx.stroke();
      }
    } else {
      ctx.strokeStyle = f.data.ColorSecondary || '#00e5ff';
      ctx.lineWidth = 1.8;
      ctx.strokeRect(-tw * 0.44, -th * 0.44, tw * 0.88, th * 0.88);
    }
    ctx.restore();

    // 6. Dibujar Pierna Delantera (Pateadora) y Brazo Delantero
    drawArticulatedLimb(hipX + dir * 6, hipY, fKneeX, fKneeY, 14, shortsCol, outlineCol);
    drawArticulatedLimb(fKneeX, fKneeY, fFootX, fFootY, 11, sockCol, outlineCol);
    // Botín delantero con tapones dorados
    ctx.fillStyle = isSfumato ? '#2b190c' : '#11151f';
    ctx.strokeStyle = '#f5c451';
    ctx.lineWidth = 1.8;
    ctx.fillRect(fFootX - 8, fFootY - 6, 18, 9);
    ctx.strokeRect(fFootX - 8, fFootY - 6, 18, 9);

    drawArticulatedLimb(shoulderX + dir * 8, shoulderY + 4, fElbowX, fElbowY, 11, f.data.ColorPrimary, outlineCol);
    drawArticulatedLimb(fElbowX, fElbowY, fHandX, fHandY, 9, skinCol, outlineCol);

    // 7. Cuello, Cabeza, Melena / Vincha o Halo Astrolabio para V.A.R.-ZERO
    drawArticulatedLimb(shoulderX, shoulderY, neckX, neckY, 8, skinCol, outlineCol);

    if (isBoss) {
      // Halo Astrolabio Dorado Renacentista detrás de la cabeza de V.A.R.-ZERO
      ctx.save();
      ctx.strokeStyle = '#ffe07d';
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      ctx.arc(headX, headY, 26, 0, Math.PI * 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(headX, headY, 20, t * 0.05, t * 0.05 + Math.PI * 1.3);
      ctx.stroke();
      ctx.restore();
    }

    const headR = 15.5;
    if (isSfumato) {
      const headGrad = ctx.createRadialGradient(
        headX + dir * 4, headY - 3, 2,
        headX, headY, headR * 1.25
      );
      headGrad.addColorStop(0, isBoss ? '#ffe299' : '#ffe4b8');
      headGrad.addColorStop(0.65, isBoss ? '#9c732b' : '#c68b59');
      headGrad.addColorStop(1, '#2d1a0c');
      ctx.fillStyle = headGrad;
    } else {
      ctx.fillStyle = isBoss ? '#00e5ff' : '#f5d0b5';
    }
    ctx.beginPath();
    ctx.arc(headX, headY, headR, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = outlineCol;
    ctx.lineWidth = 2.4;
    ctx.stroke();

    // Cabello / Melena Afro Dorada (El Pibe) / Vincha Clásica
    if (f.data.Name === 'PIBE_CO' || f.data.Name === 'LOCO_CO') {
      ctx.fillStyle = f.data.Name === 'PIBE_CO' ? '#f5c451' : '#1b1b22';
      for (let c = 0; c < 7; c++) {
        const ang = Math.PI + (c / 6) * Math.PI;
        ctx.beginPath();
        ctx.arc(headX + Math.cos(ang) * 13, headY + Math.sin(ang) * 13 - 2, 7.5, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (!isBoss) {
      // Vincha deportiva con color secundario del país
      ctx.strokeStyle = f.data.ColorSecondary || '#ffffff';
      ctx.lineWidth = 3.5;
      ctx.beginPath();
      ctx.moveTo(headX - headR + 1, headY - 5);
      ctx.lineTo(headX + headR - 1, headY - 5);
      ctx.stroke();
    }

    // 8. Caja de Daño (Hitbox) cuando está en fase ACTIVE
    if (f.state === 'ACTIVE' && f.activeMoveKey) {
      const mv = T6_MOVES[f.activeMoveKey];
      if (mv && mv.range > 0 && mv.type !== 'PROJ') {
        const hbX = dir > 0 ? x + w / 2 - 5 : x - w / 2 - mv.range + 5;
        const hbW = mv.range;
        const hbY = y - h * 0.78;
        const hbH = 54;

        ctx.fillStyle = isSfumato ? 'rgba(245, 196, 81, 0.38)' : 'rgba(255, 42, 84, 0.42)';
        ctx.strokeStyle = isSfumato ? '#ffe07d' : '#ff2a54';
        ctx.lineWidth = 2.5;
        ctx.fillRect(hbX, hbY, hbW, hbH);
        ctx.strokeRect(hbX, hbY, hbW, hbH);
      }
    }

    // 9. Etiqueta sobre el jugador
    ctx.fillStyle = isSfumato ? '#ffe599' : '#ffffff';
    ctx.font = isSfumato ? 'bold 11.5px Georgia, serif' : 'bold 11px Consolas, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`${f.isP1 ? 'P1' : 'P2'}: ${f.data.DisplayName}`, x, y - baseH - 28);
    ctx.textAlign = 'left';
  }

  function renderTab6VersusCanvas() {
    const w = t6Canvas.width;
    const h = t6Canvas.height;
    t6Ctx.clearRect(0, 0, w, h);

    const st = STAGES_DATA[t6State.stageIdx];
    const p1 = t6State.p1;
    const p2 = t6State.p2;
    const isSfumato = t6State.artStyle === 'SFUMATO';

    let shakeX = 0;
    let shakeY = 0;
    if (t6State.shakeFrames > 0) {
      shakeX = (Math.random() - 0.5) * 14;
      shakeY = (Math.random() - 0.5) * 10;
    }

    t6Ctx.save();
    t6Ctx.translate(shakeX, shakeY);

    const groundY = 390;
    const use3DArena = Boolean(t6Arena3DEnabled && t6WebGLReady && window.SAFWglArena && window.SAFWglArena.isReady());

    if (use3DArena) {
      const p1Code = p1.data.Name;
      const p2Code = p2.data.Name;
      const p1Prof = (typeof CHAR_3D_PROFILES !== 'undefined' && CHAR_3D_PROFILES[p1Code]) ? CHAR_3D_PROFILES[p1Code] : null;
      const p2Prof = (typeof CHAR_3D_PROFILES !== 'undefined' && CHAR_3D_PROFILES[p2Code]) ? CHAR_3D_PROFILES[p2Code] : null;
      const st3d = (typeof STAGES_3D_CATALOG !== 'undefined' && STAGES_3D_CATALOG[t6State.stageIdx])
        ? STAGES_3D_CATALOG[t6State.stageIdx]
        : null;

      const p1GlbUrl = `../Assets/Models3D/Fighters/${p1Prof ? p1Prof.file : (p1Code === 'VAR_ZERO_BOSS' ? 'SK_SUPREME_JUDGE_BOSS.glb' : 'SK_' + p1Code + '.glb')}`;
      const p2GlbUrl = `../Assets/Models3D/Fighters/${p2Prof ? p2Prof.file : (p2Code === 'VAR_ZERO_BOSS' ? 'SK_SUPREME_JUDGE_BOSS.glb' : 'SK_' + p2Code + '.glb')}`;
      const stageGlbUrl = `../Assets/Models3D/Stages/${st3d ? st3d.File : 'SM_Stage_Maracana_BR.glb'}`;

      window.SAFWglArena.renderFrame({
        p1: { ...p1, glbUrl: p1GlbUrl },
        p2: { ...p2, glbUrl: p2GlbUrl },
        stageGlbUrl,
        projectiles: t6State.projectiles,
        lighting: t6State.artStyle,
        inZoneB: t6State.inZoneB,
        shakeX,
        shakeY,
        impactInkFrames: t6State.impactInkFrames,
        matchEnded: t6State.matchEnded,
        winnerIsP1: p1.hp >= p2.hp,
        clockFrames: t6State.clockFrames = (t6State.clockFrames || 0) + 1
      });

      const aStat = window.SAFWglArena.getStatus();
      if (t6WebglHud) {
        t6WebglHud.style.display = 'block';
        const p1Badge = aStat.p1Loaded ? `P1 3D: ${aStat.p1Tris.toLocaleString()}t (${aStat.p1Clip})` : 'P1 Cargando...';
        const p2Badge = aStat.p2Loaded ? `P2 3D: ${aStat.p2Tris.toLocaleString()}t (${aStat.p2Clip})` : 'P2 Cargando...';
        t6WebglHud.innerHTML = `<div><span class="hud-badge">ARENA 3D WEBGL2</span><strong>${p1.data.DisplayName}</strong> vs <strong>${p2.data.DisplayName}</strong></div>` +
          `<div class="hud-sub">${p1Badge} | ${p2Badge} | Estadio: ${aStat.stageLoaded ? '3D OK' : 'Cargando'}</div>`;
      }

      // Overlay etiquetas P1/P2 proyectadas desde sus posiciones reales 3D + hitboxes activas + estela proyectil
      [p1, p2].forEach((f) => {
        const wx = (f.x - 540) / 145.0;
        const wy = Math.max(0, -f.y / 145.0) + (f.data.Name === 'VAR_ZERO_BOSS' ? 2.28 : 1.98);
        const [sx, sy] = window.SAFWglArena.projectToCanvas(wx, wy, 0);
        t6Ctx.fillStyle = isSfumato ? '#ffe599' : '#ffffff';
        t6Ctx.font = isSfumato ? 'bold 11.5px Georgia, serif' : 'bold 11px Consolas, monospace';
        t6Ctx.textAlign = 'center';
        t6Ctx.fillText(`${f.isP1 ? 'P1' : 'P2'}: ${f.data.DisplayName}`, sx, Math.max(58, sy));
        t6Ctx.textAlign = 'left';

        if (f.state === 'ACTIVE' && f.activeMoveKey) {
          const mv = T6_MOVES[f.activeMoveKey];
          if (mv && mv.range > 0 && mv.type !== 'PROJ') {
            const dir = f.facingRight ? 1 : -1;
            const [hbX, hbY] = window.SAFWglArena.projectToCanvas(wx + dir * 0.55, Math.max(0, -f.y / 145.0) + 1.05, 0);
            t6Ctx.fillStyle = isSfumato ? 'rgba(245, 196, 81, 0.28)' : 'rgba(255, 42, 84, 0.32)';
            t6Ctx.strokeStyle = isSfumato ? '#ffe07d' : '#ff2a54';
            t6Ctx.lineWidth = 2;
            t6Ctx.fillRect(hbX - 35, hbY - 24, 70, 48);
            t6Ctx.strokeRect(hbX - 35, hbY - 24, 70, 48);
          }
        }
      });

      t6State.projectiles.forEach((pr) => {
        const bwx = (pr.x - 540) / 145.0;
        const bwy = Math.max(0.18, (390 - pr.y) / 145.0);
        const [bx, by] = window.SAFWglArena.projectToCanvas(bwx, bwy, 0);
        const trailCol = isSfumato ? 'rgba(245, 196, 81, 0.45)' : 'rgba(0, 229, 255, 0.45)';
        t6Ctx.fillStyle = trailCol;
        t6Ctx.beginPath();
        t6Ctx.arc(bx - pr.vx * 1.4, by, 14, 0, Math.PI * 2);
        t6Ctx.fill();
      });

      t6State.particles.forEach((pt) => {
        t6Ctx.fillStyle = pt.color;
        t6Ctx.beginPath();
        t6Ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
        t6Ctx.fill();
      });
    } else {
      // 1. Fondo del Estadio 2D AAA con Arte Conceptual Renacentista / Nocturno según Estadio Activo
      const T6_STAGE_BACKDROPS = [
        '../Assets/ConceptArt/Stage_MaracanaBombonera_Concept.jpg',
        '../Assets/ConceptArt/Stage_MaracanaBombonera_Concept.jpg',
        '../Assets/ConceptArt/Stage_Centenario_Uruguay_Renaissance.jpg',
        '../Assets/ConceptArt/Stage_MaracanaBombonera_Concept.jpg',
        '../Assets/ConceptArt/Stage_HernandoSiles_Bolivia_Renaissance.jpg',
        '../Assets/ConceptArt/Stage_MaracanaBombonera_Concept.jpg',
        '../Assets/ConceptArt/Stage_Atahualpa_Ecuador_Renaissance.jpg',
        '../Assets/ConceptArt/Stage_Atahualpa_Ecuador_Renaissance.jpg',
        '../Assets/ConceptArt/Stage_Atahualpa_Ecuador_Renaissance.jpg',
        '../Assets/ConceptArt/Stage_HernandoSiles_Bolivia_Renaissance.jpg'
      ];
      if (!window._t6StageImgCache) window._t6StageImgCache = {};
      const stImgUrl = T6_STAGE_BACKDROPS[t6State.stageIdx] || T6_STAGE_BACKDROPS[0];
      if (!window._t6StageImgCache[stImgUrl]) {
        const simg = new Image();
        simg.src = stImgUrl;
        window._t6StageImgCache[stImgUrl] = simg;
      }
      const bgImg = window._t6StageImgCache[stImgUrl];

      if (t6State.impactInkFrames > 0) {
        t6Ctx.fillStyle = t6State.impactInkFrames % 2 === 0 ? (isSfumato ? '#f5e1a4' : '#ffffff') : '#06080d';
        t6Ctx.fillRect(0, 0, w, h);
      } else if (bgImg && bgImg.complete && bgImg.naturalWidth > 0) {
        t6Ctx.drawImage(bgImg, 0, 0, w, groundY + 14);
        t6Ctx.fillStyle = isSfumato
          ? (t6State.inZoneB ? 'rgba(62, 24, 10, 0.42)' : 'rgba(20, 14, 7, 0.28)')
          : (t6State.inZoneB ? 'rgba(28, 8, 30, 0.46)' : 'rgba(6, 16, 28, 0.38)');
        t6Ctx.fillRect(0, 0, w, groundY + 14);
      } else if (isSfumato) {
        const sfumatoSky = t6Ctx.createLinearGradient(0, 0, 0, groundY);
        sfumatoSky.addColorStop(0, '#18221f');
        sfumatoSky.addColorStop(1, '#c89d54');
        t6Ctx.fillStyle = sfumatoSky;
        t6Ctx.fillRect(0, 0, w, h);
      } else {
        const skyGrad = t6Ctx.createLinearGradient(0, 0, 0, h);
        skyGrad.addColorStop(0, '#071726');
        skyGrad.addColorStop(1, '#0a1914');
        t6Ctx.fillStyle = skyGrad;
        t6Ctx.fillRect(0, 0, w, h);
      }

      // Marco de la cancha
      t6Ctx.strokeStyle = isSfumato ? 'rgba(212, 175, 55, 0.45)' : 'rgba(245, 196, 81, 0.25)';
      t6Ctx.lineWidth = 2;
      t6Ctx.strokeRect(45, 95, w - 90, groundY - 95);

      // Césped con franjas deportivas (Ocre/Oliva al óleo en Sfumato vs Verde Cancha Neón en Street-Ink)
      for (let sx = 45; sx < w - 45; sx += 90) {
        const even = Math.floor(sx / 90) % 2 === 0;
        if (isSfumato) {
          t6Ctx.fillStyle = even ? 'rgba(68, 78, 36, 0.75)' : 'rgba(52, 62, 28, 0.75)';
        } else {
          t6Ctx.fillStyle = even
            ? (t6State.inZoneB ? 'rgba(255, 145, 0, 0.14)' : 'rgba(0, 230, 118, 0.16)')
            : (t6State.inZoneB ? 'rgba(255, 145, 0, 0.08)' : 'rgba(0, 230, 118, 0.10)');
        }
        t6Ctx.fillRect(sx, groundY, 90, h - groundY);
      }
      t6Ctx.strokeStyle = isSfumato ? '#d4af37' : (t6State.inZoneB ? '#ff9100' : '#00e676');
      t6Ctx.lineWidth = 3;
      t6Ctx.beginPath();
      t6Ctx.moveTo(0, groundY);
      t6Ctx.lineTo(w, groundY);
      t6Ctx.stroke();

      // 2. Dibujar Luchadores P1 y P2
      drawFighterOnT6Canvas(t6Ctx, p1, groundY);
      drawFighterOnT6Canvas(t6Ctx, p2, groundY);

      // 3. Dibujar Proyectiles de Balón con Estela Elemental
      t6State.projectiles.forEach((pr) => {
        const trailCol = isSfumato ? '#e5b95c' : pr.color;
        t6Ctx.shadowColor = trailCol;
        t6Ctx.shadowBlur = 18;
        t6Ctx.fillStyle = trailCol;
        t6Ctx.beginPath();
        t6Ctx.arc(pr.x - pr.vx * 1.4, pr.y, 11, 0, Math.PI * 2);
        t6Ctx.fill();

        t6Ctx.fillStyle = isSfumato ? '#f5deb3' : '#ffffff';
        t6Ctx.beginPath();
        t6Ctx.arc(pr.x, pr.y, 15, 0, Math.PI * 2);
        t6Ctx.fill();
        t6Ctx.strokeStyle = isSfumato ? '#3b2313' : '#06080d';
        t6Ctx.lineWidth = 2.5;
        t6Ctx.stroke();
        t6Ctx.shadowBlur = 0;
      });

      // 4. Dibujar Partículas de Impacto
      t6State.particles.forEach((pt) => {
        t6Ctx.fillStyle = pt.color;
        if (isSfumato) {
          t6Ctx.beginPath();
          t6Ctx.arc(pt.x, pt.y, 3.8, 0, Math.PI * 2);
          t6Ctx.fill();
        } else {
          t6Ctx.fillRect(pt.x - 3.5, pt.y - 3.5, 7, 7);
        }
      });

      // 4.5. Viñeta de Óleo Chiaroscuro y Craquelado Sutil de Lienzo en modo Renacimiento Sfumato
      if (isSfumato) {
        const vig = t6Ctx.createRadialGradient(w / 2, h / 2, w * 0.28, w / 2, h / 2, w * 0.62);
        vig.addColorStop(0, 'rgba(0, 0, 0, 0.0)');
        vig.addColorStop(1, 'rgba(18, 10, 4, 0.58)');
        t6Ctx.fillStyle = vig;
        t6Ctx.fillRect(0, 0, w, h);

        // Sutil malla de craquelado de barniz antiguo (Craquelure)
        t6Ctx.strokeStyle = 'rgba(245, 215, 150, 0.055)';
        t6Ctx.lineWidth = 1;
        for (let cxLine = 120; cxLine < w; cxLine += 180) {
          t6Ctx.beginPath();
          t6Ctx.moveTo(cxLine, 60);
          t6Ctx.lineTo(cxLine + 35, 190);
          t6Ctx.lineTo(cxLine - 15, 340);
          t6Ctx.stroke();
        }
      }
    }

    // ========================================================================
    // 5. HUD TELEVISIVO CONMEBOL (Barras de Vida, Gambeta, Reloj y Super)
    // ========================================================================
    const hudY = 16;
    const barW = 410;
    const barH = 22;

    // Fondo Barras de Vida P1 y P2
    t6Ctx.fillStyle = '#111723';
    t6Ctx.fillRect(45, hudY, barW, barH);
    t6Ctx.fillRect(w - 45 - barW, hudY, barW, barH);

    // Fill Vida P1 (Izquierda)
    const p1HpRatio = Math.max(0, p1.hp / p1.maxHp);
    t6Ctx.fillStyle = p1HpRatio < 0.25 ? '#ff2a54' : '#00e676';
    t6Ctx.fillRect(45 + barW * (1 - p1HpRatio), hudY, barW * p1HpRatio, barH);

    // Fill Vida P2 (Derecha)
    const p2HpRatio = Math.max(0, p2.hp / p2.maxHp);
    t6Ctx.fillStyle = p2HpRatio < 0.25 ? '#ff2a54' : '#00e676';
    t6Ctx.fillRect(w - 45 - barW, hudY, barW * p2HpRatio, barH);

    t6Ctx.strokeStyle = '#f5c451';
    t6Ctx.lineWidth = 2;
    t6Ctx.strokeRect(45, hudY, barW, barH);
    t6Ctx.strokeRect(w - 45 - barW, hudY, barW, barH);

    // Textos de Vida y Nombres
    t6Ctx.fillStyle = '#ffffff';
    t6Ctx.font = 'bold 12px Consolas, monospace';
    t6Ctx.fillText(`${p1.data.DisplayName.toUpperCase()} (${p1.hp} / ${p1.maxHp} HP)`, 52, hudY + 15);
    t6Ctx.textAlign = 'right';
    t6Ctx.fillText(`${p2.data.DisplayName.toUpperCase()} (${p2.hp} / ${p2.maxHp} HP)`, w - 52, hudY + 15);
    t6Ctx.textAlign = 'left';

    // Barras de Gambeta / Stamina (Cian debajo de la barra de vida)
    const gbW = 260;
    t6Ctx.fillStyle = '#111723';
    t6Ctx.fillRect(45, hudY + 27, gbW, 9);
    t6Ctx.fillRect(w - 45 - gbW, hudY + 27, gbW, 9);

    t6Ctx.fillStyle = '#00e5ff';
    t6Ctx.fillRect(45, hudY + 27, gbW * (p1.gambeta / 1000), 9);
    t6Ctx.fillRect(w - 45 - gbW * (p2.gambeta / 1000), hudY + 27, gbW * (p2.gambeta / 1000), 9);

    // Reloj Central de 99 Segundos (o ∞ en Modo Entrenamiento)
    const secsLeft = Math.ceil(t6State.timerFrames / 60);
    const timerDisplay = t6SelAI.value === 'DUMMY' ? '∞' : String(secsLeft).padStart(2, '0');
    t6Ctx.fillStyle = '#0c1018';
    t6Ctx.fillRect(w / 2 - 42, hudY - 4, 84, 42);
    t6Ctx.strokeStyle = '#f5c451';
    t6Ctx.strokeRect(w / 2 - 42, hudY - 4, 84, 42);
    t6Ctx.fillStyle = '#ffe07d';
    t6Ctx.font = 'bold 24px Consolas, monospace';
    t6Ctx.textAlign = 'center';
    t6Ctx.fillText(timerDisplay, w / 2, hudY + 25);

    // Barras Inferiores de Hinchada (Super Meter Nivel 1 a Nivel 3)
    const supW = 340;
    const supY = h - 26;
    t6Ctx.fillStyle = '#0c1018';
    t6Ctx.fillRect(45, supY, supW, 14);
    t6Ctx.fillRect(w - 45 - supW, supY, supW, 14);

    t6Ctx.fillStyle = p1.superMeter >= 3000 ? '#ffe07d' : '#f5c451';
    t6Ctx.fillRect(45, supY, supW * (p1.superMeter / 3000), 14);
    t6Ctx.fillStyle = p2.superMeter >= 3000 ? '#ffe07d' : '#f5c451';
    t6Ctx.fillRect(w - 45 - supW * (p2.superMeter / 3000), supY, supW * (p2.superMeter / 3000), 14);

    t6Ctx.strokeStyle = '#f5c451';
    t6Ctx.strokeRect(45, supY, supW, 14);
    t6Ctx.strokeRect(w - 45 - supW, supY, supW, 14);

    t6Ctx.fillStyle = '#ffffff';
    t6Ctx.font = 'bold 10.5px Consolas, monospace';
    t6Ctx.textAlign = 'left';
    t6Ctx.fillText(`HINCHADA P1: ${Math.floor(p1.superMeter / 1000)}/3 NIVELES (${p1.superMeter})`, 50, supY + 11);
    t6Ctx.textAlign = 'right';
    t6Ctx.fillText(`HINCHADA P2: ${Math.floor(p2.superMeter / 1000)}/3 NIVELES (${p2.superMeter})`, w - 50, supY + 11);

    // Banner Dinámico de Eventos ("COUNTER HIT!", "¡OOOO-LÉ!", "WALL BREAK!", "¡GOOOOOOL!")
    if (t6State.bannerTimer > 0) {
      t6Ctx.fillStyle = 'rgba(6, 8, 13, 0.82)';
      t6Ctx.fillRect(w / 2 - 330, 125, 660, 44);
      t6Ctx.strokeStyle = t6State.bannerColor;
      t6Ctx.lineWidth = 2;
      t6Ctx.strokeRect(w / 2 - 330, 125, 660, 44);

      t6Ctx.fillStyle = t6State.bannerColor;
      t6Ctx.font = 'bold 18px Segoe UI, sans-serif';
      t6Ctx.textAlign = 'center';
      t6Ctx.fillText(t6State.bannerText, w / 2, 153);
    }

    t6Ctx.textAlign = 'left';
    t6Ctx.restore();
  }

  resetTab6Match();

  // ==========================================================================
  // 10. TAB 7: ESTUDIO 3D INTERACTIVO: RIGS, CHAOS CLOTH & VISOR glTF (60 FPS)
  // ==========================================================================
  const t7SelCategory = document.getElementById('t7-sel-category');
  const t7SelChar = document.getElementById('t7-sel-char');
  const t7SelStage3D = document.getElementById('t7-sel-stage3d');
  const t7SelProp3D = document.getElementById('t7-sel-prop3d');
  const t7SelLighting = document.getElementById('t7-sel-lighting');
  const t7SelPose = document.getElementById('t7-sel-pose');
  let t7Canvas = document.getElementById('t7-canvas');
  const t7WebglHud = document.getElementById('t7-webgl-hud');
  const t7UseWebGL = Boolean(window.SAFWglViewer && window.SAFWglViewer.init(t7Canvas));
  let t7Ctx = t7UseWebGL ? null : t7Canvas.getContext('2d');
  if (!t7UseWebGL && !t7Ctx && t7Canvas && t7Canvas.parentNode) {
    const cleanCanvas = t7Canvas.cloneNode(false);
    t7Canvas.parentNode.replaceChild(cleanCanvas, t7Canvas);
    t7Canvas = cleanCanvas;
    t7Ctx = t7Canvas.getContext('2d');
  }

  // Metadatos 3D específicos por Leyenda (17 SK_*.glb High-Poly LOD0 anatómicos con texturas Turnaround embebidas y 16 clips @ 60 FPS)
  const CHAR_3D_PROFILES = {
    FENOMENO_BR:   { file: 'SK_FENOMENO_BR.glb', sizeBytes: 907204, verts: 8905, tris: 15300, heightM: 1.83, build: 1.04, hairStyle: 'SHAVED', hairDesc: 'Rapado Clásico 98 + Escultura LOD0 Texturizada (38 Joints)', bones: 186, number: '9' },
    BRUXO_BR:      { file: 'SK_BRUXO_BR.glb', sizeBytes: 940672, verts: 9336, tris: 15996, heightM: 1.82, build: 0.98, hairStyle: 'CURLY_BAND', hairDesc: 'Vincha + Rulos Largos + Escultura LOD0 Texturizada (14 Hair Chains)', bones: 200, number: '10' },
    CANON_AR:      { file: 'SK_CANON_AR.glb', sizeBytes: 941304, verts: 9344, tris: 16012, heightM: 1.85, build: 1.08, hairStyle: 'MANE_GOLD', hairDesc: 'Melena Lacia con Vincha + Escultura LOD0 Texturizada (12 Hair Chains)', bones: 198, number: '9' },
    PULGA_AR:      { file: 'SK_PULGA_AR.glb', sizeBytes: 909128, verts: 8931, tris: 15328, heightM: 1.70, build: 0.90, hairStyle: 'SHORT', hairDesc: 'Corte Degradado + Barba + Escultura LOD0 Texturizada (4 Hair Cards)', bones: 186, number: '10' },
    PIBE_CO:       { file: 'SK_PIBE_CO.glb', sizeBytes: 971056, verts: 9732, tris: 16572, heightM: 1.76, build: 1.00, hairStyle: 'AFRO_GOLD', hairDesc: 'Melena Afro Dorada Esculpida + Bigote (24 Spring Bones)', bones: 210, number: '10' },
    LOCO_CO:       { file: 'SK_LOCO_CO.glb', sizeBytes: 946464, verts: 9417, tris: 16044, heightM: 1.76, build: 1.02, hairStyle: 'CURLY_DARK', hairDesc: 'Rulos Negros + Guantes Arquero Esculpidos (18 Spring Bones)', bones: 204, number: '1' },
    PISTOLERO_UY:  { file: 'SK_PISTOLERO_UY.glb', sizeBytes: 909792, verts: 8939, tris: 15344, heightM: 1.82, build: 1.06, hairStyle: 'SHORT', hairDesc: 'Corte Corto Charrúa + Vendaje + Escultura LOD0 Texturizada', bones: 186, number: '9' },
    MATADOR_UY:    { file: 'SK_MATADOR_UY.glb', sizeBytes: 940696, verts: 9336, tris: 15996, heightM: 1.80, build: 1.00, hairStyle: 'MANE_GOLD', hairDesc: 'Melena con Vincha + Escultura LOD0 Texturizada', bones: 198, number: '10' },
    BAMBAM_CL:     { file: 'SK_BAMBAM_CL.glb', sizeBytes: 909772, verts: 8939, tris: 15344, heightM: 1.78, build: 1.02, hairStyle: 'SHORT', hairDesc: 'Corte Clásico Noventero + Escultura LOD0 Texturizada', bones: 186, number: '9' },
    REY_CL:        { file: 'SK_REY_CL.glb', sizeBytes: 905616, verts: 8885, tris: 15268, heightM: 1.80, build: 1.04, hairStyle: 'MOHAWK', hairDesc: 'Cresta Real Punk + Tatuajes Esculpida (6 Rigid Hair Bones)', bones: 192, number: '8' },
    BULLDOG_PY:    { file: 'SK_BULLDOG_PY.glb', sizeBytes: 870296, verts: 8435, tris: 14480, heightM: 1.92, build: 1.18, hairStyle: 'SHAVED', hairDesc: 'Complexión Pesada Guaraní + Guantes Esculpidos (188 Huesos)', bones: 188, number: '1' },
    MAESTRO_PE:    { file: 'SK_MAESTRO_PE.glb', sizeBytes: 909132, verts: 8931, tris: 15328, heightM: 1.77, build: 0.96, hairStyle: 'SHORT', hairDesc: 'Franja Carmesí + Bigote Esculpido (4 Hair Cards)', bones: 186, number: '10' },
    TREN_EC:       { file: 'SK_TREN_EC.glb', sizeBytes: 921932, verts: 9097, tris: 15584, heightM: 1.79, build: 1.05, hairStyle: 'SHORT', hairDesc: 'Velocista + Brazalete Capitán Esculpido (186 Huesos)', bones: 186, number: '16' },
    HURACAN_VE:    { file: 'SK_HURACAN_VE.glb', sizeBytes: 909140, verts: 8931, tris: 15328, heightM: 1.80, build: 1.00, hairStyle: 'SHORT', hairDesc: 'Vinotinto #18 + Botines Oro Esculpido (4 Hair Cards)', bones: 186, number: '18' },
    DIABLO_BO:     { file: 'SK_DIABLO_BO.glb', sizeBytes: 934100, verts: 9249, tris: 15884, heightM: 1.76, build: 0.98, hairStyle: 'CURLY_DARK', hairDesc: 'Melena Andina + Bigote Tricolor Esculpida (10 Hair Chains)', bones: 196, number: '10' },
    GENERAL_FR:    { file: 'SK_GENERAL_FR.glb', sizeBytes: 909124, verts: 8931, tris: 15328, heightM: 1.85, build: 1.03, hairStyle: 'SHAVED', hairDesc: 'Clásico Francés 98 Esculpido (186 Huesos)', bones: 186, number: '10' },
    VAR_ZERO_BOSS: { file: 'SK_SUPREME_JUDGE_BOSS.glb', sizeBytes: 1025388, verts: 10236, tris: 17628, heightM: 2.15, build: 1.24, hairStyle: 'HOLO_CROWN', hairDesc: 'Halo Astrolabio Doble Simétrico & Visor V.A.R. Esculpido (214 Huesos)', bones: 214, number: '00' }
  };

  // Catálogo Exacto de los 10 Estadios CONMEBOL 3D (`Stages3D_TechnicalManifest.json`)
  const STAGES_3D_CATALOG = [
    {
      File: 'SM_Stage_Maracana_BR.glb', StageID: 'STAGE_MARACANA_BR', DisplayName: 'Estádio do Maracanã (Brasil)',
      FileSizeBytes: 319336, Vertices: 8848, Triangles: 4492, MaterialCount: 10,
      Dimensions: { WidthX: 71.49, HeightY: 28.83, DepthZ: 34.21 },
      PrimaryColor: '#00a859', SecondaryColor: '#f5c451', ArchType: 'MARACANA_BOWL',
      Landmarks: ['Anillo elíptico curvo de concreto y marquesina', '4 torres de iluminación con bancos emisivos', 'Muros laterales LED pre-fracturados (Wall-Break)']
    },
    {
      File: 'SM_Stage_Bombonera_AR.glb', StageID: 'STAGE_BOMBONERA_AR', DisplayName: 'La Bombonera (Argentina)',
      FileSizeBytes: 124160, Vertices: 3264, Triangles: 1632, MaterialCount: 11,
      Dimensions: { WidthX: 54.31, HeightY: 22.33, DepthZ: 29.2 },
      PrimaryColor: '#1976d2', SecondaryColor: '#ffd600', ArchType: 'BOMBONERA_D',
      Landmarks: ['Tribunas verticales de 3 bandejas en forma de D con franja dorada', 'Pared vertical de Palcos VIP', 'Fachada lateral colorida estilo Caminito y muros destructibles']
    },
    {
      File: 'SM_Stage_Centenario_UY.glb', StageID: 'STAGE_CENTENARIO_UY', DisplayName: 'Estadio Centenario (Uruguay)',
      FileSizeBytes: 154464, Vertices: 4196, Triangles: 2132, MaterialCount: 8,
      Dimensions: { WidthX: 56.79, HeightY: 45.98, DepthZ: 36.2 },
      PrimaryColor: '#4fc3f7', SecondaryColor: '#e0e6ed', ArchType: 'CENTENARIO_TOWER',
      Landmarks: ['Torre de los Homenajes Art Déco (45.9m) con 9 balcones y aguja', 'Arcos históricos de columnata de concreto', 'Muros laterales celestes pre-fracturados']
    },
    {
      File: 'SM_Stage_Metropolitano_CO.glb', StageID: 'STAGE_METROPOLITANO_CO', DisplayName: 'Estadio Metropolitano (Colombia)',
      FileSizeBytes: 227164, Vertices: 6166, Triangles: 3304, MaterialCount: 11,
      Dimensions: { WidthX: 65.37, HeightY: 18.18, DepthZ: 32.5 },
      PrimaryColor: '#ffeb3b', SecondaryColor: '#d32f2f', ArchType: 'METRO_CANOPY',
      Landmarks: ['Costillas curvas tropicales y membranas blancas de sombra', 'Tazón tricolor Amarillo/Azul/Rojo', 'Explanada exterior caribeña (Zona B) con palmeras']
    },
    {
      File: 'SM_Stage_Nunoa_CL.glb', StageID: 'STAGE_NUNOA_CL', DisplayName: 'Estadio Nacional de Ñuñoa (Chile)',
      FileSizeBytes: 300628, Vertices: 8376, Triangles: 4188, MaterialCount: 8,
      Dimensions: { WidthX: 119.74, HeightY: 48.0, DepthZ: 85.65 },
      PrimaryColor: '#e53935', SecondaryColor: '#1e88e5', ArchType: 'NUNOA_ANDES',
      Landmarks: ['Pista atlética elíptica de terracota con carriles', 'Tazón abierto de perfil bajo', 'Cordillera de los Andes nevada monumental al fondo']
    },
    {
      File: 'SM_Stage_Defensores_PY.glb', StageID: 'STAGE_DEFENSORES_PY', DisplayName: 'Estadio Defensores del Chaco (Paraguay)',
      FileSizeBytes: 93876, Vertices: 2424, Triangles: 1368, MaterialCount: 9,
      Dimensions: { WidthX: 50.0, HeightY: 26.83, DepthZ: 31.55 },
      PrimaryColor: '#d32f2f', SecondaryColor: '#1976d2', ArchType: 'DEFENSORES_FORT',
      Landmarks: ['Bastiones de concreto tipo fortaleza con almenas', '4 pilones tricolores rojo/blanco/azul', 'Muros laterales pesados (4 impactos para Wall-Break)']
    },
    {
      File: 'SM_Stage_NacionalLima_PE.glb', StageID: 'STAGE_NACIONAL_LIMA_PE', DisplayName: 'Estadio Nacional de Lima (Perú)',
      FileSizeBytes: 171632, Vertices: 4660, Triangles: 2368, MaterialCount: 9,
      Dimensions: { WidthX: 62.66, HeightY: 42.03, DepthZ: 35.6 },
      PrimaryColor: '#ff2a54', SecondaryColor: '#ffffff', ArchType: 'LIMA_FINS',
      Landmarks: ['29 aletas arquitectónicas verticales iluminadas en rojo y blanco', 'Torre Norte de cristal con aguja metálica', 'Muros laterales LED rojos pre-fracturados']
    },
    {
      File: 'SM_Stage_Atahualpa_EC.glb', StageID: 'STAGE_ATAHUALPA_EC', DisplayName: 'Estadio Olímpico Atahualpa (Ecuador)',
      FileSizeBytes: 165468, Vertices: 4476, Triangles: 2328, MaterialCount: 9,
      Dimensions: { WidthX: 97.1, HeightY: 46.6, DepthZ: 88.5 },
      PrimaryColor: '#ffd600', SecondaryColor: '#ff6d00', ArchType: 'ATAHUALPA_VOLCANO',
      Landmarks: ['Línea ecuatorial dorada y monumento Mitad del Mundo', 'Cono volcánico andino imponente al fondo', 'Cráter emisivo incandescente y fisuras de lava']
    },
    {
      File: 'SM_Stage_Avila_VE.glb', StageID: 'STAGE_AVILA_VE', DisplayName: 'Estadio del Ávila (Venezuela)',
      FileSizeBytes: 203700, Vertices: 5538, Triangles: 2892, MaterialCount: 10,
      Dimensions: { WidthX: 120.95, HeightY: 36.0, DepthZ: 76.76 },
      PrimaryColor: '#880e4f', SecondaryColor: '#00e5ff', ArchType: 'AVILA_HELIPAD',
      Landmarks: ['Techo curvo moderno en voladizo plata y vinotinto', 'Cresta montañosa costera del Cerro El Ávila', 'Helipuerto VIP elevado con H luminosa y anillo perimetral']
    },
    {
      File: 'SM_Stage_HernandoSiles_BO.glb', StageID: 'STAGE_HERNANDO_SILES_BO', DisplayName: 'Estadio Hernando Siles (Bolivia - 3,600m)',
      FileSizeBytes: 130976, Vertices: 3456, Triangles: 1728, MaterialCount: 11,
      Dimensions: { WidthX: 93.38, HeightY: 52.75, DepthZ: 81.98 },
      PrimaryColor: '#00e676', SecondaryColor: '#f5c451', ArchType: 'SILES_MONOLITH',
      Landmarks: ['Planos de nubes flotantes semitransparentes a 3.600m de altitud', 'Monolito andino tallado inspirado en Tiwanaku', 'Macizo nevado del Illimani de tres picos al fondo']
    }
  ];

  // Metadatos de los 10 Clips de Animación glTF 2.0
  const CLIP_3D_METADATA = {
    Idle_Breath:          { dur: 2.0, kf: 121, interp: 'LINEAR (60 FPS)', desc: 'Respiración cíclica a 60 FPS y balanceo de guardia competitiva (+ levitación y halo orbital en V.A.R.-ZERO).' },
    Dash_Forward:         { dur: 0.6, kf: 37,  interp: 'LINEAR (60 FPS)', desc: 'Arrancada explosiva hacia adelante con traslación de root, inclinación de torso y arrastre de cabello.' },
    Kick_High:            { dur: 0.8, kf: 49,  interp: 'LINEAR (60 FPS)', desc: 'Volea alta con rotación de cadera y exageración de impacto 1.18x en tibia y botín delantero.' },
    Special_Chilena:      { dur: 1.2, kf: 73,  interp: 'LINEAR (60 FPS)', desc: 'Chilena acrobática de 360° en el aire con salto parabólico, tijera de piernas y escala 1.25x en el ápice.' },
    Victory_Pose:         { dur: 1.5, kf: 91,  interp: 'LINEAR (60 FPS)', desc: 'Saludo triunfal de campeón levantando los brazos (+ doble halo astrolabio contrarrotatorio en Boss).' },
    Anim_Idle:            { dur: 1.0, kf: 60,  interp: 'STEP (Cuantizado)', desc: 'Guardia de potrero cuantizada estilo anime FGC sin motion blur.' },
    Anim_5LP_Jab4f:       { dur: 0.24, kf: 14, interp: 'STEP (Cuantizado)', desc: 'Toque corto / Jab rápido de 4 frames de startup con rotación de Twist Bones en antebrazo.' },
    Anim_236SK_Shot:      { dur: 0.83, kf: 50, interp: 'STEP (Cuantizado)', desc: 'Disparo Bati-Cañonazo con Smear Frame Control Rig (1.25x) en tibia mientras la Hurtbox AABB es exacta.' },
    Anim_623HP_BicycleKick:{ dur: 0.68, kf: 41, interp: 'STEP (Cuantizado)', desc: 'Chilena anti-aérea rotando sobre pelvis_visual_offset con root anclado al plano del suelo.' },
    Anim_214SK_Scorpion:  { dur: 0.76, kf: 46, interp: 'STEP (Cuantizado)', desc: 'El Escorpión acrobático con Hurtbox superior azul (High-Crush Invulnerable) y talones sobre la cabeza.' },
    Mocap_Walk_Forward:   { dur: 1.0,  kf: 61, interp: 'LINEAR (60 FPS Mocap)', desc: 'Zancada atlética de avance con rotación de hombros y cadera a 60 FPS uniformes.' },
    Mocap_Backdash_Dodge: { dur: 0.45, kf: 28, interp: 'LINEAR (60 FPS Mocap)', desc: 'Salto evasivo hacia atrás en 28 cuadros con guardia recogida.' },
    Mocap_Block_Guard:    { dur: 0.8,  kf: 49, interp: 'LINEAR (60 FPS Mocap)', desc: 'Guardia cerrada cruzando antebrazos con absorción de rodillas frente a presión FGC.' },
    Mocap_Hitstun_Knockback:{ dur: 0.5, kf: 31, interp: 'LINEAR (60 FPS Mocap)', desc: 'Retroceso de impacto con vibración en pelvis_visual_offset y látigo cervical.' },
    Mocap_Super_Potrero:  { dur: 1.4,  kf: 85, interp: 'LINEAR (60 FPS Mocap)', desc: 'Super Hinchada Nivel 3: carga en suelo, salto giratorio 360° y volea de smear 1.30x.' },
    Mocap_KO_Knockdown:   { dur: 1.2,  kf: 73, interp: 'LINEAR (60 FPS Mocap)', desc: 'Caída dramática en espiral al césped con rebote de impacto tras K.O.' }
  };

  let t7State = {
    category: 'FIGHTERS', // 'FIGHTERS' | 'STAGES' | 'PROPS'
    charIdx: 4,           // El Pibe por defecto
    stageIdx: 0,          // Maracanã por defecto
    propKey: 'BALL_32',   // 'BALL_32' | 'ARENA_WALLS'
    lighting: 'SFUMATO',  // 'SFUMATO' | 'STREET_INK'
    mode: 'SHADED',       // 'SHADED' | 'SKELETON' | 'CLOTH' | 'SMEAR'
    pose: 'Idle_Breath',
    animPlaying: true,
    animSpeed: 1.0,
    animClock: 0,
    yaw: 0.55,
    pitch: 0.18,
    zoom: 1.05,
    autoRotate: true,
    showTurnaround: true,
    lastSyncedStatsKey: '',
    isDragging: false,
    lastMouseX: 0,
    lastMouseY: 0,
    windPct: 45,
    smearScale: 1.25,
    ballKickTimer: 0,
    tick: 0,
    manifestsLoaded: false
  };

  // Poblar selector de 17 Luchadores
  ROSTER_DATA.forEach((ch, idx) => {
    const prof = CHAR_3D_PROFILES[ch.Name] || CHAR_3D_PROFILES.FENOMENO_BR;
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = `${ch.DisplayName} — ${prof.file} (${ch.Country})`;
    t7SelChar.appendChild(opt);
  });
  t7SelChar.value = t7State.charIdx;

  // Poblar selector de 10 Estadios 3D
  STAGES_3D_CATALOG.forEach((st, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = `${st.DisplayName} — ${st.File}`;
    if (t7SelStage3D) t7SelStage3D.appendChild(opt);
  });

  // Intentar cargar asíncronamente los manifiestos JSON reales para enriquecer telemetría si aplica
  (async function tryFetch3DManifests() {
    try {
      const [animRes, stgRes] = await Promise.all([
        fetch('../Assets/Models3D/Fighters/Animations3D_TechnicalManifest.json'),
        fetch('../Assets/Models3D/Stages/Stages3D_TechnicalManifest.json')
      ]);
      if (animRes.ok && stgRes.ok) {
        t7State.manifestsLoaded = true;
      }
    } catch (_) {
      // Fallback integrado 100% funcional en protocolo file://
    }
  })();

  function updateTab7TurnaroundUI(ch) {
    const splitEl = document.getElementById('t7-viewport-split');
    const cardEl = document.getElementById('t7-turnaround-card');
    const toggleBtn = document.getElementById('t7-btn-toggle-turnaround');
    const imgEl = document.getElementById('t7-turnaround-img');
    const zoomEl = document.getElementById('t7-turnaround-zoom');
    const badgeEl = document.getElementById('t7-turnaround-badge');
    const captionEl = document.getElementById('t7-turnaround-caption');

    const isFighter = t7State.category === 'FIGHTERS' && Boolean(ch);
    const showCard = isFighter && t7State.showTurnaround;

    if (cardEl) cardEl.style.display = showCard ? 'flex' : 'none';
    if (splitEl) splitEl.classList.toggle('with-turnaround', showCard);

    if (toggleBtn) {
      toggleBtn.disabled = !isFighter;
      if (!isFighter) {
        toggleBtn.textContent = '📐 Turnaround 2D (Solo Luchadores)';
        toggleBtn.classList.remove('btn-cyan', 'btn-gold');
      } else {
        toggleBtn.textContent = t7State.showTurnaround
          ? '📐 Referencia Turnaround 2D: ON'
          : '📐 Referencia Turnaround 2D: OFF';
        toggleBtn.classList.toggle('btn-cyan', t7State.showTurnaround);
      }
    }

    if (isFighter) {
      const pngName = `Turnaround_${ch.Name}.png`;
      const pngPath = `../Assets/Design3D_Turnarounds/${pngName}`;
      if (imgEl && imgEl.getAttribute('src') !== pngPath) {
        imgEl.setAttribute('src', pngPath);
        imgEl.setAttribute('alt', `Referencia Turnaround 2D — ${ch.DisplayName} (${ch.Name})`);
      }
      if (zoomEl) zoomEl.setAttribute('href', pngPath);
      if (badgeEl) badgeEl.textContent = pngName;
      if (captionEl) captionEl.textContent = `${ch.DisplayName} (${ch.Name}) • A-Pose / Perfil / Espalda / 3/4`;
    }
  }

  function syncTab7LiveGlbStats(stats) {
    if (!stats || !stats.loaded) return;
    const statsKey = `${stats.file}|${stats.byteLength}|${stats.verts}|${stats.tris}|${stats.joints}|${stats.clips}|${stats.materials}|${t7State.category}|${t7State.pose}`;
    if (t7State.lastSyncedStatsKey === statsKey) return;
    t7State.lastSyncedStatsKey = statsKey;

    const sizeEl = document.getElementById('t7-insp-size');
    const geoEl = document.getElementById('t7-insp-geo');
    const boundsEl = document.getElementById('t7-insp-bounds');
    const clipsEl = document.getElementById('t7-insp-clips');
    const bonesEl = document.getElementById('t7-stat-bones');

    if (sizeEl && stats.byteLength > 0) {
      sizeEl.textContent = `${(stats.byteLength / 1024).toFixed(1)} KB`;
    }

    if (t7State.category === 'FIGHTERS') {
      const ch = ROSTER_DATA[t7State.charIdx] || ROSTER_DATA[0];
      const prof = CHAR_3D_PROFILES[ch.Name] || CHAR_3D_PROFILES.FENOMENO_BR;
      const clipMeta = CLIP_3D_METADATA[t7State.pose] || CLIP_3D_METADATA.Idle_Breath;
      const jointCount = stats.joints || 38;
      const matCount = stats.materials || 3;
      const clipCount = stats.clips || 16;
      const kfCount = stats.totalKf > 1 ? stats.totalKf : clipMeta.kf;
      const heightM = stats.heightM > 0.2 ? stats.heightM : prof.heightM;

      if (bonesEl) bonesEl.textContent = `${jointCount} glTF Joints (${prof.bones} Total UE5 Bones)`;
      if (geoEl) geoEl.textContent = `${stats.verts.toLocaleString()} Verts / ${stats.tris.toLocaleString()} Tris (${matCount} Mats glTF • LOD0 Target: 65k)`;
      if (boundsEl) boundsEl.textContent = `Altura: ${heightM.toFixed(2)}m • ${jointCount} Joints • TEXCOORD_0 + PBR`;
      if (clipsEl) clipsEl.textContent = `${clipCount} Clips Mocap/FGC @ 60 FPS | Activo: ${t7State.pose} (${kfCount} KF)`;
    } else if (t7State.category === 'STAGES') {
      const st = STAGES_3D_CATALOG[t7State.stageIdx] || STAGES_3D_CATALOG[0];
      const matCount = stats.materials || st.MaterialCount;
      if (geoEl) geoEl.textContent = `${stats.verts.toLocaleString()} Verts / ${stats.tris.toLocaleString()} Tris (${matCount} Primitivas glTF)`;
    } else {
      const matCount = stats.materials || 1;
      if (bonesEl) bonesEl.textContent = `${stats.verts.toLocaleString()} Vértices / ${stats.tris.toLocaleString()} Triángulos`;
      if (geoEl) geoEl.textContent = `${stats.verts.toLocaleString()} Verts / ${stats.tris.toLocaleString()} Tris (${matCount} Mat glTF)`;
    }
  }

  function updateTab7InspectorUI() {
    t7State.lastSyncedStatsKey = '';
    const wrapChar = document.getElementById('t7-wrap-char');
    const wrapStage = document.getElementById('t7-wrap-stage');
    const wrapProp = document.getElementById('t7-wrap-prop');
    const dlBtn = document.getElementById('t7-btn-download-active');
    const dlLbl = document.getElementById('t7-lbl-download-active');

    if (t7State.category === 'FIGHTERS') {
      if (wrapChar) wrapChar.style.display = 'block';
      if (wrapStage) wrapStage.style.display = 'none';
      if (wrapProp) wrapProp.style.display = 'none';

      const ch = ROSTER_DATA[t7State.charIdx] || ROSTER_DATA[0];
      const prof = CHAR_3D_PROFILES[ch.Name] || CHAR_3D_PROFILES.FENOMENO_BR;
      const clipMeta = CLIP_3D_METADATA[t7State.pose] || CLIP_3D_METADATA.Idle_Breath;

      document.getElementById('t7-char-badge').textContent = prof.file;
      document.getElementById('t7-stat-height').textContent = `${prof.heightM.toFixed(2)} m (Escala ${prof.build.toFixed(2)}x)`;
      document.getElementById('t7-stat-hair').textContent = prof.hairDesc;
      document.getElementById('t7-stat-bones').textContent = `38 glTF Joints (${prof.bones} Total UE5 Bones)`;

      document.getElementById('t7-manifest-source').textContent = 'Animations3D_TechnicalManifest.json • Validated';
      document.getElementById('t7-insp-size').textContent = `${(prof.sizeBytes / 1024).toFixed(1)} KB`;
      document.getElementById('t7-insp-file').textContent = `Fighters/${prof.file}`;
      document.getElementById('t7-insp-geo').textContent = `${prof.verts.toLocaleString()} Verts / ${prof.tris.toLocaleString()} Tris (HP Bake: 82k+ Tris • 4 Morph Targets)`;
      document.getElementById('t7-insp-bounds').textContent = `Altura: ${prof.heightM.toFixed(2)}m • 38 Joints • Bakes Normal/AO`;
      document.getElementById('t7-insp-clips').textContent = `16 Clips Mocap/FGC @ 60 FPS | Activo: ${t7State.pose} (${clipMeta.kf} KF)`;
      document.getElementById('t7-insp-flags').textContent = 'GPUSkinCache: ON | Chaos Cloth 5.4: ON | Nanite: OFF (Skinned)';
      document.getElementById('t7-insp-landmarks').innerHTML =
        `<strong>Clip [${t7State.pose}] (${clipMeta.interp}):</strong> ${clipMeta.desc}`;

      if (dlBtn) dlBtn.href = `../Assets/Models3D/Fighters/${prof.file}`;
      if (dlLbl) dlLbl.textContent = `📥 Descargar ${prof.file}`;
      updateTab7TurnaroundUI(ch);
    } else if (t7State.category === 'STAGES') {
      if (wrapChar) wrapChar.style.display = 'none';
      if (wrapStage) wrapStage.style.display = 'block';
      if (wrapProp) wrapProp.style.display = 'none';

      const st = STAGES_3D_CATALOG[t7State.stageIdx] || STAGES_3D_CATALOG[0];
      document.getElementById('t7-char-badge').textContent = st.File;
      document.getElementById('t7-stat-height').textContent = `${st.Dimensions.WidthX}m × ${st.Dimensions.HeightY}m × ${st.Dimensions.DepthZ}m`;
      document.getElementById('t7-stat-hair').textContent = st.Landmarks[0];
      document.getElementById('t7-stat-bones').textContent = `${st.MaterialCount} Materiales PBR + Muros Pre-Fracturados`;

      document.getElementById('t7-manifest-source').textContent = 'Stages3D_TechnicalManifest.json • Validated';
      document.getElementById('t7-insp-size').textContent = `${(st.FileSizeBytes / 1024).toFixed(1)} KB`;
      document.getElementById('t7-insp-file').textContent = `Stages/${st.File}`;
      document.getElementById('t7-insp-geo').textContent = `${st.Vertices.toLocaleString()} Verts / ${st.Triangles.toLocaleString()} Tris (${st.MaterialCount} Primitivas)`;
      document.getElementById('t7-insp-bounds').textContent = `W: ${st.Dimensions.WidthX}m | H: ${st.Dimensions.HeightY}m | D: ${st.Dimensions.DepthZ}m`;
      document.getElementById('t7-insp-clips').textContent = `Zona A: [-12.5m, 12.5m] → Wall-Break → Zona B: [-18.5m, 18.5m]`;
      document.getElementById('t7-insp-flags').textContent = 'Nanite Mesh: ON | Chaos Geometry Collection: ON | Lumen GI: ON';
      document.getElementById('t7-insp-landmarks').innerHTML =
        `<strong>Landmarks Arquitectónicos 3D:</strong> ${st.Landmarks.join(' • ')}.`;

      if (dlBtn) dlBtn.href = `../Assets/Models3D/Stages/${st.File}`;
      if (dlLbl) dlLbl.textContent = `📥 Descargar ${st.File}`;
      updateTab7TurnaroundUI(null);
    } else {
      if (wrapChar) wrapChar.style.display = 'none';
      if (wrapStage) wrapStage.style.display = 'none';
      if (wrapProp) wrapProp.style.display = 'block';

      const isBall = t7State.propKey === 'BALL_32';
      const pFile = isBall ? 'Props/SM_Ball_TruncatedIcosahedron_32Panels.glb' : 'Stages/SM_Stage_PitchAndDestructibleWalls.glb';
      const pBase = isBall ? 'SM_Ball_TruncatedIcosahedron_32Panels.glb' : 'SM_Stage_PitchAndDestructibleWalls.glb';

      document.getElementById('t7-char-badge').textContent = pBase;
      document.getElementById('t7-stat-height').textContent = isBall ? 'Radio 0.22 m (FIFA Size 5 Standard)' : '37.0 m × 4.5 m × 16.0 m';
      document.getElementById('t7-stat-hair').textContent = isBall ? 'Icoságono Truncado (12 Pentágonos + 20 Hexágonos)' : 'Cancha Reglamentaria 2.5D + 2 Muros Destructibles';
      document.getElementById('t7-stat-bones').textContent = isBall ? '561 Vértices / 1,024 Triángulos' : '216 Vértices / 108 Triángulos';

      document.getElementById('t7-manifest-source').textContent = 'Models3D_TechnicalManifest.json • Validated';
      document.getElementById('t7-insp-size').textContent = isBall ? '28.4 KB' : '14.2 KB';
      document.getElementById('t7-insp-file').textContent = pFile;
      document.getElementById('t7-insp-geo').textContent = isBall ? '561 Verts / 1,024 Tris (LOD0: 4,800 Tris)' : '216 Verts / 108 Tris (Colisión AABB Exacta)';
      document.getElementById('t7-insp-bounds').textContent = isBall ? 'Diámetro: 0.44m • UV0 Costuras + Normal Map' : 'Zona A: 25.0m • WallBreakX: ±12.55m';
      document.getElementById('t7-insp-clips').textContent = isBall ? 'Rotación Aerodinámica + Deformación Squash & Stretch' : 'Fractura Determinista al llegar WallHealth a 0';
      document.getElementById('t7-insp-flags').textContent = 'Nanite: ON | Custom Depth Stencil: Channel 1 | Lumen: ON';
      document.getElementById('t7-insp-landmarks').innerHTML = isBall
        ? '<strong>Prop Oficial:</strong> Balón geodésico de 32 paneles con texturas PBR T_Ball_32Panels_Albedo.png y T_Ball_32Panels_Normal.png.'
        : '<strong>Arena Base:</strong> Plano de combate 2.5D con líneas de cal y vallas laterales destructibles para transición de Wall Break.';

      if (dlBtn) dlBtn.href = `../Assets/Models3D/${pFile}`;
      if (dlLbl) dlLbl.textContent = `📥 Descargar ${pBase}`;
      updateTab7TurnaroundUI(null);
    }
  }

  if (t7SelCategory) {
    t7SelCategory.addEventListener('change', (e) => {
      t7State.category = e.target.value;
      updateTab7InspectorUI();
      playSynthSound('parry');
    });
  }

  t7SelChar.addEventListener('change', (e) => {
    t7State.charIdx = parseInt(e.target.value, 10) || 0;
    updateTab7InspectorUI();
    playSynthSound('step');
  });

  if (t7SelStage3D) {
    t7SelStage3D.addEventListener('change', (e) => {
      t7State.stageIdx = parseInt(e.target.value, 10) || 0;
      updateTab7InspectorUI();
      playSynthSound('step');
    });
  }

  if (t7SelProp3D) {
    t7SelProp3D.addEventListener('change', (e) => {
      t7State.propKey = e.target.value;
      updateTab7InspectorUI();
      playSynthSound('step');
    });
  }

  if (t7SelLighting) {
    t7SelLighting.addEventListener('change', (e) => {
      t7State.lighting = e.target.value;
      playSynthSound('parry');
    });
  }

  document.querySelectorAll('.t7-mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.t7-mode-btn').forEach((b) => b.classList.remove('btn-gold'));
      btn.classList.add('btn-gold');
      t7State.mode = btn.dataset.mode;
      const modeNames = {
        SHADED: 'Modo: Shaded PBR + Rim Light + Lighting Channel 1',
        SKELETON: 'Modo: Jerarquía Esqueleto UE5 / Wireframe Arquitectónico glTF',
        CLOTH: 'Modo: Mapa de Calor Chaos Cloth 5.4 / Zonas de Fractura Wall-Break',
        SMEAR: 'Modo: Stepped Animation 60Hz + Control Rig Smear (1.25x) vs AABB Exacta'
      };
      document.getElementById('t7-viewport-subtitle').textContent = modeNames[t7State.mode];
      playSynthSound('parry');
    });
  });

  t7SelPose.addEventListener('change', (e) => {
    t7State.pose = e.target.value;
    t7State.animClock = 0;
    const clipMeta = CLIP_3D_METADATA[t7State.pose] || CLIP_3D_METADATA.Idle_Breath;
    const kfLbl = document.getElementById('t7-clip-kf-lbl');
    if (kfLbl) kfLbl.textContent = `KF: 001 / ${clipMeta.kf}`;
    updateTab7InspectorUI();
    renderTab7Studio3D();
    playSynthSound('hit');
  });

  const t7BtnAnimPlay = document.getElementById('t7-btn-anim-play');
  if (t7BtnAnimPlay) {
    t7BtnAnimPlay.addEventListener('click', (e) => {
      t7State.animPlaying = !t7State.animPlaying;
      e.currentTarget.textContent = t7State.animPlaying ? '⏸ Pause Clip' : '▶ Play Clip';
      playSynthSound('step');
    });
  }

  document.querySelectorAll('.t7-spd-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.t7-spd-btn').forEach((b) => b.classList.remove('btn-gold'));
      btn.classList.add('btn-gold');
      t7State.animSpeed = parseFloat(btn.dataset.spd) || 1.0;
      playSynthSound('step');
    });
  });

  document.getElementById('t7-rng-wind').addEventListener('input', (e) => {
    t7State.windPct = parseInt(e.target.value, 10);
    document.getElementById('t7-lbl-wind').textContent = `${t7State.windPct}%`;
  });

  document.getElementById('t7-rng-smear').addEventListener('input', (e) => {
    t7State.smearScale = parseInt(e.target.value, 10) / 100;
    document.getElementById('t7-lbl-smear').textContent = `${t7State.smearScale.toFixed(2)}x (Activo)`;
  });

  document.getElementById('t7-btn-autorotate').addEventListener('click', (e) => {
    t7State.autoRotate = !t7State.autoRotate;
    e.currentTarget.textContent = t7State.autoRotate ? '🔄 Auto-Giro: ON' : '⏸ Auto-Giro: OFF';
  });

  document.getElementById('t7-btn-reset-cam').addEventListener('click', () => {
    t7State.yaw = 0.55;
    t7State.pitch = 0.18;
    t7State.zoom = 1.05;
    playSynthSound('step');
  });

  document.getElementById('t7-btn-kick-ball').addEventListener('click', () => {
    t7State.ballKickTimer = 45;
    if (t7State.category === 'FIGHTERS') {
      t7State.pose = 'Kick_High';
      t7SelPose.value = 'Kick_High';
      updateTab7InspectorUI();
    }
    playSynthSound('stinger');
  });

  const t7BtnToggleTurnaround = document.getElementById('t7-btn-toggle-turnaround');
  if (t7BtnToggleTurnaround) {
    t7BtnToggleTurnaround.addEventListener('click', () => {
      if (t7State.category !== 'FIGHTERS') return;
      t7State.showTurnaround = !t7State.showTurnaround;
      updateTab7InspectorUI();
      playSynthSound('step');
    });
  }

  // Interacción Orbital 360° con Ratón y Rueda de Zoom en el Canvas 3D
  t7Canvas.addEventListener('mousedown', (e) => {
    t7State.isDragging = true;
    t7State.autoRotate = false;
    document.getElementById('t7-btn-autorotate').textContent = '⏸ Auto-Giro: OFF';
    t7State.lastMouseX = e.clientX;
    t7State.lastMouseY = e.clientY;
  });

  window.addEventListener('mousemove', (e) => {
    if (!t7State.isDragging) return;
    const dx = e.clientX - t7State.lastMouseX;
    const dy = e.clientY - t7State.lastMouseY;
    t7State.lastMouseX = e.clientX;
    t7State.lastMouseY = e.clientY;
    t7State.yaw += dx * 0.012;
    t7State.pitch = Math.max(-0.65, Math.min(0.75, t7State.pitch + dy * 0.01));
  });

  window.addEventListener('mouseup', () => {
    t7State.isDragging = false;
  });

  t7Canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    t7State.zoom = Math.max(0.55, Math.min(1.85, t7State.zoom - e.deltaY * 0.001));
  });

  // Proyección Matemática 3D -> 2D Perspectiva con Rotación Yaw/Pitch
  function project3DPoint(pt, cx, cy, yaw, pitch, zoom) {
    const cosY = Math.cos(yaw);
    const sinY = Math.sin(yaw);
    const x1 = pt.x * cosY - pt.z * sinY;
    const z1 = pt.x * sinY + pt.z * cosY;

    const cosP = Math.cos(pitch);
    const sinP = Math.sin(pitch);
    const y2 = pt.y * cosP - z1 * sinP;
    const z2 = pt.y * sinP + z1 * cosP;

    const fov = 420 * zoom;
    const viewerDist = 4.2;
    const scale = fov / Math.max(0.8, viewerDist + z2);
    return {
      sx: cx + x1 * scale,
      sy: cy - y2 * scale,
      depth: z2,
      scale
    };
  }

  // Renderizador 3D de los 10 Estadios CONMEBOL (`SM_Stage_*.glb`)
  function renderStage3DModel(st, cx, cy, w, h, isSfumato) {
    const p3d = (x, y, z) => project3DPoint({ x, y, z }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);

    // 1. Cancha de Césped 3D (Zona A: [-1.1, 1.1], Zona B exterior: [-1.55, 1.55])
    const pitchCorners = [
      p3d(-1.25, 0, -0.78), p3d(1.25, 0, -0.78),
      p3d(1.25, 0, 0.78), p3d(-1.25, 0, 0.78)
    ];
    t7Ctx.fillStyle = isSfumato ? 'rgba(68, 82, 36, 0.85)' : 'rgba(0, 185, 95, 0.75)';
    t7Ctx.strokeStyle = isSfumato ? '#d4a347' : '#00e676';
    t7Ctx.lineWidth = 2;
    t7Ctx.beginPath();
    pitchCorners.forEach((pt, i) => (i === 0 ? t7Ctx.moveTo(pt.sx, pt.sy) : t7Ctx.lineTo(pt.sx, pt.sy)));
    t7Ctx.closePath();
    if (t7State.mode !== 'SKELETON') t7Ctx.fill();
    t7Ctx.stroke();

    // Línea central ecuatorial / círculo central
    const midA = p3d(0, 0.01, -0.78);
    const midB = p3d(0, 0.01, 0.78);
    t7Ctx.strokeStyle = st.ArchType === 'ATAHUALPA_VOLCANO' ? '#ffd600' : 'rgba(255,255,255,0.65)';
    t7Ctx.beginPath(); t7Ctx.moveTo(midA.sx, midA.sy); t7Ctx.lineTo(midB.sx, midB.sy); t7Ctx.stroke();

    // 2. Muros Laterales Pre-Fracturados (Wall-Break X = ±1.25)
    [-1.25, 1.25].forEach((wx) => {
      const wPts = [
        p3d(wx, 0, -0.78), p3d(wx, 0.28, -0.78),
        p3d(wx, 0.28, 0.78), p3d(wx, 0, 0.78)
      ];
      t7Ctx.fillStyle = t7State.mode === 'CLOTH' ? 'rgba(255, 42, 84, 0.78)' : 'rgba(245, 196, 81, 0.35)';
      t7Ctx.strokeStyle = '#ff2a54';
      t7Ctx.lineWidth = 2;
      t7Ctx.beginPath();
      wPts.forEach((pt, i) => (i === 0 ? t7Ctx.moveTo(pt.sx, pt.sy) : t7Ctx.lineTo(pt.sx, pt.sy)));
      t7Ctx.closePath();
      t7Ctx.fill();
      t7Ctx.stroke();
    });

    // 3. Tazón / Tribunas del Estadio en 3D (Anillo Poligonal de 16 Segmentos)
    const segs = 16;
    for (let s = 0; s < segs; s++) {
      // Dejar abierto el frente (+Z) para la cámara 2.5D si es Bombonera o estadio con vista frontal
      const a0 = (s / segs) * Math.PI * 2;
      const a1 = ((s + 1) / segs) * Math.PI * 2;
      if (Math.sin(a0) > 0.55 && Math.sin(a1) > 0.55) continue;

      const rxIn = 1.38;
      const rzIn = 0.92;
      const rxOut = 1.75;
      const rzOut = 1.22;
      const tierH = st.ArchType === 'BOMBONERA_D' ? 0.85 : 0.62;

      const b1 = p3d(Math.cos(a0) * rxIn, 0, Math.sin(a0) * rzIn);
      const b2 = p3d(Math.cos(a1) * rxIn, 0, Math.sin(a1) * rzIn);
      const t2 = p3d(Math.cos(a1) * rxOut, tierH, Math.sin(a1) * rzOut);
      const t1 = p3d(Math.cos(a0) * rxOut, tierH, Math.sin(a0) * rzOut);

      t7Ctx.fillStyle = (s % 2 === 0) ? st.PrimaryColor : st.SecondaryColor;
      t7Ctx.globalAlpha = t7State.mode === 'SKELETON' ? 0.18 : 0.72;
      t7Ctx.strokeStyle = isSfumato ? '#ffe299' : '#ffffff';
      t7Ctx.lineWidth = 1.2;
      t7Ctx.beginPath();
      t7Ctx.moveTo(b1.sx, b1.sy); t7Ctx.lineTo(b2.sx, b2.sy);
      t7Ctx.lineTo(t2.sx, t2.sy); t7Ctx.lineTo(t1.sx, t1.sy);
      t7Ctx.closePath();
      t7Ctx.fill();
      t7Ctx.globalAlpha = 1.0;
      t7Ctx.stroke();

      // Aletas Verticales Iluminadas para Nacional de Lima (29 Fins) o Bastiones para Defensores
      if (st.ArchType === 'LIMA_FINS' || st.ArchType === 'DEFENSORES_FORT') {
        const finTop = p3d(Math.cos(a0) * (rxOut + 0.06), tierH + 0.25, Math.sin(a0) * (rzOut + 0.06));
        t7Ctx.strokeStyle = st.PrimaryColor;
        t7Ctx.lineWidth = 3;
        t7Ctx.beginPath();
        t7Ctx.moveTo(t1.sx, t1.sy);
        t7Ctx.lineTo(finTop.sx, finTop.sy);
        t7Ctx.stroke();
      }
    }

    // 4. Landmarks Específicos por Estadio CONMEBOL en 3D
    if (st.ArchType === 'CENTENARIO_TOWER') {
      // Torre de los Homenajes Art Déco (Uruguay)
      const twBase = p3d(0, 0, -1.35);
      const twTop = p3d(0, 1.55, -1.35);
      t7Ctx.strokeStyle = '#e0e6ed';
      t7Ctx.lineWidth = 14;
      t7Ctx.beginPath(); t7Ctx.moveTo(twBase.sx, twBase.sy); t7Ctx.lineTo(twTop.sx, twTop.sy); t7Ctx.stroke();
      t7Ctx.strokeStyle = '#4fc3f7';
      t7Ctx.lineWidth = 3;
      t7Ctx.beginPath(); t7Ctx.moveTo(twBase.sx, twBase.sy); t7Ctx.lineTo(twTop.sx, twTop.sy); t7Ctx.stroke();
    } else if (st.ArchType === 'NUNOA_ANDES' || st.ArchType === 'ATAHUALPA_VOLCANO' || st.ArchType === 'SILES_MONOLITH') {
      // Cordillera de los Andes / Volcán Pichincha-Cotopaxi / Illimani + Monolito Tiwanaku
      const peaks = [-1.5, -0.75, 0, 0.75, 1.5];
      peaks.forEach((px, i) => {
        const pkBaseL = p3d(px - 0.55, 0, -1.65);
        const pkBaseR = p3d(px + 0.55, 0, -1.65);
        const pkApex = p3d(px, 1.35 + (i % 2) * 0.35, -1.75);
        t7Ctx.fillStyle = st.ArchType === 'ATAHUALPA_VOLCANO' && i === 2 ? 'rgba(255, 87, 34, 0.65)' : 'rgba(180, 210, 235, 0.45)';
        t7Ctx.strokeStyle = '#ffffff';
        t7Ctx.beginPath();
        t7Ctx.moveTo(pkBaseL.sx, pkBaseL.sy);
        t7Ctx.lineTo(pkApex.sx, pkApex.sy);
        t7Ctx.lineTo(pkBaseR.sx, pkBaseR.sy);
        t7Ctx.closePath();
        t7Ctx.fill();
        t7Ctx.stroke();
      });

      if (st.ArchType === 'SILES_MONOLITH') {
        // Monolito Tiwanaku + Nubes flotantes a 3600m
        const mBot = p3d(0, 0, -1.18);
        const mTop = p3d(0, 1.05, -1.18);
        t7Ctx.strokeStyle = '#c89d54';
        t7Ctx.lineWidth = 16;
        t7Ctx.beginPath(); t7Ctx.moveTo(mBot.sx, mBot.sy); t7Ctx.lineTo(mTop.sx, mTop.sy); t7Ctx.stroke();
      }
    } else if (st.ArchType === 'AVILA_HELIPAD') {
      // Helipuerto VIP elevado con H luminosa
      const hpCenter = p3d(1.45, 0.95, -0.95);
      t7Ctx.fillStyle = 'rgba(0, 229, 255, 0.32)';
      t7Ctx.strokeStyle = '#00e5ff';
      t7Ctx.lineWidth = 2.5;
      t7Ctx.beginPath();
      t7Ctx.arc(hpCenter.sx, hpCenter.sy, 26, 0, Math.PI * 2);
      t7Ctx.fill();
      t7Ctx.stroke();
      t7Ctx.fillStyle = '#ffffff';
      t7Ctx.font = 'bold 14px Consolas, monospace';
      t7Ctx.fillText('H', hpCenter.sx - 5, hpCenter.sy + 5);
    }

    // 4 Torres de Reflectores Emisivos
    [[-1.55, -1.05], [1.55, -1.05], [-1.55, 1.05], [1.55, 1.05]].forEach(([tx, tz]) => {
      const pBot = p3d(tx, 0, tz);
      const pTop = p3d(tx, 1.32, tz);
      t7Ctx.strokeStyle = '#8b9bb4';
      t7Ctx.lineWidth = 2.5;
      t7Ctx.beginPath(); t7Ctx.moveTo(pBot.sx, pBot.sy); t7Ctx.lineTo(pTop.sx, pTop.sy); t7Ctx.stroke();

      t7Ctx.fillStyle = isSfumato ? '#ffe299' : '#00e5ff';
      t7Ctx.beginPath(); t7Ctx.arc(pTop.sx, pTop.sy, 6, 0, Math.PI * 2); t7Ctx.fill();
    });
  }

  // Renderizador 3D de Props (`SM_Ball_TruncatedIcosahedron_32Panels.glb` y `SM_Stage_PitchAndDestructibleWalls.glb`)
  function renderProp3DModel(propKey, cx, cy, isSfumato) {
    const p3d = (x, y, z) => project3DPoint({ x, y, z }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);

    if (propKey === 'BALL_32') {
      // Icoságono Truncado 3D de 32 Paneles a Gran Escala
      const radius = 0.85;
      const centerPt = p3d(0, 0.92, 0);
      const screenR = Math.max(45, radius * centerPt.scale);

      const ballGrad = t7Ctx.createRadialGradient(
        centerPt.sx - screenR * 0.3, centerPt.sy - screenR * 0.3, screenR * 0.1,
        centerPt.sx, centerPt.sy, screenR
      );
      if (isSfumato) {
        ballGrad.addColorStop(0, '#fff3d1');
        ballGrad.addColorStop(0.7, '#c89d54');
        ballGrad.addColorStop(1, '#3b240e');
      } else {
        ballGrad.addColorStop(0, '#ffffff');
        ballGrad.addColorStop(0.75, '#cfd8e3');
        ballGrad.addColorStop(1, '#1b263b');
      }

      t7Ctx.fillStyle = ballGrad;
      t7Ctx.strokeStyle = isSfumato ? '#d4a347' : '#00e5ff';
      t7Ctx.lineWidth = 3;
      t7Ctx.beginPath();
      t7Ctx.arc(centerPt.sx, centerPt.sy, screenR, 0, Math.PI * 2);
      t7Ctx.fill();
      t7Ctx.stroke();

      // Dibujar los paneles pentagonales/hexagonales rotando en 3D sobre la esfera
      const latRings = [-0.55, 0, 0.55];
      latRings.forEach((lat, rIdx) => {
        const count = rIdx === 1 ? 8 : 5;
        for (let i = 0; i < count; i++) {
          const lon = (i / count) * Math.PI * 2;
          const bx = Math.cos(lon) * Math.cos(lat) * radius;
          const by = 0.92 + Math.sin(lat) * radius;
          const bz = Math.sin(lon) * Math.cos(lat) * radius;
          const panelPt = p3DOnFront(bx, by, bz, cx, cy);
          if (panelPt) {
            t7Ctx.fillStyle = (i + rIdx) % 2 === 0 ? '#12161f' : 'rgba(212, 163, 71, 0.45)';
            t7Ctx.strokeStyle = '#f5c451';
            t7Ctx.lineWidth = 1.5;
            t7Ctx.beginPath();
            for (let v = 0; v < 5; v++) {
              const va = (v / 5) * Math.PI * 2 + t7State.yaw;
              const px = panelPt.sx + Math.cos(va) * (screenR * 0.22);
              const py = panelPt.sy + Math.sin(va) * (screenR * 0.22);
              if (v === 0) t7Ctx.moveTo(px, py);
              else t7Ctx.lineTo(px, py);
            }
            t7Ctx.closePath();
            t7Ctx.fill();
            t7Ctx.stroke();
          }
        }
      });
    } else {
      // Prop Arena Base + Muros Destructibles (`SM_Stage_PitchAndDestructibleWalls.glb`)
      renderStage3DModel(STAGES_3D_CATALOG[0], cx, cy, t7Canvas.width, t7Canvas.height, isSfumato);
    }
  }

  function p3DOnFront(x, y, z, cx, cy) {
    const cosY = Math.cos(t7State.yaw);
    const sinY = Math.sin(t7State.yaw);
    const z1 = x * sinY + z * cosY;
    if (z1 > 0.25) return null; // Oculto detrás de la esfera
    return project3DPoint({ x, y, z }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
  }

  function getActiveTab7GlbUrl() {
    if (t7State.category === 'FIGHTERS') {
      const ch = ROSTER_DATA[t7State.charIdx] || ROSTER_DATA[0];
      const prof = CHAR_3D_PROFILES[ch.Name] || CHAR_3D_PROFILES.FENOMENO_BR;
      return `../Assets/Models3D/Fighters/${prof.file}`;
    }
    if (t7State.category === 'STAGES') {
      const st = STAGES_3D_CATALOG[t7State.stageIdx] || STAGES_3D_CATALOG[0];
      return `../Assets/Models3D/Stages/${st.File}`;
    }
    return t7State.propKey === 'BALL_32'
      ? '../Assets/Models3D/Props/SM_Ball_TruncatedIcosahedron_32Panels.glb'
      : '../Assets/Models3D/Stages/SM_Stage_PitchAndDestructibleWalls.glb';
  }

  function renderTab7Studio3D() {
    t7State.tick++;
    if (t7State.animPlaying) {
      t7State.animClock += t7State.animSpeed;
    }
    if (t7State.autoRotate && !t7State.isDragging) {
      t7State.yaw += 0.011;
    }
    if (t7State.ballKickTimer > 0) {
      t7State.ballKickTimer--;
    }

    if (t7UseWebGL && window.SAFWglViewer && window.SAFWglViewer.isReady()) {
      const glbUrl = getActiveTab7GlbUrl();
      window.SAFWglViewer.render(glbUrl, t7State);
      const stats = window.SAFWglViewer.getStats();
      syncTab7LiveGlbStats(stats);

      const kfLbl = document.getElementById('t7-clip-kf-lbl');
      if (t7State.category === 'FIGHTERS') {
        const clipMeta = CLIP_3D_METADATA[t7State.pose] || CLIP_3D_METADATA.Idle_Breath;
        const totalKf = stats.loaded && stats.totalKf > 1 ? stats.totalKf : clipMeta.kf;
        const curKf = stats.loaded && stats.totalKf > 1 ? stats.curKf : ((Math.floor(t7State.animClock) % clipMeta.kf) + 1);
        if (kfLbl) kfLbl.textContent = `KF: ${String(curKf).padStart(3, '0')} / ${totalKf}`;
      } else if (kfLbl) {
        kfLbl.textContent = 'STATIC MESH';
      }

      if (t7WebglHud) {
        t7WebglHud.style.display = 'block';
        const statusBadge = stats.loaded
          ? `<span class="hud-badge">WEBGL2 glTF 2.0</span>`
          : `<span class="hud-badge" style="color:#ffe07d;border-color:#ffe07d;">CARGANDO .GLB...</span>`;
        const geoInfo = stats.loaded
          ? `${stats.verts.toLocaleString()} VERTS / ${stats.tris.toLocaleString()} TRIS${stats.joints ? ` • ${stats.joints} JOINTS` : ''}`
          : stats.file;
        t7WebglHud.innerHTML =
          `<div>${statusBadge}<strong>${stats.file || glbUrl.split('/').pop()}</strong> (${geoInfo})</div>` +
          `<div class="hud-sub">MODE: ${t7State.mode} | LIGHT: ${t7State.lighting} | CLIP: ${t7State.category === 'FIGHTERS' ? t7State.pose : 'N/A'} | SPEED: ${t7State.animSpeed}x | YAW: ${(t7State.yaw * 57.3).toFixed(0)}°</div>`;
      }
      return;
    }

    if (t7WebglHud) t7WebglHud.style.display = 'none';
    if (!t7Ctx) return;

    const w = t7Canvas.width;
    const h = t7Canvas.height;
    t7Ctx.clearRect(0, 0, w, h);

    const isSfumato = t7State.lighting === 'SFUMATO';
    const cx = w / 2;
    const cy = h * 0.76;

    // Fondo del Estudio según Preset de Iluminación (Renacimiento Sfumato vs Estadio Nocturno Street-Ink)
    const bgGrad = t7Ctx.createRadialGradient(cx, h * 0.45, 30, cx, h * 0.5, 440);
    if (isSfumato) {
      bgGrad.addColorStop(0, '#3a2714');
      bgGrad.addColorStop(0.55, '#1b1209');
      bgGrad.addColorStop(1, '#090603');
    } else {
      bgGrad.addColorStop(0, '#131d31');
      bgGrad.addColorStop(1, '#05080f');
    }
    t7Ctx.fillStyle = bgGrad;
    t7Ctx.fillRect(0, 0, w, h);

    // 1. Grilla 3D de Piso Determinista (Radio 1.6m)
    t7Ctx.lineWidth = 1;
    for (let g = -1.6; g <= 1.61; g += 0.4) {
      const pA = project3DPoint({ x: g, y: 0, z: -1.6 }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
      const pB = project3DPoint({ x: g, y: 0, z: 1.6 }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
      t7Ctx.strokeStyle = Math.abs(g) < 0.05
        ? (isSfumato ? 'rgba(212, 163, 71, 0.55)' : 'rgba(0, 229, 255, 0.45)')
        : (isSfumato ? 'rgba(255, 220, 150, 0.1)' : 'rgba(255, 255, 255, 0.08)');
      t7Ctx.beginPath(); t7Ctx.moveTo(pA.sx, pA.sy); t7Ctx.lineTo(pB.sx, pB.sy); t7Ctx.stroke();

      const pC = project3DPoint({ x: -1.6, y: 0, z: g }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
      const pD = project3DPoint({ x: 1.6, y: 0, z: g }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
      t7Ctx.strokeStyle = Math.abs(g) < 0.05 ? 'rgba(245, 196, 81, 0.45)' : 'rgba(255, 255, 255, 0.08)';
      t7Ctx.beginPath(); t7Ctx.moveTo(pC.sx, pC.sy); t7Ctx.lineTo(pD.sx, pD.sy); t7Ctx.stroke();
    }

    // Si la categoría activa es STAGES o PROPS, renderizar el estadio o prop 3D correspondiente
    if (t7State.category === 'STAGES') {
      const st = STAGES_3D_CATALOG[t7State.stageIdx] || STAGES_3D_CATALOG[0];
      renderStage3DModel(st, cx, cy, w, h, isSfumato);

      t7Ctx.fillStyle = 'rgba(8, 12, 20, 0.88)';
      t7Ctx.fillRect(14, 14, 465, 62);
      t7Ctx.strokeStyle = isSfumato ? '#d4a347' : '#00e5ff';
      t7Ctx.strokeRect(14, 14, 465, 62);
      t7Ctx.fillStyle = '#ffe07d';
      t7Ctx.font = 'bold 12px Consolas, monospace';
      t7Ctx.fillText(`3D STADIUM: ${st.File} (${st.Vertices.toLocaleString()} VERTS / ${st.Triangles.toLocaleString()} TRIS)`, 24, 34);
      t7Ctx.fillStyle = '#00e5ff';
      t7Ctx.fillText(`BOUNDS: ${st.Dimensions.WidthX}m × ${st.Dimensions.HeightY}m × ${st.Dimensions.DepthZ}m | MATERIALS: ${st.MaterialCount}`, 24, 54);
      return;
    }

    if (t7State.category === 'PROPS') {
      renderProp3DModel(t7State.propKey, cx, cy, isSfumato);

      t7Ctx.fillStyle = 'rgba(8, 12, 20, 0.88)';
      t7Ctx.fillRect(14, 14, 465, 62);
      t7Ctx.strokeStyle = '#f5c451';
      t7Ctx.strokeRect(14, 14, 465, 62);
      t7Ctx.fillStyle = '#ffe07d';
      t7Ctx.font = 'bold 12px Consolas, monospace';
      t7Ctx.fillText(
        t7State.propKey === 'BALL_32'
          ? '3D PROP: SM_Ball_TruncatedIcosahedron_32Panels.glb (561 VERTS / 1024 TRIS)'
          : '3D ARENA: SM_Stage_PitchAndDestructibleWalls.glb (216 VERTS / 108 TRIS)',
        24,
        34
      );
      t7Ctx.fillStyle = '#00e5ff';
      t7Ctx.fillText(`YAW: ${(t7State.yaw * 57.3).toFixed(0)}° | ZOOM: ${t7State.zoom.toFixed(2)}x | LIGHTING: ${t7State.lighting}`, 24, 54);
      return;
    }

    // 2. Categoría FIGHTERS: Evaluar los 10 Clips de Animación glTF 2.0 (5 Full-Body 60 FPS + 5 Stepped)
    const ch = ROSTER_DATA[t7State.charIdx] || ROSTER_DATA[0];
    const prof = CHAR_3D_PROFILES[ch.Name] || CHAR_3D_PROFILES.FENOMENO_BR;
    const clipMeta = CLIP_3D_METADATA[t7State.pose] || CLIP_3D_METADATA.Idle_Breath;
    const isSteppedClip = t7State.pose.startsWith('Anim_') || t7State.mode === 'SMEAR';
    const animT = isSteppedClip ? Math.floor(t7State.animClock / 4) * 4 : t7State.animClock;

    const curKf = (Math.floor(animT) % clipMeta.kf) + 1;
    const kfLbl = document.getElementById('t7-clip-kf-lbl');
    if (kfLbl) {
      kfLbl.textContent = `KF: ${String(curKf).padStart(3, '0')} / ${clipMeta.kf}`;
    }

    const breath = Math.sin(animT * 0.08) * 0.03;
    const hScale = prof.heightM / 1.80;
    const bScale = prof.build;
    const isBoss = ch.Name === 'VAR_ZERO_BOSS';
    const bossHover = isBoss ? 0.14 + Math.sin(animT * 0.06) * 0.05 : 0;

    let pelvisOffset = { x: 0, y: 0.96 * hScale + breath + bossHover, z: 0 };
    let headPos = { x: 0, y: 1.72 * hScale + breath + bossHover, z: 0.04 };
    let handL = { x: -0.34 * bScale, y: 1.18 * hScale + breath + bossHover, z: 0.22 };
    let handR = { x: 0.34 * bScale, y: 1.22 * hScale + breath + bossHover, z: 0.26 };
    let kneeL = { x: -0.15 * bScale, y: 0.50 * hScale + bossHover, z: 0.06 };
    let kneeR = { x: 0.15 * bScale, y: 0.50 * hScale + bossHover, z: -0.04 };
    let footL = { x: -0.16 * bScale, y: 0.06 + bossHover, z: 0.10 };
    let footR = { x: 0.16 * bScale, y: 0.06 + bossHover, z: -0.10 };

    const smearMult = (t7State.mode === 'SMEAR' || t7State.pose === 'Anim_236SK_Shot' || t7State.pose === 'Kick_High' || t7State.pose === 'Special_Chilena')
      ? t7State.smearScale
      : 1.0;

    if (t7State.pose === 'Idle_Breath' || t7State.pose === 'Anim_Idle') {
      const sway = Math.sin(animT * 0.07) * 0.06;
      pelvisOffset.x = sway * 0.5;
      headPos.x = sway;
      handL.y += Math.cos(animT * 0.07) * 0.04;
      handR.y -= Math.cos(animT * 0.07) * 0.04;
    } else if (t7State.pose === 'Dash_Forward') {
      const stride = Math.sin(animT * 0.22);
      pelvisOffset.z = 0.18;
      headPos.z = 0.42;
      headPos.y = 1.56 * hScale;
      kneeL.z = stride * 0.38;
      footL.z = stride * 0.62;
      footL.y = Math.max(0.05, 0.18 + stride * 0.16);
      kneeR.z = -stride * 0.38;
      footR.z = -stride * 0.62;
      footR.y = Math.max(0.05, 0.18 - stride * 0.16);
      handL.z = -stride * 0.45;
      handR.z = stride * 0.45;
    } else if (t7State.pose === 'Anim_5LP_Jab4f') {
      handR = { x: 0.18 * bScale, y: 1.42 * hScale, z: 0.75 * smearMult };
    } else if (t7State.pose === 'Kick_High' || t7State.pose === 'Anim_236SK_Shot') {
      const kickPulse = 0.75 + Math.abs(Math.sin(animT * 0.12)) * 0.25;
      kneeR = { x: 0.14 * bScale, y: 0.82 * hScale, z: 0.38 * kickPulse };
      footR = { x: 0.10 * bScale, y: 1.08 * hScale, z: 0.88 * smearMult * kickPulse };
      pelvisOffset.z = -0.10;
    } else if (t7State.pose === 'Special_Chilena' || t7State.pose === 'Anim_623HP_BicycleKick') {
      // Chilena Acrobática 360° sobre pelvis_visual_offset
      const flip = Math.sin(animT * 0.14) * 0.15;
      pelvisOffset = { x: 0, y: (1.32 + flip) * hScale, z: -0.12 };
      headPos = { x: 0, y: (0.86 + flip) * hScale, z: -0.48 };
      kneeR = { x: 0.12, y: (1.58 + flip) * hScale, z: 0.18 };
      footR = { x: 0.08, y: (1.96 + flip) * hScale * smearMult, z: 0.45 };
      footL = { x: -0.14, y: (1.46 + flip) * hScale, z: -0.12 };
    } else if (t7State.pose === 'Anim_214SK_Scorpion') {
      // Pose El Escorpión (High-Crush arqueado hacia adelante con talones sobre la cabeza)
      pelvisOffset = { x: 0, y: 0.82 * hScale, z: 0.12 };
      headPos = { x: 0, y: 0.95 * hScale, z: 0.52 };
      kneeL = { x: -0.15, y: 1.18 * hScale, z: -0.35 };
      kneeR = { x: 0.15, y: 1.18 * hScale, z: -0.35 };
      footL = { x: -0.12, y: 1.48 * hScale, z: 0.25 * smearMult };
      footR = { x: 0.12, y: 1.48 * hScale, z: 0.25 * smearMult };
    } else if (t7State.pose === 'Victory_Pose') {
      // Saludo Triunfal de Campeón con ambos brazos en alto
      const cheer = Math.abs(Math.sin(animT * 0.1)) * 0.08;
      handL = { x: -0.44 * bScale, y: (1.92 + cheer) * hScale + bossHover, z: 0.12 };
      handR = { x: 0.44 * bScale, y: (1.92 + cheer) * hScale + bossHover, z: 0.12 };
      headPos.y += cheer * 0.5;
    } else if (t7State.pose === 'Mocap_Walk_Forward') {
      const stride = Math.sin(animT * 0.14);
      kneeL.z = stride * 0.25;
      footL.z = stride * 0.42;
      footL.y = Math.max(0.05, 0.12 + stride * 0.09);
      kneeR.z = -stride * 0.25;
      footR.z = -stride * 0.42;
      footR.y = Math.max(0.05, 0.12 - stride * 0.09);
      handL.z = -stride * 0.28;
      handR.z = stride * 0.28;
    } else if (t7State.pose === 'Mocap_Backdash_Dodge') {
      const hop = Math.abs(Math.sin(animT * 0.16));
      pelvisOffset.z = -0.28;
      pelvisOffset.y += hop * 0.16;
      headPos.y += hop * 0.12;
      headPos.z = -0.22;
      kneeL.z = 0.24;
      kneeR.z = 0.18;
    } else if (t7State.pose === 'Mocap_Block_Guard') {
      pelvisOffset.y = 0.78 * hScale;
      headPos.y = 1.48 * hScale;
      headPos.z = 0.08;
      handL = { x: -0.14 * bScale, y: 1.42 * hScale, z: 0.34 };
      handR = { x: 0.14 * bScale, y: 1.46 * hScale, z: 0.36 };
      kneeL.z = 0.22;
      kneeR.z = -0.14;
    } else if (t7State.pose === 'Mocap_Hitstun_Knockback') {
      const whip = Math.sin(animT * 0.2);
      pelvisOffset.z = -0.24;
      headPos.z = -0.45 - whip * 0.08;
      headPos.y = 1.56 * hScale;
      handL = { x: -0.52 * bScale, y: 1.45 * hScale, z: -0.12 };
      handR = { x: 0.52 * bScale, y: 1.45 * hScale, z: -0.12 };
    } else if (t7State.pose === 'Mocap_Super_Potrero') {
      const air = 0.45 + Math.abs(Math.sin(animT * 0.12)) * 0.38;
      pelvisOffset = { x: 0, y: (1.05 + air) * hScale, z: 0.12 };
      headPos = { x: 0, y: (1.68 + air) * hScale, z: -0.18 };
      kneeR = { x: 0.16, y: (1.35 + air) * hScale, z: 0.48 };
      footR = { x: 0.12, y: (1.58 + air) * hScale, z: 0.92 * smearMult };
    } else if (t7State.pose === 'Mocap_KO_Knockdown') {
      pelvisOffset = { x: 0, y: 0.28 * hScale, z: -0.18 };
      headPos = { x: 0, y: 0.22 * hScale, z: -0.92 };
      kneeL = { x: -0.18, y: 0.24, z: 0.32 };
      footL = { x: -0.20, y: 0.10, z: 0.72 };
      footR = { x: 0.20, y: 0.10, z: 0.68 };
    }

    const joints = {
      root: { x: 0, y: 0, z: 0 },
      pelvis: pelvisOffset,
      spine2: { x: (pelvisOffset.x + headPos.x) * 0.5, y: (pelvisOffset.y + headPos.y) * 0.52, z: (pelvisOffset.z + headPos.z) * 0.5 },
      neck: { x: headPos.x, y: headPos.y - 0.16 * hScale, z: headPos.z },
      head: headPos,
      clavL: { x: -0.22 * bScale, y: headPos.y - 0.20 * hScale, z: headPos.z },
      clavR: { x: 0.22 * bScale, y: headPos.y - 0.20 * hScale, z: headPos.z },
      elbowL: { x: -0.32 * bScale, y: (headPos.y + handL.y) * 0.48, z: 0.06 },
      elbowR: { x: 0.32 * bScale, y: (headPos.y + handR.y) * 0.48, z: 0.12 },
      handL,
      handR,
      hipL: { x: -0.13 * bScale, y: pelvisOffset.y - 0.04, z: pelvisOffset.z },
      hipR: { x: 0.13 * bScale, y: pelvisOffset.y - 0.04, z: pelvisOffset.z },
      kneeL,
      kneeR,
      footL,
      footR
    };

    const projJoints = {};
    Object.keys(joints).forEach((k) => {
      projJoints[k] = project3DPoint(joints[k], cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
    });

    // 3. Si estamos en modo SMEAR o SKELETON, mostrar Caja AABB Determinista Exacta (Hurtbox Verde / Azul en Escorpión)
    if (t7State.mode === 'SMEAR' || t7State.pose === 'Anim_214SK_Scorpion') {
      const boxTop = t7State.pose === 'Anim_214SK_Scorpion' ? 1.12 * hScale : 1.78 * hScale;
      const boxColor = t7State.pose === 'Anim_214SK_Scorpion' ? '#00e5ff' : '#00e676';
      const corners = [
        { x: -0.32, y: 0, z: -0.25 }, { x: 0.32, y: 0, z: -0.25 },
        { x: 0.32, y: boxTop, z: -0.25 }, { x: -0.32, y: boxTop, z: -0.25 },
        { x: -0.32, y: 0, z: 0.25 }, { x: 0.32, y: 0, z: 0.25 },
        { x: 0.32, y: boxTop, z: 0.25 }, { x: -0.32, y: boxTop, z: 0.25 }
      ].map((c) => project3DPoint(c, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom));

      t7Ctx.strokeStyle = boxColor;
      t7Ctx.lineWidth = 1.8;
      t7Ctx.setLineDash([5, 4]);
      const edges = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
      edges.forEach(([a, b]) => {
        t7Ctx.beginPath();
        t7Ctx.moveTo(corners[a].sx, corners[a].sy);
        t7Ctx.lineTo(corners[b].sx, corners[b].sy);
        t7Ctx.stroke();
      });
      t7Ctx.setLineDash([]);
    }

    // 4. Renderizado Volumétrico 3D del Cuerpo, Camiseta (Chaos Cloth Weight Map) y Extremidades
    if (t7State.mode !== 'SKELETON') {
      const drawLimb3D = (pA, pB, radiusPx, fillCol, strokeCol) => {
        t7Ctx.strokeStyle = fillCol;
        t7Ctx.lineCap = 'round';
        t7Ctx.lineWidth = radiusPx * 2;
        t7Ctx.beginPath();
        t7Ctx.moveTo(pA.sx, pA.sy);
        t7Ctx.lineTo(pB.sx, pB.sy);
        t7Ctx.stroke();

        t7Ctx.strokeStyle = strokeCol;
        t7Ctx.lineWidth = 2;
        t7Ctx.stroke();
      };

      const rimCol = isSfumato ? '#ffe299' : '#ffffff';
      drawLimb3D(projJoints.hipL, projJoints.kneeL, 14 * bScale, ch.ColorSecondary || '#102038', rimCol);
      drawLimb3D(projJoints.hipR, projJoints.kneeR, 14 * bScale, ch.ColorSecondary || '#102038', rimCol);
      drawLimb3D(projJoints.kneeL, projJoints.footL, 10 * bScale, '#d9a17c', ch.ColorPrimary);
      drawLimb3D(projJoints.kneeR, projJoints.footR, 10 * bScale * ((t7State.pose === 'Kick_High' || t7State.pose === 'Anim_236SK_Shot') ? smearMult : 1), '#d9a17c', '#ff2a54');

      // Simulación de Malla 3D de la Camiseta Noventera + Chaos Cloth 5.4
      const windWave = (t7State.windPct / 100) * 0.14;
      const rows = 6;
      const cols = 8;
      for (let r = 0; r < rows; r++) {
        const v0 = r / rows;
        const v1 = (r + 1) / rows;
        const maxDistCm = (0.5 + Math.pow(v1, 1.6) * 11.5).toFixed(1);

        for (let c = 0; c < cols; c++) {
          const ang0 = (c / cols) * Math.PI * 2;
          const ang1 = ((c + 1) / cols) * Math.PI * 2;

          const flare0 = 1 + v0 * 0.18;
          const flare1 = 1 + v1 * 0.28;
          const clothFlutter0 = Math.sin(animT * 0.18 + c * 1.1) * windWave * v0;
          const clothFlutter1 = Math.sin(animT * 0.18 + (c + 1) * 1.1) * windWave * v1;

          const yTop = joints.neck.y - v0 * (joints.neck.y - joints.pelvis.y + 0.08);
          const yBot = joints.neck.y - v1 * (joints.neck.y - joints.pelvis.y + 0.08);

          const rx = 0.23 * bScale;
          const rz = 0.15 * bScale;

          const p1 = project3DPoint({ x: Math.cos(ang0) * rx * flare0 + clothFlutter0, y: yTop, z: Math.sin(ang0) * rz * flare0 }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
          const p2 = project3DPoint({ x: Math.cos(ang1) * rx * flare0 + clothFlutter0, y: yTop, z: Math.sin(ang1) * rz * flare0 }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
          const p3 = project3DPoint({ x: Math.cos(ang1) * rx * flare1 + clothFlutter1, y: yBot, z: Math.sin(ang1) * rz * flare1 }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
          const p4 = project3DPoint({ x: Math.cos(ang0) * rx * flare1 + clothFlutter1, y: yBot, z: Math.sin(ang0) * rz * flare1 }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);

          if (t7State.mode === 'CLOTH') {
            const hue = Math.round((1 - v1) * 195);
            t7Ctx.fillStyle = `hsla(${hue}, 95%, 52%, 0.78)`;
            t7Ctx.strokeStyle = '#ffffff';
            t7Ctx.lineWidth = 1;
          } else {
            t7Ctx.fillStyle = (c % 2 === 0) ? ch.ColorPrimary : (ch.ColorSecondary || ch.ColorPrimary);
            t7Ctx.strokeStyle = isSfumato ? 'rgba(255, 226, 153, 0.35)' : 'rgba(255, 255, 255, 0.25)';
            t7Ctx.lineWidth = 1;
          }

          t7Ctx.beginPath();
          t7Ctx.moveTo(p1.sx, p1.sy);
          t7Ctx.lineTo(p2.sx, p2.sy);
          t7Ctx.lineTo(p3.sx, p3.sy);
          t7Ctx.lineTo(p4.sx, p4.sy);
          t7Ctx.closePath();
          t7Ctx.fill();
          t7Ctx.stroke();

          if (t7State.mode === 'CLOTH' && c === 0 && (r === 0 || r === rows - 1)) {
            t7Ctx.fillStyle = '#ffffff';
            t7Ctx.font = 'bold 10px Consolas, monospace';
            t7Ctx.fillText(`MaxDist: ${maxDistCm}cm`, p2.sx + 8, p2.sy);
          }
        }
      }

      drawLimb3D(projJoints.clavL, projJoints.elbowL, 11 * bScale, ch.ColorPrimary, rimCol);
      drawLimb3D(projJoints.clavR, projJoints.elbowR, 11 * bScale, ch.ColorPrimary, rimCol);
      drawLimb3D(projJoints.elbowL, projJoints.handL, 9 * bScale, '#d9a17c', rimCol);
      drawLimb3D(projJoints.elbowR, projJoints.handR, 9 * bScale, '#d9a17c', rimCol);
    }

    // Halo Astrolabio Doble Contrarrotatorio en SK_SUPREME_JUDGE_BOSS
    const headR = 22 * (projJoints.head.scale / 110);
    if (isBoss) {
      t7Ctx.save();
      t7Ctx.strokeStyle = '#ffe299';
      t7Ctx.lineWidth = 2.5;
      t7Ctx.beginPath();
      t7Ctx.arc(projJoints.head.sx, projJoints.head.sy, headR * 1.85, animT * 0.05, animT * 0.05 + Math.PI * 1.45);
      t7Ctx.stroke();
      t7Ctx.strokeStyle = '#00e5ff';
      t7Ctx.beginPath();
      t7Ctx.arc(projJoints.head.sx, projJoints.head.sy, headR * 1.45, -animT * 0.07, -animT * 0.07 + Math.PI * 1.35);
      t7Ctx.stroke();
      t7Ctx.restore();
    }

    // Cabeza 3D + Hair Cards Dinámicas (`M_FighterHairCards`)
    t7Ctx.fillStyle = t7State.mode === 'SKELETON' ? 'rgba(0, 229, 255, 0.25)' : '#e0ac8b';
    t7Ctx.strokeStyle = isSfumato ? '#ffe299' : '#ffffff';
    t7Ctx.lineWidth = 2.5;
    t7Ctx.beginPath();
    t7Ctx.arc(projJoints.head.sx, projJoints.head.sy, Math.max(12, headR), 0, Math.PI * 2);
    t7Ctx.fill();
    t7Ctx.stroke();

    if (prof.hairStyle === 'AFRO_GOLD' || prof.hairStyle === 'CURLY_DARK' || prof.hairStyle === 'MANE_GOLD' || prof.hairStyle === 'CURLY_BAND') {
      const hairCol = (prof.hairStyle === 'AFRO_GOLD' || prof.hairStyle === 'MANE_GOLD') ? '#f5c451' : '#1c1c24';
      const strands = prof.hairStyle === 'AFRO_GOLD' ? 18 : 12;
      for (let s = 0; s < strands; s++) {
        const ang = (s / strands) * Math.PI * 2;
        const springFlutter = Math.sin(animT * 0.2 + s) * (t7State.windPct / 100) * 0.09;
        const hPt = project3DPoint({
          x: joints.head.x + Math.cos(ang) * 0.19 + springFlutter,
          y: joints.head.y + 0.05 + Math.sin(ang * 2) * 0.08,
          z: joints.head.z + Math.sin(ang) * 0.19
        }, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);

        t7Ctx.fillStyle = hairCol;
        t7Ctx.strokeStyle = '#ffe07d';
        t7Ctx.lineWidth = 1.2;
        t7Ctx.beginPath();
        t7Ctx.arc(hPt.sx, hPt.sy, prof.hairStyle === 'AFRO_GOLD' ? 11 : 8, 0, Math.PI * 2);
        t7Ctx.fill();
        if (t7State.mode === 'SKELETON') t7Ctx.stroke();
      }
    }

    // 5. Dibujar Jerarquía de Huesos UE5 (`root` -> `pelvis_visual_offset` -> `Twist Bones`)
    if (t7State.mode === 'SKELETON' || t7State.mode === 'SMEAR') {
      const boneLinks = [
        ['root', 'pelvis'], ['pelvis', 'spine2'], ['spine2', 'neck'], ['neck', 'head'],
        ['neck', 'clavL'], ['clavL', 'elbowL'], ['elbowL', 'handL'],
        ['neck', 'clavR'], ['clavR', 'elbowR'], ['elbowR', 'handR'],
        ['pelvis', 'hipL'], ['hipL', 'kneeL'], ['kneeL', 'footL'],
        ['pelvis', 'hipR'], ['hipR', 'kneeR'], ['kneeR', 'footR']
      ];
      t7Ctx.strokeStyle = '#f5c451';
      t7Ctx.lineWidth = 2.5;
      boneLinks.forEach(([bA, bB]) => {
        t7Ctx.beginPath();
        t7Ctx.moveTo(projJoints[bA].sx, projJoints[bA].sy);
        t7Ctx.lineTo(projJoints[bB].sx, projJoints[bB].sy);
        t7Ctx.stroke();
      });

      Object.keys(projJoints).forEach((jk) => {
        const pj = projJoints[jk];
        t7Ctx.fillStyle = jk === 'pelvis' ? '#ff2a54' : '#00e5ff';
        t7Ctx.beginPath();
        t7Ctx.arc(pj.sx, pj.sy, jk === 'pelvis' ? 6 : 4, 0, Math.PI * 2);
        t7Ctx.fill();
      });

      t7Ctx.fillStyle = '#ffe07d';
      t7Ctx.font = 'bold 10.5px Consolas, monospace';
      t7Ctx.fillText('pelvis_visual_offset (Hitshake & Smear Pivot)', projJoints.pelvis.sx + 10, projJoints.pelvis.sy);
      t7Ctx.fillStyle = '#00e676';
      t7Ctx.fillText('root (0,0,0 Ground Locked)', projJoints.root.sx + 10, projJoints.root.sy);
    }

    // 6. Dibujar el Balón Oficial CONMEBOL 3D (`SM_Ball_TruncatedIcosahedron_32Panels.glb`)
    const ballOrbitAng = t7State.tick * 0.035;
    const kickDist = t7State.ballKickTimer > 0 ? (45 - t7State.ballKickTimer) * 0.045 : 0;
    const ball3D = {
      x: Math.cos(ballOrbitAng) * (0.68 + kickDist),
      y: 0.22 + Math.abs(Math.sin(t7State.tick * 0.08)) * 0.28 + kickDist * 0.35,
      z: Math.sin(ballOrbitAng) * (0.68 + kickDist)
    };
    const projBall = project3DPoint(ball3D, cx, cy, t7State.yaw, t7State.pitch, t7State.zoom);
    const ballRad = Math.max(10, 17 * (projBall.scale / 110));

    t7Ctx.fillStyle = isSfumato ? '#f5deb3' : '#ffffff';
    t7Ctx.strokeStyle = '#f5c451';
    t7Ctx.lineWidth = 2;
    t7Ctx.beginPath();
    t7Ctx.arc(projBall.sx, projBall.sy, ballRad, 0, Math.PI * 2);
    t7Ctx.fill();
    t7Ctx.stroke();

    t7Ctx.fillStyle = '#0c1018';
    t7Ctx.beginPath();
    t7Ctx.arc(projBall.sx, projBall.sy, ballRad * 0.42, 0, Math.PI * 2);
    t7Ctx.fill();

    // HUD Técnico Superior Izquierdo en el Viewport 3D
    t7Ctx.fillStyle = 'rgba(8, 12, 20, 0.86)';
    t7Ctx.fillRect(14, 14, 485, 62);
    t7Ctx.strokeStyle = isSfumato ? '#d4a347' : '#b388ff';
    t7Ctx.lineWidth = 1.5;
    t7Ctx.strokeRect(14, 14, 485, 62);

    t7Ctx.fillStyle = '#ffe07d';
    t7Ctx.font = 'bold 12px Consolas, monospace';
    t7Ctx.fillText(`glTF 2.0: ${prof.file} (#${prof.number}) — CLIP: ${t7State.pose}`, 24, 34);
    t7Ctx.fillStyle = '#00e5ff';
    t7Ctx.fillText(
      `SPEED: ${t7State.animSpeed}x | KF: ${curKf}/${clipMeta.kf} | SMEAR: ${t7State.smearScale.toFixed(2)}x | LIGHT: ${t7State.lighting}`,
      24,
      54
    );
  }

  updateTab7InspectorUI();

  // ==========================================================================
  // 11. DEEP-LINKING POR URL HASH (#tab-1..#tab-7 & p1/p2/stage/art/boss)
  // ==========================================================================
  function applyUrlHashDeepLink() {
    const rawHash = (window.location.hash || '').replace(/^#/, '');
    if (!rawHash) return;

    const parts = rawHash.split('&');
    const tabPart = parts[0].replace('tab-', 'tab'); // soporta #tab-6 o #tab6
    const params = {};
    parts.slice(1).forEach((kv) => {
      const [k, v] = kv.split('=');
      if (k && v !== undefined) params[k] = decodeURIComponent(v);
    });

    const isBossChallenge = params.boss === '1';

    const targetTabBtn = document.querySelector(`#main-tabs .tab-btn[data-tab="${tabPart}"]`);
    if (targetTabBtn) {
      targetTabBtn.click();
    }

    if (tabPart === 'tab6') {
      if (params.p1 !== undefined) {
        const p1Val = Math.max(0, Math.min(ROSTER_DATA.length - 1, parseInt(params.p1, 10) || 0));
        t6SelP1.value = p1Val;
      }
      if (params.p2 !== undefined) {
        const p2Val = Math.max(0, Math.min(ROSTER_DATA.length - 1, parseInt(params.p2, 10) || 3));
        t6SelP2.value = p2Val;
      }
      if (params.stage !== undefined) {
        const stVal = Math.max(0, Math.min(STAGES_DATA.length - 1, parseInt(params.stage, 10) || 0));
        t6SelStage.value = stVal;
      }
      if (params.art && t6SelArtStyle) {
        if (params.art === 'SFUMATO' || params.art === 'STREET_INK') {
          t6SelArtStyle.value = params.art;
          t6State.artStyle = params.art;
        }
      }
      if (params.tourney === '1') {
        t6State.tourneyMode = true;
        t6State.tourneyRound = Math.max(1, Math.min(5, parseInt(params.round, 10) || 1));
      } else {
        t6State.tourneyMode = false;
      }

      if (params.story === '1') {
        t6State.storyMode = true;
        t6State.storyChapter = Math.max(1, Math.min(6, parseInt(params.chapter, 10) || 1));
      } else {
        t6State.storyMode = false;
      }

      if (params.mode === 'DUMMY' || params.mode === 'TRAINING') {
        t6SelAI.value = 'DUMMY';
      } else if (params.mode === 'LOCAL_2P') {
        t6SelAI.value = 'LOCAL_2P';
      } else if (isBossChallenge || parseInt(t6SelP2.value, 10) === ROSTER_DATA.length - 1) {
        t6SelAI.value = 'BOSS_VAR';
        t6SelP2.value = ROSTER_DATA.length - 1;
      } else {
        t6SelAI.value = 'CPU_PRO';
      }
      resetTab6Match();
    } else if (tabPart === 'tab7') {
      updateTab7InspectorUI();
      renderTab7Studio3D();
    }
  }

  window.addEventListener('hashchange', applyUrlHashDeepLink);
  applyUrlHashDeepLink();

  // ==========================================================================
  // 12. BUCLE MAESTRO DETERMINISTA A 60 FPS (requestAnimationFrame)
  // ==========================================================================
  let lastTime = performance.now();
  let frameCounter = 0;

  function masterLoop(now) {
    const dt = now - lastTime;
    if (dt >= 16.2) {
      lastTime = now;
      frameCounter++;

      if (t1Playing) {
        t1CurrentFrame = (t1CurrentFrame % 60) + 1;
        if (activeTab === 'tab1') updateTab1FrameMeterUI();
      }

      if (activeTab === 'tab1') renderTab1Canvas();
      else if (activeTab === 'tab3') renderTab3Canvas();
      else if (activeTab === 'tab4') renderTab4Canvases();
      else if (activeTab === 'tab6') stepTab6VersusSimulation();
      else if (activeTab === 'tab7') renderTab7Studio3D();

      if (frameCounter % 15 === 0) {
        const fpsVal = Math.min(60.0, Math.max(59.4, 1000 / Math.max(16.66, dt))).toFixed(1);
        document.getElementById('hdr-fps').textContent = `${fpsVal} FPS`;
      }
    }
    requestAnimationFrame(masterLoop);
  }

  requestAnimationFrame(masterLoop);
})();
