const page = document.querySelector('.page');
const batchId = page?.dataset.batchId;

const duplicateCount = document.getElementById('duplicate-count');
const tableContainer = document.getElementById('table-container');
const exportLink = document.getElementById('export-duplicates');

const renderEmptyState = (message) => {
  tableContainer.innerHTML = `<div class="empty-state">${message}</div>`;
};

const buildTable = (rows) => {
  const table = document.createElement('table');
  table.className = 'table-grid';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  ['Name', 'LinkedIn URL'].forEach((label) => {
    const th = document.createElement('th');
    th.textContent = label;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  rows.forEach((row) => {
    const tr = document.createElement('tr');

    const nameCell = document.createElement('td');
    const fullName = row.full_name || `${row.first_name || ''} ${row.last_name || ''}`.trim();
    nameCell.textContent = fullName || 'Unknown';
    if (!fullName) {
      nameCell.classList.add('muted');
    }
    tr.appendChild(nameCell);

    const linkedinCell = document.createElement('td');
    linkedinCell.textContent = row.linkedin_url || '';
    if (!row.linkedin_url) {
      linkedinCell.classList.add('muted');
    }
    tr.appendChild(linkedinCell);

    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  return table;
};

const loadDuplicates = async () => {
  if (!batchId) {
    renderEmptyState('Missing batch id.');
    return;
  }

  try {
    const response = await fetch(`/api/batches/${batchId}/duplicates`);
    if (!response.ok) {
      throw new Error('Failed to load duplicates.');
    }
    const payload = await response.json();
    const deduped = payload.deduplicated_count ?? 0;

    if (duplicateCount) {
      duplicateCount.textContent = deduped;
    }

    const duplicates = payload.duplicates || [];
    if (!duplicates.length) {
      renderEmptyState('No duplicates were removed for this batch.');
      return;
    }

    tableContainer.innerHTML = '';
    tableContainer.appendChild(buildTable(duplicates));
  } catch (error) {
    renderEmptyState('Unable to load duplicates.');
  }
};

if (exportLink && batchId) {
  exportLink.href = `/api/batches/${batchId}/duplicates/export`;
}

loadDuplicates();
