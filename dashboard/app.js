function setupNavigation(){
  const links=[...document.querySelectorAll(".nav-link")];
  const sections=[...document.querySelectorAll(".page-section")];
  function show(id){
    const target=document.getElementById(id)||document.getElementById("jobsSection");
    sections.forEach(s=>s.classList.toggle("hidden-section",s!==target));
    links.forEach(a=>a.classList.toggle("active",a.dataset.section===target.id));
    if(target.id!=="jobsSection" && location.hash!=="#"+target.id.replace("Section","")){
      history.replaceState(null,"","#"+target.id.replace("Section",""));
    }
  }
  links.forEach(a=>a.addEventListener("click",e=>{
    e.preventDefault();
    show(a.dataset.section);
  }));
  const initial=(location.hash||"").slice(1);
  show(initial==="filters"?"filtersSection":initial==="settings"?"settingsSection":initial==="sources"?"sourcesSection":initial==="applied"?"appliedSection":"jobsSection");
}
const REPO = "AvinashBhalla/job-beeper";
const RAW = "https://raw.githubusercontent.com/" + REPO + "/main/";
const API = "https://api.github.com";
let state = {jobs: []};
let config = null;
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
const csv = s => s.split(",").map(x=>x.trim()).filter(Boolean);
const fieldLabels = {
  frontend:"Frontend", backend:"Backend", full_stack:"Full Stack", automation:"Automation",
  ai_ml:"AI / ML", python:"Python", javascript_typescript:"JavaScript / TypeScript",
  devops:"DevOps", mobile:"Mobile", data:"Data"
};

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

function renderFields(){
  const selected = new Set(config?.filters?.fields || []);
  $("fieldChoices").innerHTML = Object.entries(fieldLabels).map(([key,label]) =>
    `<label class="choice"><input type="checkbox" data-field="${key}" ${selected.has(key)?"checked":""}><span>${label}</span></label>`
  ).join("");
}

function loadForm(){
  const f=config.filters;
  $("cfgKeywords").value=(f.keywords||[]).join(", ");
  $("cfgLocations").value=(f.locations||[]).join(", ");
  $("cfgExclude").value=(f.title_exclude||[]).join(", ");
  $("cfgExperience").value=String(f.max_experience_years ?? 3);
  $("cfgAge").value=String(f.max_age_hours ?? 72);
  $("cfgRemoteOnly").checked=!!f.remote_only;
  $("cfgTelegram").checked=f.notifications_enabled !== false;
  renderFields();
}

function collectConfig(){
  const next=JSON.parse(JSON.stringify(config));
  const f=next.filters;
  f.keywords=csv($("cfgKeywords").value);
  f.locations=csv($("cfgLocations").value);
  f.title_exclude=csv($("cfgExclude").value);
  f.fields=[...document.querySelectorAll("[data-field]:checked")].map(x=>x.dataset.field);
  f.max_experience_years=Number($("cfgExperience").value);
  f.max_age_hours=Number($("cfgAge").value);
  f.remote_only=$("cfgRemoteOnly").checked;
  f.notifications_enabled=$("cfgTelegram").checked;
  f.search_from_filters=true;
  return next;
}

function token(){
  return sessionStorage.getItem("jobbeeper_github_token") || $("githubToken").value.trim();
}

function apiHeaders(t){
  return {"Accept":"application/vnd.github+json","Authorization":"Bearer "+t,"X-GitHub-Api-Version":"2026-03-10","Content-Type":"application/json"};
}

function b64utf8(text){
  const bytes=new TextEncoder().encode(text);
  let binary="";
  for(let i=0;i<bytes.length;i+=0x8000) binary+=String.fromCharCode(...bytes.subarray(i,i+0x8000));
  return btoa(binary);
}

async function saveAndRun(){
  const t=token();
  if(!t){ $("saveStatus").textContent="Add your GitHub token first."; return; }
  const next=collectConfig();
  $("saveStatus").textContent="Saving filters…";
  try{
    const getr=await fetch(API+"/repos/"+REPO+"/contents/config.json?ref=main",{headers:apiHeaders(t)});
    if(!getr.ok) throw new Error("GitHub read failed: "+getr.status);
    const current=await getr.json();
    const putr=await fetch(API+"/repos/"+REPO+"/contents/config.json",{
      method:"PUT",headers:apiHeaders(t),
      body:JSON.stringify({message:"Update job filters from dashboard",content:b64utf8(JSON.stringify(next,null,2)+"\n"),sha:current.sha,branch:"main"})
    });
    if(!putr.ok) throw new Error("GitHub save failed: "+putr.status);
    const runr=await fetch(API+"/repos/"+REPO+"/actions/workflows/job-watch.yml/dispatches",{
      method:"POST",headers:apiHeaders(t),body:JSON.stringify({ref:"main"})
    });
    if(!runr.ok) throw new Error("Workflow dispatch failed: "+runr.status);
    config=next;
    sessionStorage.setItem("jobbeeper_github_token",t);
    if ($("githubToken")) $("githubToken").value="";
    $("saveStatus").textContent="Saved. Scan started — Telegram will receive only jobs matching these filters.";
  }catch(e){ $("saveStatus").textContent=e.message; }
}

async function loadConfig(){
  const r=await fetch(RAW+"config.json?t="+Date.now(),{cache:"no-store"});
  if(!r.ok) throw new Error("Config unavailable");
  config=await r.json();
  loadForm();
}

async function load(){
  try{
    const r = await fetch(RAW+"dashboard/data/jobs.json?t="+Date.now(), {cache:"no-store"});
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
  }catch(e){ $("statusText").textContent = "Feed unavailable"; }
}

$("githubToken").value="";
$("clearToken").onclick=()=>{sessionStorage.removeItem("jobbeeper_github_token");$("githubToken").value="";$("saveStatus").textContent="Token cleared.";};
$("saveConfig").onclick=saveAndRun;
["search","source","score","age"].forEach(id=>$(id).addEventListener("input",render));
$("refresh").onclick=load;
setupNavigation();
loadConfig().catch(e=>{ if ($("saveStatus")) $("saveStatus").textContent="Could not load config."; });
load();
setInterval(load,30000);
