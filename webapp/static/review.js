const page = document.querySelector('.page');
const roleId = page?.dataset.roleId;
const batchId = page?.dataset.batchId;

const batchNameInput = document.getElementById('batch-name');
const metricFiles = document.getElementById('metric-files');
const metricUploaded = document.getElementById('metric-uploaded');
const metricDeduped = document.getElementById('metric-deduped');
const metricFinal = document.getElementById('metric-final');
const dedupSummaryText = document.getElementById('dedup-summary-text');
const viewDuplicatesLink = document.getElementById('view-duplicates');
const tableContainer = document.getElementById('table-container');
const exportBtn = document.getElementById('export-btn');
const exportDuplicatesBtn = document.getElementById('export-duplicates-btn');
const approveBtn = document.getElementById('approve-btn');
const approveMessage = document.getElementById('approve-message');

const tabs = Array.from(document.querySelectorAll('.tab'));

const STANDARDIZED_FIELDS = [
  'first_name',
  'last_name',
  'linkedin_url',
  'location',
  'current_company',
  'current_title',
];

let currentCustomFields = [];

const toTitle = (value) => value.replace(/_/g, ' ');

const setMetric = (element, value) => {
  if (element) {
    element.textContent = value ?? '0';
  }
};

const renderEmptyState = (message) => {
  tableContainer.innerHTML = `<div class="empty-state">${message}</div>`;
};

const setApproveMessage = (message, isError = false) => {
  if (!approveMessage) {
    return;
  }
  approveMessage.textContent = message;
  approveMessage.classList.toggle('error', isError);
};

const buildTable = (columns, rows, rowAccessor) => {
  const table = document.createElement('table');
  table.className = 'table-grid';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  columns.forEach((column) => {
    const th = document.createElement('th');
    th.textContent = toTitle(column);
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  rows.forEach((row) => {
    const tr = document.createElement('tr');
    columns.forEach((column) => {
      const td = document.createElement('td');
      const value = rowAccessor(row, column);
      td.textContent = value ?? '';
      if (!value) {
        td.classList.add('muted');
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  return table;
};

const getRawColumns = (candidates) => {
  const columns = [];
  const seen = new Set();
  candidates.forEach((candidate) => {
    const raw = candidate.raw_data || {};
    Object.keys(raw).forEach((key) => {
      if (!seen.has(key)) {
        seen.add(key);
        columns.push(key);
      }
    });
  });
  return columns;
};

const renderStandardized = (candidates, customFields = []) => {
  const columns = [...STANDARDIZED_FIELDS, ...customFields];
  const table = buildTable(
    columns,
    candidates,
    (row, column) => row?.[column]
  );
  tableContainer.innerHTML = '';
  tableContainer.appendChild(table);
};

const renderRaw = (candidates) => {
  const columns = getRawColumns(candidates);
  if (!columns.length) {
    renderEmptyState('No raw columns found for this batch.');
    return;
  }

  const table = buildTable(columns, candidates, (row, column) => {
    const raw = row?.raw_data || {};
    return raw[column];
  });
  tableContainer.innerHTML = '';
  tableContainer.appendChild(table);
};

const renderComparison = (candidates, customFields = []) => {
  const columns = getRawColumns(candidates);
  const container = document.createElement('div');
  container.className = 'split-view';
  const standardizedColumns = [...STANDARDIZED_FIELDS, ...customFields];

  const rawCard = document.createElement('div');
  rawCard.className = 'split-card';
  const rawTitle = document.createElement('h3');
  rawTitle.textContent = 'Raw Data';
  rawCard.appendChild(rawTitle);
  if (!columns.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'No raw columns available.';
    rawCard.appendChild(empty);
  } else {
    rawCard.appendChild(
      buildTable(columns, candidates, (row, column) => {
        const raw = row?.raw_data || {};
        return raw[column];
      })
    );
  }

  const standardizedCard = document.createElement('div');
  standardizedCard.className = 'split-card';
  const standardTitle = document.createElement('h3');
  standardTitle.textContent = 'Standardized Data';
  standardizedCard.appendChild(standardTitle);
  standardizedCard.appendChild(
    buildTable(standardizedColumns, candidates, (row, column) => row?.[column])
  );

  container.appendChild(rawCard);
  container.appendChild(standardizedCard);

  tableContainer.innerHTML = '';
  tableContainer.appendChild(container);
};

const updateMetrics = (payload) => {
  setMetric(metricFiles, payload.file_count);
  setMetric(metricUploaded, payload.total_uploaded);
  setMetric(metricDeduped, payload.deduplicated_count);
  setMetric(metricFinal, payload.final_count);

  if (batchNameInput && payload.batch_name) {
    batchNameInput.value = payload.batch_name;
  }

  if (dedupSummaryText) {
    const deduped = payload.deduplicated_count ?? 0;
    dedupSummaryText.textContent = `${deduped} duplicates removed by LinkedIn URL.`;
  }

  if (viewDuplicatesLink && roleId && batchId) {
    const deduped = payload.deduplicated_count ?? 0;
    viewDuplicatesLink.href = `/roles/${roleId}/batches/${batchId}/duplicates`;
    viewDuplicatesLink.classList.toggle('disabled', deduped <= 0);
  }
};

const fetchCandidates = async (view) => {
  if (!batchId) {
    renderEmptyState('Missing batch id.');
    return;
  }
  renderEmptyState('Loading candidates...');

  try {
    const response = await fetch(`/api/batches/${batchId}/candidates?view=${view}`);
    if (!response.ok) {
      throw new Error('Failed to load candidates.');
    }

    const payload = await response.json();
    updateMetrics(payload);

    const candidates = payload.candidates || [];
    currentCustomFields = payload.custom_fields || [];
    if (!candidates.length) {
      renderEmptyState('No candidates found for this batch.');
      return;
    }

    if (view === 'raw') {
      renderRaw(candidates);
    } else if (view === 'comparison') {
      renderComparison(candidates, currentCustomFields);
    } else {
      renderStandardized(candidates, currentCustomFields);
    }
  } catch (error) {
    renderEmptyState('Unable to load candidate data.');
  }
};

const setActiveTab = (targetView) => {
  tabs.forEach((tab) => {
    if (tab.dataset.view === targetView) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });
};

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    const view = tab.dataset.view || 'standardized';
    setActiveTab(view);
    fetchCandidates(view);
  });
});

if (exportBtn && batchId) {
  exportBtn.href = `/api/batches/${batchId}/export`;
}

if (exportDuplicatesBtn && batchId) {
  exportDuplicatesBtn.href = `/api/batches/${batchId}/duplicates/export`;
}

if (approveBtn && batchId && roleId) {
  approveBtn.addEventListener('click', async () => {
    approveBtn.disabled = true;
    setApproveMessage('Approving batch...');
    try {
      const response = await fetch(`/api/batches/${batchId}/approve`, {
        method: 'POST',
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Failed to approve batch.');
      }
      setApproveMessage('Batch approved. Redirecting to test run...');
      window.setTimeout(() => {
        window.location.href = `/roles/${roleId}/batches/${batchId}/test-run`;
      }, 900);
    } catch (error) {
      setApproveMessage(error.message || 'Unable to approve batch.', true);
      approveBtn.disabled = false;
    }
  });
}

setActiveTab('standardized');
fetchCandidates('standardized');
