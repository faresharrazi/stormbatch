<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true,
  },
});

defineEmits(["update:modelValue"]);
</script>

<template>
  <label class="field">
    <span>Livestorm API key</span>
    <input
      :value="modelValue"
      type="password"
      placeholder="Paste your API key"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  </label>
</template>

<style scoped>
.field {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

span {
  font-weight: 700;
}

input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 1rem;
}
</style>
