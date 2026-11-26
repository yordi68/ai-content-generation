const state = {
  projects: [],
  slug: null,
  project: null,
  shotId: null,
  tab: "shot",
  aspect: "shot_9x16",
  stream: null,
  poll: null,
  logLines: [],
  dirty: false,
};

const STAGE_ORDER = ["script", "narration", "keyframes", "shots", "music", "assemble"];
const STAGE_LABELS = {
  script: "Draft",
  narration: "Voice",
  keyframes: "Illustrations",
  shots: "Motion",
  music: "Score",
  assemble: "Assembly",
};
const STYLE_LABELS = {
  storybook: "Storybook",
  cinematic: "Cinematic",
  papercut: "Paper-cut",
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function pad(number) {
  return String(number).padStart(2, "0");
}

function fmtDuration(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return "—";
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

function shorten(text, limit) {
  const value = String(text ?? "");
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

function mediaUrl(slug, relative, mtime) {
  return `/api/projects/${encodeURIComponent(slug)}/media/${relative}?v=${mtime || 0}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = {};
  }
  if (!response.ok) {
    const detail = data.detail;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item.msg || JSON.stringify(item)).join("; ")
        : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}

let toastTimer = null;
function toast(message, isError = false) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.toggle("error", isError);
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.hidden = true; }, isError ? 9000 : 4500);
}

function isActive(job) {
  return Boolean(job && (job.status === "queued" || job.status === "running"));
}

/* ------------------------------------------------------------------ boot */

async function boot() {
  bindStatic();
  try {
    await loadProjects();
    const wanted = new URLSearchParams(location.search).get("film")
      || localStorage.getItem("studio:lastFilm");
    const slug = wanted && state.projects.some((item) => item.slug === wanted)
      ? wanted
      : null;
    if (slug) await selectProject(slug);
    else showWelcome();
  } catch (error) {
    toast(error.message, true);
  }
}

function bindStatic() {
  $("#projectSelect").addEventListener("change", (event) => selectProject(event.target.value));
  $("#newFilmBtn").addEventListener("click", showCreate);
  $("#welcomeNewBtn").addEventListener("click", showCreate);
  $("#welcomeShowcaseBtn").addEventListener("click", () => selectProject("showcase"));
  $("#createForm").addEventListener("submit", submitCreate);
  $$('input[name="mode"]').forEach((input) => {
    input.addEventListener("change", () => {
      const scriptMode = $('input[name="mode"]:checked').value === "script";
      $("#promptField").hidden = scriptMode;
      $("#scriptField").hidden = !scriptMode;
    });
  });
  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => setTab(tab.dataset.tab));
  });
}

async function loadProjects() {
  const data = await api("/api/projects");
  state.projects = data.projects;
  renderProjectSelect();
}

/* --------------------------------------------------------------- render */

function renderProjectSelect() {
  const select = $("#projectSelect");
  const options = state.projects
    .map((project) => {
      const title = project.meta.title || project.slug;
      const suffix = project.read_only ? " · showcase" : "";
      return `<option value="${esc(project.slug)}">${esc(title)}${suffix}</option>`;
    })
    .join("");
  const placeholder = state.slug ? "" : '<option value="" selected disabled>Choose a film…</option>';
  select.innerHTML = placeholder + options;
  if (state.slug) select.value = state.slug;
}

function renderSidebar() {
  const project = state.project;
  if (!project) {
    $("#filmCard").innerHTML = "";
    $("#shotList").innerHTML = "";
    $("#shotCount").textContent = "";
    return;
  }

  const film = project.film || {};
  const title = film.title || project.meta.title || project.slug;
  const voice = film.voice?.models?.[0] || "—";
  const style = STYLE_LABELS[project.meta.inputs?.style] || (film.style_block ? shorten(film.style_block, 34) : "—");
  const runtime = project.total_seconds ? fmtDuration(project.total_seconds) : "—";

  $("#filmCard").innerHTML = `
    <div class="film-title-row">
      <div>
        <h2>${esc(title)}</h2>
        ${film.title_local ? `<p class="film-local">${esc(film.title_local)}</p>` : ""}
      </div>
      ${project.read_only ? '<span class="badge">showcase</span>' : ""}
      ${project.film_stale && !project.read_only ? '<span class="badge warn">cuts need assembly</span>' : ""}
    </div>
    <dl class="film-meta">
      <div><dt>Runtime</dt><dd>${runtime}</dd></div>
      <div><dt>Shots</dt><dd>${project.shots.length || "—"}</dd></div>
      <div><dt>Voice</dt><dd title="${esc(voice)}">${esc(voice)}</dd></div>
      <div><dt>Style</dt><dd>${esc(style)}</dd></div>
    </dl>
    <div class="film-actions">
      ${project.storyboard_exists && !project.read_only ? '<button class="btn" id="generateBtn" type="button">Generate film</button>' : ""}
      ${project.read_only ? '<button class="btn" id="newFilmBtnSide" type="button">Make your own</button>' : '<button class="btn danger" id="deleteBtn" type="button">Delete</button>'}
    </div>`;

  const newFilmSide = $("#newFilmBtnSide");
  if (newFilmSide) newFilmSide.addEventListener("click", showCreate);

  const generate = $("#generateBtn");
  if (generate) {
    generate.addEventListener("click", async () => {
      try {
        await api(`/api/projects/${project.slug}/generate`, { method: "POST" });
        toast("Generating the film. You can keep editing while it runs.");
        openStream();
        startPoll();
        setTab("film");
        await refreshProject();
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  const remove = $("#deleteBtn");
  if (remove) {
    remove.addEventListener("click", async () => {
      if (!confirm(`Delete "${title}" and all of its generated media? This cannot be undone.`)) return;
      try {
        await api(`/api/projects/${project.slug}`, { method: "DELETE" });
        closeStream();
        stopPoll();
        state.slug = null;
        await loadProjects();
        if (state.projects[0]) await selectProject(state.projects[0].slug);
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  $("#shotCount").textContent = project.storyboard_exists
    ? `${project.shots.length} shots`
    : "drafting…";

  if (!project.storyboard_exists) {
    $("#shotList").innerHTML = `<li class="empty-list">Drafting the storyboard…</li>`;
    return;
  }

  $("#shotList").innerHTML = project.shots
    .map((shot) => {
      const keyframe = shot.artifacts.keyframe;
      const thumb = keyframe.exists
        ? `<img src="${mediaUrl(project.slug, `keyframes/shot_${pad(shot.id)}.jpg`, keyframe.mtime)}" alt="">`
        : `<span class="thumb-empty">${shot.id}</span>`;
      const chips = [
        shot.missing ? '<span class="chip warn">missing</span>' : "",
        shot.stale ? '<span class="chip">out of date</span>' : "",
      ].join("");
      const duration = shot.duration_s ? `${shot.duration_s.toFixed(1)}s` : "timing…";
      return `
        <li>
          <button class="shot-item ${state.shotId === shot.id ? "active" : ""}" data-shot="${shot.id}" type="button">
            <span class="thumb">${thumb}</span>
            <span class="shot-info">
              <strong>${shot.id}. ${esc(shorten(shot.subtitle, 44))}</strong>
              <span>${duration} ${chips}</span>
            </span>
          </button>
        </li>`;
    })
    .join("");

  $$(".shot-item").forEach((button) => {
    button.addEventListener("click", () => {
      state.shotId = Number(button.dataset.shot);
      state.dirty = false;
      setTab("shot");
      renderShot();
      renderSidebar();
    });
  });
}

function renderShot() {
  const project = state.project;
  const host = $("#shotTab");
  if (!project) {
    host.innerHTML = "";
    return;
  }

  if (!project.storyboard_exists) {
    const job = project.job || {};
    const failed = job.status === "failed";
    const message = failed
      ? `The storyboard could not be drafted: ${esc(job.error || "unknown error")}`
      : "Drafting the storyboard… the shots will appear here as soon as it is valid.";
    host.innerHTML = `
      <div class="empty-list">
        ${message}
        ${failed ? '<p style="margin-top:14px"><button class="btn primary" id="retryDraftBtn" type="button">Retry generation</button></p>' : ""}
      </div>`;
    const retry = $("#retryDraftBtn");
    if (retry) {
      retry.addEventListener("click", async () => {
        try {
          await api(`/api/projects/${project.slug}/draft`, { method: "POST" });
          toast("Retrying. The storyboard will appear when it validates.");
          openStream();
          startPoll();
          setTab("film");
          await refreshProject();
        } catch (error) {
          toast(error.message, true);
        }
      });
    }
    return;
  }

  if (!project.shots.length) {
    host.innerHTML = `<div class="empty-list">This storyboard has no shots.</div>`;
    return;
  }

  if (state.shotId == null) state.shotId = project.shots[0].id;
  const shot = project.shots.find((item) => item.id === state.shotId) || project.shots[0];
  state.shotId = shot.id;

  const film = project.film || {};
  const keyframe = shot.artifacts.keyframe;
  const narration = shot.artifacts.narration;
  const aspectFile = state.aspect === "shot_16x9" ? "16x9" : "9x16";
  const clip = shot.artifacts[state.aspect];
  const characters = Object.entries(film.characters || {});
  const readOnly = project.read_only;
  const jobActive = isActive(project.job);

  const videoHtml = clip.exists
    ? `<video controls playsinline preload="metadata" src="${mediaUrl(project.slug, `shots/shot_${pad(shot.id)}_${aspectFile}.mp4`, clip.mtime)}"></video>`
    : `<div class="empty-state">${jobActive ? "Rendering this shot…" : "No clip yet. Save a change or press Generate film."}</div>`;

  const imageHtml = keyframe.exists
    ? `<img src="${mediaUrl(project.slug, `keyframes/shot_${pad(shot.id)}.jpg`, keyframe.mtime)}" alt="Keyframe for shot ${shot.id}">`
    : `<div class="empty-state">${jobActive ? "Illustrating…" : "No illustration yet."}</div>`;

  const audioHtml = narration.exists
    ? `<audio controls preload="none" src="${mediaUrl(project.slug, `narration/shot_${pad(shot.id)}.wav`, narration.mtime)}"></audio>`
    : `<div class="empty-state">${jobActive ? "Recording…" : "No narration yet."}</div>`;

  const characterHtml = characters.length
    ? characters
        .map(([key, description]) => `
          <label title="${esc(description)}">
            <input type="checkbox" name="f-char" value="${esc(key)}" ${shot.characters.includes(key) ? "checked" : ""} ${readOnly ? "disabled" : ""}>
            ${esc(key)}
          </label>`)
        .join("")
    : `<span class="muted">No characters defined for this film.</span>`;

  const motion = shot.motion || { type: "push-in", amount: "slow" };
  const motionTypes = ["push-in", "pull-out", "pan-left", "pan-right", "none"];
  const amounts = ["slow", "gentle", "none"];

  host.innerHTML = `
    <div class="shot-head">
      <div>
        <h2>Shot ${shot.id} of ${project.shots.length}</h2>
        <p class="reason">${esc(shot.reason || "")}</p>
      </div>
      <span class="meta">${shot.duration_s ? `${shot.duration_s.toFixed(1)}s` : "timing pending"}${shot.stale ? " · out of date" : ""}</span>
    </div>

    ${readOnly ? '<div class="notice">This is the graded showcase film. It is read-only: create a new film to draft, edit and generate your own.</div>' : ""}

    <div class="preview-grid">
      <div class="preview">
        <div class="preview-head">
          <span>Moving shot</span>
          <span class="aspect-toggle">
            <button type="button" data-aspect="shot_9x16" class="${state.aspect === "shot_9x16" ? "active" : ""}">9:16</button>
            <button type="button" data-aspect="shot_16x9" class="${state.aspect === "shot_16x9" ? "active" : ""}">16:9</button>
          </span>
        </div>
        ${videoHtml}
      </div>
      <div class="preview">
        <div class="preview-head"><span>Illustration</span></div>
        ${imageHtml}
        <div class="preview-head" style="margin-top:6px"><span>Narration</span></div>
        ${audioHtml}
      </div>
    </div>

    <div class="edit-grid">
      <label class="field wide">
        <span>Narration (spoken)</span>
        <textarea id="f-narration" rows="3" ${readOnly ? "disabled" : ""}>${esc(shot.narration)}</textarea>
      </label>
      <label class="field wide">
        <span>English subtitle</span>
        <textarea id="f-subtitle" rows="2" ${readOnly ? "disabled" : ""}>${esc(shot.subtitle)}</textarea>
      </label>
      <label class="field wide">
        <span>Picture prompt</span>
        <textarea id="f-picture" rows="3" ${readOnly ? "disabled" : ""}>${esc(shot.picture)}</textarea>
      </label>
      <div class="field wide">
        <span>Characters in frame</span>
        <div class="char-row">${characterHtml}</div>
      </div>
      <label class="field">
        <span>Camera motion</span>
        <select id="f-motion-type" ${readOnly ? "disabled" : ""}>
          ${motionTypes.map((type) => `<option value="${type}" ${motion.type === type ? "selected" : ""}>${type}</option>`).join("")}
        </select>
      </label>
      <label class="field">
        <span>Motion amount</span>
        <select id="f-motion-amount" ${readOnly ? "disabled" : ""}>
          ${amounts.map((amount) => `<option value="${amount}" ${motion.amount === amount ? "selected" : ""}>${amount}</option>`).join("")}
        </select>
      </label>
      <label class="field">
        <span>Seed</span>
        <input id="f-seed" type="number" min="0" step="1" value="${shot.seed}" ${readOnly ? "disabled" : ""}>
      </label>
      <label class="field">
        <span>Why this shot exists</span>
        <input id="f-reason" value="${esc(shot.reason)}" ${readOnly ? "disabled" : ""}>
      </label>
    </div>

    <div class="save-row">
      <p class="hint">
        Saving regenerates this shot's media only. Rebuild the three finished
        cuts with <strong>Assemble full film</strong> when the shots look right.
      </p>
      ${readOnly ? "" : '<button class="btn primary" id="saveShotBtn" type="button">Save &amp; regenerate</button>'}
    </div>`;

  $$("[data-aspect]").forEach((button) => {
    button.addEventListener("click", () => {
      state.aspect = button.dataset.aspect;
      renderShot();
    });
  });

  $$("#shotTab input, #shotTab textarea, #shotTab select").forEach((input) => {
    input.addEventListener("input", () => { state.dirty = true; });
  });

  const save = $("#saveShotBtn");
  if (save) save.addEventListener("click", saveShot);
}

function stageState(stage, job) {
  if (!job || !job.status || job.status === "idle") return "";
  const list = job.stages || [];
  const current = job.stage;
  if (job.status === "done") return "done";
  if (job.status === "failed") {
    if (stage === current) return "failed";
    if (current && list.includes(stage) && list.indexOf(stage) < list.indexOf(current)) return "done";
    return "";
  }
  if (job.status === "running") {
    if (stage === current) return "running";
    if (current && list.includes(stage) && list.indexOf(stage) < list.indexOf(current)) return "done";
  }
  return "";
}

function renderFilm() {
  const project = state.project;
  const host = $("#filmTab");
  if (!project) {
    host.innerHTML = "";
    return;
  }

  const job = project.job || {};
  const stages = job.stages && job.stages.length
    ? job.stages
    : ["narration", "keyframes", "shots", "music", "assemble"];
  const ordered = [...stages].sort((a, b) => STAGE_ORDER.indexOf(a) - STAGE_ORDER.indexOf(b));

  const chips = ordered
    .map((stage) => `<span class="stage-pill ${stageState(stage, job)}"><span class="pip"></span>${STAGE_LABELS[stage] || stage}</span>`)
    .join("");

  const outputCard = (label, file, meta, note) => `
    <div class="output-card">
      <h3>${label}</h3>
      <span class="muted">${meta.exists ? `${(meta.bytes / 1048576).toFixed(1)} MB · ${note}` : "not rendered yet"}</span>
      <a class="${meta.exists ? "" : "disabled"}" href="${mediaUrl(project.slug, file, meta.mtime)}" download="${project.slug}-${file}">Download</a>
    </div>`;

  const running = isActive(job);
  const statusLine = job.error
    ? `<div class="notice">${esc(job.error)}</div>`
    : job.status === "running"
      ? `<p class="muted">Working on ${esc(STAGE_LABELS[job.stage] || job.stage || "the film")}…</p>`
      : job.status === "done"
        ? `<p class="muted">Last build finished ${esc(job.finished_at || "")}.</p>`
        : `<p class="muted">No build running. Generate the film or edit a shot.</p>`;

  const staleNotice = project.film_stale
    ? '<div class="notice">Shot edits are saved. Press <strong>Assemble full film</strong> to rebuild the three cuts.</div>'
    : "";
  const shotsDirty = (project.shots || []).some((shot) => shot.stale);

  host.innerHTML = `
    <div class="shot-head">
      <div>
        <h2>${esc(project.film?.title || project.meta.title || project.slug)}</h2>
        <p class="reason">${project.total_seconds ? `${project.total_seconds.toFixed(1)}s including the end card` : "Runtime is set once narration exists."}</p>
      </div>
      <span class="meta">${project.read_only ? "showcase" : "workspace"}</span>
    </div>

    <p class="section-kicker">Last build</p>
    <div class="stage-strip">${chips}</div>
    ${statusLine}
    ${staleNotice}

    <div class="output-grid">
      ${outputCard("Vertical 9:16", "film_9x16.mp4", project.films.film_9x16, "phone")}
      ${outputCard("Horizontal 16:9", "film_16x9.mp4", project.films.film_16x9, "TV")}
      ${outputCard("Radio cut", "radio_cut.mp4", project.films.radio_cut, "voice + score")}
    </div>

    <div class="film-actions-row">
      ${project.storyboard_exists ? `<button class="btn ${project.film_stale ? "primary" : ""}" id="assembleBtn" type="button" ${running || shotsDirty ? "disabled" : ""}>Assemble full film</button>` : ""}
      ${project.storyboard_exists && !project.read_only ? '<button class="btn" id="generateBtnFilm" type="button">Generate everything</button>' : ""}
      ${running ? '<button class="btn danger" id="cancelBtn" type="button">Cancel</button>' : ""}
      ${project.storyboard_exists ? `<a class="btn ghost" href="/api/projects/${esc(project.slug)}/storyboard" download>Download storyboard.json</a>` : ""}
      ${project.read_only ? "" : '<button class="btn ghost" id="newFilmBtnFilm" type="button">New film</button>'}
    </div>

    <h3 style="margin-top:24px">Build log</h3>
    <div class="log" id="logBox"></div>`;

  const logBox = $("#logBox");
  logBox.textContent = state.logLines.slice(-300).join("\n");
  logBox.scrollTop = logBox.scrollHeight;

  const assemble = $("#assembleBtn");
  if (assemble) {
    assemble.addEventListener("click", async () => {
      try {
        await api(`/api/projects/${project.slug}/assemble`, { method: "POST" });
        toast("Assembling the three cuts.");
        openStream();
        startPoll();
        await refreshProject();
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  const generate = $("#generateBtnFilm");
  if (generate) {
    generate.addEventListener("click", async () => {
      try {
        await api(`/api/projects/${project.slug}/generate`, { method: "POST" });
        toast("Generating the film.");
        openStream();
        startPoll();
        await refreshProject();
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  const cancel = $("#cancelBtn");
  if (cancel) {
    cancel.addEventListener("click", async () => {
      try {
        await api(`/api/projects/${project.slug}/cancel`, { method: "POST" });
        toast("Cancelling after the current step.");
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  const newFilm = $("#newFilmBtnFilm");
  if (newFilm) newFilm.addEventListener("click", showCreate);
}

/* ------------------------------------------------------------- actions */

async function selectProject(slug) {
  closeStream();
  stopPoll();
  state.slug = slug;
  try { localStorage.setItem("studio:lastFilm", slug); } catch (error) { /* private mode */ }
  state.shotId = null;
  state.aspect = "shot_9x16";
  state.dirty = false;
  state.logLines = [];

  await refreshProject();
  try {
    const data = await api(`/api/projects/${slug}/log`);
    state.logLines = data.log ? data.log.split("\n").slice(-300) : [];
  } catch (error) {
    state.logLines = [];
  }

  $("#welcome").hidden = true;
  $("#createPanel").hidden = true;
  $("#projectPanel").hidden = false;
  setTab("shot");
  renderAll();
  history.replaceState(null, "", `?film=${encodeURIComponent(slug)}`);

  if (isActive(state.project?.job)) {
    openStream();
    startPoll();
  }
}

async function refreshProject() {
  if (!state.slug) return;
  state.project = await api(`/api/projects/${state.slug}`);
  renderProjectSelect();
  renderSidebar();
  renderFilm();
  if (!state.dirty) renderShot();
}

function renderAll() {
  renderProjectSelect();
  renderSidebar();
  renderShot();
  renderFilm();
}

async function saveShot() {
  const project = state.project;
  if (!project) return;
  const button = $("#saveShotBtn");
  if (button) {
    button.disabled = true;
    button.textContent = "Saving…";
  }
  const payload = {
    narration: $("#f-narration").value.trim(),
    subtitle: $("#f-subtitle").value.trim(),
    picture: $("#f-picture").value.trim(),
    characters: $$('input[name="f-char"]:checked').map((input) => input.value),
    motion: { type: $("#f-motion-type").value, amount: $("#f-motion-amount").value },
    seed: Number($("#f-seed").value),
    reason: $("#f-reason").value.trim(),
  };
  try {
    const result = await api(`/api/projects/${project.slug}/shots/${state.shotId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    state.dirty = false;
    await refreshProject();
    if (result.stages.length) {
      const labels = result.stages.map((stage) => STAGE_LABELS[stage] || stage).join(" → ");
      toast(`Saved. Regenerating ${labels}. Press Assemble full film to rebuild the cuts.`);
      openStream();
      startPoll();
      setTab("film");
    } else if (state.project.film_stale) {
      toast("Saved. Press Assemble full film to rebuild the cuts.");
    } else {
      toast("Saved. No generated media needed to change.");
    }
  } catch (error) {
    toast(error.message, true);
    if (button) {
      button.disabled = false;
      button.textContent = "Save & regenerate";
    }
  }
}

async function submitCreate(event) {
  event.preventDefault();
  const button = $("#createBtn");
  button.disabled = true;
  button.textContent = "Creating…";
  const mode = $('input[name="mode"]:checked').value;
  const body = {
    title: $("#titleInput").value.trim(),
    mode,
    story_prompt: mode === "prompt" ? $("#promptInput").value : "",
    script: mode === "script" ? $("#scriptInput").value : "",
    language: $("#languageInput").value,
    style: $("#styleInput").value,
  };
  try {
    const result = await api("/api/projects", { method: "POST", body: JSON.stringify(body) });
    $("#createForm").reset();
    $("#promptField").hidden = false;
    $("#scriptField").hidden = true;
    await loadProjects();
    await selectProject(result.slug);
    toast("Drafting your storyboard…");
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "Create film";
  }
}

function showCreate() {
  closeStream();
  stopPoll();
  state.dirty = false;
  $("#welcome").hidden = true;
  $("#projectPanel").hidden = true;
  $("#createPanel").hidden = false;
  $("#promptInput").focus();
}

function showWelcome() {
  $("#welcome").hidden = false;
  $("#createPanel").hidden = true;
  $("#projectPanel").hidden = true;
}

function setTab(name) {
  state.tab = name;
  $$(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
  $("#shotTab").hidden = name !== "shot";
  $("#filmTab").hidden = name !== "film";
}

/* ---------------------------------------------------------------- stream */

function openStream() {
  if (!state.slug) return;
  closeStream();
  const stream = new EventSource(`/api/projects/${state.slug}/events`);
  state.stream = stream;
  stream.onmessage = (event) => {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch (error) {
      return;
    }
    handleEvent(payload);
  };
}

function closeStream() {
  if (state.stream) {
    state.stream.close();
    state.stream = null;
  }
}

async function handleEvent(event) {
  if (event.type === "log") {
    appendLog(event.line);
    return;
  }
  if (event.type === "stage") {
    appendLog(`— ${STAGE_LABELS[event.stage] || event.stage} ${event.status === "start" ? "started" : "done"}`);
    renderFilm();
    return;
  }
  if (event.type === "refresh") {
    await refreshProject();
    return;
  }
  if (event.type === "done") {
    appendLog("— film ready");
    toast("Film ready.");
    stopPoll();
    closeStream();
    await refreshProject();
    return;
  }
  if (event.type === "failed") {
    appendLog(`— failed: ${event.error}`);
    toast(event.error, true);
    stopPoll();
    closeStream();
    await refreshProject();
    return;
  }
  if (event.type === "cancelled") {
    appendLog("— cancelled");
    toast("Build cancelled.");
    stopPoll();
    closeStream();
    await refreshProject();
    return;
  }
  if (event.type === "stream_end" || event.type === "idle") {
    closeStream();
  }
}

function appendLog(line) {
  state.logLines.push(line);
  if (state.logLines.length > 500) state.logLines.splice(0, state.logLines.length - 500);
  const box = $("#logBox");
  if (box) {
    box.textContent = state.logLines.slice(-300).join("\n");
    box.scrollTop = box.scrollHeight;
  }
}

function startPoll() {
  stopPoll();
  state.poll = setInterval(async () => {
    try {
      await refreshProject();
    } catch (error) {
      /* the stream will report the real failure */
    }
    if (!isActive(state.project?.job)) stopPoll();
  }, 4000);
}

function stopPoll() {
  if (state.poll) {
    clearInterval(state.poll);
    state.poll = null;
  }
}

boot();
