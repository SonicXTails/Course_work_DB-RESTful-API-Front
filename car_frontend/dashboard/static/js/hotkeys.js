(function(){
  // ==== КОНФИГ ====
  const routes = {
    swagger: '/swagger/',
    redoc:   '/redoc/',
    admin:   '/admin/',
    apiRoot: '/api/',
    analytics: '/dashboard/analytics/',
    audit: '/admin/core_auditlog/'
  };

  // какие Alt-клавиши считаем «админскими»
  // 1 — Swagger, 2 — ReDoc, 3 — Django Admin, 6 — Аудит
  const ADMIN_ONLY_KEYS = new Set(['1','2','3','6']);

  // определяем, админ ли пользователь
  const IS_ADMIN = document.querySelector('meta[name="is-staff"]')?.content === '1';

  // ==== УТИЛИТЫ ====
  const $ = (s)=>document.querySelector(s);
  function navigate(url){ if(url){ window.location.href = url; } }
  function clickIfExists(selector, fallbackUrl){
    const el = $(selector);
    if(el){ el.click(); return true; }
    if(fallbackUrl){ navigate(fallbackUrl); return true; }
    return false;
  }

  // ==== TOAST ====
  let toastTimer=null;
  function ensureStyles(){
    if($('#hotkeys-style')) return;
    const css = `#hotkeys-toast{position:fixed;right:16px;bottom:16px;padding:10px 14px;border-radius:10px;background:rgba(0,0,0,.75);color:#fff;font:14px/1.2 system-ui,sans-serif;z-index:9999;opacity:0;transform:translateY(8px);transition:.2s}#hotkeys-toast.show{opacity:1;transform:none}#hotkeys-help{position:fixed;right:16px;bottom:64px;width:42px;height:42px;border-radius:50%;background:#111;color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25);z-index:9998}#hotkeys-modal{position:fixed;inset:0;background:rgba(0,0,0,.35);display:none;align-items:center;justify-content:center;z-index:99999}#hotkeys-modal .sheet{background:#fff;color:#111;width:min(720px,92%);max-height:80vh;overflow:auto;border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.25);padding:18px}#hotkeys-modal table{width:100%;border-collapse:collapse}#hotkeys-modal th,#hotkeys-modal td{padding:8px 10px;border-bottom:1px solid rgba(0,0,0,.08)}#hotkeys-modal .close{float:right;cursor:pointer}`;
    const style = document.createElement('style');
    style.id='hotkeys-style';
    style.textContent = css;
    document.head.appendChild(style);
  }
  function toast(msg){
    ensureStyles();
    let t = $('#hotkeys-toast');
    if(!t){ t = document.createElement('div'); t.id='hotkeys-toast'; document.body.appendChild(t);}
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(()=>t.classList.remove('show'), 1500);
  }

  // ==== ПАМЯТКА ====
  function ensureCheatSheet(){
    ensureStyles();
    if($('#hotkeys-help')) return;

    const btn = document.createElement('button');
    btn.id='hotkeys-help'; btn.setAttribute('title','Горячие клавиши (Alt+0 / Shift+?)');
    btn.textContent='?';
    btn.addEventListener('click', openCheatSheet);
    document.body.appendChild(btn);

    const modal = document.createElement('div');
    modal.id='hotkeys-modal';
    modal.innerHTML = `<div class='sheet'>
      <div class='close' id='hk-close'>&times;</div>
      <h3 style='margin-top:0'>Горячие клавиши</h3>
      <table>
        <thead><tr><th>Комбинация</th><th>Действие</th></tr></thead>
        <tbody id='hk-rows'></tbody>
      </table>
    </div>`;
    modal.addEventListener('click', (e)=>{ if(e.target===modal) closeCheatSheet();});
    document.body.appendChild(modal);
    document.getElementById('hk-close').addEventListener('click', closeCheatSheet);

    // список хоткеев (adminOnly = true будет скрыт для не-админа)
    const rows = [
      {k:'Alt+1', a:'Открыть Swagger', adminOnly:true},
      {k:'Alt+2', a:'Открыть ReDoc',   adminOnly:true},
      {k:'Alt+3', a:'Админ-панель',    adminOnly:true},
      {k:'Alt+4', a:'DRF API root'},
      {k:'Alt+5', a:'Аналитика'},
      {k:'Alt+6', a:'Журнал аудита',   adminOnly:true},
      {k:'Alt+7', a:'Экспорт CSV'},
      {k:'Alt+8', a:'Переключить тему'},
      {k:'Alt+9', a:'Фокус на поиск'},
      {k:'Alt+0 / Shift+?', a:'Памятка хоткеев'},
      {k:'Alt+Shift+F', a:'Показать/скрыть фильтры'},
      {k:'Alt+S', a:'Сохранить фильтры'}
    ];

    const tbody = document.getElementById('hk-rows');
    rows.filter(r => IS_ADMIN || !r.adminOnly).forEach(r=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `<td><code>${r.k}</code></td><td>${r.a}</td>`;
      tbody.appendChild(tr);
    });
  }
  function openCheatSheet(){ $('#hotkeys-modal').style.display='flex'; }
  function closeCheatSheet(){ $('#hotkeys-modal').style.display='none'; }

  // ==== ДЕЙСТВИЯ ====
  function toggleTheme(){
    const curr = document.documentElement.getAttribute('data-theme') || 'light';
    const next = (curr === 'dark') ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    toast('Тема: ' + next);
  }
  function focusSearch(){
    const el = $('#global-search') || $('#q') || document.querySelector('input[type="search"], input[name*="search" i]');
    if(el){ el.focus(); el.select && el.select(); toast('Фокус: поиск'); }
    else toast('Поле поиска не найдено');
  }
  function exportCSV(){
    if(!clickIfExists('#btnExportCsv') && !clickIfExists('#btn-export-csv')){
      toast('Кнопка экспорта CSV не найдена');
    } else {
      toast('Экспорт CSV…');
    }
  }
  function toggleFiltersPanel(){
    if(!clickIfExists('#filter-drawer-toggle')){
      const panel = $('#filters-panel') || $('#filtersPanel');
      if(panel){ panel.classList.toggle('is-open'); }
    }
    toast('Фильтры: показать/скрыть');
  }
  function saveFilters(){
    const form = $('#filters-form') || $('#filtersPanel') || $('#filters-panel');
    if(!form){ toast('Форма фильтров не найдена'); return; }
    // имитация сохранения (без сервера)
    toast('Фильтры сохранены');
  }

  // ==== ОБРАБОТЧИК КЛАВИШ ====
  function handleKey(e){
    const tag = (e.target && e.target.tagName || '').toLowerCase();
    const isTyping = ['input','textarea','select'].includes(tag) || (e.target?.isContentEditable);

    const k = e.key.toLowerCase();

    // блокируем админ-горячие клавиши для не-админов
    if(e.altKey && ADMIN_ONLY_KEYS.has(k) && !IS_ADMIN){
      e.preventDefault();
      toast('Это действие только для администратора');
      return;
    }

    if(isTyping && !e.altKey) return;

    if(e.altKey){
      if(k==='1'){ navigate(routes.swagger); return void e.preventDefault(); }
      if(k==='2'){ navigate(routes.redoc);   return void e.preventDefault(); }
      if(k==='3'){ navigate(routes.admin);   return void e.preventDefault(); }
      if(k==='4'){ navigate(routes.apiRoot); return void e.preventDefault(); }
      if(k==='5'){ clickIfExists('#nav-analytics', routes.analytics); return void e.preventDefault(); }
      if(k==='6'){ clickIfExists('#nav-audit', routes.audit);         return void e.preventDefault(); }
      if(k==='7'){ exportCSV();   return void e.preventDefault(); }
      if(k==='8'){ toggleTheme(); return void e.preventDefault(); }
      if(k==='9'){ focusSearch(); return void e.preventDefault(); }
      if(k==='0'){ openCheatSheet(); return void e.preventDefault(); }
      if(k==='s'){ saveFilters();  return void e.preventDefault(); }
    }

    // Новый хоткей для панели фильтров — Alt+Shift+F (чтобы не конфликтовал с браузером)
    if(e.altKey && e.shiftKey && k==='f'){
      toggleFiltersPanel();
      return void e.preventDefault();
    }

    if(e.shiftKey && k==='?'){
      openCheatSheet(); return void e.preventDefault();
    }
  }

  function init(){
    ensureCheatSheet();
    window.addEventListener('keydown', handleKey, true);
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();