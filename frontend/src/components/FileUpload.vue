<script setup>
defineProps({
  selectedFile: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  previewReady: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["file-selected", "preview"]);

function onChange(event) {
  const [file] = event.target.files;
  if (file) {
    event.target.value = "";
  }
  if (file) {
    // The parent keeps the file reference for preview and submission.
    // This avoids any extra client-side parsing logic.
    return file;
  }
  return null;
}
</script>

<template>
  <div class="upload-card">
    <div class="upload-copy">
      <span>Spreadsheet upload</span>
      <strong>Drop in the registrant list</strong>
      <p>StormBatch reads .xlsx or .csv files, trims headers and values, and previews the first rows before anything is sent.</p>
    </div>

    <label class="drop-zone" :class="{ selected: selectedFile }">
      <input
        type="file"
        accept=".xlsx,.csv"
        @change="
          ($event) => {
            const file = onChange($event);
            if (file) $emit('file-selected', file);
          }
        "
      />
      <span class="file-icon">XLSX</span>
      <strong>{{ selectedFile ? selectedFile.name : "Choose an .xlsx or .csv file" }}</strong>
      <small>{{ selectedFile ? "Ready to preview" : "Click to browse from your computer" }}</small>
    </label>

    <button class="secondary-button" type="button" :disabled="loading || !selectedFile" @click="$emit('preview')">
      <span v-if="loading" class="spinner"></span>
      {{ loading ? "Reading file..." : previewReady ? "Refresh preview" : "Detect columns and preview" }}
    </button>
  </div>
</template>

<style scoped>
.upload-card {
  display: grid;
  gap: 16px;
}

.upload-copy span {
  display: inline-flex;
  width: fit-content;
  margin-bottom: 8px;
  color: #12262b;
  background: #d8fff4;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.upload-copy strong {
  display: block;
  font-size: 1.25rem;
  font-weight: 700;
}

.upload-copy p {
  margin: 6px 0 0;
  color: #64748b;
  line-height: 1.55;
}

.drop-zone {
  display: grid;
  place-items: center;
  gap: 8px;
  min-height: 190px;
  padding: 24px;
  text-align: center;
  border: 2px dashed rgba(18, 38, 43, 0.22);
  border-radius: 22px;
  background:
    radial-gradient(circle at center, rgba(0, 229, 168, 0.16), transparent 55%),
    #f8fffc;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.drop-zone:hover {
  border-color: #12262b;
  transform: translateY(-1px);
}

.drop-zone.selected {
  border-style: solid;
  border-color: #12262b;
}

.drop-zone input {
  display: none;
}

.file-icon {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border-radius: 18px;
  color: white;
  background: linear-gradient(135deg, #12262b, #00e5a8);
  font-size: 0.8rem;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.drop-zone small {
  color: #64748b;
}

.secondary-button {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  border: 1px solid #12262b;
  background: #12262b;
  color: white;
  border-radius: 16px;
  padding: 14px 16px;
  font-weight: 900;
  cursor: pointer;
}

.secondary-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: white;
  border-radius: 999px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
