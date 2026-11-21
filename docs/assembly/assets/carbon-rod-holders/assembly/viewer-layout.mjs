// index.html loads this controller to remember the assembly viewer's layout choice.
const layoutButtons = [...document.querySelectorAll('[data-layout-choice]')];
const storageKey = 'magic-wand.assembly.layout';

// Portrait stacks the model and details. Auto waits until both have room side by side.
const landscapeWidth = matchMedia('(min-width: 960px)');
let choice = 'auto';
try {
  const savedChoice = localStorage.getItem(storageKey);
  if (layoutButtons.some(button => button.dataset.layoutChoice === savedChoice)) {
    choice = savedChoice;
  }
} catch {
  // An embedded viewer can still lock its layout when storage is unavailable.
}

function applyLayout() {
  document.body.dataset.layout = choice === 'auto'
    ? (landscapeWidth.matches ? 'landscape' : 'portrait')
    : choice;

  for (const button of layoutButtons) {
    button.setAttribute('aria-pressed', String(button.dataset.layoutChoice === choice));
  }
}

for (const button of layoutButtons) {
  button.addEventListener('click', () => {
    choice = button.dataset.layoutChoice;
    applyLayout();
    try {
      localStorage.setItem(storageKey, choice);
    } catch {
      // The current page keeps the chosen layout without storing it.
    }
  });
}

landscapeWidth.addEventListener('change', applyLayout);
applyLayout();
