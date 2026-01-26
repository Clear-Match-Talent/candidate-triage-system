const page = document.querySelector('.page');
const roleId = page?.dataset.roleId;
const batchId = page?.dataset.batchId;
const totalCandidates = Number(page?.dataset.candidateCount || 0);

const startButton = document.getElementById('start-full-run');
const message = document.getElementById('run-message');
const progress = document.getElementById('run-progress');
const scopeInputs = document.querySelectorAll('input[name="run-scope"]');
const subsetInput = document.getElementById('subset-count');

let pollingTimer = null;
let runStartedAt = null;

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

const getSelectedScope = () => {
  const selected = Array.from(scopeInputs).find((input) => input.checked);
  return selected ? selected.value : 'all';
};

const getSubsetCount = () => {
  const raw = Number(subsetInput?.value || 0);
  return Number.isFinite(raw) ? raw : 0;
};

const updateSubsetState = () => {
  if (!subsetInput) {
    return;
  }
  const scope = getSelectedScope();
  subsetInput.disabled = scope !== 'subset';
};

const formatMinutes = (ms) => {
  const minutes = Math.max(ms / 60000, 0);
  if (minutes < 1) {
    return '<1 min';
  }
  return `${Math.round(minutes)} min`;
};

const pollRun = async (runId) => {
  if (!runId) {
    return;
  }
  try {
    const response = await fetch(`/api/filter-runs/${runId}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || 'Failed to load run status.');
    }
    const evaluated = payload.evaluated_count || 0;
    const total = payload.candidate_count || 0;
    if (payload.status === 'completed') {
      setProgress('Evaluation complete. Redirecting to results...');
      window.location.href = `/roles/${roleId}/batches/${batchId}/results?run_id=${runId}`;
      return;
    }
    if (payload.status === 'failed') {
      setMessage('Run failed. Please try again.', true);
      startButton && (startButton.disabled = false);
      return;
    }
    let eta = '';
    if (runStartedAt && evaluated > 0) {
      const elapsed = Date.now() - runStartedAt;
      const perCandidate = elapsed / evaluated;
      const remaining = (total - evaluated) * perCandidate;
      eta = ` ~${formatMinutes(remaining)} remaining`;
    }
    setProgress(`Evaluated ${evaluated} of ${total}...${eta}`);
  } catch (error) {
    setMessage(error.message || 'Unable to load run status.', true);
  }
  pollingTimer = window.setTimeout(() => pollRun(runId), 3000);
};

const startPolling = (runId) => {
  if (pollingTimer) {
    window.clearTimeout(pollingTimer);
  }
  pollRun(runId);
};

scopeInputs.forEach((input) => {
  input.addEventListener('change', updateSubsetState);
});
updateSubsetState();

if (startButton && roleId && batchId) {
  startButton.addEventListener('click', async () => {
    const scope = getSelectedScope();
    let count = 0;
    if (scope === 'subset') {
      count = getSubsetCount();
      if (!count || count < 1 || count > totalCandidates) {
        setMessage(`Enter a subset between 1 and ${totalCandidates}.`, true);
        return;
      }
    }
    startButton.disabled = true;
    setMessage('Starting run...');
    setProgress('');
    try {
      const response = await fetch(`/api/batches/${batchId}/run-full?count=${count}`, {
        method: 'POST',
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Failed to start run.');
      }
      runStartedAt = Date.now();
      setMessage(`Run started with ${payload.candidate_count} candidates.`);
      startPolling(payload.run_id);
    } catch (error) {
      setMessage(error.message || 'Unable to start run.', true);
      startButton.disabled = false;
    }
  });
}
