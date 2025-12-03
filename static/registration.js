document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registration-form');
  const pwdEl = document.getElementById('password');
  const cpwdEl = document.getElementById('confirmpassword');
  const pwError = document.getElementById('passworderror');
  const emailEl = document.getElementById('emailid');
  const emailErr = document.getElementById('emailerror');

  function checkPasswords() {
    if (!pwdEl || !cpwdEl || !pwError) return true;
    if (pwdEl.value !== cpwdEl.value) {
      pwError.textContent = 'Passwords do not match';
      return false;
    }
    pwError.textContent = '';
    return true;
  }

  if (cpwdEl) cpwdEl.addEventListener('input', checkPasswords);
  if (pwdEl) pwdEl.addEventListener('input', checkPasswords);

  if (form) {
    form.addEventListener('submit', function (e) {
      if (!checkPasswords()) {
        e.preventDefault();
      }
    });
  }

  if (emailEl && emailErr) {
    let emailCheckTimeout;
    emailEl.addEventListener('input', () => {
      emailErr.textContent = '';
      clearTimeout(emailCheckTimeout);
      const email = emailEl.value.trim();

      if (email && email.includes('@')) {
        emailCheckTimeout = setTimeout(async () => {
          try {
            const response = await fetch('/api/check-email', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ email: email })
            });

            const data = await response.json();
            if (data.exists) {
              emailErr.textContent = data.message;
              emailErr.style.color = 'red';
            } else {
              emailErr.textContent = data.message;
              emailErr.style.color = 'green';
            }
          } catch (error) {
            console.error('Error checking email:', error);
          }
        }, 500); // Wait 500ms after user stops typing
      }
    });
  }
});
