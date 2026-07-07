/* ICML 2026 bilingual schedule app (vanilla JS, works over file://) */
(function () {
  'use strict';

  var SCHED = window.ICML_SCHEDULE;
  var DETAILS = window.ICML_DETAILS || {};
  window.ICML_PAPERS = window.ICML_PAPERS || {};

  // ---------------- i18n ----------------
  var I18N = {
    ko: {
      venue: 'COEX · 서울', search_ph: '일정·논문 검색 (제목, 연사, 세션…)',
      all: '전체', oral: '오럴', poster: '포스터', invited: '초청·특별', workshop: '워크숍',
      social: '소셜·어피니티', ops: '운영·휴식',
      papers_n: '편의 발표', ends: '종료', room: '장소', time: '시간', speaker: '연사',
      organizers: '주최', abstract: '소개', speakers: '연사 소개', links: '링크',
      talks: '발표 목록', posters: '포스터 목록', accepted: '수록 논문', filter_papers: '이 세션에서 논문 검색…',
      shown: '표시', of: '/', results_events: '일정', results_papers: '논문',
      no_results: '검색 결과가 없습니다', no_events: '해당하는 일정이 없습니다',
      load_all: '전체 논문(6,035편)에서도 검색하기 — 최초 1회 로딩(약 9MB)',
      loading: '불러오는 중…', show_original: '영어 원문 보기', hide_original: '원문 닫기',
      orig_label: '원문(EN)', in_session: '세션', view_original_title: '원제',
      wish: '위시', route: '동선', wish_empty: '카드나 논문을 길게 누르면 위시리스트에 추가됩니다',
      wish_hint: '길게 눌러 위시리스트에 추가/제거', pinned_papers: '핀한 논문', floor: '층',
      footer: '데이터 출처: icml.cc (2026 가상 사이트) · 모든 시간은 한국 표준시(KST) 기준 · 초록 원문은 영어로 제공됩니다.',
      search_hint_papers: '논문 제목도 함께 검색됩니다',
      day_note: { 3: '본회의 1일차', 4: '본회의 2일차', 5: '본회의 3일차', 6: '워크숍 1일차', 7: '워크숍 2일차' }
    },
    en: {
      venue: 'COEX · Seoul', search_ph: 'Search events & papers (title, speaker, session…)',
      all: 'All', oral: 'Orals', poster: 'Posters', invited: 'Invited', workshop: 'Workshops',
      social: 'Social · Affinity', ops: 'Logistics',
      papers_n: ' papers', ends: 'ends', room: 'Room', time: 'Time', speaker: 'Speaker',
      organizers: 'Organizers', abstract: 'Abstract', speakers: 'Speakers', links: 'Links',
      talks: 'Talks', posters: 'Posters', accepted: 'Accepted Papers', filter_papers: 'Filter papers in this session…',
      shown: 'shown', of: ' of ', results_events: 'Events', results_papers: 'Papers',
      no_results: 'No results found', no_events: 'No matching events',
      load_all: 'Also search all 6,035 papers — one-time load (~9MB)',
      loading: 'Loading…', show_original: 'Show English original', hide_original: 'Hide original',
      orig_label: 'Original (EN)', in_session: 'Session', view_original_title: 'Original title',
      wish: 'Wishlist', route: 'Route', wish_empty: 'Long-press any card or paper to add it to your wishlist',
      wish_hint: 'Long-press to add/remove from wishlist', pinned_papers: 'Pinned papers', floor: 'floor',
      footer: 'Data source: icml.cc (2026 virtual site) · All times are KST (Korea Standard Time).',
      search_hint_papers: 'Paper titles are searched too',
      day_note: { 3: 'Main Conference Day 1', 4: 'Main Conference Day 2', 5: 'Main Conference Day 3', 6: 'Workshops Day 1', 7: 'Workshops Day 2' }
    }
  };

  var TYPE_GROUP = {
    'oral-session': 'oral', 'poster-session': 'poster',
    'invited-talk': 'invited', 'test-of-time': 'invited', 'town-hall': 'invited', 'remarks': 'invited',
    'workshop': 'workshop',
    'social': 'social', 'reception': 'social', 'affinity-event': 'social', 'affinity-poster-session': 'social',
    'break': 'ops', 'registration-desk': 'ops'
  };
  var GROUP_COLOR = {
    oral: 'var(--c-oral)', poster: 'var(--c-poster)', invited: 'var(--c-invited)',
    workshop: 'var(--c-workshop)', social: 'var(--c-social)', ops: 'var(--c-ops)'
  };
  var CHIP_ORDER = ['all', 'wish', 'oral', 'poster', 'invited', 'workshop', 'social', 'ops'];

  // ---------------- wishlist store ----------------
  var wish = { events: {}, papers: {} };
  try { wish = JSON.parse(localStorage.getItem('icml_wish')) || wish; } catch (e) { /* fresh */ }
  wish.events = wish.events || {};
  wish.papers = wish.papers || {};
  function saveWish() { localStorage.setItem('icml_wish', JSON.stringify(wish)); }
  function wishCount() { return Object.keys(wish.events).length + Object.keys(wish.papers).length; }
  function toggleEventPin(e) {
    if (wish.events[e.id]) delete wish.events[e.id];
    else wish.events[e.id] = 1;
    saveWish();
  }
  function togglePaperPin(p, sid) {
    if (wish.papers[p.id]) delete wish.papers[p.id];
    else wish.papers[p.id] = { s: sid || null, en: p.en, ko: p.ko, pos: p.pos, time: p.time };
    saveWish();
  }

  // long-press to pin (mouse hold works too); suppresses the following click
  function longPress(el, fn) {
    var timer = null, fired = false;
    function start(ev) {
      if (ev.type === 'mousedown' && ev.button !== 0) return;
      fired = false;
      el.classList.add('pressing');
      timer = setTimeout(function () {
        fired = true;
        el._lpFired = true;
        el.classList.remove('pressing');
        fn();
      }, 480);
    }
    function cancel() { clearTimeout(timer); timer = null; el.classList.remove('pressing'); }
    el.addEventListener('touchstart', start, { passive: true });
    el.addEventListener('mousedown', start);
    ['touchend', 'touchmove', 'touchcancel', 'mouseup', 'mouseleave'].forEach(function (t) {
      el.addEventListener(t, cancel);
    });
    el.addEventListener('contextmenu', function (ev) { if (fired || timer) ev.preventDefault(); });
  }

  // room -> COEX floor (from media.icml.cc/Conferences/ICML2026/coex_map.svg)
  function floorOf(room) {
    if (!room) return null;
    var r = room.toLowerCase();
    if (r.indexOf('hall c') >= 0) return '4F';
    if (r.indexOf('hall d') >= 0 || r.indexOf('auditorium') >= 0 || r.indexOf('hall e') >= 0) return '3F';
    if (r.indexOf('asem') >= 0) return '2F';
    if (r.indexOf('hall a') >= 0 || r.indexOf('hall b') >= 0 || r.indexOf('grand ballroom') >= 0) return '1F';
    var m = r.match(/room\s*e\d/) || (r.indexOf('room e') >= 0 ? ['e'] : null);
    if (m) return '3F';
    var n = r.match(/room\s*(\d)\d{2}/);
    if (n) return n[1] + 'F';
    return null;
  }
  function roomWithFloor(room) {
    var f = floorOf(room);
    return room ? room + (f ? ' · ' + f : '') : '';
  }

  // event id -> {ev, day} index
  var EV_INDEX = {};
  SCHED.days.forEach(function (d) {
    d.events.forEach(function (e) { EV_INDEX[e.id] = { ev: e, day: d }; });
  });

  // ---------------- state ----------------
  var params = new URLSearchParams(location.search);
  var state = {
    lang: params.get('lang') || localStorage.getItem('icml_lang') || 'en',
    day: parseInt(params.get('day') || localStorage.getItem('icml_day') || '0', 10) || defaultDay(),
    chip: 'all',
    q: '',
    allPapersLoaded: false
  };
  if (['ko', 'en'].indexOf(state.lang) < 0) state.lang = 'ko';
  if (!SCHED.days.some(function (d) { return d.day === state.day; })) state.day = defaultDay();
  if (params.get('q')) state.q = params.get('q');

  function defaultDay() {
    var today = new Date();
    var map = { '2026-07-07': 3, '2026-07-08': 4, '2026-07-09': 5, '2026-07-10': 6, '2026-07-11': 7 };
    var iso = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');
    return map[iso] || 3;
  }
  function t(key) { return I18N[state.lang][key]; }
  function loc(obj) {
    if (!obj) return '';
    return (state.lang === 'ko' && obj.ko) ? obj.ko : (obj.en || obj.ko || '');
  }

  // ---------------- helpers ----------------
  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === 'class') el.className = attrs[k];
      else if (k === 'html') el.innerHTML = attrs[k];
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), attrs[k]);
      else if (k === 'style') el.style.cssText = attrs[k];
      else el.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) {
      if (c == null) return;
      el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return el;
  }
  function fmtTime(s) { return s || ''; }
  function esc(s) { return (s || '').replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // dynamic paper file loader (script injection -> file:// safe)
  var loading = {};
  function loadPapers(sid) {
    return new Promise(function (resolve, reject) {
      if (window.ICML_PAPERS[sid]) return resolve(window.ICML_PAPERS[sid]);
      if (loading[sid]) { loading[sid].push(resolve); return; }
      loading[sid] = [resolve];
      var sc = document.createElement('script');
      sc.src = 'data/papers/s' + sid + '.js';
      sc.onload = function () {
        var cbs = loading[sid] || []; delete loading[sid];
        cbs.forEach(function (cb) { cb(window.ICML_PAPERS[sid] || []); });
      };
      sc.onerror = function () { delete loading[sid]; resolve([]); };
      document.head.appendChild(sc);
    });
  }
  function sessionsWithPapers() {
    var out = [];
    SCHED.days.forEach(function (d) {
      d.events.forEach(function (e) { if (e.nPapers) out.push({ day: d, ev: e }); });
    });
    return out;
  }
  function loadAllPapers(progressCb) {
    var list = sessionsWithPapers();
    var done = 0;
    return Promise.all(list.map(function (it) {
      return loadPapers(it.ev.id).then(function () { done++; if (progressCb) progressCb(done, list.length); });
    })).then(function () { state.allPapersLoaded = true; });
  }

  // ---------------- root render ----------------
  var app = document.getElementById('app');

  function render() {
    document.documentElement.lang = state.lang;
    app.innerHTML = '';
    app.appendChild(renderTopbar());
    app.appendChild(renderDayTabs());
    app.appendChild(renderToolbar());
    var main = h('main', { class: 'timeline', id: 'timeline' });
    app.appendChild(main);
    renderMain();
    app.appendChild(renderFooter());
  }

  function renderTopbar() {
    var themeBtn = h('button', {
      class: 'icon-btn', title: 'Theme',
      onclick: function () {
        var cur = document.documentElement.getAttribute('data-theme');
        var next = cur === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('icml_theme', next);
        themeBtn.textContent = next === 'dark' ? '☀' : '☾';
      }
    }, [document.documentElement.getAttribute('data-theme') === 'dark' ? '☀' : '☾']);

    return h('header', { class: 'topbar' }, [
      h('div', { class: 'topbar-inner' }, [
        h('div', { class: 'brand' }, [
          h('h1', null, ['ICML 2026']),
          h('span', { class: 'venue' }, [t('venue') + ' · 7.7 – 7.11'])
        ]),
        h('div', { class: 'controls' }, [
          h('div', { class: 'seg' }, [
            h('button', { class: state.lang === 'ko' ? 'on' : '', onclick: function () { setLang('ko'); } }, ['한국어']),
            h('button', { class: state.lang === 'en' ? 'on' : '', onclick: function () { setLang('en'); } }, ['EN'])
          ]),
          themeBtn
        ])
      ])
    ]);
  }
  function setLang(l) { state.lang = l; localStorage.setItem('icml_lang', l); render(); }

  function renderDayTabs() {
    return h('div', { class: 'daytabs-wrap' }, [
      h('nav', { class: 'daytabs' }, SCHED.days.map(function (d) {
        return h('button', {
          class: 'daytab' + (state.day === d.day ? ' on' : ''),
          onclick: function () {
            state.day = d.day; localStorage.setItem('icml_day', String(d.day));
            state.q = ''; render(); window.scrollTo(0, 0);
          }
        }, [h('span', { class: 'dow' }, [loc(d.label)])]);
      }))
    ]);
  }

  function renderToolbar() {
    var input = h('input', {
      type: 'search', placeholder: t('search_ph'), value: state.q,
      oninput: debounce(function (ev) { state.q = ev.target.value.trim(); renderMain(); }, 220)
    });
    var chips = h('div', { class: 'chips' }, CHIP_ORDER.map(function (c) {
      if (c === 'wish') {
        var n = wishCount();
        return h('button', {
          class: 'chip chip-wish' + (state.chip === c ? ' on' : ''),
          onclick: function () { state.chip = c; render(); }
        }, ['⭐ ' + t('wish') + (n ? ' ' + n : '')]);
      }
      var dot = c === 'all' ? null : h('span', { class: 'dot', style: 'background:' + GROUP_COLOR[c] });
      return h('button', {
        class: 'chip' + (state.chip === c ? ' on' : ''),
        onclick: function () { state.chip = c; render(); }
      }, [dot, t(c)]);
    }));
    return h('div', { class: 'toolbar' }, [
      h('div', { class: 'searchbox' }, [h('span', { class: 'mag' }, ['⌕']), input]),
      chips
    ]);
  }

  function debounce(fn, ms) {
    var to; return function () { var a = arguments, self = this; clearTimeout(to); to = setTimeout(function () { fn.apply(self, a); }, ms); };
  }

  // ---------------- main (timeline or search) ----------------
  function renderMain() {
    var main = document.getElementById('timeline');
    main.innerHTML = '';
    if (state.q.length >= 2) renderSearch(main);
    else renderTimeline(main);
  }

  function eventMatchesChip(e) {
    if (state.chip === 'all') return true;
    if (state.chip === 'wish') return !!wish.events[e.id];
    return TYPE_GROUP[e.type] === state.chip;
  }

  function renderTimeline(main) {
    var day = SCHED.days.find(function (d) { return d.day === state.day; });
    if (!day) return;
    if (state.chip === 'wish') return renderWishDay(main, day);
    main.appendChild(h('div', { class: 'date-heading' }, [loc(day.dateFull) + ' — ' + t('day_note')[day.day]]));

    var evs = day.events.filter(eventMatchesChip);
    if (!evs.length) { main.appendChild(h('div', { class: 'empty' }, [t('no_events')])); return; }

    // group by start time
    var groups = {};
    evs.forEach(function (e) {
      var k = e.start || '——';
      (groups[k] = groups[k] || []).push(e);
    });
    Object.keys(groups).sort().forEach(function (k) {
      var lbl = h('div', { class: 'tlabel' }, [k]);
      var cards = h('div', { class: 'tcards' }, groups[k].map(function (e) { return renderCard(e, day); }));
      main.appendChild(h('section', { class: 'tgroup' }, [lbl, cards]));
    });
  }

  function renderCard(e, day, ctxLabel) {
    var g = TYPE_GROUP[e.type] || 'ops';
    var color = GROUP_COLOR[g];
    var compact = (g === 'ops');
    var times = e.start ? (e.start + (e.end ? ' – ' + e.end : '')) : '';
    var pinned = !!wish.events[e.id];
    var card;
    function onOpen() {
      if (card._lpFired) { card._lpFired = false; return; }
      openEvent(e, day);
    }
    if (compact) {
      card = h('button', {
        class: 'card compact' + (pinned ? ' pinned' : ''), style: '--tc:' + color,
        title: t('wish_hint'), onclick: onOpen
      }, [
        h('h3', null, [loc(e.title)]),
        h('span', { class: 'times' }, [times])
      ]);
    } else {
      var subs = [];
      if (e.speaker) subs.push(e.speaker);
      else if (e.organizers) subs.push(e.organizers);
      card = h('button', {
        class: 'card' + (pinned ? ' pinned' : ''), style: '--tc:' + color,
        title: t('wish_hint'), onclick: onOpen
      }, [
        h('div', { class: 'rowtop' }, [
          h('span', { class: 'badge' }, [loc(e.typeName)]),
          h('span', { class: 'times' }, [times]),
          e.room ? h('span', { class: 'room' }, ['· ' + roomWithFloor(e.room)]) : null
        ]),
        h('h3', null, [loc(e.title)]),
        subs.length ? h('div', { class: 'sub' }, [subs.join(' · ')]) : null,
        e.nPapers ? h('div', { class: 'npapers' }, [
          state.lang === 'ko' ? '발표 ' + e.nPapers + '편' : e.nPapers + ' papers'
        ]) : null,
        ctxLabel ? h('div', { class: 'ctx' }, [ctxLabel]) : null
      ]);
    }
    longPress(card, function () {
      toggleEventPin(e);
      card.classList.toggle('pinned', !!wish.events[e.id]);
      var chip = document.querySelector('.chip-wish');
      if (chip) {
        var n = wishCount();
        chip.textContent = '⭐ ' + t('wish') + (n ? ' ' + n : '');
      }
      if (state.chip === 'wish') renderMain();
    });
    return card;
  }

  // ---------------- wishlist day view ----------------
  function renderWishDay(main, day) {
    main.appendChild(h('div', { class: 'date-heading' }, [loc(day.dateFull) + ' — ⭐ ' + t('wish')]));

    // pinned events on this day
    var items = [];   // {start, ev, papers:[...]}
    day.events.forEach(function (e) {
      if (wish.events[e.id]) items.push({ ev: e, papers: [] });
    });
    // pinned papers whose session is on this day
    Object.keys(wish.papers).forEach(function (pid) {
      var w = wish.papers[pid];
      var hit = w.s && EV_INDEX[w.s];
      if (!hit || hit.day.day !== day.day) return;
      var found = items.find(function (it) { return it.ev.id === hit.ev.id; });
      if (!found) { found = { ev: hit.ev, papers: [] }; items.push(found); }
      found.papers.push(Object.assign({ id: pid }, w));
    });
    if (!items.length) {
      main.appendChild(h('div', { class: 'empty' }, [t('wish_empty')]));
      return;
    }
    items.sort(function (a, b) { return (a.ev.start || '').localeCompare(b.ev.start || ''); });

    // route strip: time + room(floor) hops
    var hops = [];
    items.forEach(function (it) {
      if (!it.ev.start) return;
      var label = it.ev.start + ' ' + (it.ev.room ? roomWithFloor(it.ev.room) : loc(it.ev.title).slice(0, 14));
      if (!hops.length || hops[hops.length - 1] !== label) hops.push(label);
    });
    if (hops.length > 1 || (hops.length === 1 && items.length)) {
      main.appendChild(h('div', { class: 'route-strip' }, [
        h('span', { class: 'route-label' }, [t('route')]),
        h('span', { class: 'route-hops' }, [hops.join('  →  ')])
      ]));
    }

    // grouped timeline
    var groups = {};
    items.forEach(function (it) {
      var k = it.ev.start || '——';
      (groups[k] = groups[k] || []).push(it);
    });
    Object.keys(groups).sort().forEach(function (k) {
      var cards = h('div', { class: 'tcards' }, []);
      groups[k].forEach(function (it) {
        cards.appendChild(renderCard(it.ev, day));
        if (it.papers.length) {
          it.papers.sort(function (a, b) { return (a.time || a.pos || '').localeCompare(b.time || b.pos || ''); });
          var box = h('div', { class: 'wish-papers' }, [
            h('div', { class: 'pcount' }, [t('pinned_papers') + ' · ' + it.papers.length])
          ]);
          cards.appendChild(box);
          loadPapers(it.ev.id).then(function (full) {
            var map = {};
            (full || []).forEach(function (fp) { map[fp.id] = fp; });
            box.appendChild(h('div', null, it.papers.map(function (w) {
              return renderPaperItem(map[w.id] || w, { sid: it.ev.id });
            })));
          });
        }
      });
      main.appendChild(h('section', { class: 'tgroup' }, [
        h('div', { class: 'tlabel' }, [k]), cards
      ]));
    });
  }

  // ---------------- search ----------------
  function renderSearch(main) {
    var q = state.q.toLowerCase();
    var evHits = [];
    SCHED.days.forEach(function (d) {
      d.events.forEach(function (e) {
        if (!eventMatchesChip(e)) return;
        var hay = [e.title.en, e.title.ko, e.speaker, e.organizers, e.room].join(' ').toLowerCase();
        if (hay.indexOf(q) >= 0) evHits.push({ d: d, e: e });
      });
    });

    main.appendChild(h('div', { class: 'results-note' }, [
      '“' + state.q + '” — ' + t('results_events') + ' ' + evHits.length
    ]));

    if (evHits.length) {
      main.appendChild(h('div', { class: 'rsection' }, [t('results_events')]));
      var wrap = h('div', { class: 'tcards' });
      evHits.slice(0, 50).forEach(function (hit) {
        wrap.appendChild(renderCard(hit.e, hit.d, loc(hit.d.label)));
      });
      main.appendChild(wrap);
    }

    // paper search
    var psec = h('div');
    main.appendChild(psec);
    if (!state.allPapersLoaded) {
      var btn = h('button', {
        class: 'load-all',
        onclick: function () {
          btn.disabled = true;
          btn.textContent = t('loading');
          loadAllPapers(function (done, total) { btn.textContent = t('loading') + ' ' + done + '/' + total; })
            .then(function () { renderMain(); });
        }
      }, [t('load_all')]);
      psec.appendChild(btn);
    } else {
      var hits = [];
      sessionsWithPapers().forEach(function (it) {
        (window.ICML_PAPERS[it.ev.id] || []).forEach(function (p) {
          var hay = ((p.en || '') + ' ' + (p.ko || '') + ' ' + (p.authors || '')).toLowerCase();
          if (hay.indexOf(q) >= 0) hits.push({ d: it.day, e: it.ev, p: p });
        });
      });
      psec.appendChild(h('div', { class: 'rsection' }, [t('results_papers') + ' · ' + hits.length]));
      var pw = h('div');
      hits.slice(0, 100).forEach(function (hit) {
        pw.appendChild(renderPaperItem(hit.p, {
          sid: hit.e.id,
          ctx: loc(hit.d.label) + ' · ' + loc(hit.e.title) + (hit.e.room ? ' · ' + roomWithFloor(hit.e.room) : '')
        }));
      });
      if (hits.length > 100) pw.appendChild(h('div', { class: 'results-note' }, ['+' + (hits.length - 100)]));
      psec.appendChild(pw);
    }

    if (!evHits.length && state.allPapersLoaded === false) { /* note already shown */ }
    if (!evHits.length && state.allPapersLoaded && !main.querySelector('.paper')) {
      main.appendChild(h('div', { class: 'empty' }, [t('no_results')]));
    }
  }

  // ---------------- event modal ----------------
  function openEvent(e, day) {
    var det = DETAILS[e.id] || {};
    var overlay = h('div', { class: 'overlay', onclick: function (ev) { if (ev.target === overlay) close(); } });
    function close() { overlay.remove(); document.body.style.overflow = ''; document.removeEventListener('keydown', onKey); }
    function onKey(ev) { if (ev.key === 'Escape') close(); }
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';

    var g = TYPE_GROUP[e.type] || 'ops';
    var times = (e.start || '') + (e.end ? ' – ' + e.end : '');
    var head = h('div', { class: 'modal-head' }, [
      h('div', { class: 'heads' }, [
        h('span', { class: 'badge', style: '--tc:' + GROUP_COLOR[g] }, [loc(e.typeName)]),
        h('h2', null, [loc(e.title)]),
        (state.lang === 'ko' && e.title.ko && e.title.en !== e.title.ko)
          ? h('div', { class: 'sub' }, [e.title.en]) : null,
        h('div', { class: 'meta' }, [
          h('span', null, ['🗓 ' + loc(day.dateFull)]),
          times ? h('span', null, ['🕐 ' + times + ' KST']) : null,
          e.room ? h('span', null, ['📍 ' + roomWithFloor(e.room)]) : null,
          e.speaker ? h('span', null, ['🎤 ' + e.speaker]) : null,
          e.organizers ? h('span', null, ['👥 ' + e.organizers]) : null
        ])
      ]),
      h('button', { class: 'modal-close', onclick: close }, ['✕'])
    ]);

    var body = h('div', { class: 'modal-body' });

    // abstract / description
    if (det.abs) {
      var absHtml = (state.lang === 'ko' && det.abs.ko) ? det.abs.ko : det.abs.en;
      var sec = h('div', { class: 'msec' }, [
        h('h4', null, [t('abstract')]),
        h('div', { class: 'abs', html: absHtml })
      ]);
      if (state.lang === 'ko' && det.abs.ko) {
        var shown = false;
        var origBox = null;
        sec.appendChild(h('button', {
          class: 'lang-orig',
          onclick: function (ev) {
            shown = !shown;
            ev.target.textContent = shown ? t('hide_original') : t('show_original');
            if (shown && !origBox) {
              origBox = h('div', { class: 'abs', style: 'margin-top:8px', html: det.abs.en });
              sec.appendChild(origBox);
            } else if (origBox) { origBox.style.display = shown ? '' : 'none'; }
          }
        }, [t('show_original')]));
      }
      body.appendChild(sec);
    }

    // speakers
    if (det.speakers && det.speakers.length) {
      body.appendChild(h('div', { class: 'msec' }, [
        h('h4', null, [t('speakers')]),
        h('div', null, det.speakers.map(function (sp) {
          var bio = sp.bio ? ((state.lang === 'ko' && sp.bio.ko) ? sp.bio.ko : sp.bio.en) : null;
          return h('div', { class: 'speaker-row' }, [
            h('div', { class: 'nm' }, [sp.name || '']),
            bio ? h('div', { class: 'bio' }, [bio]) : null
          ]);
        }))
      ]));
    }

    // links
    if (det.links && det.links.length) {
      body.appendChild(h('div', { class: 'msec' }, [
        h('h4', null, [t('links')]),
        h('div', { class: 'linkrow' }, det.links.map(function (l) {
          return h('a', { href: l.url, target: '_blank', rel: 'noopener' }, [l.label + ' ↗']);
        }))
      ]));
    }

    // papers
    if (e.nPapers) {
      var plabel = e.type === 'oral-session' ? t('talks')
        : e.type === 'poster-session' ? t('posters') : t('accepted');
      var psec = h('div', { class: 'msec' }, [
        h('h4', null, [plabel + ' · ' + e.nPapers]),
        h('div', { class: 'spin' }, [t('loading')])
      ]);
      body.appendChild(psec);
      loadPapers(e.id).then(function (papers) {
        psec.innerHTML = '';
        psec.appendChild(h('h4', null, [plabel + ' · ' + papers.length]));
        psec.appendChild(renderPaperList(papers, e.id));
      });
    }

    var modal = h('div', { class: 'modal' }, [head, body]);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  }

  // ---------------- paper list w/ filter + incremental render ----------------
  function renderPaperList(papers, sid) {
    var wrap = h('div');
    var listEl = h('div');
    var count = h('div', { class: 'pcount' });
    var filtered = papers;
    var shown = 0;
    var CHUNK = 60;

    var finput = h('input', {
      type: 'search', placeholder: t('filter_papers'),
      oninput: debounce(function (ev) {
        var q = ev.target.value.trim().toLowerCase();
        filtered = !q ? papers : papers.filter(function (p) {
          return ((p.en || '') + ' ' + (p.ko || '') + ' ' + (p.authors || '') + ' ' + (p.pos || '')).toLowerCase().indexOf(q) >= 0;
        });
        reset();
      }, 200)
    });

    function updateCount() {
      count.textContent = Math.min(shown, filtered.length) + ' ' + t('shown') + t('of') + filtered.length;
    }
    function renderChunk() {
      var frag = document.createDocumentFragment();
      var end = Math.min(shown + CHUNK, filtered.length);
      for (var i = shown; i < end; i++) frag.appendChild(renderPaperItem(filtered[i], { sid: sid }));
      shown = end;
      listEl.insertBefore(frag, sentinel);
      updateCount();
    }
    var sentinel = h('div', { class: 'loadmore-sentinel' });
    listEl.appendChild(sentinel);
    var io = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting && shown < filtered.length) renderChunk();
    }, { rootMargin: '600px' });
    io.observe(sentinel);

    function reset() {
      listEl.querySelectorAll('.paper').forEach(function (n) { n.remove(); });
      shown = 0;
      renderChunk();
    }

    wrap.appendChild(h('div', { class: 'paperfilter' }, [finput]));
    wrap.appendChild(count);
    wrap.appendChild(listEl);
    renderChunk();
    return wrap;
  }

  function renderPaperItem(p, opts) {
    opts = opts || {};
    var title = (state.lang === 'ko' && p.ko) ? p.ko : (p.en || '');
    var expanded = false;
    var bodyEl = null;
    var pinned = !!wish.papers[p.id];
    var item = h('div', { class: 'paper' + (opts.ctx ? ' paper-hit' : '') + (pinned ? ' pinned' : '') });
    var tags = [];
    if (p.time) tags.push(h('span', { class: 'ptag oraltime' }, [p.time]));
    if (p.pos) tags.push(h('span', { class: 'ptag' }, [p.pos]));
    var btn = h('button', {
      title: t('wish_hint'),
      onclick: function () {
        if (btn._lpFired) { btn._lpFired = false; return; }
        expanded = !expanded;
        if (expanded && !bodyEl) {
          var useKoAbs = state.lang === 'ko' && p.absKo;
          var absHtml = useKoAbs ? p.absKo : p.abs;
          bodyEl = h('div', { class: 'pbody' }, [
            (state.lang === 'ko' && p.ko && p.en) ? h('div', { class: 'sub-en' }, [t('view_original_title') + ': ' + p.en]) : null,
            absHtml ? h('div', { class: 'abs', html: absHtml }) : null,
            p.link ? h('div', { class: 'plinks linkrow' }, [
              h('a', { href: p.link, target: '_blank', rel: 'noopener' }, ['OpenReview ↗'])
            ]) : null
          ]);
          if (useKoAbs && p.abs) {
            var shownOrig = false;
            var origEl = null;
            bodyEl.insertBefore(h('button', {
              class: 'lang-orig',
              onclick: function (ev2) {
                ev2.stopPropagation();
                shownOrig = !shownOrig;
                ev2.target.textContent = shownOrig ? t('hide_original') : t('show_original');
                if (shownOrig && !origEl) {
                  origEl = h('div', { class: 'abs', style: 'margin-top:8px', html: p.abs });
                  ev2.target.insertAdjacentElement('afterend', origEl);
                } else if (origEl) origEl.style.display = shownOrig ? '' : 'none';
              }
            }, [t('show_original')]), bodyEl.querySelector('.plinks'));
          }
          item.appendChild(bodyEl);
        } else if (bodyEl) bodyEl.style.display = expanded ? '' : 'none';
      }
    }, [
      tags.length ? h('div', { class: 'ptags' }, tags) : null,
      h('div', { class: 'pt' }, [title]),
      p.authors ? h('div', { class: 'pa' }, [p.authors]) : null,
      opts.ctx ? h('div', { class: 'ctx' }, [opts.ctx]) : null
    ]);
    if (p.id) {
      longPress(btn, function () {
        togglePaperPin(p, opts.sid);
        item.classList.toggle('pinned', !!wish.papers[p.id]);
        var chip = document.querySelector('.chip-wish');
        if (chip) {
          var n = wishCount();
          chip.textContent = '⭐ ' + t('wish') + (n ? ' ' + n : '');
        }
      });
    }
    item.appendChild(btn);
    return item;
  }

  function renderFooter() {
    return h('footer', null, [h('div', null, [t('footer')])]);
  }

  // ---------------- boot ----------------
  // dev/test: seed pins from URL (in-memory only; persisted on next user toggle)
  if (params.get('pin')) {
    params.get('pin').split(',').forEach(function (id) {
      if (id.indexOf('@') > 0) {
        var pr = id.split('@');
        wish.papers[pr[0]] = { s: pr[1] };
      } else {
        wish.events[id] = 1;
      }
    });
  }
  if (params.get('chip')) state.chip = params.get('chip');

  var savedTheme = params.get('theme') || localStorage.getItem('icml_theme');
  if (savedTheme) document.documentElement.setAttribute('data-theme', savedTheme);
  else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  render();

  // deep link: ?open=<eventId> opens that event's detail modal
  var openId = params.get('open');
  if (openId) {
    SCHED.days.forEach(function (d) {
      d.events.forEach(function (e) {
        if (e.id === openId) {
          state.day = d.day;
          openEvent(e, d);
        }
      });
    });
  }
})();
