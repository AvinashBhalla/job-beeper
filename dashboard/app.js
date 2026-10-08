function setupNavigation(){
  const links=[...document.querySelectorAll(".nav-link")];
  const sections=[...document.querySelectorAll(".page-section")];

  function show(id){
    const target=document.getElementById(id)||document.getElementById("jobsSection");
    sections.forEach(s=>{
      const active=s===target;
      s.classList.toggle("hidden-section",!active);
      s.classList.toggle("active-section",active);
    });
    links.forEach(a=>a.classList.toggle("active",a.dataset.section===target.id));
  }

  window.showPage=show;

  links.forEach(link=>link.addEventListener("click",event=>{
    event.preventDefault();
    show(link.dataset.section);
    const hash=link.getAttribute("href");
    if(hash) history.replaceState(null,"",hash);
  }));

  const initial=(location.hash||"").slice(1);
  show(
    initial==="filters" ? "filtersSection" :
    initial==="settings" ? "settingsSection" :
    initial==="sources" ? "sourcesSection" :
    initial==="applied" ? "appliedSection" :
    "jobsSection"
  );
}

const API="/api";
let state={jobs:[]};
let config=null;

const $=id=>document.getElementById(id);

function esc(value){
  return String(value ?? "").replace(/[&<>"]/g,char=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"
  }[char]));
}

function csv(value){
  return value.split(",").map(x=>x.trim()).filter(Boolean);
}

function jobTimestamp(job){
  return job.source_posted_at || job.discovered_at || null;
}

function ageHours(timestamp){
  return timestamp ? Math.max(0,(Date.now()-new Date(timestamp).getTime())/3600000) : 9999;
}

function fmtAge(timestamp){
  if(!timestamp) return "time unknown";
  const hours=ageHours(timestamp);
  if(hours<1) return Math.max(1,Math.round(hours*60))+" min ago";
  if(hours<24) return Math.round(hours)+" hr ago";
  return Math.round(hours/24)+" days ago";
}

function fmtTimestamp(timestamp){
  return timestamp ? new Date(timestamp).toLocaleString() : "Not specified";
}

function populateSources(jobs){
  const current=$("source").value;
  const names=[...new Set(jobs.map(j=>j.source).filter(Boolean))].sort();
  $("source").innerHTML='<option value="">All sources</option>'+
    names.map(name=>'<option value="'+esc(name)+'">'+esc(name)+'</option>').join("");
  $("source").value=names.includes(current) ? current : "";
}

function renderSourceChoices(){
  const enabled=config?.source_enabled || {};
  const sources=[
    ["linkedin","LinkedIn"],
    ["naukri","Naukri"],
    ["instahyre","Instahyre"]
  ];
  $("sourceChoices").innerHTML=sources.map(([key,label])=>
    '<label class="choice"><input type="checkbox" data-source="'+key+'" '+
    (enabled[key]!==false ? "checked" : "")+'><span>'+label+'</span></label>'
  ).join("");
}

function loadForm(){
  const c=config;
  $("cfgRoles").value=(c.target_roles||[]).join(", ");
  $("cfgLocations").value=(c.locations||[]).join(", ");
  $("cfgSkills").value=(c.skills||[]).join(", ");
  $("cfgExclude").value=(c.title_exclude||[]).join(", ");
  $("cfgExcludeRoles").value=(c.excluded_role_terms||[]).join(", ");
  $("cfgCandidateExperience").value=c.candidate_experience_years ?? "";
  $("cfgMinExperience").value=c.min_experience_years ?? "";
  $("cfgExperience").value=c.max_experience_years ?? 3;
  $("cfgThreshold").value=c.match_threshold ?? 55;
  $("cfgRemoteOnly").checked=!!c.remote_only;
  $("cfgRequireExperience").checked=!!c.require_explicit_experience_for_alerts;
  $("cfgTelegram").checked=c.notifications_enabled!==false;
  renderSourceChoices();
}

function collectConfig(){
  const next=JSON.parse(JSON.stringify(config||{}));
  next.target_roles=csv($("cfgRoles").value);
  next.locations=csv($("cfgLocations").value);
  next.skills=csv($("cfgSkills").value);
  next.title_exclude=csv($("cfgExclude").value);
  next.excluded_role_terms=csv($("cfgExcludeRoles").value);

  const candidate=$("cfgCandidateExperience").value.trim();
  const minimum=$("cfgMinExperience").value.trim();

  next.candidate_experience_years=candidate==="" ? null : Number(candidate);
  next.min_experience_years=minimum==="" ? null : Number(minimum);
  next.max_experience_years=Number($("cfgExperience").value);
  next.match_threshold=Number($("cfgThreshold").value);
  next.remote_only=$("cfgRemoteOnly").checked;
  next.require_explicit_experience_for_alerts=$("cfgRequireExperience").checked;
  next.notifications_enabled=$("cfgTelegram").checked;

  next.source_enabled={};
  document.querySelectorAll("[data-source]").forEach(input=>{
    next.source_enabled[input.dataset.source]=input.checked;
  });

  return next;
}

function configToken(){
  return sessionStorage.getItem("jobradar_config_token") || $("configToken").value.trim();
}

function setToken(value){
  if(value) sessionStorage.setItem("jobradar_config_token",value);
  $("configToken").value="";
}

function clearToken(){
  sessionStorage.removeItem("jobradar_config_token");
  $("configToken").value="";
  $("tokenStatus").textContent="Configuration token cleared.";
}

async function loadConfig(){
  const response=await fetch(API+"/config",{cache:"no-store"});
  if(!response.ok) throw new Error("V2 configuration unavailable.");
  const data=await response.json();
  config=data.config;
  loadForm();
}

async function saveConfig(){
  const token=configToken();
  if(!token){
    $("saveStatus").textContent="Enter the V2 configuration token in Access first.";
    return;
  }

  const next=collectConfig();
  $("saveStatus").textContent="Saving V2 preferences…";

  try{
    const response=await fetch(API+"/config",{
      method:"PUT",
      headers:{
        "Content-Type":"application/json",
        "X-Config-Token":token
      },
      body:JSON.stringify(next)
    });

    if(!response.ok){
      let detail="";
      try{
        const body=await response.json();
        detail=body.detail || "";
      }catch(_){}
      if(response.status===401){
        $("saveStatus").textContent="Invalid configuration token.";
      }else{
        $("saveStatus").textContent="Could not save preferences"+(detail ? ": "+detail : ".");
      }
      return;
    }

    const data=await response.json();
    config=data.config;
    loadForm();
    $("saveStatus").textContent="Preferences saved. Matching uses them immediately.";
  }catch(error){
    $("saveStatus").textContent="Configuration API unavailable.";
  }
}

function showJobDetail(id){
  const job=state.jobs.find(item=>String(item.id)===String(id));
  if(!job) return;

  document.querySelectorAll(".page-section").forEach(section=>{
    const active=section.id==="jobDetailSection";
    section.classList.toggle("hidden-section",!active);
    section.classList.toggle("active-section",active);
  });

  document.querySelectorAll(".nav-link").forEach(link=>link.classList.remove("active"));

  $("detailSource").textContent=(job.source||"").toUpperCase();
  $("detailTitle").textContent=job.title||"Untitled job";
  $("detailCompany").textContent=job.company||"";
  $("detailScore").innerHTML="<b>"+esc(job.match_score ?? 0)+"%</b><small>MATCH</small>";

  const experience=(job.experience_min_years!=null || job.experience_max_years!=null)
    ? String(job.experience_min_years ?? "?")+"–"+String(job.experience_max_years ?? "?")+" years"
    : "Not specified";

  $("detailExperience").textContent=experience;
  $("detailLocation").textContent=job.location||"Not specified";
  $("detailWorkMode").textContent=job.location?.toLowerCase().includes("remote") ? "Remote / hybrid indicated" : "Not specified";
  $("detailPosted").textContent=fmtTimestamp(job.source_posted_at);

  $("detailApply").href=job.url||"#";

  $("detailMatch").textContent=job.alertable ? "Eligible for alerting" : "Not currently alertable";

  const reasons=(job.match_reasons||[]).map(reason=>
    "<div class='reason'><span>✓</span>"+esc(reason)+"</div>"
  ).join("");

  const alertReasons=(job.alertability_reasons||[]).map(reason=>
    "<div class='reason'><span>•</span>"+esc(reason)+"</div>"
  ).join("");

  $("detailReasons").innerHTML=(reasons||"<div class='empty'>No match reasons.</div>")+
    (alertReasons ? "<div class='reason-list'>"+alertReasons+"</div>" : "");

  $("detailSkillCount").textContent=(config?.skills||[]).length+" configured skills";
  $("detailSkills").innerHTML="<span>Match reasons above show detected configured skills.</span>";

  $("detailDescription").textContent=job.description ||
    "The source did not expose a full description during this scan. Open the original posting for details.";

  history.pushState(null,"","#job/"+encodeURIComponent(id));
  window.scrollTo({top:0,behavior:"instant"});
}

function closeJobDetail(){
  if(window.showPage) window.showPage("jobsSection");
  history.pushState(null,"","#jobs");
}

function render(){
  if(!config) return;

  const query=$("search").value.toLowerCase().trim();
  const source=$("source").value;
  const minimumScore=Number($("score").value);
  const maximumAge=Number($("age").value);

  let jobs=state.jobs.filter(job=>{
    const timestamp=jobTimestamp(job);
    const hay=[
      job.title,job.company,job.location,job.source,
      ...(job.match_reasons||[]),
      ...(job.alertability_reasons||[])
    ].join(" ").toLowerCase();

    return (!query || hay.includes(query)) &&
      (!source || job.source===source) &&
      (job.match_score ?? 0)>=minimumScore &&
      ageHours(timestamp)<=maximumAge;
  });

  if($("sort").value==="match"){
    jobs.sort((a,b)=>
      (b.match_score||0)-(a.match_score||0) ||
      String(jobTimestamp(b)||"").localeCompare(String(jobTimestamp(a)||""))
    );
  }else{
    jobs.sort((a,b)=>
      String(jobTimestamp(b)||"").localeCompare(String(jobTimestamp(a)||"")) ||
      (b.match_score||0)-(a.match_score||0)
    );
  }

  $("count").textContent=jobs.length+" jobs";

  $("jobs").innerHTML=jobs.map(job=>{
    const timestamp=jobTimestamp(job);
    const alertBadge=job.alertable
      ? "<span class='new'>ALERTABLE</span>"
      : "";

    return `
      <article class="card">
        <div class="cardmain">
          <div class="titleline">
            <h2><button class="job-title-link" data-job-id="${esc(job.id)}">${esc(job.title)}</button></h2>
            ${alertBadge}
          </div>
          <div class="company">${esc(job.company)}</div>
          <div class="meta">⌖ ${esc(job.location||"Location not listed")} · ◷ ${esc(fmtAge(timestamp))} · <b>${esc(job.source)}</b></div>
          <div class="chips">
            ${(job.match_reasons||[]).slice(0,7).map(reason=>"<span>"+esc(reason)+"</span>").join("")}
          </div>
        </div>
        <div class="actions">
          <div class="score ${(job.match_score||0)>=90?"hot":""}">${esc(job.match_score||0)}%<small>match</small></div>
          <a class="apply" href="${esc(job.url)}" target="_blank" rel="noopener">Apply now ↗</a>
        </div>
      </article>`;
  }).join("") || '<div class="empty">No jobs in the current feed.</div>';
}

async function loadJobs(){
  try{
    const maxAge=Math.max(1,Number(config?.max_age_hours||72));
    const minutes=Math.min(maxAge*60,10080);

    const response=await fetch(API+"/jobs?minutes="+encodeURIComponent(minutes)+"&limit=500",{
      cache:"no-store"
    });

    if(!response.ok) throw new Error("Jobs unavailable");

    const data=await response.json();
    state={jobs:data.jobs||[]};

    $("total").textContent=state.jobs.length;
    $("today").textContent=state.jobs.filter(job=>ageHours(jobTimestamp(job))<24).length;
    $("notified").textContent=state.jobs.filter(job=>job.alertable).length;
    $("lastRun").textContent=state.jobs.length ? "· live" : "";

    $("statusText").textContent="Live · V2 backend";
    populateSources(state.jobs);
    render();
  }catch(error){
    $("statusText").textContent="Feed unavailable";
  }
}

async function loadSourceStatus(){
  try{
    const response=await fetch(API+"/source-status",{cache:"no-store"});
    if(!response.ok) throw new Error();
    const data=await response.json();
    const rows=(data.sources||[]).map(source=>{
      const runtime=source.runtime||{};
      const stateLabel=runtime.error ? "ERROR" : runtime.running ? "RUNNING" : "OK";
      return "<div class='reason'><span>•</span><b>"+esc(source.source)+"</b> — "+
        stateLabel+" · seen "+esc(source.jobs_seen)+" · new "+esc(source.new_jobs)+
        (runtime.last_success ? " · last success "+esc(fmtTimestamp(runtime.last_success)) : "")+
        (runtime.error ? " · "+esc(runtime.error) : "")+
        "</div>";
    }).join("");
    $("sourceStatus").innerHTML=rows || '<div class="empty">No source runs recorded yet.</div>';
  }catch(error){
    $("sourceStatus").textContent="Source status unavailable.";
  }
}

$("saveConfig").onclick=saveConfig;
$("saveToken").onclick=()=>{
  const value=$("configToken").value.trim();
  if(!value){
    $("tokenStatus").textContent="Enter the token first.";
    return;
  }
  setToken(value);
  $("tokenStatus").textContent="Token remembered for this browser session.";
};
$("clearToken").onclick=clearToken;
$("refresh").onclick=()=>loadJobs();
$("backToJobs").onclick=closeJobDetail;

["search","source","score","age","sort"].forEach(id=>$(id).addEventListener("input",render));
document.addEventListener("click",event=>{
  const button=event.target.closest(".job-title-link");
  if(button) showJobDetail(button.dataset.jobId);
});

setupNavigation();

(async()=>{
  try{
    await loadConfig();
    await loadJobs();
    await loadSourceStatus();
    setInterval(loadJobs,30000);
    setInterval(loadSourceStatus,30000);
  }catch(error){
    $("statusText").textContent="V2 backend unavailable";
    $("saveStatus").textContent="Could not load V2 configuration.";
  }
})();
