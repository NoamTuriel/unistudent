const root = document.documentElement;
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const M = window.Motion;
const moving = !!M && !reduce;
if (!moving) root.classList.remove('m');
const ease = [.16, 1, .3, 1];

// The bar takes the colour of the chapter passing under it
const bar = document.querySelector('.bar');
const barWatch = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) bar.dataset.field = e.target.dataset.field;
}), { rootMargin: `-63px 0px -${innerHeight - 64}px 0px` });
document.querySelectorAll('main [data-field], footer[data-field]').forEach(c => barWatch.observe(c));

// Video: plays muted with captions, unless the visitor prefers reduced motion
const film = document.getElementById('film');
if (!reduce) film.play().catch(() => {});
document.getElementById('sound').addEventListener('click', () => {
  film.muted = false; film.currentTime = 0; film.play();
});

if (moving) {
  const { animate, inView, scroll, stagger, press, hover } = M;

  // Hero: the two lines rise out of their masks
  animate('h1 .ln > span', { y: ['105%', '0%'] }, { type: 'spring', visualDuration: .9, bounce: .12, delay: stagger(.1, { startDelay: .1 }) });
  animate('.hero [data-rise]', { opacity: [0, 1], y: [28, 0] }, { duration: .8, ease, delay: stagger(.08, { startDelay: .35 }) });

  // Every other section: heading, then text, then picture, as each part arrives
  let batch = 0, reset;
  inView('main > :not(.hero) [data-rise]', el => {
    const d = batch++ * .075;
    clearTimeout(reset); reset = setTimeout(() => (batch = 0), 60);
    animate(el, { opacity: [0, 1], y: [28, 0] }, { duration: .8, ease, delay: d });
  }, { margin: '0px 0px -8% 0px' });

  // The two answer marks land like stamps
  inView('.stamp', el => {
    animate(el, { opacity: [0, 1], scale: [1.5, 1], rotate: [-8, 0] }, { type: 'spring', visualDuration: .45, bounce: .45, delay: .15 });
  }, { amount: 1 });

  // The preview video eases back as the hero scrolls away
  scroll(animate('.hero-film video', { scale: [1, .94], y: [0, 30] }, { ease: 'linear' }), { target: document.querySelector('.hero'), offset: ['start start', 'end start'] });

  // The name returns at full width, letter by letter
  inView('.wordmark', el => {
    animate(el.querySelectorAll('span'), { y: ['100%', '0%'] }, { type: 'spring', visualDuration: .8, bounce: .2, delay: stagger(.045) });
  }, { amount: .6 });

  // Feedback on every control
  press('.btn, .dtabs button, .tabs button, .copy, .sound', el => {
    animate(el, { scale: .95 }, { type: 'spring', stiffness: 700, damping: 30 });
    return () => animate(el, { scale: 1 }, { type: 'spring', stiffness: 500, damping: 18 });
  });
  hover('.btn', el => {
    animate(el, { y: -3 }, { type: 'spring', stiffness: 500, damping: 25 });
    return () => animate(el, { y: 0 }, { type: 'spring', stiffness: 500, damping: 25 });
  });
}

// Demo player: plays each feature in turn until the visitor picks one
const demo = document.getElementById('demo');
const dtabs = [...demo.querySelectorAll('[role=tab]')];
const DUR = 9;
let cur = 0, timer = null, auto = moving, progress = null;
if (auto) demo.classList.add('auto');

function play(pane) {
  if (!moving) return;
  const { animate } = M;
  pane.querySelectorAll('[data-d]').forEach(el => {
    const delay = +el.dataset.d;
    el.style.opacity = 0;
    const from = el.dataset.from === 'left' ? { x: [-36, 0], scale: [.96, 1] } : { y: [12, 0] };
    animate(el, { opacity: [0, 1], ...from }, { duration: .6, ease, delay });
  });
  const curve = pane.querySelector('.curve');
  if (curve) animate(curve, { strokeDashoffset: [420, 0] }, { duration: 1.6, ease: 'easeOut', delay: 1.4 });
  const done = pane.querySelector('.scrub .done'), knob = pane.querySelector('.scrub .knob');
  if (done) {
    animate(done, { scaleX: [.19, 1] }, { duration: .8, ease, delay: 3.4 });
    animate(knob, { left: ['12%', '64%'] }, { duration: .8, ease, delay: 3.4 });
  }
  const ping = pane.querySelector('.ping');
  if (ping) animate(ping, { scale: [1, 1.18, 1] }, { duration: .5, delay: 2, repeat: 1, repeatDelay: .4 });
  const now = pane.querySelector('.now');
  if (now) animate(now, { scale: [1, 1.025, 1] }, { duration: .6, delay: 3.6, repeat: 1, repeatDelay: .3 });
  const model = pane.querySelector('.model svg');
  if (model) animate(model, { y: [0, -8, 0], rotate: [0, -2, 0] }, { duration: 4, ease: 'easeInOut', repeat: Infinity, delay: 2.2 });
}

function show(i) {
  cur = (i + dtabs.length) % dtabs.length;
  dtabs.forEach((t, j) => {
    const on = j === cur;
    t.setAttribute('aria-selected', on);
    t.tabIndex = on ? 0 : -1;
    const p = document.getElementById(t.getAttribute('aria-controls'));
    p.hidden = !on;
    if (on) play(p);
  });
  clearTimeout(timer);
  if (progress) progress.cancel();
  dtabs.forEach(t => (t.querySelector('.prog').style.transform = ''));
  if (auto) {
    progress = M.animate(dtabs[cur].querySelector('.prog'), { scaleX: [0, 1] }, { duration: DUR, ease: 'linear' });
    timer = setTimeout(() => show(cur + 1), DUR * 1000);
  }
}
function stopAuto() {
  auto = false; clearTimeout(timer); demo.classList.remove('auto');
  if (progress) progress.cancel();
}
dtabs.forEach((t, i) => {
  t.addEventListener('click', () => { stopAuto(); show(i); });
  t.addEventListener('keydown', e => {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault(); stopAuto(); show(cur + d); dtabs[cur].focus();
  });
});
// Start playing when the demo comes into view
new IntersectionObserver((entries, obs) => {
  if (entries[0].isIntersecting) { show(0); obs.disconnect(); }
}, { threshold: .3 }).observe(demo.querySelector('.stage'));

// Install tabs
document.querySelectorAll('[role=tablist]:not([data-demo])').forEach(list => {
  const tabs = [...list.querySelectorAll('[role=tab]')];
  const pick = tab => tabs.forEach(t => {
    const on = t === tab;
    t.setAttribute('aria-selected', on);
    t.tabIndex = on ? 0 : -1;
    document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
  });
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => pick(t));
    t.addEventListener('keydown', e => {
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!d) return;
      const next = tabs[(i + d + tabs.length) % tabs.length];
      pick(next); next.focus();
    });
  });
});
if (/Win/.test(navigator.platform)) document.getElementById('t-win').click();
else if (/Linux/.test(navigator.platform)) document.getElementById('t-linux').click();

// Copy buttons
document.querySelectorAll('.copy').forEach(b => b.addEventListener('click', async () => {
  const text = b.dataset.copy || b.parentElement.querySelector('code').textContent;
  try { await navigator.clipboard.writeText(text); b.textContent = 'Copied'; }
  catch { b.textContent = 'Select and copy'; }
  setTimeout(() => (b.textContent = 'Copy'), 1800);
}));
