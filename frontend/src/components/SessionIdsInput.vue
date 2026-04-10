<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  count: {
    type: Number,
    default: 0,
  },
});

defineEmits(["update:modelValue"]);
</script>

<template>
  <label class="field session-field">
    <div class="field-heading">
      <span>Session IDs</span>
      <strong>{{ count }}</strong>
    </div>
    <textarea
      :value="modelValue"
      rows="4"
      placeholder="91ca6a71-a2a0-4d8f-9ef8-828c1fa70a4a&#10;872bbcfa-96cd-4f8f-99e9-f60cf4582917"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <small>Paste one per line or comma-separated. We will create one Livestorm job per session.</small>
  </label>
</template>

<style scoped>
.field {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

.field-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.field-heading span {
  font-weight: 700;
}

.field-heading strong {
  display: grid;
  place-items: center;
  min-width: 34px;
  height: 34px;
  border-radius: 999px;
  background: #12262b;
  color: white;
}

textarea {
  width: 100%;
  border: 1px solid rgba(18, 38, 43, 0.2);
  border-radius: 16px;
  padding: 14px 16px;
  font-size: 1rem;
  resize: vertical;
  background: #fbfffd;
  box-shadow: inset 0 1px 0 rgba(18, 38, 43, 0.06);
}

textarea:focus {
  outline: 3px solid rgba(0, 229, 168, 0.18);
  border-color: #12262b;
}

small {
  color: #6b7280;
}
</style>
