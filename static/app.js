document.addEventListener('click', function(e){
  const card = e.target.closest && e.target.closest('.res-card');
  if(card){
    const radio = card.querySelector && card.querySelector('input[type=radio]');
    if(radio) radio.checked = true;
  }
});

// get elements safely (may be null on other pages)
const fetchBtn = document.getElementById('fetch-btn');
const urlInput = document.getElementById('url');
const metaCard = document.getElementById('meta-card');
const metaThumb = document.getElementById('meta-thumb');
const metaTitle = document.getElementById('meta-title');
const metaAuthor = document.getElementById('meta-author');
const metaLength = document.getElementById('meta-length');
const resSelect = document.getElementById('res-select');
const resTrigger = document.getElementById('res-trigger');
const resOptions = document.getElementById('res-options');
const downloadBtn = document.getElementById('download-btn');
const statusBox = document.getElementById('status');

if(!fetchBtn || !urlInput) {
  // nothing to do (script might be loaded on a different page)
}

if(fetchBtn) fetchBtn.addEventListener('click', async function(){
  const url = urlInput.value.trim();
  if(!url) return;
  fetchBtn.disabled = true; fetchBtn.textContent = 'Loading...';
  statusBox.textContent = '';
  try{
    const res = await fetch('/api/info', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({url})});
    const data = await res.json();
    if(!res.ok){ throw new Error(data.error || 'Failed') }

    if(metaCard){ metaCard.style.display = 'block'; }
    if(metaThumb) metaThumb.src = data.thumbnail || '';
    if(metaTitle) metaTitle.textContent = data.title || '';
    if(metaAuthor) metaAuthor.textContent = data.author ? 'Channel: ' + data.author : '';
    if(metaLength) metaLength.textContent = data.length ? 'Duration: ' + data.length : '';

    // populate resolutions into the custom select (if present)
    if(resSelect && resOptions && resTrigger){
      resOptions.innerHTML = '';
      data.resolutions.forEach(function(r, idx){
        const opt = document.createElement('div');
        opt.className = 'custom-option';
        opt.dataset.value = r.res;
        opt.textContent = r.res + (r.progressive ? ' (progressive)' : r.video_only ? ' (video-only)' : '');
        if(idx === data.resolutions.length - 1){
          opt.dataset.selected = 'true';
          resSelect.dataset.value = r.res;
          resTrigger.textContent = opt.textContent;
        }
        opt.addEventListener('click', function(e){
          e.stopPropagation();
          // clear previous selection
          Array.from(resOptions.querySelectorAll('.custom-option')).forEach(function(o){ o.dataset.selected = 'false'; });
          opt.dataset.selected = 'true';
          resSelect.dataset.value = opt.dataset.value;
          resTrigger.textContent = opt.textContent;
          // hide immediately (keep display in sync)
          resOptions.hidden = true;
          resOptions.style.display = 'none';
          // return focus to trigger for better keyboard UX
          try{ resTrigger.focus(); }catch(_){}
        });
        resOptions.appendChild(opt);
      });
      resOptions.hidden = false;
      // initially hide options until user clicks trigger
      resOptions.hidden = true;
      resSelect.style.display = data.resolutions.length ? 'block' : 'none';
    }
    if(downloadBtn) { downloadBtn.disabled = false; }
  }catch(err){
    statusBox.textContent = 'Error: ' + err.message;
  }finally{
    fetchBtn.disabled = false; fetchBtn.textContent = 'Get Resolutions';
  }
});

// toggle removed; select is shown under duration

if(downloadBtn) downloadBtn.addEventListener('click', async function(){
  // support both native select (if any) and custom select
  let chosen = null;
  if(resSelect && resSelect.dataset && resSelect.dataset.value){ chosen = resSelect.dataset.value; }
  else if(resSelect && resSelect.value){ chosen = resSelect.value; }
  if(!chosen){ if(statusBox) statusBox.textContent = 'Please select a resolution.'; return }
  const url = urlInput.value.trim();
  downloadBtn.disabled = true; downloadBtn.textContent = 'Downloading...';
  statusBox.textContent = '';
  try{
    const res = await fetch('/download', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({url, resolution: chosen})});
    const data = await res.json();
    if(!res.ok){ throw new Error(data.error || 'download failed') }
    const id = data.id;
    // show progress UI
    const progressWrap = document.getElementById('progress-wrap');
    const progressBar = document.getElementById('progress-bar');
    const progressPct = document.getElementById('progress-pct');
    const progressMsg = document.getElementById('progress-msg');
    if(progressWrap){ progressWrap.style.display = 'block' }

    // poll status until finished
    let finished = false;
    while(!finished){
      await new Promise(r => setTimeout(r, 600));
      const sres = await fetch('/status/' + id);
      const sdata = await sres.json();
      if(!sres.ok){ throw new Error(sdata.error || 'status failed') }
      const pct = sdata.percent || 0;
      if(progressBar) progressBar.style.width = pct + '%';
      if(progressPct) progressPct.textContent = pct + '%';
      if(progressMsg) progressMsg.textContent = sdata.message || '';
      if(sdata.status === 'finished'){
        finished = true;
        statusBox.textContent = 'Done: ' + (sdata.file || '');
      } else if(sdata.status === 'error'){
        finished = true;
        statusBox.textContent = 'Error: ' + (sdata.message || '');
      }
    }
  }catch(err){
    statusBox.textContent = 'Error: ' + err.message;
  }finally{
    downloadBtn.disabled = false; downloadBtn.textContent = 'Download';
  }
});

// toggle custom select options when trigger clicked
if(resTrigger && resOptions){
  function positionOptions(){
    const rect = resTrigger.getBoundingClientRect();
    const left = rect.left + window.scrollX;
    const top = rect.bottom + window.scrollY + 8; // 8px gap
    resOptions.style.left = (rect.left) + 'px';
    resOptions.style.top = (rect.bottom + 8) + 'px';
    resOptions.style.width = rect.width + 'px';
    // limit max-height to available viewport space below trigger
    const avail = window.innerHeight - rect.bottom - 24;
    if(avail > 80){ resOptions.style.maxHeight = Math.min(avail, window.innerHeight * 0.6) + 'px'; }
    else { resOptions.style.maxHeight = '180px'; }
  }

  resTrigger.addEventListener('click', function(e){
    const open = !resOptions.hidden;
    if(!open){ // show -> position then show
      positionOptions();
      resOptions.hidden = false;
      resOptions.style.display = 'block';
    }else{
      resOptions.hidden = true;
      resOptions.style.display = 'none';
    }
  });

  // reposition on scroll/resize while open
  window.addEventListener('resize', function(){ if(!resOptions.hidden) positionOptions(); });
  window.addEventListener('scroll', function(){ if(!resOptions.hidden) positionOptions(); }, true);

  // close the custom select when clicking outside
  document.addEventListener('click', function(e){
    if(!e.target.closest) return;
    const inside = e.target.closest && e.target.closest('.custom-select');
    if(!inside){ resOptions.hidden = true; resOptions.style.display = 'none'; }
  });
}

