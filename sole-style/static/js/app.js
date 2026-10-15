(() => {
  const menu = document.getElementById('mobileMenu');
  const nav = document.getElementById('mainNav');
  menu?.addEventListener('click', () => nav?.classList.toggle('open'));

  const toggle = document.getElementById('filterToggle');
  toggle?.addEventListener('click', () => {
    const sidebar = document.querySelector('.filter-sidebar');
    sidebar?.classList.toggle('open');
    if (sidebar?.classList.contains('open')) sidebar.scrollIntoView({behavior: 'smooth', block: 'start'});
  });

  document.querySelectorAll('.password-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.target);
      if (!input) return;
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.innerHTML = show ? '<i class="fa-regular fa-eye-slash"></i>' : '<i class="fa-regular fa-eye"></i>';
      button.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    });
  });

  const imageInput = document.getElementById('imageInput');
  imageInput?.addEventListener('change', () => {
    const file = imageInput.files?.[0];
    const preview = document.getElementById('imagePreview');
    const placeholder = document.getElementById('imagePlaceholder');
    if (!file || !preview) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      imageInput.value = '';
      window.alert('Choose a JPG, PNG or WebP image.');
      return;
    }
    preview.src = URL.createObjectURL(file);
    preview.classList.remove('hidden');
    placeholder?.classList.add('hidden');
  });

  const variantData = document.getElementById('variantData');
  const selectedVariant = document.getElementById('selectedVariant');
  if (variantData && selectedVariant) {
    const variants = JSON.parse(variantData.textContent || '[]');
    const sizeInputs = [...document.querySelectorAll('input[name="size_choice"]')];
    const colorInputs = [...document.querySelectorAll('input[name="color_choice"]')];
    const quantitySelect = document.getElementById('variantQuantity');
    const addButton = document.querySelector('.add-to-bag');
    const updateVariant = () => {
      const size = sizeInputs.find((input) => input.checked)?.value;
      const color = colorInputs.find((input) => input.checked)?.value;
      const variant = variants.find((item) => item.size === size && item.color === color && item.stock > 0);
      selectedVariant.value = variant ? variant.id : '';
      if (quantitySelect) {
        quantitySelect.replaceChildren();
        for (let qty = 1; qty <= Math.min(5, variant?.stock || 0); qty++) {
          const option = document.createElement('option'); option.value = String(qty); option.textContent = String(qty); quantitySelect.append(option);
        }
      }
      if (addButton) addButton.disabled = !variant;
    };
    [...sizeInputs, ...colorInputs].forEach((input) => input.addEventListener('change', updateVariant));
    updateVariant();
  }

  const toast = (message) => {
    const node = document.getElementById('toast');
    if (!node) return;
    node.textContent = message;
    node.classList.add('show');
    window.setTimeout(() => node.classList.remove('show'), 2600);
  };
  document.querySelectorAll('.quick-wish button').forEach((button) => button.addEventListener('click', () => {
    button.classList.add('wish-tap');
    window.setTimeout(() => button.classList.remove('wish-tap'), 450);
  }));

  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); }
    }), {threshold: 0.08});
    document.querySelectorAll('.reveal').forEach((item) => observer.observe(item));
  } else document.querySelectorAll('.reveal').forEach((item) => item.classList.add('visible'));

  document.querySelectorAll('.form-stack, .detail-form, .booking-admin-update').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const button = form.querySelector('button[type="submit"],button:not([type])');
      if (!button || !form.checkValidity()) return;
      button.dataset.original = button.innerHTML;
      button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> One moment';
      button.disabled = true;
      window.setTimeout(() => { if (button.isConnected) { button.disabled = false; button.innerHTML = button.dataset.original; } }, 7000);
    });
  });

  if (window.io && document.body.dataset.userLoggedIn === 'true') {
    const socket = window.io({transports: ['websocket', 'polling']});
    socket.on('notification', (note) => {
      toast(`${note.title}: ${note.message}`);
      const badge = document.getElementById('unreadCount');
      if (badge) badge.textContent = String(Number(badge.textContent || '0') + 1);
    });
  }

  const chartEl = document.getElementById('bookingChart');
  const dataEl = document.getElementById('trendData');
  if (chartEl && dataEl) {
    const rows = JSON.parse(dataEl.textContent || '[]');
    drawChart(chartEl, rows.map((r) => r[0]), rows.map((r) => r[1]));
  }
  function drawChart(canvas, labels, values) {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr; canvas.height = 180 * dpr;
    ctx.scale(dpr, dpr);
    const w = rect.width, h = 180, pad = {l: 25, r: 8, t: 12, b: 24};
    const max = Math.max(4, ...values);
    ctx.font = '9px DM Sans, sans-serif'; ctx.fillStyle = '#999a92'; ctx.strokeStyle = '#efeee8'; ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
      const y = pad.t + (h - pad.t - pad.b) * i / 3;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
      ctx.fillText(String(Math.ceil(max * (3 - i) / 3)), 2, y + 3);
    }
    const points = values.map((v, i) => ({x: pad.l + (values.length <= 1 ? (w-pad.l-pad.r)/2 : (w-pad.l-pad.r)*i/(values.length-1)), y: h-pad.b-(h-pad.t-pad.b)*(v/max)}));
    if (points.length) {
      ctx.beginPath(); points.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
      ctx.strokeStyle = '#dc805c'; ctx.lineWidth = 2; ctx.stroke();
      points.forEach((p) => { ctx.beginPath(); ctx.arc(p.x, p.y, 3, 0, Math.PI*2); ctx.fillStyle = '#dc805c'; ctx.fill(); });
      const skip = Math.max(1, Math.ceil(labels.length/5));
      labels.forEach((label, i) => { if (i % skip === 0 || i === labels.length-1) { ctx.fillStyle='#92938b'; ctx.fillText(String(label).slice(5), points[i].x-12, h-6); } });
    } else { ctx.fillStyle = '#999a92'; ctx.fillText('No reservation activity yet', pad.l+5, 65); }
  }
})();
