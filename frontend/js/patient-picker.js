// Type-ahead patient search. Replaces "enter a patient ID" inputs with a name
// search: the user types part of a name or national ID and picks from the list.
// Usage: const picker = attachPatientPicker(inputEl, (patient) => { ... });
//        picker.selected  -> the chosen patient object, or null
//        picker.clear()
function attachPatientPicker(input, onSelect) {
  const wrapper = input.parentElement;
  wrapper.style.position = "relative";
  input.setAttribute("autocomplete", "off");

  const list = document.createElement("div");
  list.className = "card";
  list.style.cssText =
    "display:none; position:absolute; z-index:10; left:0; right:0; max-height:220px; overflow-y:auto; padding:4px; margin-top:2px;";
  wrapper.appendChild(list);

  const picker = {
    selected: null,
    clear() {
      picker.selected = null;
      input.value = "";
      list.style.display = "none";
    },
  };

  let timer = null;
  let matches = [];

  input.addEventListener("input", () => {
    picker.selected = null;
    if (onSelect) onSelect(null);
    const q = input.value.trim();
    clearTimeout(timer);
    if (!q) {
      list.style.display = "none";
      return;
    }
    timer = setTimeout(async () => {
      matches = await api.get(`/patients?q=${encodeURIComponent(q)}`);
      list.innerHTML = matches.length
        ? matches
            .map(
              (p, i) => `<div class="patient-suggestion" data-index="${i}"
                style="padding:8px; cursor:pointer; border-bottom:1px solid var(--color-border)">
                ${escapeHtml(p.first_name)} ${escapeHtml(p.last_name)}
                <span class="text-muted">${p.national_id ? "· " + escapeHtml(p.national_id) : ""} ${p.phone ? "· " + escapeHtml(p.phone) : ""}</span>
              </div>`
            )
            .join("")
        : `<div class="text-muted" style="padding:8px">No patient found. <a href="/patients.html">Register a new patient</a></div>`;
      list.style.display = "block";
    }, 250);
  });

  list.addEventListener("click", (e) => {
    const row = e.target.closest(".patient-suggestion");
    if (!row) return;
    const patient = matches[Number(row.dataset.index)];
    picker.selected = patient;
    input.value = `${patient.first_name} ${patient.last_name}`;
    list.style.display = "none";
    if (onSelect) onSelect(patient);
  });

  document.addEventListener("click", (e) => {
    if (!wrapper.contains(e.target)) list.style.display = "none";
  });

  return picker;
}
