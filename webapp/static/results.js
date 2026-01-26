const page = document.querySelector('.page');
const roleId = page?.dataset.roleId;
const batchId = page?.dataset.batchId;
let runId = page?.dataset.runId;

const resultsBody = document.getElementById('results-body');
const resultsEmpty = document.getElementById('results-empty');
const summaryProceed = document.getElementById('summary-proceed');
const summaryReview = document.getElementById('summary-review');
const summaryDismiss = document.getElementById('summary-dismiss');
const summaryUnable = document.getElementById('summary-unable');
const bucketFilter = document.getElementById('bucket-filter');
const exportButtons = document.querySelectorAll('[data-export]');
const summaryButtons = document.querySelectorAll('.summary-card');

let cachedResults = [];
let criteriaLabels = [];
let activeFilter = 'All';

const statusClass = (status) => {
  if (status === 'Pass') return 'pass';
  if (status === 'Fail') return 'fail';
  return 'unsure';
};

const bucketClass = (bucket) => {
  if (bucket === 'Proceed') return 'bucket proceed';
  if (bucket === 'Human Review') return 'bucket review';
  if (bucket === 'Dismiss') return 'bucket dismiss';
  if (bucket === 'Unable to Enrich') return 'bucket unable';
  return 'bucket';
};

const buildCriteriaLabels = (criteriaColumns) => {
  const labels = [];
  ['must_haves', 'gating_params', 'nice_to_haves'].forEach((section) => {
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

const setSummary = (counts = {}) => {
  if (summaryProceed) summaryProceed.textContent = counts.Proceed || 0;
  if (summaryReview) summaryReview.textContent = counts['Human Review'] || 0;
  if (summaryDismiss) summaryDismiss.textContent = counts.Dismiss || 0;
  if (summaryUnable) summaryUnable.textContent = counts['Unable to Enrich'] || 0;
};

const renderRows = () => {
  if (!resultsBody) {
    return;
  }
  resultsBody.innerHTML = '';

  const filtered = cachedResults.filter((result) => {
    if (activeFilter === 'All') {
      return true;
    }
    return result.final_bucket === activeFilter;
  });

  if (!filtered.length) {
    resultsEmpty && (resultsEmpty.style.display = 'block');
    return;
  }

  resultsEmpty && (resultsEmpty.style.display = 'none');

  filtered.forEach((result) => {
    const row = document.createElement('tr');
    row.classList.add('result-row');

    const nameCell = document.createElement('td');
    nameCell.textContent = result.candidate_name || result.full_name || 'Unknown';
    row.appendChild(nameCell);

    const linkedinCell = document.createElement('td');
    linkedinCell.textContent = result.candidate_linkedin || result.linkedin_url || '';
    row.appendChild(linkedinCell);

    const locationCell = document.createElement('td');
    locationCell.textContent = result.location || '';
    row.appendChild(locationCell);

    const companyCell = document.createElement('td');
    companyCell.textContent = result.current_company || '';
    row.appendChild(companyCell);

    const titleCell = document.createElement('td');
    titleCell.textContent = result.current_title || '';
    row.appendChild(titleCell);

    const bucketCell = document.createElement('td');
    const bucketPill = document.createElement('span');
    bucketPill.className = bucketClass(result.final_bucket || '');
    bucketPill.textContent = result.final_bucket || '—';
    bucketCell.appendChild(bucketPill);
    row.appendChild(bucketCell);

    const detailRow = document.createElement('tr');
    detailRow.classList.add('detail-row');
    detailRow.style.display = 'none';
    const detailCell = document.createElement('td');
    detailCell.colSpan = 6;
    detailCell.className = 'detail-cell';

    const detailGrid = document.createElement('div');
    detailGrid.className = 'detail-grid';
    const evaluationMap = buildEvaluationMap(result.criteria_evaluations || {});
    criteriaLabels.forEach((criterion) => {
      const entry = evaluationMap[criterion] || {
        status: 'Unsure',
        reason: 'Insufficient information.',
      };
      const item = document.createElement('div');
      item.className = 'detail-item';
      item.innerHTML = `
        <h4>${criterion}</h4>
        <p><span class="status-pill ${statusClass(entry.status)}">${entry.status}</span> ${entry.reason}</p>
      `;
      detailGrid.appendChild(item);
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

const loadResults = async () => {
  if (!runId) {
    return;
  }
  try {
    const response = await fetch(`/api/filter-runs/${runId}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || 'Failed to load results.');
    }
    cachedResults = payload.results || [];
    criteriaLabels = buildCriteriaLabels(payload.criteria_columns || {});
    setSummary(payload.bucket_counts || {});
    renderRows();
  } catch (error) {
    resultsEmpty && (resultsEmpty.textContent = error.message || 'Unable to load results.');
    resultsEmpty && (resultsEmpty.style.display = 'block');
  }
};

const loadLatestRun = async () => {
  if (runId || !roleId || !batchId) {
    return;
  }
  try {
    const response = await fetch(`/api/batches/${batchId}/runs/latest?role_id=${roleId}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || 'No run available.');
    }
    runId = payload.run_id;
    await loadResults();
  } catch (error) {
    resultsEmpty && (resultsEmpty.textContent = error.message || 'No results yet.');
    resultsEmpty && (resultsEmpty.style.display = 'block');
  }
};

if (bucketFilter) {
  bucketFilter.addEventListener('change', (event) => {
    activeFilter = event.target.value;
    renderRows();
  });
}

summaryButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const filter = button.dataset.filter;
    if (filter) {
      activeFilter = filter;
      if (bucketFilter) {
        bucketFilter.value = filter;
      }
      renderRows();
    }
  });
});

exportButtons.forEach((button) => {
  button.addEventListener('click', () => {
    if (!runId) {
      return;
    }
    const bucket = button.dataset.export || 'All';
    const url = new URL(`/api/filter-runs/${runId}/export`, window.location.origin);
    if (bucket && bucket !== 'All') {
      url.searchParams.set('bucket', bucket);
    }
    window.location.href = url.toString();
  });
});

if (runId) {
  loadResults();
} else {
  loadLatestRun();
}
