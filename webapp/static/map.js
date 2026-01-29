const page = document.querySelector('.page');
const roleId = page?.dataset.roleId;
const batchId = page?.dataset.batchId;

const loadingState = document.getElementById('loading-state');
const gridContainer = document.getElementById('grid-container');
const gridBody = document.getElementById('grid-body');
const gridHead = document.querySelector('#mapping-grid thead tr');
const applyButton = document.getElementById('apply-mappings');
const addCustomFieldButton = document.getElementById('add-custom-field');
const errorBanner = document.getElementById('mapping-error');

// Standard target fields (order matters)
const STANDARD_FIELDS = [
  'first_name',
  'last_name',
  'full_name',
  'linkedin_url',
  'location',
  'current_company',
  'current_title'
];

let filesData = [];
let customFields = [];
let hasAttemptedApply = false;

const normalizeValue = (value) => (value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
const showToast = (message, type = 'success') => {
  if (window.showToast) {
    window.showToast(message, type);
  }
};

/**
 * Create an option element for a select dropdown
 */
const createOption = (value, label, selected = false) => {
  const option = document.createElement('option');
  option.value = value;
  option.textContent = label;
  if (selected) {
    option.selected = true;
  }
  return option;
};

/**
 * Check if all required fields are mapped and update Apply button state
 */
const updateApplyState = () => {
  const linkedinSelects = Array.from(
    document.querySelectorAll('tr[data-target="linkedin_url"] select')
  );

  const hasLinkedInMapping = linkedinSelects.some(select => {
    const value = select.value;
    return value && value !== '' && value !== 'skip';
  });

  applyButton.disabled = !hasLinkedInMapping;

  if (hasLinkedInMapping) {
    errorBanner.classList.add('hidden');
  } else if (hasAttemptedApply) {
    errorBanner.textContent = 'LinkedIn URL must be mapped before you can continue.';
    errorBanner.classList.remove('hidden');
  }
};

/**
 * Check if a suggested mapping should be applied (high confidence only)
 */
const isHighConfidenceMatch = (sourceColumn, targetField) => {
  const source = normalizeValue(sourceColumn);
  const target = normalizeValue(targetField);

  if (!source || !target) {
    return false;
  }

  if (source === target) {
    return true;
  }

  return source.startsWith(target) || target.startsWith(source);
};

/**
 * Create a select dropdown for a mapping cell
 */
const createMappingSelect = (filename, targetField, suggestedMappings) => {
  const select = document.createElement('select');
  select.dataset.filename = filename;
  select.dataset.target = targetField;

  // Add empty option (default)
  select.appendChild(createOption('', '(blank)', false));

  // Get headers for this file
  const fileData = filesData.find(f => f.filename === filename);
  if (!fileData || !fileData.headers) {
    return select;
  }

  // Add each header as an option
  fileData.headers.forEach(header => {
    const isSelected = suggestedMappings?.[header] === targetField &&
                       isHighConfidenceMatch(header, targetField);
    select.appendChild(createOption(header, header, isSelected));
  });

  select.addEventListener('change', updateApplyState);

  return select;
};

/**
 * Create a row for a target field
 */
const createTargetFieldRow = (targetField, isRequired = false, isCustom = false) => {
  const row = document.createElement('tr');
  row.dataset.target = targetField;

  if (isRequired) {
    row.classList.add('required-row');
  }
  if (isCustom) {
    row.classList.add('custom-row');
  }

  // Create mapping cells for each file FIRST (left side)
  filesData.forEach(fileData => {
    const cell = document.createElement('td');
    cell.classList.add('mapping-cell');

    const select = createMappingSelect(
      fileData.filename,
      targetField,
      fileData.suggested_mappings
    );

    cell.appendChild(select);
    row.appendChild(cell);
  });

  // Target field cell LAST (right column, sticky)
  const targetCell = document.createElement('td');
  targetCell.classList.add('target-cell');
  targetCell.textContent = targetField;

  if (isRequired) {
    const badge = document.createElement('span');
    badge.classList.add('required-badge');
    badge.textContent = 'REQUIRED';
    targetCell.appendChild(badge);
  }

  if (isCustom) {
    const badge = document.createElement('span');
    badge.classList.add('custom-badge');
    badge.textContent = 'CUSTOM';
    targetCell.appendChild(badge);

    // Add remove button for custom fields
    const removeBtn = document.createElement('button');
    removeBtn.classList.add('remove-field');
    removeBtn.innerHTML = '×';
    removeBtn.title = 'Remove custom field';
    removeBtn.addEventListener('click', () => removeCustomField(targetField));
    targetCell.appendChild(removeBtn);
  }

  row.appendChild(targetCell);

  return row;
};

/**
 * Render the entire grid
 */
const renderGrid = () => {
  // Clear existing content
  gridBody.innerHTML = '';

  // Clear and rebuild header - file columns on LEFT, target on RIGHT
  // Remove all but the last child (target header)
  while (gridHead.childNodes.length > 1) {
    gridHead.removeChild(gridHead.firstChild);
  }

  // Insert file headers BEFORE the target header (on the left)
  const targetHeader = gridHead.querySelector('.target-header');
  filesData.forEach(fileData => {
    const th = document.createElement('th');
    th.classList.add('file-header');
    th.textContent = fileData.filename || 'Untitled';
    gridHead.insertBefore(th, targetHeader);
  });

  // Add standard fields
  STANDARD_FIELDS.forEach(field => {
    const isRequired = field === 'linkedin_url';
    const row = createTargetFieldRow(field, isRequired, false);
    gridBody.appendChild(row);
  });

  // Add custom fields
  customFields.forEach(field => {
    const row = createTargetFieldRow(field, false, true);
    gridBody.appendChild(row);
  });

  updateApplyState();
};

/**
 * Add a custom field to the grid
 */
const addCustomField = () => {
  const fieldName = prompt('Enter custom field name:');
  if (!fieldName || fieldName.trim() === '') {
    return;
  }

  const normalizedName = fieldName.trim().toLowerCase().replace(/\s+/g, '_');

  // Check if field already exists
  if (STANDARD_FIELDS.includes(normalizedName) || customFields.includes(normalizedName)) {
    showToast('This field already exists.', 'error');
    return;
  }

  customFields.push(normalizedName);
  renderGrid();
  showToast(`Added custom field: ${normalizedName}`, 'success');
};

/**
 * Remove a custom field
 */
const removeCustomField = (fieldName) => {
  const index = customFields.indexOf(fieldName);
  if (index > -1) {
    customFields.splice(index, 1);
    renderGrid();
  }
};

/**
 * Build the mappings payload for backend API
 * Format: { mappings: { targetField: { filename: sourceColumn, ... }, ... }, custom_fields: [...] }
 */
const buildMappingsPayload = () => {
  const mappings = {};

  // Get all target field rows
  const rows = Array.from(document.querySelectorAll('#grid-body tr[data-target]'));

  rows.forEach(row => {
    const targetField = row.dataset.target;
    const selects = Array.from(row.querySelectorAll('select'));
    const fieldMappings = {};

    selects.forEach(select => {
      const filename = select.dataset.filename;
      const sourceColumn = select.value;

      // Only include if a source column is selected (not blank)
      if (sourceColumn && sourceColumn !== '') {
        fieldMappings[filename] = sourceColumn;
      }
    });

    // Only include target field if at least one file is mapped
    if (Object.keys(fieldMappings).length > 0) {
      mappings[targetField] = fieldMappings;
    }
  });

  return {
    mappings,
    custom_fields: customFields
  };
};

/**
 * Load suggested mappings from backend
 */
const loadMappings = async () => {
  try {
    loadingState.classList.add('loading');
    const response = await fetch(`/api/batches/${batchId}/suggest-mappings`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to load suggested mappings.');
    }

    const payload = await response.json();
    filesData = payload.files || [];

    loadingState.classList.add('hidden');
    gridContainer.classList.remove('hidden');
    loadingState.classList.remove('loading');

    errorBanner.classList.add('hidden');
    renderGrid();
  } catch (error) {
    console.error('Error loading mappings:', error);
    loadingState.textContent = 'Unable to load mappings. Please try again.';
    loadingState.classList.remove('loading');
    errorBanner.textContent = 'Unable to load mappings. Please refresh the page.';
    errorBanner.classList.remove('hidden');
    showToast('Unable to load mappings.', 'error');
  }
};

/**
 * Apply the mappings and proceed to review
 */
const applyMappings = async () => {
  if (applyButton.disabled) {
    hasAttemptedApply = true;
    updateApplyState();
    return;
  }

  applyButton.disabled = true;
  applyButton.textContent = 'Applying...';
  applyButton.classList.add('loading');
  errorBanner.classList.add('hidden');

  try {
    const payload = buildMappingsPayload();

    const response = await fetch(`/api/batches/${batchId}/apply-mappings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to apply mappings.');
    }

    showToast('Mappings applied. Redirecting…', 'success');
    window.setTimeout(() => {
      window.location.href = `/roles/${roleId}/batches/${batchId}/review`;
    }, 600);
  } catch (error) {
    console.error('Error applying mappings:', error);
    applyButton.disabled = false;
    applyButton.textContent = 'Apply Mappings';
    applyButton.classList.remove('loading');
    errorBanner.textContent = error.message || 'Unable to apply mappings. Please try again.';
    errorBanner.classList.remove('hidden');
    showToast(error.message || 'Unable to apply mappings.', 'error');
  }
};

// Event listeners
applyButton?.addEventListener('click', applyMappings);
addCustomFieldButton?.addEventListener('click', addCustomField);

// Initialize
if (batchId) {
  loadMappings();
}
