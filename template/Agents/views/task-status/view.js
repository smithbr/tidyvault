// Task status view: the one DataviewJS block the vault allows outside Home.md,
//   await dv.view("Agents/views/task-status", {status: "next-action", columns: "contexts,due"})
// A table of tasks with a <select> per row that sets the task's `status` in its frontmatter.
// Which tasks, every option and its default: Agents/body-sections.md, Task status view.

// Task frontmatter key order from Agents/schema.md (vault-lint FOLDER_FIELDS["Tasks"] and COMMON_TAIL):
// a key assigned in processFrontMatter lands last, so rebuild the object in schema order after each write.
const KEY_ORDER = ["title", "status", "priority", "due", "project", "area", "parent", "contexts", "assignee",
  "waiting_on", "waiting_since", "people", "resources", "blocked_by", "completed",
  "aliases", "tags", "sensitive", "public_places", "created"];
function reorder(fm) {
  const rank = k => { const i = KEY_ORDER.indexOf(k); return i < 0 ? KEY_ORDER.length : i; };
  const keys = Object.keys(fm).sort((a, b) => rank(a) - rank(b));  // stable: unknown keys keep their order, last
  const copy = {};
  for (const k of keys) copy[k] = fm[k];
  for (const k of keys) delete fm[k];
  for (const k of keys) fm[k] = copy[k];
}

const STATUSES = ["inbox", "queued", "next-action", "waiting-for", "done", "cancelled"];
const COLUMNS = {
  due: ["Due", t => t.due],
  priority: ["Priority", t => t.priority],
  contexts: ["Contexts", t => t.contexts],
  project: ["Project", t => t.project],
  area: ["Area", t => t.area],
  for: ["For", t => t.project ?? t.area],
  waiting_on: ["Who", t => t.waiting_on],
  waiting_since: ["Since", t => t.waiting_since],
  assignee: ["Agent", t => t.assignee],
  question: ["Question", t => t["question"]],
  created: ["Captured", t => t.created],
};
const PRIORITY_RANK = { urgent: 0, high: 1, med: 2, low: 3 };
const DEFAULT_COLUMNS = { Projects: "due,priority", Areas: "due", People: "due", Resources: "due", Tasks: "due", "": "project,due" };

const opts = input ?? {};
const list = v => v == null ? [] : Array.isArray(v) ? v : Array.isArray(v.values) ? v.values : [v];  // plain arrays, Dataview DataArrays, or one value; never Array.prototype.values
const first = v => list(v)[0];
const same = (a, b) => !!a && !!b && a.path === b.path;
const has = (v, l) => list(v).some(x => same(x, l));
const label = k => typeof k === "string" ? k : (k?.path ?? String(k)).split("/").pop().replace(/\.md$/, "");

const here = dv.current();
const folder = here?.archived_from ?? (here?.file?.folder ?? "").split("/")[0];
const link = here?.file?.link;
const scopes = {
  Projects: t => same(t.project, link),
  Areas: t => has(t.area, link),
  People: t => has(t.people, link) || has(t.assignee, link) || same(t.waiting_on, link),
  Resources: t => has(t.resources, link) || has(t.people, link) || has(t.assignee, link) || same(t.waiting_on, link),
  Tasks: t => t.file.path === here.file.path,
};
const inScope = scopes[folder] ?? (() => true);
const splitList = v => v ? v.split(",").map(s => s.trim()).filter(Boolean) : null;
const wanted = opts.status === "open" ? STATUSES.filter(s => s !== "done" && s !== "cancelled") : splitList(opts.status);
const priorities = splitList(opts.priority);
const hideRoles = opts.hide === "roles";
const onlyRoles = opts.assignee === "roles";
const onlyQuestions = opts.question === "true";
const today = dv.date("today");
const dueOk = (() => {
  const d = opts.due;
  if (!d) return () => true;
  if (d === "none") return t => !t.due;
  if (d === "today") return t => t.due && +t.due >= +today && +t.due < +today.plus({ days: 1 });
  const m = /^(\d+)d$/.exec(d);
  if (m) { const limit = today.plus({ days: Number(m[1]) }); return t => t.due && +t.due <= +limit; }
  return () => true;
})();
const isRoleTask = t => list(t.assignee).some(a => label(a).startsWith("role-"));
const sortKey = {
  due: t => `${t.due ?? "9999"} ${t.file.name}`,
  priority: t => `${PRIORITY_RANK[t.priority] ?? 9} ${t.file.name}`,
  created: t => `${t.created ?? "9999"} ${t.file.name}`,
  waiting_since: t => `${t.waiting_since ?? "9999"} ${t.file.name}`,
  name: t => t.file.name,
}[opts.sort] ?? (t => `${t.due ?? "9999"} ${t.file.name}`);
const cols = (opts.columns ?? DEFAULT_COLUMNS[folder] ?? DEFAULT_COLUMNS[""])
  .split(",").map(s => s.trim()).filter(s => COLUMNS[s]).map(s => COLUMNS[s]);

function statusSelect(t) {
  const wrap = document.createElement("span");
  wrap.className = "task-status";
  const sel = document.createElement("select");
  sel.className = "dropdown";
  for (const s of STATUSES) {
    const o = document.createElement("option");
    o.value = s;
    o.textContent = s;
    o.selected = s === t.status;
    sel.appendChild(o);
  }
  const note = document.createElement("small");
  note.className = "task-status-note";
  sel.onchange = async () => {
    const from = t.status, to = sel.value;
    sel.disabled = true;  // before the write, so a second change can't race it
    const file = app.vault.getAbstractFileByPath(t.file.path);
    if (!file) { note.textContent = "Moved"; return; }  // renamed or archived since the page rendered
    let changed = false;
    try {
      await app.fileManager.processFrontMatter(file, fm => {
        if (fm.status !== from) { changed = true; return; }  // someone changed it; don't overwrite
        const today = moment().format("YYYY-MM-DD");  // the day of the click, not of the render
        fm.status = to;
        if (to === "done" || to === "cancelled") fm.completed = today;
        else delete fm.completed;
        if (to === "waiting-for") { if (!fm.waiting_since) fm.waiting_since = today; }
        else if (from === "waiting-for") { delete fm.waiting_on; delete fm.waiting_since; }
        reorder(fm);
      });
      note.textContent = changed ? "Changed" : "Saved";
    } catch (e) {
      console.error("task-status view", t.file.path, e);
      note.textContent = "Error";
      sel.value = from;
      sel.disabled = false;
    }
  };
  wrap.append(sel, note);
  return wrap;
}

const tasks = dv.pages('"Tasks"')
  .where(t => inScope(t) && (!wanted || wanted.includes(t.status)))
  .where(t => !priorities || priorities.includes(t.priority))
  .where(dueOk)
  .where(t => !onlyQuestions || !!t["question"])
  .where(t => (!hideRoles || !isRoleTask(t)) && (!onlyRoles || isRoleTask(t)))
  .sort(sortKey);
const headers = ["", "Task", ...cols.map(c => c[0])];
const row = t => [statusSelect(t), t.file.link, ...cols.map(c => c[1](t))];

// A Project page with no `status` option: what remains, then what's done (Tasks/ and Archive/), with counts.
const CLOSED = ["done", "cancelled"];
const STATUS_RANK = { "next-action": 0, "waiting-for": 1, queued: 2, inbox: 3 };
if (folder === "Projects" && !opts.status) {
  const open = tasks.where(t => !CLOSED.includes(t.status))
    .sort(t => `${STATUS_RANK[t.status] ?? 9} ${sortKey(t)}`);
  const closed = dv.pages('"Tasks" or "Archive"')
    .where(t => CLOSED.includes(t.status) && same(t.project, link))
    .sort(t => `${t.completed ?? ""}`, "desc");
  const archivedStatus = t => { const s = document.createElement("span"); s.className = "task-status-closed"; s.textContent = t.status; return s; };
  dv.header(4, `Remaining (${open.length})`);
  if (open.length) dv.table(headers, open.map(row));
  else dv.paragraph("Nothing left.");
  dv.header(4, `Done (${closed.length})`);
  if (closed.length) dv.table(["", "Task", "Completed"], closed.map(t =>
    [t.file.folder.startsWith("Tasks") ? statusSelect(t) : archivedStatus(t), t.file.link, t.completed]));
} else if (opts.group === "project") {
  const groupOf = t => t.project ?? first(t.area) ?? "Unfiled";
  for (const g of tasks.groupBy(groupOf).sort(g => label(g.key).toLowerCase())) {
    dv.header(4, g.key);
    dv.table(headers, g.rows.map(row));
  }
} else {
  dv.table(headers, tasks.map(row));
}
