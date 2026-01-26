const page = document.querySelector('.page');
const roleId = page?.dataset.roleId;
const batchId = page?.dataset.batchId;

const filesContainer = document.getElementById('files');
const fieldsList = document.getElementById('standardized-fields');
const applyButton = document.getElementById('apply-mappings');
const errorBanner = document.getElementById('mapping-error');

let standardizedFields = [];

const createOption = (value, label, selected) => {
  const option = document.createElement('option');
  option.value = value;
  option.textContent = label;
  if (selected) {
    option.selected = true;
  }
  return option;
};

const updateApplyState = () => {
  const hasLinkedIn = Array.from(document.querySelectorAll('select[data-source]'))
    .some((select) => select.value === 'linkedin_url');
  applyButton.disabled = !hasLinkedIn;
  if (hasLinkedIn) {
    errorBanner.classList.add('hidden');
  }
};

const renderStandardizedFields = () => {
  fieldsList.innerHTML = '';
  standardizedFields.forEach((field) => {
    const item = document.createElement('li');
    item.textContent = field;
    fieldsList.appendChild(item);
  });
};

const renderFiles = (files) => {
  filesContainer.innerHTML = '';

  if (!files.length) {
    filesContainer.innerHTML = '<div class="empty-state">No files found for this batch.</div>';
    return;
  }

  files.forEach((file) => {
    const card = document.createElement('div');
    card.className = 'file-card';
    if (file.filename) {
      card.dataset.filename = file.filename;
    }

    const title = document.createElement('h3');
    title.textContent = file.filename || 'Untitled CSV';
    card.appendChild(title);

    (file.headers || []).forEach((header) => {
      const row = document.createElement('div');
      row.className = 'column-row';

      const label = document.createElement('div');
      label.className = 'column-label';
      label.textContent = header;
      const subtitle = document.createElement('span');
      subtitle.textContent = 'Source column';
      label.appendChild(subtitle);

      const select = document.createElement('select');
      select.dataset.source = header;
      select.appendChild(createOption('skip', 'Skip', false));
      standardizedFields.forEach((field) => {
        select.appendChild(createOption(field, field, false));
      });

      const suggested = file.suggested_mappings?.[header];
      if (suggested && standardizedFields.includes(suggested)) {
        select.value = suggested;
      } else if (suggested === 'skip') {
        select.value = 'skip';
      }

      select.addEventListener('change', updateApplyState);

      row.appendChild(label);
      row.appendChild(select);
      card.appendChild(row);
    });

    filesContainer.appendChild(card);
  });

  updateApplyState();
};

const loadMappings = async () => {
  try {
    const response = await fetch(`/api/batches/${batchId}/suggest-mappings`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to load suggested mappings.');
    }

    const payload = await response.json();
    standardizedFields = payload.standardized_fields || [];
    renderStandardizedFields();
    renderFiles(payload.files || []);
  } catch (error) {
    filesContainer.innerHTML = '<div class="empty-state">Unable to load mappings.</div>';
  }
};

const buildMappingsPayload = () => {
  const fileCards = Array.from(document.querySelectorAll('.file-card'));

  return fileCards.map((card) => {
    const filename = card.dataset.filename || card.querySelector('h3')?.textContent || '';
    const selects = Array.from(card.querySelectorAll('select[data-source]'));
    const mappings = {};
    selects.forEach((select) => {
      mappings[select.dataset.source] = select.value;
    });
    return { filename, mappings };
  });
};

const applyMappings = async () => {
  if (applyButton.disabled) {
    errorBanner.classList.remove('hidden');
    return;
  }

  applyButton.disabled = true;
  applyButton.textContent = 'Applying...';

  try {
    const response = await fetch(`/api/batches/${batchId}/apply-mappings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files: buildMappingsPayload() }),
    });

    if (!response.ok) {
      throw new Error('Failed to apply mappings.');
    }

    window.location.href = `/roles/${roleId}/batches/${batchId}/review`;
  } catch (error) {
    applyButton.disabled = false;
    applyButton.textContent = 'Apply Mappings';
    errorBanner.textContent = 'Unable to apply mappings. Please try again.';
    errorBanner.classList.remove('hidden');
  }
};

applyButton?.addEventListener('click', applyMappings);

if (batchId) {
  loadMappings();
}
