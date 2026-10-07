let state = {jobs: []};
const $ = id => document.getElementById(id);
const ageHours = iso => iso ? (Date.now() - new Date(iso).getTime()) / 3600000 : 9999;
const fmtAge = iso => {
  if (!iso) return "time unknown";
  const h = ageHours(iso);
  if (h < 1) return Math.max(1, Math.round(h*60)) + " min ago";
  if (h < 24) return Math.round(h) + " hr ago";
  return Math.round(h/24) + " days ago";
};
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function populateSources(jobs){
  const current = $("source").value;
  const names = [...new Set(jobs.map(j=>j.source).filter(Boolean))].sort();
  $("source").innerHTML = '<option value="">All sources</option>' + names.map(s=>'<option>'+esc(s)+'</option>').join("");
  $("source").value = names.includes(current) ? current : "";
}

function render(){
  const q = $("search").value.toLowerCase().trim();
  const src = $("source").value;
  const minScore = Number($("score").value);
  const maxAge = Number($("age").value);
  let jobs = state.jobs.filter(j=>{
    const hay = [j.title,j.company,j.location,j.source,(j.reasons||[]).join(" ")].join(" ").toLowerCase();
    return (!q || hay.includes(q)) && (!src || j.source===src) &&
      (j.score ?? 0) >= minScore && ageHours(j.posted) <= maxAge;
  });
  jobs.sort((a,b)=>(b.score||0)-(a.score||0) || String(b.posted||"").localeCompare(String(a.posted||"")));
  $("count").textContent = jobs.length + " jobs";
  $("jobs").innerHTML = jobs.map(j=>`
    <article class="card">
      <div class="cardmain">
        <div class="titleline"><h2>${esc(j.title)}</h2><span class="new">${ageHours(j.posted)<1 ? "NEW" : fmtAge(j.posted)}</span></div>
        <div class="company">${esc(j.company)}</div>
        <div class="meta">⌖ ${esc(j.location || "Location not listed")} · ◷ ${fmtAge(j.posted)} · <b>${esc(j.source)}</b></div>
        <div class="chips">${(j.reasons||[]).slice(0,7).map(x=>'<span>'+esc(x)+'</span>').join("")}</div>
      </div>
      <div class="actions">
        <div class="score ${(j.score||0)>=90?"hot":""}">${j.score ?? 0}%<small>match</small></div>
        <a class="apply" href="${esc(j.url)}" target="_blank" rel="noopener">Apply now ↗</a>
      </div>
    </article>`).join("") || '<div class="empty">No matching jobs in the current feed.</div>';
}

async function load(){
  try{
    const r = await fetch("https://raw.githubusercontent.com/AvinashBhalla/job-beeper/main/dashboard/data/jobs.json?t="+Date.now(), {cache:"no-store"});
    if(!r.ok) throw new Error(r.status);
    const data = await r.json();
    state = data;
    $("total").textContent = data.jobs?.length ?? 0;
    $("today").textContent = data.jobs?.filter(j=>ageHours(j.posted)<24).length ?? 0;
    $("notified").textContent = data.new_alerts ?? 0;
    $("lastRun").textContent = data.last_run ? "· " + new Date(data.last_run).toLocaleTimeString() : "";
    $("statusText").textContent = "Live · checked " + (data.last_run ? new Date(data.last_run).toLocaleTimeString() : "now");
    populateSources(data.jobs||[]);
    render();
  }catch(e){
    $("statusText").textContent = "Feed unavailable";
  }
}
["search","source","score","age"].forEach(id=>$(id).addEventListener("input",render));
$("refresh").onclick = load;
load();
setInterval(load,30000);
