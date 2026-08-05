const $ = (selector) => document.querySelector(selector);
const state = { user: null, doctors: [], selectedServices: new Map() };
const resultDocumentTypes = new Set([
  "Էխոսրտագրության պատասխան",
  "Հոլտերի եզրակացություն",
  "Ֆիզիկական ծանրաբեռնվածության թեստի պատասխան",
]);

function today() {
  return new Date().toISOString().slice(0, 10);
}

function monday(value) {
  const d = new Date(`${value}T00:00:00`);
  const diff = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - diff);
  return d.toISOString().slice(0, 10);
}

function addDays(value, days) {
  const d = new Date(`${value}T00:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function shortDate(value) {
  const d = new Date(`${value}T00:00:00`);
  return d.toLocaleDateString("hy-AM", { month: "short", day: "numeric" });
}

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2400);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || "Սխալ հարցում։");
  }
  return response.status === 204 ? null : response.json();
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function serviceKey(service) {
  return `${service.category}::${service.label}`;
}

function selectedServiceKey(doctor, service) {
  return `${doctor}::${serviceKey(service)}`;
}

function activeServiceDoctor() {
  return $("#serviceActiveDoctor").value.trim();
}

function doctorByName(name) {
  return state.doctors.find(doctor => doctor.name === name) || null;
}

function serviceCatalog() {
  const kind = $("#serviceForm").elements.kind.value;
  return (window.SERVICE_CATALOG || { general: [], lab: [] })[kind] || [];
}

function generalServiceAllowedForDoctor(service, doctor) {
  if (!doctor || !doctor.specialty) return true;
  const specialty = doctor.specialty.toLowerCase();
  const text = `${service.category} ${service.name} ${service.label}`.toLowerCase();
  if (specialty.includes("սրտաբան")) {
    return /սրտ|էսգ|էխո|հոլտեր|ճնշաչափ|սթրես|տնային/.test(text);
  }
  if (specialty.includes("նյարդաբան")) return text.includes("նյարդաբան");
  if (specialty.includes("էնդոկրինոլոգ")) return text.includes("էնդոկրինոլոգ");
  if (specialty.includes("ռևմատոլոգ")) return text.includes("ռևմատոլոգ");
  if (specialty.includes("թերապ")) return text.includes("թերապ");
  return true;
}

function visibleServiceCatalog() {
  const items = serviceCatalog();
  if (activeServiceKind() === "lab") return items;
  return items.filter(item => generalServiceAllowedForDoctor(item, doctorByName(activeServiceDoctor())));
}

function activeServiceKind() {
  return $("#serviceForm").elements.kind.value;
}

function servicePriceLabel(price) {
  return price ? `${Number(price).toLocaleString("hy-AM")} դր` : "";
}

function doctorOptions(value = "") {
  return `<option value="">Ընտրեք բժիշկ</option>${state.doctors.map(d => `<option ${d.name === value ? "selected" : ""}>${d.name}</option>`).join("")}`;
}

function serviceDoctorOptions(value = "") {
  const label = activeServiceKind() === "lab" ? "Ուղղորդող բժիշկ" : "Բժիշկ";
  return `<option value="">${label}</option>${state.doctors.map(d => `<option value="${d.name}" ${d.name === value ? "selected" : ""}>${d.name}${d.specialty ? ` · ${d.specialty}` : ""}</option>`).join("")}`;
}

function serviceDoctorLabel(item) {
  return item.kind === "lab" ? `Ուղղորդող բժիշկ՝ ${item.doctor}` : `Բժիշկ՝ ${item.doctor}`;
}

function renderSelectedServices() {
  const selected = [...state.selectedServices.values()];
  const total = selected.reduce((sum, item) => sum + Number(item.price || 0), 0);
  $("#servicePickCount").textContent = `${selected.length} ընտրված`;
  $("#serviceTotal").textContent = `Ընդամենը՝ ${total.toLocaleString("hy-AM")} դր`;
  $("#selectedServices").innerHTML = selected.length ? selected.map(item => `
    <div class="service-chip">
      <span>${item.name}<small>${serviceDoctorLabel(item)} · ${item.category}</small></span>
      <b>${servicePriceLabel(item.price)}</b>
      <button type="button" data-unselect-service="${encodeURIComponent(selectedServiceKey(item.doctor, item))}">×</button>
    </div>`).join("") : "<p>Ընտրեք ծառայությունները ցանկից։</p>";
}

function renderServiceOptions() {
  const query = ($("#serviceSearch").value || "").trim().toLowerCase();
  const doctor = activeServiceDoctor();
  const groups = visibleServiceCatalog()
    .filter(item => !query || `${item.category} ${item.name} ${item.label}`.toLowerCase().includes(query))
    .reduce((acc, item) => {
      (acc[item.category] ||= []).push(item);
      return acc;
    }, {});
  const html = Object.entries(groups).map(([category, items]) => `
    <section class="service-group">
      <div class="service-group-head">
        <h3>${category}</h3>
        <label>
          <input type="checkbox" data-category-toggle="${encodeURIComponent(category)}">
          Նշել բոլորը
        </label>
      </div>
      ${items.map(item => {
        const key = doctor ? selectedServiceKey(doctor, item) : "";
        return `
          <label class="service-option">
            <input type="checkbox" data-service="${encodeURIComponent(JSON.stringify(item))}" ${state.selectedServices.has(key) ? "checked" : ""}>
            <span>${item.name}<small>${item.label}</small></span>
            <b>${servicePriceLabel(item.price)}</b>
          </label>`;
      }).join("")}
    </section>`).join("");
  $("#serviceOptions").innerHTML = html || "<p>Ծառայություն չի գտնվել։</p>";
  document.querySelectorAll("[data-category-toggle]").forEach(input => {
    const category = decodeURIComponent(input.dataset.categoryToggle);
    const items = visibleServiceCatalog().filter(item => item.category === category);
    const selected = doctor ? items.filter(item => state.selectedServices.has(selectedServiceKey(doctor, item))).length : 0;
    input.checked = items.length > 0 && selected === items.length;
    input.indeterminate = selected > 0 && selected < items.length;
  });
  renderSelectedServices();
}

function resetServicePicker() {
  state.selectedServices.clear();
  $("#serviceSearch").value = "";
  $("#serviceActiveDoctor").innerHTML = serviceDoctorOptions();
  renderServiceOptions();
}

function doctorSelectTemplate(value = "") {
  return `
    <div class="doctor-row">
      <select name="appointment_doctor" required>
        ${state.doctors.map(d => `<option ${d.name === value ? "selected" : ""}>${d.name}</option>`).join("")}
      </select>
      <button type="button" class="secondary-button" data-remove-doctor>Ջնջել</button>
    </div>`;
}

function addAppointmentDoctor(value = "") {
  $("#appointmentDoctors").insertAdjacentHTML("beforeend", doctorSelectTemplate(value));
}

function resetAppointmentDoctors() {
  $("#appointmentDoctors").innerHTML = "";
  addAppointmentDoctor();
}

function updateUserRoleFields() {
  const role = $("#userRole").value;
  $("#userForm").elements.branch.classList.toggle("hidden", role !== "staff");
  $("#userDoctorName").classList.toggle("hidden", role !== "doctor");
  $("#userDoctorInfo").classList.toggle("hidden", role !== "doctor");
  renderUserDoctorInfo();
}

function renderUserDoctorInfo() {
  const name = $("#userDoctorName").value;
  const doctor = state.doctors.find(item => item.name === name);
  if ($("#userRole").value !== "doctor" || !doctor) {
    $("#userDoctorInfo").innerHTML = "<p>Ընտրեք բժիշկին։</p>";
    return;
  }
  $("#userDoctorInfo").innerHTML = `
    <div><span>Անուն Ազգանուն</span><strong>${doctor.name}</strong></div>
    <div><span>Մասնագիտություն</span><strong>${doctor.specialty || "Բժիշկ"}</strong></div>
  `;
}

function selectedAppointmentDoctors() {
  return [...document.querySelectorAll("#appointmentDoctors select")]
    .map(select => select.value.trim())
    .filter(Boolean)
    .filter((doctor, index, doctors) => doctors.indexOf(doctor) === index);
}

function renderTable(target, rows, columns, options = {}) {
  if (!rows.length) {
    target.innerHTML = "<p>Դեռ տվյալ չկա։</p>";
    return;
  }
  const actions = options.actions === false ? "" : "<th></th>";
  target.innerHTML = `<table><thead><tr>${columns.map(c => `<th>${c.label}</th>`).join("")}${actions}</tr></thead><tbody>${
    rows.map(row => `<tr>${columns.map(c => `<td>${row[c.key] ?? ""}</td>`).join("")}${options.actions === false ? "" : `<td>${options.actionHtml ? options.actionHtml(row) : ""}${options.deleteAction === false ? "" : `<button data-delete="${row.id}">Ջնջել</button>`}</td>`}</tr>`).join("")
  }</tbody></table>`;
}

function money(value) {
  return `${Number(value || 0).toLocaleString("hy-AM")} դր`;
}

function fullPatientName(patient) {
  return [patient.first_name, patient.last_name, patient.father_name].filter(Boolean).join(" ");
}

function detailGrid(items) {
  return `<div class="detail-grid">${items.map(([label, value]) => `
    <div><span>${label}</span><strong>${value || "—"}</strong></div>
  `).join("")}</div>`;
}

function maxCount(rows, key = "count") {
  return Math.max(1, ...rows.map(row => Number(row[key] || 0)));
}

function renderBars(target, rows, labelKey, valueKey, suffix = "") {
  if (!rows.length) {
    target.innerHTML = "<p>Դեռ տվյալ չկա։</p>";
    return;
  }
  const max = maxCount(rows, valueKey);
  target.innerHTML = `<div class="bars">${rows.map(row => {
    const value = Number(row[valueKey] || 0);
    return `<div class="bar-row"><span>${row[labelKey] || "Չնշված"}</span><b>${value.toLocaleString("hy-AM")}${suffix}</b><i style="--w:${Math.max(4, (value / max) * 100)}%"></i></div>`;
  }).join("")}</div>`;
}

function applyBranchAccess() {
  if (state.user?.role !== "staff") return;
  document.querySelectorAll('select[name="branch"], #calendarBranch').forEach(select => {
    select.innerHTML = `<option>${state.user.branch}</option>`;
    select.value = state.user.branch;
  });
}

async function fillNextPatientAnketa(force = false) {
  const form = $("#patientForm");
  if (!form || state.user?.role === "doctor") return;
  const field = form.elements.anketa_number;
  if (!force && field.value.trim()) return;
  const branch = form.elements.branch.value;
  const hint = $("#patientAnketaHint");
  try {
    const data = await api(`/api/next-anketa?branch=${encodeURIComponent(branch)}`);
    field.value = data.anketa_number;
    hint.textContent = `${data.branch} հաջորդ անկետա՝ ${data.anketa_number}`;
    hint.className = "field-hint success";
  } catch (error) {
    hint.textContent = "Չհաջողվեց ստեղծել ավտոմատ համարը։ Կարող եք լրացնել ձեռքով։";
    hint.className = "field-hint warning";
  }
}

async function fillAppointmentFromAnketa(force = false) {
  return fillFormFromAnketa($("#appointmentForm"), $("#appointmentPatientHint"), force);
}

async function fillHolterFromAnketa(force = false) {
  return fillFormFromAnketa($("#holterForm"), $("#holterPatientHint"), force);
}

async function fillFormFromAnketa(form, hint, force = false) {
  const anketa = form.elements.anketa_number.value.trim();
  hint.textContent = "";
  hint.className = "field-hint";
  if (!anketa) return;
  try {
    const patient = await api(`/api/patient?anketa_number=${encodeURIComponent(anketa)}`);
    if (force || !(form.elements.patient_name && form.elements.patient_name.value.trim())) applyPatientToForm(form, patient, hint);
    else {
      hint.textContent = `Գտնվեց՝ ${fullPatientName(patient) || patient.anketa_number}`;
      hint.classList.add("success");
    }
    return patient;
  } catch (error) {
    hint.textContent = "Պացիենտը չգտնվեց։ Կարող եք շարունակել ձեռքով։";
    hint.classList.add("warning");
    return null;
  }
}

function applyPatientToForm(form, patient, hint) {
  const fullName = fullPatientName(patient);
  if (form.elements.anketa_number) form.elements.anketa_number.value = patient.anketa_number || "";
  if (form.elements.patient_name) form.elements.patient_name.value = fullName;
  if (form.elements.passport) form.elements.passport.value = patient.passport || "";
  if (form.elements.phone) form.elements.phone.value = patient.phone || "";
  if (form.elements.branch && patient.branch) form.elements.branch.value = patient.branch;
  if (hint) {
    hint.textContent = `Ընտրված է՝ ${fullName || patient.anketa_number}`;
    hint.className = "field-hint success";
  }
}

async function searchAppointmentPatients() {
  const query = $("#appointmentPatientSearch").value.trim();
  const target = $("#appointmentPatientResults");
  if (query.length < 2) {
    target.innerHTML = "";
    return;
  }
  const branch = $("#appointmentForm").elements.branch.value;
  try {
    const rows = await api(`/api/patient-lookup?q=${encodeURIComponent(query)}&branch=${encodeURIComponent(branch)}`);
    target.innerHTML = rows.length ? rows.map(patient => `
      <button type="button" class="patient-result" data-appointment-patient="${encodeURIComponent(JSON.stringify(patient))}">
        <strong>${fullPatientName(patient) || patient.anketa_number}</strong>
        <span>${patient.anketa_number} · ${patient.branch || "—"} · ${patient.phone || "հեռախոս չկա"}</span>
        <small>${patient.passport || "անձնագիր չկա"}</small>
      </button>
    `).join("") : "<p>Պացիենտ չի գտնվել։</p>";
  } catch (error) {
    toast(error.message);
  }
}

function openQuickBooking(date, timeValue) {
  const modal = $("#quickBookingModal");
  const form = $("#quickBookingForm");
  form.reset();
  form.elements.appointment_date.value = date;
  form.elements.appointment_time.value = timeValue;
  form.elements.branch.value = $("#calendarBranch").value;
  form.elements.doctor.value = $("#calendarDoctor").value;
  form.elements.status.value = "Նշանակված";
  form.elements.notes.value = "Արագ ժամադրում հեռախոսազանգից";
  $("#quickBookingHint").textContent = "";
  $("#quickBookingHint").className = "field-hint";
  $("#quickBookingSlot").textContent = `${date} ${timeValue} · ${form.elements.branch.value} · ${form.elements.doctor.value}`;
  modal.classList.remove("hidden");
  form.elements.anketa_number.focus();
}

function closeQuickBooking() {
  $("#quickBookingModal").classList.add("hidden");
}

async function loadDoctors() {
  state.doctors = await api("/api/doctors");
  $("#calendarDoctor").innerHTML = state.doctors.map(d => `<option>${d.name}</option>`).join("");
  $("#serviceActiveDoctor").innerHTML = serviceDoctorOptions();
  $("#userDoctorName").innerHTML = `<option value="">Բժիշկ</option>${state.doctors.map(d => `<option>${d.name}</option>`).join("")}`;
  updateUserRoleFields();
  resetAppointmentDoctors();
  renderSelectedServices();
}

async function loadLists() {
  const [patients, appointments, holters, services, summary] = await Promise.all([
    api("/api/patients"),
    api("/api/appointments"),
    api("/api/holters"),
    api("/api/service-orders"),
    api("/api/summary"),
  ]);
  renderTable($("#patientsTable"), patients, [
    { key: "anketa_number", label: "Անկետա #" },
    { key: "visit_date", label: "Ամսաթիվ" },
    { key: "branch", label: "Մասնաճյուղ" },
    { key: "first_name", label: "Անուն" },
    { key: "last_name", label: "Ազգանուն" },
    { key: "passport", label: "Անձնագիր" },
    { key: "phone", label: "Հեռախոս" },
  ]);
  renderTable($("#appointmentsTable"), appointments, [
    { key: "appointment_date", label: "Ամսաթիվ" },
    { key: "appointment_time", label: "Ժամ" },
    { key: "branch", label: "Մասնաճյուղ" },
    { key: "doctor", label: "Բժիշկ" },
    { key: "patient_name", label: "Պացիենտ" },
    { key: "passport", label: "Անձնագիր" },
    { key: "status", label: "Կարգավիճակ" },
  ]);
  renderTable($("#holtersTable"), holters, [
    { key: "anketa_number", label: "Անկետա #" },
    { key: "patient_name", label: "Պացիենտ" },
    { key: "phone", label: "Հեռախոս" },
    { key: "branch", label: "Մասնաճյուղ" },
    { key: "provided_date", label: "Տրման ամսաթիվ" },
    { key: "provided_time", label: "Տրման ժամ" },
    { key: "duration_hours", label: "Ժամ" },
    { key: "return_at", label: "Վերադարձ" },
  ], { actionHtml: row => `<button type="button" data-print-holter="${row.id}">Տպել</button> ` });
  renderTable($("#servicesTable"), services, [
    { key: "anketa_number", label: "Անկետա #" },
    { key: "kind", label: "Տեսակ" },
    { key: "doctor", label: "Բժիշկ" },
    { key: "service_name", label: "Ծառայություն" },
    { key: "price", label: "Գին" },
    { key: "status", label: "Կարգավիճակ" },
  ]);
  const revenue = Object.fromEntries(summary.revenue.map(r => [r.kind, r.total || 0]));
  $("#summaryBox").innerHTML = `
    <div class="stats">
      <strong>${summary.patients}<span>Պացիենտներ</span></strong>
      <strong>${summary.appointments}<span>Ժամադրություններ</span></strong>
      <strong>${revenue.general || 0}<span>Ընդհանուր եկամուտ</span></strong>
      <strong>${revenue.lab || 0}<span>Լաբ․ եկամուտ</span></strong>
    </div>`;
  if (state.user.role === "admin") {
    const users = await api("/api/users");
    renderTable($("#usersTable"), users, [
      { key: "username", label: "Օգտանուն" },
      { key: "role", label: "Դեր" },
      { key: "branch", label: "Մասնաճյուղ" },
      { key: "doctor_name", label: "Բժիշկ" },
    ]);
  }
}

async function searchPatientOverview() {
  const query = $("#patientSearchInput").value.trim();
  const params = new URLSearchParams({
    q: query,
    date_type: $("#patientReportDateType").value,
    patient_type: $("#patientReportType").value,
    from: $("#patientReportFrom").value,
    to: $("#patientReportTo").value,
  });
  try {
    const rows = await api(`/api/patient-report?${params.toString()}`);
    $("#patientSearchResults").innerHTML = rows.length ? rows.map(patient => `
      <button type="button" class="patient-result" data-profile-anketa="${patient.anketa_number}">
        <strong>${fullPatientName(patient) || patient.anketa_number}</strong>
        <span>${patient.anketa_number} · ${patient.branch || "—"} · ${patient.phone || "հեռախոս չկա"}</span>
        <small>Գրանցում՝ ${patient.registration_date || "—"} · Այց՝ ${patient.visit_date || "—"} · Ծառայություններ՝ ${patient.service_count || 0} · ${money(patient.service_total)}</small>
      </button>
    `).join("") : "<p>Պացիենտ չի գտնվել։</p>";
  } catch (error) {
    toast(error.message);
  }
}

async function loadPatientProfile(anketaNumber) {
  try {
    const data = await api(`/api/patient-profile?anketa_number=${encodeURIComponent(anketaNumber)}`);
    const patient = data.patient;
    $("#patientProfileBox").innerHTML = `
      <section class="profile-section">
        <h3>${fullPatientName(patient) || patient.anketa_number}</h3>
        ${detailGrid([
          ["Անկետա #", patient.anketa_number],
          ["Գրանցման ամսաթիվ", (patient.created_at || "").slice(0, 10)],
          ["Այցի ամսաթիվ", patient.visit_date],
          ["Մասնաճյուղ", patient.branch],
          ["Ծննդյան ամսաթիվ", patient.birth_date],
          ["Անձնագիր", patient.passport],
          ["Հեռախոս", patient.phone],
          ["Էլ․ փոստ", patient.email],
          ["Կարգավիճակ", patient.status],
          ["Վճարում", patient.payment],
          ["Նշումներ", patient.notes],
        ])}
      </section>
      <section class="profile-section"><h3>Ժամադրություններ</h3><div id="profileAppointments"></div></section>
      <section class="profile-section"><h3>Ծառայություններ</h3><div id="profileServices"></div></section>
      <section class="profile-section"><h3>Հոլտեր</h3><div id="profileHolters"></div></section>
      <section class="profile-section"><h3>Ախտորոշումներ և նշանակումներ</h3><div id="profileDoctorNotes"></div></section>
    `;
    renderTable($("#profileAppointments"), data.appointments, [
      { key: "appointment_date", label: "Ամսաթիվ" },
      { key: "appointment_time", label: "Ժամ" },
      { key: "branch", label: "Մասնաճյուղ" },
      { key: "doctor", label: "Բժիշկ" },
      { key: "status", label: "Կարգավիճակ" },
      { key: "notes", label: "Նշումներ" },
    ], { actions: false });
    renderTable($("#profileServices"), data.services, [
      { key: "kind", label: "Տեսակ" },
      { key: "branch", label: "Մասնաճյուղ" },
      { key: "doctor", label: "Բժիշկ" },
      { key: "service_name", label: "Ծառայություն" },
      { key: "price", label: "Գին" },
      { key: "status", label: "Կարգավիճակ" },
    ], { actions: false });
    renderTable($("#profileHolters"), data.holters, [
      { key: "provided_date", label: "Տրման ամսաթիվ" },
      { key: "provided_time", label: "Ժամ" },
      { key: "duration_hours", label: "Տևողություն" },
      { key: "return_at", label: "Վերադարձ" },
      { key: "return_status", label: "Կարգավիճակ" },
      { key: "actual_return", label: "Փաստացի վերադարձ" },
    ], { actionHtml: row => `<button type="button" data-print-holter="${row.id}">Տպել</button> `, deleteAction: false });
    renderTable($("#profileDoctorNotes"), data.doctor_notes || [], [
      { key: "created_at", label: "Ամսաթիվ" },
      { key: "doctor", label: "Բժիշկ" },
      { key: "complaints", label: "Գանգատներ" },
      { key: "diagnosis", label: "Ախտորոշում" },
      { key: "prescription", label: "Նշանակում" },
      { key: "notes", label: "Նշումներ" },
    ], { actions: false });
  } catch (error) {
    toast(error.message);
  }
}

async function searchDoctorPatients() {
  const query = $("#doctorPatientSearch").value.trim();
  try {
    const rows = await api(`/api/doctor-patients?q=${encodeURIComponent(query)}`);
    $("#doctorPatientResults").innerHTML = rows.length ? rows.map(patient => `
      <button type="button" class="patient-result" data-doctor-anketa="${patient.anketa_number}">
        <strong>${fullPatientName(patient) || patient.anketa_number}</strong>
        <span>${patient.anketa_number} · ${patient.branch || "—"} · ${patient.phone || "հեռախոս չկա"}</span>
        <small>Վերջին այց՝ ${patient.last_appointment_date || patient.last_service_date || patient.visit_date || "—"}</small>
        <b>Ընտրել</b>
      </button>
    `).join("") : "<p>Այս բժշկի համար պացիենտ չի գտնվել։</p>";
    if (rows.length === 1) await loadDoctorNotes(rows[0].anketa_number);
  } catch (error) {
    toast(error.message);
  }
}

async function loadDoctorNotes(anketaNumber) {
  try {
    const data = await api(`/api/doctor-notes?anketa_number=${encodeURIComponent(anketaNumber)}`);
    const patient = data.patient;
    $("#doctorNoteForm").elements.anketa_number.value = anketaNumber;
    $("#doctorNotePatient").textContent = `${fullPatientName(patient) || anketaNumber} · ${patient.phone || "հեռախոս չկա"}`;
    $("#doctorNotePatient").className = "field-hint success";
    $("#doctorHolterHistory").innerHTML = data.holters?.length ? `
      <h3>Հոլտերի պատասխաններ</h3>
      ${data.holters.map(holter => `
        <article class="doctor-note-card">
          <div class="doctor-note-head">
            <h3>${holter.provided_date || "—"} ${holter.provided_time || ""}</h3>
            <button type="button" data-print-holter="${holter.id}">Տպել</button>
          </div>
          <p><strong>Տևողություն</strong><br>${holter.duration_hours || "—"} ժամ</p>
          <p><strong>Վերադարձ</strong><br>${holter.return_at || "—"} · ${holter.return_status || "—"}</p>
          ${holter.notes ? `<p><strong>Պատասխան / եզրակացություն</strong><br>${holter.notes}</p>` : ""}
        </article>
      `).join("")}
    ` : "<p>Այս պացիենտի համար հոլտերի պատասխան չկա։</p>";
    $("#doctorNotesHistory").innerHTML = data.notes.length ? data.notes.map(note => `
      <article class="doctor-note-card">
        <div class="doctor-note-head">
          <h3>${note.note_type || "Ախտորոշում"} · ${note.created_at.slice(0, 16).replace("T", " ")}</h3>
          <button type="button" data-print-note="${note.id}">Տպել</button>
        </div>
        ${note.complaints ? `<p><strong>Գանգատներ</strong><br>${note.complaints}</p>` : ""}
        ${note.diagnosis ? `<p><strong>Ախտորոշում</strong><br>${note.diagnosis}</p>` : ""}
        ${note.prescription ? `<p><strong>${resultDocumentTypes.has(note.note_type) ? (note.note_type || "Պատասխան / եզրակացություն") : "Նշանակում"}</strong><br>${note.prescription}</p>` : ""}
        ${note.notes ? `<p><strong>Նշումներ</strong><br>${note.notes}</p>` : ""}
      </article>
    `).join("") : "<p>Այս պացիենտի համար գրառում դեռ չկա։</p>";
  } catch (error) {
    toast(error.message);
  }
}

async function loadDashboard() {
  if (state.user?.role !== "admin") return;
  const data = await api("/api/dashboard");
  $("#dashboardDate").textContent = `Այսօր՝ ${data.today}`;
  const cards = [
    ["Այսօրվա պացիենտներ", data.totals.today_patients],
    ["Այսօրվա ժամադրություններ", data.totals.today_appointments],
    ["Այս ամսվա եկամուտ", money(data.totals.month_revenue)],
    ["Ընդհանուր եկամուտ", money(data.totals.total_revenue)],
    ["Պացիենտներ", data.totals.patients],
    ["Ժամադրություններ", data.totals.appointments],
    ["Ծառայություններ", data.totals.services],
    ["Հոլտերներ", data.totals.holters],
  ];
  $("#dashboardMetrics").innerHTML = cards.map(([label, value]) => `<article><strong>${value}</strong><span>${label}</span></article>`).join("");
  $("#branchMetrics").innerHTML = `<table><thead><tr><th>Մասնաճյուղ</th><th>Պացիենտ</th><th>Ժամադրություն</th><th>Եկամուտ</th></tr></thead><tbody>${
    data.by_branch.map(row => `<tr><td>${row.branch}</td><td>${row.patients}</td><td>${row.appointments}</td><td>${money(row.revenue)}</td></tr>`).join("")
  }</tbody></table>`;
  renderBars($("#statusMetrics"), data.by_status, "status", "count");
  renderBars($("#doctorMetrics"), data.by_doctor, "doctor", "count");
  renderBars($("#serviceMetrics"), data.by_service.map(row => ({
    kind: row.kind === "lab" ? "Լաբորատոր" : "Ընդհանուր",
    revenue: row.revenue,
  })), "kind", "revenue", " դր");
  renderTable($("#holterMetrics"), data.upcoming_holters, [
    { key: "anketa_number", label: "Անկետա #" },
    { key: "return_at", label: "Վերադարձ" },
    { key: "return_status", label: "Կարգավիճակ" },
  ], { actions: false });
  renderTable($("#recentAppointments"), data.recent_appointments, [
    { key: "appointment_date", label: "Ամսաթիվ" },
    { key: "appointment_time", label: "Ժամ" },
    { key: "branch", label: "Մասնաճյուղ" },
    { key: "doctor", label: "Բժիշկ" },
    { key: "patient_name", label: "Պացիենտ" },
  ], { actions: false });
}

async function loadCalendar() {
  const branch = encodeURIComponent($("#calendarBranch").value);
  const doctor = encodeURIComponent($("#calendarDoctor").value);
  const weekStart = monday($("#calendarWeek").value || today());
  $("#calendarWeek").value = weekStart;
  const week = encodeURIComponent(weekStart);
  const data = await api(`/api/calendar?branch=${branch}&doctor=${doctor}&week=${week}`);
  const dayNames = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ", "Շաբաթ", "Կիրակի"];
  const counters = data.days.map(day => ({ date: day, free: 0, busy: 0, closed: 0 }));
  data.slots.forEach(slot => slot.days.forEach((day, index) => {
    if (day.status === "Ազատ") counters[index].free += 1;
    if (day.status === "Զբաղված") counters[index].busy += 1;
    if (day.status === "Փակ") counters[index].closed += 1;
  }));
  $("#calendarRange").textContent = `${shortDate(data.days[0])} - ${shortDate(data.days[6])}`;
  $("#calendarStats").innerHTML = counters.map((day, index) => `
    <div class="${day.date === today() ? "today-card" : ""}">
      <strong>${dayNames[index]}</strong>
      <span>${shortDate(day.date)}</span>
      <b>${day.free} ազատ</b>
    </div>`).join("");
  $("#calendarGrid").innerHTML = `<table class="calendar-table"><thead><tr><th>Ժամ</th>${data.days.map((d, i) => `<th class="${d === today() ? "today-col" : ""}"><strong>${dayNames[i]}</strong><span>${shortDate(d)}</span></th>`).join("")}</tr></thead><tbody>${
    data.slots.map(slot => `<tr><th>${slot.time}</th>${slot.days.map(day => {
      const cls = day.status === "Փակ" ? "closed" : day.status === "Զբաղված" ? "busy" : "free";
      const appointmentTitle = day.appointment?.patient_name || day.appointment?.anketa_number || "Ժամադրություն";
      const text = day.appointment ? `<strong>${appointmentTitle}</strong><span>${day.appointment.branch} · ${day.appointment.status}</span>` : `<strong>${day.status}</strong>`;
      return `<td class="${cls} ${day.date === today() ? "today-col" : ""}" data-date="${day.date}" data-time="${slot.time}" data-status="${day.status}">${text}</td>`;
    }).join("")}</tr>`).join("")
  }</tbody></table>`;
}

function setDefaultDates() {
  document.querySelectorAll('input[name="visit_date"], input[name="appointment_date"], input[name="provided_date"], #calendarWeek').forEach(input => {
    if (!input.value) input.value = today();
    input.min = "1900-01-01";
  });
  ["#patientReportFrom", "#patientReportTo"].forEach(selector => {
    const input = $(selector);
    if (input && !input.value) input.value = today();
  });
}

async function init() {
  const me = await api("/api/me");
  if (!me.user) return;
  state.user = me.user;
  $("#login").classList.add("hidden");
  $("#app").classList.remove("hidden");
  $("#userLabel").textContent = `${me.user.username} ${me.user.doctor_name || me.user.branch || "բոլոր մասնաճյուղերը"}`;
  document.querySelectorAll(".admin-only").forEach(el => el.classList.toggle("hidden", me.user.role !== "admin"));
  document.querySelectorAll(".doctor-only").forEach(el => el.classList.toggle("hidden", me.user.role !== "doctor"));
  document.querySelectorAll(".staff-flow").forEach(el => el.classList.toggle("hidden", me.user.role === "doctor"));
  applyBranchAccess();
  setDefaultDates();
  await loadDoctors();
  if (me.user.role === "doctor") {
    activateTab("doctorWorkspace");
    await searchDoctorPatients();
    return;
  }
  activateTab(me.user.role === "admin" ? "dashboard" : "patients");
  $("#calendarWeek").value = monday(today());
  await fillNextPatientAnketa();
  resetServicePicker();
  await loadLists();
  if (me.user.role === "admin") await loadDashboard();
  await loadCalendar();
}

$("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/login", { method: "POST", body: JSON.stringify(formData(event.target)) });
    await init();
  } catch (error) {
    $("#loginError").textContent = error.message;
  }
});

$("#logoutButton").addEventListener("click", async () => {
  try {
    await api("/api/logout", { method: "POST" });
  } finally {
    location.reload();
  }
});

function activateTab(tab) {
  document.querySelectorAll("[data-tab]").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelector(`[data-tab="${tab}"]`)?.classList.add("active");
  $(`#${tab}`)?.classList.add("active");
}

document.querySelectorAll("[data-tab]").forEach(button => button.addEventListener("click", () => activateTab(button.dataset.tab)));

[
  ["#patientForm", "/api/patients"],
  ["#holterForm", "/api/holters"],
  ["#userForm", "/api/users"],
].forEach(([selector, path]) => {
  $(selector).addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api(path, { method: "POST", body: JSON.stringify(formData(event.target)) });
      event.target.reset();
      setDefaultDates();
      if (selector === "#patientForm") await fillNextPatientAnketa(true);
      toast("Պահպանվեց։");
      await loadLists();
      await loadDashboard();
      await loadCalendar();
    } catch (error) {
      toast(error.message);
    }
  });
});

$("#patientForm").elements.branch.addEventListener("change", () => fillNextPatientAnketa(true));

$("#appointmentForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const doctors = selectedAppointmentDoctors();
  if (!doctors.length) {
    toast("Ընտրեք առնվազն մեկ բժիշկ։");
    return;
  }
  try {
    await api("/api/appointments", {
      method: "POST",
      body: JSON.stringify({ ...formData(event.target), doctor: doctors[0], doctors }),
    });
    event.target.reset();
    $("#appointmentPatientSearch").value = "";
    $("#appointmentPatientResults").innerHTML = "";
    resetAppointmentDoctors();
    setDefaultDates();
    toast(`${doctors.length} բժիշկի համար գրանցվեց։`);
    await loadLists();
    await loadDashboard();
    await loadCalendar();
  } catch (error) {
    toast(error.message);
  }
});

$("#serviceForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const services = [...state.selectedServices.values()].map(item => ({
    category: item.category,
    service_name: item.name,
    price: item.price,
    doctor: item.doctor || "",
  }));
  if (!services.length) {
    toast("Ընտրեք առնվազն մեկ ծառայություն։");
    return;
  }
  if (services.some(item => !item.doctor)) {
    toast("Յուրաքանչյուր ծառայության համար ընտրեք բժիշկ։");
    return;
  }
  try {
    await api("/api/service-orders", {
      method: "POST",
      body: JSON.stringify({ ...formData(form), services }),
    });
    form.reset();
    resetServicePicker();
    setDefaultDates();
    toast(`${services.length} ծառայություն պահպանվեց։`);
    await loadLists();
    await loadDashboard();
  } catch (error) {
    toast(error.message);
  }
});

document.body.addEventListener("click", async (event) => {
  if (event.target.matches("#calendarGrid td.free")) {
    openQuickBooking(event.target.dataset.date, event.target.dataset.time);
    return;
  }
  if (event.target.matches("[data-unselect-service]")) {
    state.selectedServices.delete(decodeURIComponent(event.target.dataset.unselectService));
    renderServiceOptions();
    return;
  }
  if (event.target.matches("[data-remove-doctor]")) {
    const rows = document.querySelectorAll("#appointmentDoctors .doctor-row");
    if (rows.length > 1) event.target.closest(".doctor-row").remove();
    else toast("Պետք է մնա առնվազն մեկ բժիշկ։");
    return;
  }
  const appointmentPatientButton = event.target.closest("[data-appointment-patient]");
  if (appointmentPatientButton) {
    const patient = JSON.parse(decodeURIComponent(appointmentPatientButton.dataset.appointmentPatient));
    applyPatientToForm($("#appointmentForm"), patient, $("#appointmentPatientHint"));
    $("#appointmentPatientSearch").value = "";
    $("#appointmentPatientResults").innerHTML = "";
    return;
  }
  const profileButton = event.target.closest("[data-profile-anketa]");
  if (profileButton) {
    await loadPatientProfile(profileButton.dataset.profileAnketa);
    return;
  }
  const doctorPatientButton = event.target.closest("[data-doctor-anketa]");
  if (doctorPatientButton) {
    await loadDoctorNotes(doctorPatientButton.dataset.doctorAnketa);
    return;
  }
  if (event.target.matches("[data-print-note]")) {
    window.open(`/print/doctor-note?id=${encodeURIComponent(event.target.dataset.printNote)}`, "_blank");
    return;
  }
  if (event.target.matches("[data-print-holter]")) {
    window.open(`/print/holter?id=${encodeURIComponent(event.target.dataset.printHolter)}`, "_blank");
    return;
  }
  const id = event.target.dataset.delete;
  if (!id) return;
  const page = event.target.closest(".page").id;
  const endpoint = { patients: "patients", appointments: "appointments", services: "service-orders", holter: "holters", users: "users" }[page];
  if (!endpoint || !confirm("Ջնջե՞լ գրառումը։")) return;
  await api(`/api/${endpoint}/${id}`, { method: "DELETE" });
  await loadLists();
  await loadDashboard();
  await loadCalendar();
});

$("#refreshCalendar").addEventListener("click", loadCalendar);
$("#calendarBranch").addEventListener("change", loadCalendar);
$("#calendarDoctor").addEventListener("change", loadCalendar);
$("#calendarWeek").addEventListener("change", loadCalendar);
$("#prevWeek").addEventListener("click", () => {
  $("#calendarWeek").value = addDays($("#calendarWeek").value || today(), -7);
  loadCalendar();
});
$("#nextWeek").addEventListener("click", () => {
  $("#calendarWeek").value = addDays($("#calendarWeek").value || today(), 7);
  loadCalendar();
});
$("#todayWeek").addEventListener("click", () => {
  $("#calendarWeek").value = today();
  loadCalendar();
});
$("#addAppointmentDoctor").addEventListener("click", () => addAppointmentDoctor());
$("#serviceForm").elements.kind.addEventListener("change", resetServicePicker);
$("#serviceActiveDoctor").addEventListener("change", renderServiceOptions);
$("#serviceSearch").addEventListener("input", renderServiceOptions);
$("#clearSelectedServices").addEventListener("click", resetServicePicker);
$("#serviceOptions").addEventListener("change", (event) => {
  if (event.target.matches("[data-category-toggle]")) {
    const doctor = activeServiceDoctor();
    if (!doctor) {
      event.target.checked = false;
      toast("Նախ ընտրեք բժիշկ։");
      return;
    }
    const category = decodeURIComponent(event.target.dataset.categoryToggle);
    visibleServiceCatalog()
      .filter(item => item.category === category)
      .forEach(item => {
        const key = selectedServiceKey(doctor, item);
        if (event.target.checked) state.selectedServices.set(key, state.selectedServices.get(key) || { ...item, doctor, kind: activeServiceKind() });
        else state.selectedServices.delete(key);
      });
    renderServiceOptions();
    return;
  }
  if (!event.target.matches("[data-service]")) return;
  const item = JSON.parse(decodeURIComponent(event.target.dataset.service));
  const doctor = activeServiceDoctor();
  if (!doctor) {
    event.target.checked = false;
    toast("Նախ ընտրեք բժիշկ։");
    return;
  }
  const key = selectedServiceKey(doctor, item);
  if (event.target.checked) state.selectedServices.set(key, state.selectedServices.get(key) || { ...item, doctor, kind: activeServiceKind() });
  else state.selectedServices.delete(key);
  renderServiceOptions();
});
$("#appointmentForm").elements.anketa_number.addEventListener("change", () => fillAppointmentFromAnketa());
$("#appointmentForm").elements.anketa_number.addEventListener("blur", () => fillAppointmentFromAnketa());
$("#appointmentPatientSearch").addEventListener("input", searchAppointmentPatients);
$("#appointmentPatientSearch").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    searchAppointmentPatients();
  }
});
$("#appointmentForm").elements.branch.addEventListener("change", () => {
  $("#appointmentPatientResults").innerHTML = "";
  if ($("#appointmentPatientSearch").value.trim().length >= 2) searchAppointmentPatients();
});
$("#holterForm").elements.anketa_number.addEventListener("change", () => fillHolterFromAnketa());
$("#holterForm").elements.anketa_number.addEventListener("blur", () => fillHolterFromAnketa());
$("#quickBookingForm").elements.anketa_number.addEventListener("change", () => fillFormFromAnketa($("#quickBookingForm"), $("#quickBookingHint")));
$("#quickBookingForm").elements.anketa_number.addEventListener("blur", () => fillFormFromAnketa($("#quickBookingForm"), $("#quickBookingHint")));
$("#quickBookingForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/appointments", { method: "POST", body: JSON.stringify(formData(event.target)) });
    closeQuickBooking();
    toast("Ժամադրությունը պահպանվեց։");
    await loadLists();
    await loadDashboard();
    await loadCalendar();
  } catch (error) {
    toast(error.message);
  }
});
$("#closeQuickBooking").addEventListener("click", closeQuickBooking);
$("#quickBookingModal").addEventListener("click", (event) => {
  if (event.target.id === "quickBookingModal") closeQuickBooking();
});
$("#refreshDashboard").addEventListener("click", loadDashboard);
$("#exportButton").addEventListener("click", () => window.open("/api/export", "_blank"));
$("#userRole").addEventListener("change", updateUserRoleFields);
$("#userDoctorName").addEventListener("change", renderUserDoctorInfo);
$("#patientSearchButton").addEventListener("click", searchPatientOverview);
$("#patientSearchInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    searchPatientOverview();
  }
});
["#patientReportDateType", "#patientReportFrom", "#patientReportTo", "#patientReportType"].forEach(selector => {
  $(selector).addEventListener("change", searchPatientOverview);
});
$("#doctorPatientSearchButton").addEventListener("click", searchDoctorPatients);
$("#doctorPatientSearch").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    searchDoctorPatients();
  }
});
$("#doctorNoteForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/doctor-notes", { method: "POST", body: JSON.stringify(formData(event.target)) });
    const anketa = event.target.elements.anketa_number.value;
    event.target.elements.note_type.value = "Ախտորոշում";
    event.target.elements.complaints.value = "";
    event.target.elements.diagnosis.value = "";
    event.target.elements.prescription.value = "";
    event.target.elements.notes.value = "";
    updateDoctorDocumentFields();
    toast("Գրառումը պահպանվեց։");
    await loadDoctorNotes(anketa);
  } catch (error) {
    toast(error.message);
  }
});

function updateDoctorDocumentFields() {
  const form = $("#doctorNoteForm");
  const isResult = resultDocumentTypes.has(form.elements.note_type.value);
  form.elements.diagnosis.placeholder = "Ախտորոշում";
  form.elements.prescription.placeholder = isResult ? form.elements.note_type.value : "Նշանակում / դեղատոմս";
  form.elements.notes.placeholder = "Լրացուցիչ նշումներ";
}

$("#doctorNoteType").addEventListener("change", updateDoctorDocumentFields);

init().catch(error => toast(error.message));
