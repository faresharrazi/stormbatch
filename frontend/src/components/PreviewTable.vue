<script setup>
defineProps({
  headers: {
    type: Array,
    required: true,
  },
  rows: {
    type: Array,
    required: true,
  },
});
</script>

<template>
  <div class="preview-shell">
    <div class="preview-heading">
      <strong>First {{ rows.length }} rows</strong>
      <span>{{ headers.length }} detected column(s)</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th v-for="header in headers" :key="header">{{ header }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in rows" :key="index">
            <td v-for="header in headers" :key="header">{{ row[header] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.preview-shell {
  display: grid;
  gap: 10px;
}

.preview-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #334155;
}

.preview-heading span {
  color: #64748b;
}

.table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(18, 38, 43, 0.14);
  border-radius: 18px;
  background: white;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 13px 14px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  white-space: nowrap;
}

th {
  background: #d8fff4;
  color: #12262b;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

tbody tr:hover {
  background: #f8fffc;
}
</style>
