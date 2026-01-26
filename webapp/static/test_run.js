const page = document.querySelector('.page');
const roleId = page?.dataset.roleId;
const batchId = page?.dataset.batchId;
const criteriaId = page?.dataset.criteriaId;
const criteriaLocked = page?.dataset.criteriaLocked === '1';

const startButton = document.getElementById('start-test-run');
const message = document.getElementById('test-run-message');
const progress = document.getElementById('test-run-progress');
const candidateCountEl = document.getElementById('candidate-count');
const refineButton = document.getElementById('refine-criteria');
const approveButton = document.getElementById('approve-criteria');

const summaryProceed = document.getElementById('summary-proceed');
const summaryReview = document.getElementById('summary-review');
const summaryDismiss = document.getElementById('summary-dismiss');
const summaryUnable = document.getElementById('summary-unable');
const resultsHead = document.getElementById('results-head');
const resultsBody = document.getElementById('results-body');
const resultsTable = document.getElementById('results-table');
const resultsEmpty = document.getElementById('results-empty');
const tableWrapper = resultsTable?.closest('.table-wrapper');

let pollingTimer = null;

const setMessage = (text, isError = false) => {
  if (!message) {
    return;
  }
  message.textContent = text || '';
  message.classList.toggle('error', isError);
};

const setProgress = (text) => {
  if (!progress) {
    return;
  }
  progress.textContent = text || '';
};

const setTableEmpty = (isEmpty) => {
  if (!tableWrapper) {
    return;
  }
  tableWrapper.classList.toggle('empty', isEmpty);
  if (resultsEmpty) {
    resultsEmpty.style.display = isEmpty ? 'block' : 'none';
  }
};

setTableEmpty(true);

const statusClass = (status) => {
  if (status === 'Pass') return 'pass';
  if (status === 'Fail') return 'fail';
  return 'unsure';
};

const renderSummary = (counts = {}) => {
  if (summaryProceed) summaryProceed.textContent = counts.Proceed || 0;
  if (summaryReview) summaryReview.textContent = counts['Human Review'] || 0;
  if (summaryDismiss) summaryDismiss.textContent = counts.Dismiss || 0;
  if (summaryUnable) summaryUnable.textContent = counts['Unable to Enrich'] || 0;
};

const buildCriteriaColumns = (criteriaColumns) => {
  const sections = ['must_haves', 'gating_params', 'nice_to_haves'];
  const labels = [];
  sections.forEach((section) => {
    (criteriaColumns?.[section] || []).forEach((criterion) => {
      labels.push(criterion);
    });
  });
  return labels;
};

const buildEvaluationMap = (evaluations) => {
  const map = {};
  ['must_haves', 'gating_params', 'nice_to_haves'].forEach((section) => {
    (evaluations?.[section] || []).forEach((entry) => {
      if (!entry || !entry.criterion) {
        return;
      }
      map[entry.criterion] = entry;
    });
  });
  return map;
};

const renderResults = (payload) => {
  if (!resultsHead || !resultsBody) {
    return;
  }

  const criteriaLabels = buildCriteriaColumns(payload.criteria_columns);
  const results = payload.results || [];
  resultsHead.innerHTML = '';
  resultsBody.innerHTML = '';

  const headerRow = document.createElement('tr');
  const baseHeaders = ['Name', 'LinkedIn', ...criteriaLabels, 'Bucket'];
  baseHeaders.forEach((label) => {
    const th = document.createElement('th');
    th.textContent = label;
    headerRow.appendChild(th);
  });
  resultsHead.appendChild(headerRow);

  if (!results.length) {
    setTableEmpty(true);
    return;
  }

  setTableEmpty(false);

  results.forEach((result, index) => {
    const row = document.createElement('tr');
    row.classList.add('result-row');
    row.dataset.index = String(index);
    const evaluationMap = buildEvaluationMap(result.criteria_evaluations);

    const nameCell = document.createElement('td');
    nameCell.textContent = result.candidate_name || 'Unknown';
    row.appendChild(nameCell);

    const linkedinCell = document.createElement('td');
    linkedinCell.textContent = result.candidate_linkedin || '';
    row.appendChild(linkedinCell);

    criteriaLabels.forEach((criterion) => {
      const entry = evaluationMap[criterion];
      const status = entry?.status || 'Unsure';
      const cell = document.createElement('td');
      const pill = document.createElement('span');
      pill.className = `status-pill ${statusClass(status)}`;
      pill.textContent = status;
      cell.appendChild(pill);
      row.appendChild(cell);
    });

    const bucketCell = document.createElement('td');
    const bucket = document.createElement('span');
    bucket.className = 'bucket-pill';
    bucket.textContent = result.final_bucket || '—';
    bucketCell.appendChild(bucket);
    row.appendChild(bucketCell);

    const detailRow = document.createElement('tr');
    detailRow.classList.add('detail-row');
    detailRow.style.display = 'none';
    const detailCell = document.createElement('td');
    detailCell.className = 'detail-cell';
    detailCell.colSpan = baseHeaders.length;

    const detailGrid = document.createElement('div');
    detailGrid.className = 'detail-grid';
    Object.keys(evaluationMap).forEach((criterion) => {
      const entry = evaluationMap[criterion];
      const detailItem = document.createElement('div');
      detailItem.className = 'detail-item';
      detailItem.innerHTML = `
        <h4>${criterion}</h4>
        <p><strong>${entry.status}</strong>: ${entry.reason}</p>
      `;
      detailGrid.appendChild(detailItem);
    });

    detailCell.appendChild(detailGrid);
    detailRow.appendChild(detailCell);

    row.addEventListener('click', () => {
      const isOpen = detailRow.style.display === 'table-row';
      detailRow.style.display = isOpen ? 'none' : 'table-row';
    });

    resultsBody.appendChild(row);
    resultsBody.appendChild(detailRow);
  });
};

const updateFromPayload = (payload) => {
  if (!payload) {
    return;
  }
  if (candidateCountEl && payload.candidate_count != null) {
    candidateCountEl.textContent = payload.candidate_count;
  }
  renderSummary(payload.bucket_counts || {});
  renderResults(payload);
};

const pollTestRun = async (testRunId) => {
  if (!testRunId) {
    return;
  }
  try {
    const response = await fetch(`/api/test-runs/${testRunId}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || 'Failed to load test run.');
    }
    updateFromPayload(payload);
    if (payload.status === 'complete') {
      setProgress('Evaluation complete.');
    if (approveButton && !criteriaLocked) {
      approveButton.disabled = false;
    }
      startButton && (startButton.disabled = true);
      pollingTimer = null;
      return;
    }
    setProgress(
      `Evaluated ${payload.evaluated_count || 0} of ${payload.candidate_count || 0}...`
    );
  } catch (error) {
    setMessage(error.message || 'Unable to load test run.', true);
  }
  pollingTimer = window.setTimeout(() => pollTestRun(testRunId), 2500);
};

const startPolling = (testRunId) => {
  if (pollingTimer) {
    window.clearTimeout(pollingTimer);
  }
  pollTestRun(testRunId);
};

const setQueryParam = (testRunId) => {
  const url = new URL(window.location.href);
  url.searchParams.set('test_run_id', testRunId);
  window.history.replaceState({}, '', url.toString());
};

if (startButton && roleId && batchId) {
  if (!criteriaId) {
    startButton.disabled = true;
    setMessage('Add criteria before running a test run.', true);
  } else if (criteriaLocked) {
    startButton.disabled = true;
    setMessage('Criteria are locked for this role.', true);
  }

  startButton.addEventListener('click', async () => {
    startButton.disabled = true;
    setMessage('Starting test run...');
    setProgress('');
    try {
      const response = await fetch(`/api/batches/${batchId}/test-run`, {
        method: 'POST',
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Failed to start test run.');
      }
      setMessage(`Test run started with ${payload.candidate_count} candidates.`);
      setQueryParam(payload.test_run_id);
      startPolling(payload.test_run_id);
    } catch (error) {
      setMessage(error.message || 'Unable to start test run.', true);
      startButton.disabled = false;
    }
  });
}

if (refineButton && roleId) {
  refineButton.addEventListener('click', () => {
    window.location.href = `/roles/${roleId}`;
  });
}

if (approveButton && roleId && batchId) {
  approveButton.disabled = true;
  if (criteriaLocked) {
    approveButton.title = 'Criteria already locked.';
  }
  approveButton.addEventListener('click', async () => {
    if (!criteriaId) {
      return;
    }
    approveButton.disabled = true;
    setMessage('Locking criteria...');
    try {
      const response = await fetch(
        `/api/roles/${roleId}/criteria/${criteriaId}/lock`,
        { method: 'POST' }
      );
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Failed to lock criteria.');
      }
      setMessage('Criteria approved. Redirecting to full run...');
      window.location.href = `/roles/${roleId}/batches/${batchId}/run`;
    } catch (error) {
      setMessage(error.message || 'Unable to lock criteria.', true);
      approveButton.disabled = false;
    }
  });
}

const existingTestRunId = new URLSearchParams(window.location.search).get(
  'test_run_id'
);
if (existingTestRunId) {
  startPolling(existingTestRunId);
}
