// Ask for confirmation before submitting any form that carries data-confirm.
document.addEventListener("submit", function (event) {
  var message = event.target.dataset && event.target.dataset.confirm;
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});
