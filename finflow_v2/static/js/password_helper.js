document.addEventListener('DOMContentLoaded', function(){
  function checkPw(el, hintEl){
    const v = el.value || '';
    const checks = [
      {ok: v.length>=12 && v.length<=128, msg: '12–128 chars'},
      {ok: /[A-Z]/.test(v), msg: 'Uppercase'},
      {ok: /[a-z]/.test(v), msg: 'Lowercase'},
      {ok: /\d/.test(v), msg: 'Number'},
      {ok: /[^A-Za-z0-9]/.test(v), msg: 'Special'}
    ];
    hintEl.innerHTML = checks.map(c => `<span style="margin-right:8px;color:${c.ok? '#10b981':'#ef4444'}">${c.msg}</span>`).join('');
    return checks;
  }

  function validateEmailFormat(v){
    return /^[\w\.\-]+@[\w\.\-]+\.[A-Za-z]{2,}$/.test(v);
  }

  const pwFields = document.querySelectorAll('input[type=password]');
  pwFields.forEach(pw => {
    const hint = document.getElementById('pwHint') || document.createElement('div');
    if(!document.getElementById('pwHint')){
      hint.className='muted'; hint.style.marginTop='6px'; hint.style.fontSize='0.9rem';
      pw.parentNode.insertBefore(hint, pw.nextSibling);
    }
    pw.addEventListener('input', () => { checkPw(pw, hint); hint.style.color=''; });
    // Prevent submit if password invalid (for forms with id resetForm or others)
    const form = pw.closest('form');
    if(form){
      form.addEventListener('submit', function(e){
        const checks = checkPw(pw, hint);
        const allOk = checks.every(c=>c.ok);
        if(!allOk){
          e.preventDefault();
          hint.style.color = '#ef4444';
          hint.scrollIntoView({behavior:'smooth', block:'center'});
        }
      });
    }
    checkPw(pw, hint);
  });

  // Email validation for forgot password form
  const forgotForm = document.getElementById('forgotForm');
  if(forgotForm){
    const email = document.getElementById('forgotEmail');
    const hint = document.getElementById('emailHint') || document.createElement('div');
    if(!document.getElementById('emailHint')){
      hint.className='muted'; hint.style.marginTop='6px'; hint.style.fontSize='0.9rem';
      if(email) email.parentNode.insertBefore(hint, email.nextSibling);
    }
    function checkEmail(){
      if(!email) return;
      const val = email.value || '';
      if(val === ''){ hint.textContent = ''; return; }
      if(validateEmailFormat(val)){
        hint.innerHTML = '<span style="color:#10b981">Looks like a valid email</span>';
      } else {
        hint.innerHTML = '<span style="color:#ef4444">Please enter a valid email address</span>';
      }
    }
    if(email){
      email.addEventListener('input', checkEmail);
      forgotForm.addEventListener('submit', function(e){
        if(!validateEmailFormat(email.value || '')){
          e.preventDefault();
          checkEmail();
          email.focus();
        }
      });
      checkEmail();
    }
  }
});
