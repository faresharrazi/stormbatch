<script setup>
import { computed, ref } from "vue";
import ApiKeyInput from "./components/ApiKeyInput.vue";
import FileUpload from "./components/FileUpload.vue";
import JobResults from "./components/JobResults.vue";
import PreviewTable from "./components/PreviewTable.vue";
import SessionIdsInput from "./components/SessionIdsInput.vue";
import livestormIcon from "../assets/Icon-Livestorm-Primary.png";

const apiKey = ref("");
const sessionIds = ref("");
const selectedFile = ref(null);
const preview = ref(null);
const jobs = ref([]);
const duplicateEmails = ref([]);
const errorMessage = ref("");
const successMessage = ref("");
const isPreviewLoading = ref(false);
const isSubmitting = ref(false);
const poller = ref(null);
const rowResults = ref([]);
const hasSubmittedJobs = ref(false);
const retryingSessions = ref({});
const totalSessionCount = ref(0);
const createdSessionCount = ref(0);

const parsedSessionIds = computed(() =>
  sessionIds.value
    .split(/[\n,]/)
    .map((value) => value.trim())
    .filter(Boolean),
);

const emailColumn = computed(() => {
  if (!preview.value) {
    return "";
  }
  return preview.value.headers.find(
    (header) => preview.value.normalized_headers[header] === "email",
  ) || "";
});

const hasEmailColumn = computed(() => Boolean(emailColumn.value));

const autoMapping = computed(() => {
  if (!preview.value) {
    return {};
  }
  return Object.fromEntries(
    preview.value.headers.map((header) => [
      header,
      preview.value.normalized_headers[header],
    ]),
  );
});

const mappedAttributePreview = computed(() =>
  Object.entries(autoMapping.value).map(([column, attributeId]) => ({
    column,
    attributeId,
  })),
);

const finishedJobs = computed(() =>
  jobs.value.filter((job) =>
    ["ended", "failed", "completed"].includes(String(job.status).toLowerCase()),
  ).length,
);

const progressPercent = computed(() => {
  if (isSubmitting.value) {
    if (!totalSessionCount.value) {
      return 0;
    }
    return Math.round((createdSessionCount.value / totalSessionCount.value) * 100);
  }
  const total = totalSessionCount.value || jobs.value.length;
  if (!total) {
    return 0;
  }
  return Math.round((finishedJobs.value / total) * 100);
});

const isPollingJobs = computed(() =>
  jobs.value.some(
    (job) => !["ended", "failed", "completed"].includes(String(job.status).toLowerCase()),
  ),
);

const registrationSummary = computed(() => {
  const taskResults = jobs.value.flatMap((job) => job.tasks || []);
  const failedTasks = taskResults.filter((task) => {
    const status = task?.attributes?.status || task?.status;
    return String(status).toLowerCase() === "failed";
  }).length;

  return {
    jobs: totalSessionCount.value || jobs.value.length || (isSubmitting.value ? parsedSessionIds.value.length : 0),
    created: createdSessionCount.value,
    finished: finishedJobs.value,
    totalTasks: taskResults.length,
    failedTasks,
  };
});

const progressTitle = computed(() => {
  if (isSubmitting.value) {
    return "Creating Livestorm jobs one session at a time...";
  }
  return isPollingJobs.value ? "Livestorm is processing..." : "Batch complete";
});

function resetMessages() {
  errorMessage.value = "";
  successMessage.value = "";
}

function onFileSelected(file) {
  selectedFile.value = file;
  preview.value = null;
  jobs.value = [];
  rowResults.value = [];
  hasSubmittedJobs.value = false;
  duplicateEmails.value = [];
  stopPolling();
  resetMessages();
}

function startNewBatch() {
  sessionIds.value = "";
  selectedFile.value = null;
  preview.value = null;
  jobs.value = [];
  rowResults.value = [];
  hasSubmittedJobs.value = false;
  duplicateEmails.value = [];
  retryingSessions.value = {};
  totalSessionCount.value = 0;
  createdSessionCount.value = 0;
  isSubmitting.value = false;
  isPreviewLoading.value = false;
  totalSessionCount.value = 0;
  createdSessionCount.value = 0;
  stopPolling();
  resetMessages();
}

async function loadPreview() {
  if (!selectedFile.value) {
    errorMessage.value = "Please choose an .xlsx or .csv file first.";
    return;
  }

  resetMessages();
  isPreviewLoading.value = true;

  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);

    const response = await fetch("/api/preview", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Preview failed");
    }

    preview.value = data;
    const detectedEmailColumn = data.headers.find(
      (header) => data.normalized_headers[header] === "email",
    );
    duplicateEmails.value = detectedEmailColumn
      ? data.duplicate_email_columns[detectedEmailColumn] || []
      : [];
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isPreviewLoading.value = false;
  }
}

function stopPolling() {
  if (poller.value) {
    clearInterval(poller.value);
    poller.value = null;
  }
}

function attachRowResults(tasks) {
  return tasks.map((task, index) => ({
    ...task,
    row_result: rowResults.value[index] || {
      row_number: index + 2,
      email: "",
      fields: [],
    },
  }));
}

function jobFailedTasks(job) {
  return (job.tasks || []).filter((task) => {
    const status = task?.attributes?.status || task?.status;
    return String(status).toLowerCase() === "failed";
  });
}

function wait(milliseconds) {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}

async function pollJobStatuses() {
  const activeJobs = jobs.value.filter((job) =>
    !["ended", "failed", "completed"].includes(String(job.status).toLowerCase()),
  );

  if (!activeJobs.length) {
    stopPolling();
    return;
  }

  await Promise.all(
    activeJobs.map(async (job) => {
      const response = await fetch("/api/job-status", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          api_key: apiKey.value,
          session_id: job.session_id,
          job_id: job.job_id,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        job.status = "failed";
        job.error = data.detail || "Failed to fetch job status";
        return;
      }

      job.status = data.status;
      job.tasks = attachRowResults(data.tasks || []);
      job.raw = data.raw || {};
    }),
  );

  const finished = jobs.value.every((job) =>
    ["ended", "failed", "completed"].includes(String(job.status).toLowerCase()),
  );
  if (finished) {
    stopPolling();
    successMessage.value = "All Livestorm jobs finished.";
  }
}

async function retryFailedRows(job) {
  let failedRegistrants = jobFailedTasks(job)
    .map((task) => task.row_result)
    .filter((row) => row?.email);

  if (!failedRegistrants.length && String(job.status).toLowerCase() === "failed") {
    failedRegistrants = rowResults.value;
  }

  if (!failedRegistrants.length) {
    job.error = "No row details were available to diagnose with single registration.";
    return;
  }

  retryingSessions.value = {
    ...retryingSessions.value,
    [job.session_id]: true,
  };

  try {
    const response = await fetch("/api/retry-failed", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api_key: apiKey.value,
        session_id: job.session_id,
        registrants: failedRegistrants,
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Retry failed");
    }

    job.retry_results = data.results || [];
  } catch (error) {
    job.error = error.message;
  } finally {
    retryingSessions.value = {
      ...retryingSessions.value,
      [job.session_id]: false,
    };
  }
}

async function submitRegistration() {
  resetMessages();

  if (!selectedFile.value) {
    errorMessage.value = "Please upload an .xlsx or .csv file.";
    return;
  }
  if (!preview.value) {
    errorMessage.value = "Preview the file before submitting.";
    return;
  }
  if (!parsedSessionIds.value.length) {
    errorMessage.value = "Session IDs must not be empty.";
    return;
  }
  if (!hasEmailColumn.value) {
    errorMessage.value = "The file must include an Email column.";
    return;
  }
  if (!apiKey.value.trim()) {
    errorMessage.value = "Livestorm API key is required.";
    return;
  }

  isSubmitting.value = true;
  jobs.value = [];
  hasSubmittedJobs.value = false;
  totalSessionCount.value = parsedSessionIds.value.length;
  createdSessionCount.value = 0;
  stopPolling();

  try {
    for (const sessionId of parsedSessionIds.value) {
      const formData = new FormData();
      formData.append("api_key", apiKey.value.trim());
      formData.append("session_ids", sessionId);
      formData.append("mapping", JSON.stringify(autoMapping.value));
      formData.append("file", selectedFile.value);

      const response = await fetch("/api/register", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) {
        jobs.value.push({
          session_id: sessionId,
          job_id: "not-created",
          status: "failed",
          tasks: [],
          raw: {},
          error: data.detail || "Registration failed",
        });
      } else {
        const [createdJob] = data.jobs;
        jobs.value.push({
          ...createdJob,
          tasks: [],
          raw: {},
          error: "",
        });
        if (!rowResults.value.length) {
          rowResults.value = data.row_results || [];
        }
        duplicateEmails.value = data.duplicate_emails || [];
      }

      createdSessionCount.value += 1;
      if (createdSessionCount.value < totalSessionCount.value) {
        await wait(900);
      }
    }

    hasSubmittedJobs.value = true;

    if (duplicateEmails.value.length) {
      successMessage.value =
        "Jobs created. Duplicate emails were detected in the file, so Livestorm may reject some rows.";
    } else {
      successMessage.value = "Jobs created. Polling Livestorm for updates.";
    }

    if (jobs.value.some((job) => !["ended", "failed", "completed"].includes(String(job.status).toLowerCase()))) {
      poller.value = setInterval(pollJobStatuses, 2500);
      await pollJobStatuses();
    }
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <main class="page-shell">
    <section class="hero">
      <div>
        <div class="brand-lockup">
          <img :src="livestormIcon" alt="Livestorm" />
          <div>
            <p class="eyebrow">StormBatch</p>
            <span>Powered by Livestorm workflows</span>
          </div>
        </div>
        <h1>Turn an Excel sheet into Livestorm session registrants.</h1>
      </div>
      <div class="hero-card">
        <span>Email required</span>
        <strong>Everything else is optional prefill data.</strong>
        <p>Attendees can complete other required event fields before joining.</p>
      </div>
    </section>

    <section class="workflow-grid">
      <div class="panel step-panel">
        <div class="step-label">Step 1</div>
        <ApiKeyInput v-model="apiKey" />
        <SessionIdsInput v-model="sessionIds" :count="parsedSessionIds.length" />
      </div>
      <div class="panel step-panel">
        <div class="step-label">Step 2</div>
        <FileUpload
          :selected-file="selectedFile"
          :loading="isPreviewLoading"
          :preview-ready="Boolean(preview)"
          @file-selected="onFileSelected"
          @preview="loadPreview"
        />
      </div>
    </section>

    <section v-if="errorMessage" class="notice error">{{ errorMessage }}</section>
    <section v-if="successMessage" class="notice success">{{ successMessage }}</section>

    <section v-if="preview" class="panel preview-panel">
      <div class="panel-header">
        <div>
          <span class="step-label">Step 3</span>
          <h2>Preview registrants</h2>
          <p>
            {{ preview.row_count }} row(s), {{ preview.headers.length }} column(s).
            We automatically use normalized column names as Livestorm attribute IDs.
          </p>
        </div>
        <div class="preview-statuses">
          <div class="status-pill" :class="{ ok: hasEmailColumn, error: !hasEmailColumn }">
            {{ hasEmailColumn ? `Email column: ${emailColumn}` : "Email column missing" }}
          </div>
          <div v-if="duplicateEmails.length" class="warning-pill">
            Duplicate emails: {{ duplicateEmails.join(", ") }}
          </div>
        </div>
      </div>

      <div class="attribute-preview">
        <span
          v-for="item in mappedAttributePreview"
          :key="item.column"
          class="attribute-chip"
        >
          {{ item.column }} -> {{ item.attributeId }}
        </span>
      </div>
      <PreviewTable :headers="preview.headers" :rows="preview.preview_rows" />

      <div class="cta-card">
        <div>
          <span class="step-label">Step 4</span>
          <h2>Ready to batch register?</h2>
          <p>
            This will create {{ parsedSessionIds.length }} Livestorm job(s) for
            {{ preview.row_count }} registrant row(s).
          </p>
        </div>
        <div class="cta-actions">
          <button
            class="primary-button"
            :disabled="isSubmitting || isPollingJobs"
            @click="submitRegistration"
          >
            {{ isSubmitting ? "Creating jobs..." : "Batch register now" }}
          </button>
        </div>
      </div>
    </section>

    <section v-if="jobs.length || isSubmitting" class="panel progress-panel">
      <div class="panel-header">
        <div>
          <span class="step-label">Job progress</span>
          <h2>{{ progressTitle }}</h2>
          <p>
            <template v-if="isSubmitting">
              {{ registrationSummary.created }} of {{ registrationSummary.jobs }} job(s)
              created.
            </template>
            <template v-else>
              {{ registrationSummary.finished }} of {{ registrationSummary.jobs }} job(s)
              finished.
            </template>
          </p>
        </div>
        <strong class="progress-percent">{{ progressPercent }}%</strong>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
      </div>
      <div class="progress-stats">
        <span>{{ registrationSummary.totalTasks }} task result(s)</span>
        <span>{{ registrationSummary.failedTasks }} failed task(s)</span>
      </div>
    </section>

    <section v-if="hasSubmittedJobs && !isPollingJobs && jobs.length" class="confirmation-card">
      <div>
        <span class="confirmation-icon">OK</span>
      </div>
      <div>
        <h2>Livestorm jobs confirmed</h2>
        <p>
          {{ registrationSummary.jobs }} job(s) finished. Review per-session and
          per-row outcomes below.
        </p>
      </div>
      <button class="new-batch-button" type="button" @click="startNewBatch">
        New Batch
      </button>
    </section>

    <section v-if="jobs.length" class="panel">
      <div class="panel-header results-header">
        <div>
          <span class="step-label">Results</span>
          <h2>Job details</h2>
        </div>
      </div>
      <JobResults
        :jobs="jobs"
        :retrying-sessions="retryingSessions"
        @retry-failed="retryFailedRows"
      />
    </section>
  </main>
</template>

<style>
:root {
  --storm-ink: #12262b;
  --storm-ink-soft: #21383e;
  --storm-mint: #00e5a8;
  --storm-mint-soft: #d8fff4;
  --storm-sand: #fbf7ef;
  --storm-line: rgba(18, 38, 43, 0.14);
  font-family: "Avenir Next", "Segoe UI", sans-serif;
  color: var(--storm-ink);
  background:
    radial-gradient(circle at 8% 0%, rgba(0, 229, 168, 0.2), transparent 28%),
    radial-gradient(circle at 92% 10%, rgba(18, 38, 43, 0.1), transparent 26%),
    linear-gradient(135deg, #fbf7ef 0%, #f4fbf8 48%, #edf7f4 100%);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
}

.page-shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 36px 16px 56px;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 24px;
  align-items: end;
  margin-bottom: 24px;
}

.brand-lockup {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 18px;
}

.brand-lockup img {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  box-shadow: 0 10px 24px rgba(18, 38, 43, 0.12);
}

.brand-lockup span {
  display: block;
  color: #607075;
  font-size: 0.86rem;
  font-weight: 700;
}

.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.75rem;
  color: var(--storm-ink);
  font-weight: 800;
}

.hero h1 {
  max-width: 760px;
  margin: 0;
  font-size: clamp(1.95rem, 4vw, 3.35rem);
  line-height: 1.04;
  letter-spacing: -0.045em;
}

.intro {
  max-width: 760px;
  color: #4f6268;
  font-size: 1.05rem;
  line-height: 1.7;
}

.hero-card,
.confirmation-card,
.cta-card {
  border: 1px solid var(--storm-line);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(216, 255, 244, 0.82)),
    repeating-linear-gradient(45deg, rgba(18, 38, 43, 0.035) 0 8px, transparent 8px 16px);
  border-radius: 24px;
  padding: 22px;
  box-shadow: 0 18px 50px rgba(18, 38, 43, 0.08);
}

.hero-card span,
.step-label {
  display: inline-flex;
  width: fit-content;
  margin-bottom: 8px;
  color: var(--storm-ink);
  background: var(--storm-mint-soft);
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-card strong {
  display: block;
  font-size: 1.15rem;
}

.hero-card p,
.cta-card p {
  margin-bottom: 0;
  color: #64748b;
}

.workflow-grid {
  display: grid;
  grid-template-columns: 0.95fr 1.05fr;
  gap: 18px;
  align-items: stretch;
}

.panel {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--storm-line);
  border-radius: 24px;
  padding: 22px;
  margin-bottom: 18px;
  box-shadow: 0 18px 50px rgba(18, 38, 43, 0.07);
  backdrop-filter: blur(14px);
}

.step-panel {
  min-height: 100%;
}

.preview-panel {
  border-color: rgba(18, 38, 43, 0.22);
  margin-top: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.panel-header h2,
.cta-card h2,
.confirmation-card h2 {
  margin: 0 0 6px;
  letter-spacing: -0.03em;
}

.panel-header p,
.confirmation-card p {
  margin: 0;
  color: #6b7280;
}

.notice {
  margin-bottom: 18px;
  padding: 14px 16px;
  border-radius: 16px;
  font-weight: 700;
}

.notice.error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.notice.success {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.warning-pill {
  background: #fff7ed;
  color: #c2410c;
  padding: 10px 12px;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 800;
}

.preview-statuses {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.status-pill,
.attribute-chip {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border-radius: 999px;
  padding: 10px 12px;
  font-size: 0.9rem;
  font-weight: 800;
}

.status-pill.ok {
  color: #12262b;
  background: #d8fff4;
}

.status-pill.error {
  color: #b91c1c;
  background: #fef2f2;
}

.attribute-preview {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.attribute-chip {
  color: #4f6268;
  background: rgba(18, 38, 43, 0.06);
  border: 1px solid var(--storm-line);
  font-size: 0.82rem;
}

.cta-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 18px;
  align-items: center;
  margin-top: 20px;
}

.primary-button {
  width: 100%;
  border: none;
  border-radius: 18px;
  padding: 16px 18px;
  font-size: 1rem;
  font-weight: 900;
  color: white;
  background: linear-gradient(135deg, var(--storm-ink), var(--storm-ink-soft));
  cursor: pointer;
  box-shadow: 0 14px 28px rgba(18, 38, 43, 0.24);
}

.primary-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  box-shadow: none;
}

.progress-panel {
  border-color: rgba(18, 38, 43, 0.2);
}

.progress-percent {
  font-size: 2rem;
  color: var(--storm-ink);
}

.progress-track {
  height: 14px;
  overflow: hidden;
  border-radius: 999px;
  background: #e2e8f0;
}

.progress-fill {
  height: 100%;
  min-width: 8px;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--storm-mint), #3bd5bd, var(--storm-ink));
  transition: width 0.4s ease;
}

.progress-stats {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 12px;
  color: #64748b;
  font-weight: 700;
}

.confirmation-card {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.confirmation-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--storm-ink);
  color: white;
  font-weight: 900;
  font-size: 1.4rem;
}

.new-batch-button {
  flex: 0 0 auto;
  border: 1px solid var(--storm-ink);
  border-radius: 999px;
  padding: 12px 16px;
  color: var(--storm-ink);
  background: white;
  font-weight: 900;
  cursor: pointer;
}

.new-batch-button:hover {
  color: white;
  background: var(--storm-ink);
}

.results-header {
  margin-bottom: 14px;
}

@media (max-width: 860px) {
  .hero,
  .workflow-grid,
  .cta-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-shell {
    padding: 20px 12px 36px;
  }

  .panel,
  .hero-card,
  .confirmation-card,
  .cta-card {
    padding: 16px;
    border-radius: 18px;
  }

  .confirmation-card {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
