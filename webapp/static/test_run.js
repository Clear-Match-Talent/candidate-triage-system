const page = document.querySelector('.page');
const roleId = page?.dataset.roleId;
const batchId = page?.dataset.batchId;

const startButton = document.getElementById('start-test-run');
const message = document.getElementById('test-run-message');

const setMessage = (text, isError = false) => {
  if (!message) {
    return;
  }
  message.textContent = text;
  message.classList.toggle('error', isError);
};

if (startButton && roleId && batchId) {
  startButton.addEventListener('click', async () => {
    startButton.disabled = true;
    setMessage('Creating test run...');
    try {
      const response = await fetch(`/api/roles/${roleId}/test-runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id: batchId }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Failed to create test run.');
      }
      setMessage(
        `Test run created with ${payload.candidate_count} candidates.`
      );
    } catch (error) {
      setMessage(error.message || 'Unable to create test run.', true);
      startButton.disabled = false;
    }
  });
}
