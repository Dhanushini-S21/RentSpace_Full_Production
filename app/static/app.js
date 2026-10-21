async function refreshEvents(){
  const box=document.getElementById("eventsList"), status=document.getElementById("eventStatus");
  if(!box) return;
  try{
    const r=await fetch("/api/v1/events",{credentials:"same-origin"});
    if(!r.ok) throw new Error();
    const data=await r.json();
    box.innerHTML=data.map(e=>`<div class="event"><b>${escapeHtml(e.type)}</b><span>${escapeHtml(e.message||"")}</span><small>${escapeHtml(e.created_at||"")}</small></div>`).join("");
    if(status) status.textContent="Live";
  }catch(e){if(status) status.textContent="Offline";}
}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));}
setInterval(refreshEvents,3000);


// Save admin management fields in place without navigating to Live Activity.
// The server still persists each form through its existing POST endpoint.
document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (!form.matches("form.cell-edit")) return;
  event.preventDefault();
  const button = form.querySelector('button[type="submit"], button:not([type])');
  if (!button || button.dataset.saving === "1") return;
  const originalText = button.textContent;
  button.dataset.saving = "1";
  button.disabled = true;
  button.textContent = "Saving...";
  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    if (!response.ok) throw new Error("Save failed");
    button.textContent = "Saved";
    button.classList.add("save-success");
    window.setTimeout(() => {
      button.textContent = originalText.trim() || "Save";
      button.classList.remove("save-success");
      button.disabled = false;
      delete button.dataset.saving;
    }, 2500);
  } catch (error) {
    button.textContent = "Retry";
    button.disabled = false;
    delete button.dataset.saving;
    window.setTimeout(() => { button.textContent = originalText.trim() || "Save"; }, 2500);
  }
});
