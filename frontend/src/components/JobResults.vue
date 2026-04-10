<script setup>
const props = defineProps({
  jobs: {
    type: Array,
    required: true,
  },
  retryingSessions: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(["retry-failed"]);

const FINAL_STATUSES = ["ended", "failed", "completed"];

function isFinal(job) {
  return FINAL_STATUSES.includes(String(job.status).toLowerCase());
}

function taskStatus(task) {
  return task?.attributes?.status || task?.status || "unknown";
}

function taskError(task) {
  const attributes = task?.attributes || {};
  const errors = attributes.errors || task?.errors;
  if (Array.isArray(errors)) {
    return errors
      .map((error) => error.detail || error.title || error.message || String(error))
      .join(", ");
  }
  return attributes.error || attributes.message || task?.error || task?.message || "";
}

function rowLabel(task) {
  const row = task?.row_result || {};
  return [row.email, `Excel row ${row.row_number || "?"}`].filter(Boolean).join(" - ");
}

function failedTasks(job) {
  return (job.tasks || []).filter(
    (task) => String(taskStatus(task)).toLowerCase() === "failed",
  );
}

function succeededTasks(job) {
  return (job.tasks || []).filter(
    (task) => String(taskStatus(task)).toLowerCase() === "succeeded",
  );
}

function retryResults(job) {
  return job.retry_results || [];
}

function canDiagnose(job) {
  return isFinal(job)
    && String(job.status).toLowerCase() === "failed"
    && !failedTasks(job).length;
}

function summaryText(job) {
  if (!isFinal(job)) {
    return "Livestorm is still processing this session.";
  }
  if (!job.tasks?.length) {
    return String(job.status).toLowerCase() === "failed"
      ? "The job failed before Livestorm returned row-level task details."
      : "The job finished successfully. Livestorm did not return row-level task details.";
  }
  const failed = failedTasks(job).length;
  const succeeded = succeededTasks(job).length;
  if (!failed) {
    return `${succeeded} registrant(s) succeeded.`;
  }
  return `${succeeded} succeeded, ${failed} need attention.`;
}

function cardClass(job) {
  if (!isFinal(job)) {
    return "processing";
  }
  return failedTasks(job).length || String(job.status).toLowerCase() === "failed"
    ? "has-failures"
    : "succeeded";
}
</script>

<template>
  <div class="jobs-grid">
    <article
      v-for="job in props.jobs"
      :key="`${job.session_id}-${job.job_id}`"
      class="job-card"
      :class="cardClass(job)"
    >
      <div class="job-header">
        <div>
          <span class="session-label">Session</span>
          <h3>{{ job.session_id }}</h3>
          <p>{{ summaryText(job) }}</p>
        </div>
        <span class="status">{{ job.status }}</span>
      </div>

      <p v-if="job.error" class="job-error">{{ job.error }}</p>

      <div v-if="failedTasks(job).length" class="failed-panel">
        <div class="failed-header">
          <strong>Failed registrants</strong>
          <button
            class="retry-button"
            type="button"
            :disabled="props.retryingSessions[job.session_id]"
            @click="emit('retry-failed', job)"
          >
            {{ props.retryingSessions[job.session_id] ? "Retrying..." : "Retry failed rows" }}
          </button>
        </div>

        <div v-for="task in failedTasks(job)" :key="task.id || rowLabel(task)" class="failed-row">
          <div>
            <strong>{{ rowLabel(task) }}</strong>
            <p>{{ taskError(task) || "Livestorm did not provide a row-level error." }}</p>
          </div>
        </div>
      </div>

      <div v-else-if="canDiagnose(job)" class="failed-panel">
        <div class="failed-header">
          <div>
            <strong>No row-level details from bulk job</strong>
            <p>Check which emails already exist, then try missing ones with single registration.</p>
          </div>
          <button
            class="retry-button"
            type="button"
            :disabled="props.retryingSessions[job.session_id]"
            @click="emit('retry-failed', job)"
          >
            {{ props.retryingSessions[job.session_id] ? "Diagnosing..." : "Diagnose rows" }}
          </button>
        </div>
      </div>

      <div v-if="retryResults(job).length" class="retry-results">
        <strong>Retry results</strong>
        <div v-for="result in retryResults(job)" :key="`${result.email}-${result.row_number}`" class="retry-row">
          <span>{{ result.email }}</span>
          <span :class="['retry-status', result.status]">{{ result.status }}</span>
          <p v-if="result.error">{{ result.error }}</p>
        </div>
      </div>
    </article>
  </div>
</template>

<style scoped>
.jobs-grid {
  display: grid;
  gap: 14px;
}

.job-card {
  border: 1px solid rgba(18, 38, 43, 0.14);
  background: #ffffff;
  border-radius: 18px;
  padding: 18px;
}

.job-card.succeeded {
  border-color: rgba(0, 229, 168, 0.5);
  background: #f8fffc;
}

.job-card.has-failures {
  border-color: #fecaca;
  background: #fffafa;
}

.job-card.processing {
  background: #fbf7ef;
}

.job-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: start;
  flex-wrap: wrap;
}

h3,
p {
  margin: 0;
}

h3 {
  margin: 4px 0 6px;
  font-size: 1rem;
  overflow-wrap: anywhere;
}

.session-label {
  color: #607075;
  font-size: 0.78rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.status {
  background: #d8fff4;
  color: #12262b;
  border-radius: 999px;
  padding: 8px 12px;
  font-weight: 900;
  text-transform: capitalize;
}

.failed-panel,
.retry-results {
  display: grid;
  gap: 10px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(18, 38, 43, 0.1);
}

.failed-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.failed-row,
.retry-row {
  padding: 12px;
  background: white;
  border: 1px solid rgba(18, 38, 43, 0.1);
  border-radius: 14px;
}

.failed-row p,
.retry-row p,
.job-error {
  margin-top: 4px;
  color: #b91c1c;
}

.retry-button {
  border: none;
  border-radius: 999px;
  padding: 10px 14px;
  color: white;
  background: #12262b;
  font-weight: 900;
  cursor: pointer;
}

.retry-button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.retry-row {
  display: grid;
  gap: 6px;
}

.retry-status {
  width: fit-content;
  border-radius: 999px;
  padding: 5px 9px;
  font-size: 0.8rem;
  font-weight: 900;
  text-transform: capitalize;
}

.retry-status.succeeded {
  background: #d8fff4;
  color: #12262b;
}

.retry-status.registered {
  background: #eef2ff;
  color: #3730a3;
}

.retry-status.failed {
  background: #fef2f2;
  color: #b91c1c;
}
</style>
