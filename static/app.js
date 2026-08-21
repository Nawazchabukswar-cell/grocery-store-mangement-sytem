// GroceryHub Web Application JS Logic
let currentTab = 'dashboard';
let currentProducts = [];
let currentCart = [];
let selectedPaymentMethod = 'Cash';
let salesChart = null;
let categoryChart = null;

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNavigation();
  initGlobalSearch();

  // Load initial data
  loadDashboardStats();
  loadProducts();
  loadCategories();
  loadCustomers();
  loadSuppliers();
  loadReports();
});

// Theme Control
function initTheme() {
  const savedTheme = localStorage.getItem('groceryhub_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeButtonText(savedTheme);

  document.getElementById('theme-toggle').addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('groceryhub_theme', newTheme);
    updateThemeButtonText(newTheme);

    // Refresh chart colors if existing
    if (salesChart) loadDashboardStats();
  });
}

function updateThemeButtonText(theme) {
  document.getElementById('theme-text').textContent = theme === 'light' ? 'Light Mode' : 'Dark Mode';
}

// Navigation & Tabs
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const targetTab = item.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));

  const navLink = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
  if (navLink) navLink.classList.add('active');

  const viewSec = document.getElementById(`${tabId}-view`);
  if (viewSec) viewSec.classList.add('active');

  if (tabId === 'dashboard') loadDashboardStats();
  if (tabId === 'products') loadProducts();
  if (tabId === 'pos') renderPosProducts();
  if (tabId === 'reports') loadReports();
}

// Global Search
function initGlobalSearch() {
  const searchInput = document.getElementById('global-search');
  searchInput.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') {
      const query = searchInput.value.trim().toLowerCase();
      if (!query) return;
      switchTab('products');
      document.getElementById('product-search').value = query;
      loadProducts(query);
    }
  });
}

// Dashboard Analytics & Charts
async function loadDashboardStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();

    document.getElementById('stat-total-sales').textContent = `₹${data.total_sales.toFixed(2)}`;
    document.getElementById('stat-total-profit').textContent = `₹${data.total_profit.toFixed(2)}`;
    document.getElementById('stat-total-orders').textContent = data.total_orders;
    document.getElementById('stat-low-stock').textContent = data.low_stock_items;

    document.getElementById('stat-cash-sales').textContent = `₹${data.cash_sales.toFixed(2)}`;
    document.getElementById('stat-online-sales').textContent = `₹${data.online_sales.toFixed(2)}`;
    document.getElementById('stat-card-sales').textContent = `₹${data.card_sales.toFixed(2)}`;

    renderSalesChart(data.chart_labels, data.chart_data);
    renderCategoryChart(data.cat_labels, data.cat_data);
    loadRecentTransactions();
  } catch (err) {
    console.error("Failed to load dashboard stats", err);
  }
}

function renderSalesChart(labels, dataValues) {
  const ctx = document.getElementById('salesOverviewChart').getContext('2d');
  if (salesChart) salesChart.destroy();

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)';
  const textColor = isDark ? '#94a3b8' : '#64748b';

  salesChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Sales (₹)',
        data: dataValues,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.12)',
        borderWidth: 3,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: '#10b981',
        pointRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: textColor } },
        y: { grid: { color: gridColor }, ticks: { color: textColor } }
      }
    }
  });
}

function renderCategoryChart(labels, dataValues) {
  const ctx = document.getElementById('categoryChart').getContext('2d');
  if (categoryChart) categoryChart.destroy();

  categoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: dataValues,
        backgroundColor: ['#10b981', '#6366f1', '#f59e0b', '#3b82f6', '#ec4899', '#8b5cf6'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
      cutout: '70%'
    }
  });
}

async function loadRecentTransactions() {
  try {
    const res = await fetch('/api/sales');
    const sales = await res.json();
    const tbody = document.getElementById('recent-transactions-body');
    tbody.innerHTML = '';

    if (sales.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center">No transactions recorded yet.</td></tr>`;
      return;
    }

    sales.slice(0, 5).forEach(s => {
      const pMethod = s.payment_method || 'Cash';
      let badgeClass = 'badge-cash';
      if (pMethod.includes('Online')) badgeClass = 'badge-online';
      if (pMethod.includes('Card')) badgeClass = 'badge-card';

      const row = document.createElement('tr');
      row.innerHTML = `
        <td><strong>${s.invoice_no}</strong></td>
        <td>${s.customer_name || 'Walk-in Customer'}</td>
        <td>${s.sale_date}</td>
        <td><strong>₹${s.total_amount.toFixed(2)}</strong></td>
        <td><span class="badge ${badgeClass}">${pMethod}</span></td>
        <td><span class="badge badge-success">Completed</span></td>
        <td><button class="btn btn-sm btn-secondary" onclick="viewInvoiceModal('${s.invoice_no}')"><i class="fa-solid fa-eye"></i></button></td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    console.error("Failed to load transactions", err);
  }
}

// Products Management
async function loadProducts(query = '') {
  try {
    const res = await fetch(`/api/products?q=${encodeURIComponent(query)}`);
    currentProducts = await res.json();

    const tbody = document.getElementById('products-table-body');
    tbody.innerHTML = '';

    currentProducts.forEach(p => {
      const row = document.createElement('tr');
      const isLowStock = p.quantity <= 10;
      const defaultImg = "https://images.unsplash.com/photo-1542838132-92c53300491e?w=100";

      row.innerHTML = `
        <td>#${p.id}</td>
        <td><img src="${p.image_url || defaultImg}" alt="${p.name}" style="width:36px;height:36px;border-radius:6px;object-fit:cover;" /></td>
        <td><strong>${p.name}</strong></td>
        <td>${p.category || 'General'}</td>
        <td>₹${p.price.toFixed(2)}</td>
        <td>
          <span class="badge ${isLowStock ? 'badge-danger' : 'badge-success'}">
            ${p.quantity} units ${isLowStock ? '(Low Stock)' : ''}
          </span>
        </td>
        <td>${p.supplier || '-'}</td>
        <td>${p.expiry_date || '-'}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick='openProductModal(${JSON.stringify(p)})'><i class="fa-solid fa-pen"></i></button>
          <button class="btn btn-sm btn-danger" onclick="deleteProduct(${p.id})"><i class="fa-solid fa-trash"></i></button>
        </td>
      `;
      tbody.appendChild(row);
    });

    renderLowStockTable();
  } catch (err) {
    console.error("Failed to load products", err);
  }
}

function renderLowStockTable() {
  const tbody = document.getElementById('low-stock-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  const lowStockProds = currentProducts.filter(p => p.quantity <= 10);
  if (lowStockProds.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center">All inventory levels are healthy!</td></tr>`;
    return;
  }

  lowStockProds.forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${p.name}</strong></td>
      <td>${p.category || 'General'}</td>
      <td><strong style="color:var(--color-danger)">${p.quantity}</strong></td>
      <td>10</td>
      <td><span class="badge badge-danger">Reorder Required</span></td>
      <td><button class="btn btn-sm btn-primary" onclick='openProductModal(${JSON.stringify(p)})'>Restock</button></td>
    `;
    tbody.appendChild(tr);
  });
}

function openProductModal(product = null) {
  document.getElementById('prod-edit-id').value = product ? product.id : '';
  document.getElementById('prod-name').value = product ? product.name : '';
  document.getElementById('prod-category').value = product ? (product.category || '') : '';
  document.getElementById('prod-price').value = product ? product.price : '';
  document.getElementById('prod-quantity').value = product ? product.quantity : '';
  document.getElementById('prod-supplier').value = product ? (product.supplier || '') : '';
  document.getElementById('prod-expiry').value = product ? (product.expiry_date || '') : '';
  document.getElementById('prod-image').value = product ? (product.image_url || '') : '';
  document.getElementById('product-modal-title').textContent = product ? 'Edit Product' : 'Add New Product';

  document.getElementById('product-modal').classList.add('active');
}

async function saveProduct() {
  const id = document.getElementById('prod-edit-id').value;
  const name = document.getElementById('prod-name').value.trim();
  const category = document.getElementById('prod-category').value.trim();
  const price = parseFloat(document.getElementById('prod-price').value);
  const quantity = parseInt(document.getElementById('prod-quantity').value);
  const supplier = document.getElementById('prod-supplier').value.trim();
  const expiry_date = document.getElementById('prod-expiry').value;
  const image_url = document.getElementById('prod-image').value.trim();

  if (!name || isNaN(price) || isNaN(quantity)) {
    alert("Please fill in valid name, price, and quantity.");
    return;
  }

  const payload = { name, category, price, quantity, supplier, expiry_date, image_url };
  const method = id ? 'PUT' : 'POST';
  const url = id ? `/api/products/${id}` : '/api/products';

  const res = await fetch(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    closeModal('product-modal');
    loadProducts();
    loadDashboardStats();
  } else {
    alert("Error saving product.");
  }
}

async function deleteProduct(id) {
  if (!confirm("Are you sure you want to delete this product?")) return;
  const res = await fetch(`/api/products/${id}`, { method: 'DELETE' });
  if (res.ok) {
    loadProducts();
    loadDashboardStats();
  }
}

// Categories Management
async function loadCategories() {
  try {
    const res = await fetch('/api/categories');
    const cats = await res.json();

    const grid = document.getElementById('categories-grid');
    const filterSelect = document.getElementById('product-cat-filter');
    const pillsBox = document.getElementById('pos-category-pills');

    if (grid) grid.innerHTML = '';
    if (filterSelect) filterSelect.innerHTML = '<option value="All">All Categories</option>';
    if (pillsBox) pillsBox.innerHTML = '<button class="pill active" onclick="filterPosCategory(\'All\', this)">All</button>';

    cats.forEach(c => {
      if (grid) {
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.innerHTML = `
          <div class="stat-icon profit"><i class="fa-solid fa-folder-open"></i></div>
          <div>
            <h3>${c.name}</h3>
            <small>${c.description || 'Category'}</small>
          </div>
        `;
        grid.appendChild(card);
      }

      if (filterSelect) {
        const opt = document.createElement('option');
        opt.value = c.name;
        opt.textContent = c.name;
        filterSelect.appendChild(opt);
      }

      if (pillsBox) {
        const pill = document.createElement('button');
        pill.className = 'pill';
        pill.textContent = c.name;
        pill.onclick = () => filterPosCategory(c.name, pill);
        pillsBox.appendChild(pill);
      }
    });
  } catch (err) {
    console.error("Failed to load categories", err);
  }
}

function openCategoryModal() {
  document.getElementById('cat-name').value = '';
  document.getElementById('cat-desc').value = '';
  document.getElementById('category-modal').classList.add('active');
}

async function saveCategory() {
  const name = document.getElementById('cat-name').value.trim();
  const description = document.getElementById('cat-desc').value.trim();

  if (!name) {
    alert("Category name is required.");
    return;
  }

  const res = await fetch('/api/categories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description })
  });

  if (res.ok) {
    closeModal('category-modal');
    loadCategories();
  }
}

// POS Billing & Cart Logic
function renderPosProducts(category = 'All', search = '') {
  const grid = document.getElementById('pos-products-grid');
  if (!grid) return;
  grid.innerHTML = '';

  let filtered = currentProducts;
  if (category !== 'All') {
    filtered = filtered.filter(p => p.category === category);
  }
  if (search) {
    filtered = filtered.filter(p => p.name.toLowerCase().includes(search.toLowerCase()));
  }

  const defaultImg = "https://images.unsplash.com/photo-1542838132-92c53300491e?w=200";

  filtered.forEach(p => {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.onclick = () => addToCart(p);
    card.innerHTML = `
      <img src="${p.image_url || defaultImg}" alt="${p.name}" class="product-img" />
      <div class="product-title">${p.name}</div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span class="product-price">₹${p.price.toFixed(2)}</span>
        <small style="color:var(--text-muted);">Stock: ${p.quantity}</small>
      </div>
    `;
    grid.appendChild(card);
  });

  // Search input binding
  const searchInput = document.getElementById('pos-search');
  if (searchInput) {
    searchInput.onkeyup = () => renderPosProducts(category, searchInput.value);
  }
}

function filterPosCategory(category, pillEl) {
  document.querySelectorAll('#pos-category-pills .pill').forEach(p => p.classList.remove('active'));
  if (pillEl) pillEl.classList.add('active');
  renderPosProducts(category);
}

function addToCart(product) {
  if (product.quantity <= 0) {
    alert(`Out of stock! '${product.name}' is currently unavailable.`);
    return;
  }

  const existing = currentCart.find(i => i.product_id === product.id);
  if (existing) {
    if (existing.quantity + 1 > product.quantity) {
      alert(`Cannot add more. Only ${product.quantity} units in stock.`);
      return;
    }
    existing.quantity++;
    existing.item_total = existing.quantity * existing.price;
  } else {
    currentCart.push({
      product_id: product.id,
      product_name: product.name,
      price: product.price,
      quantity: 1,
      item_total: product.price
    });
  }

  renderCart();
}

function updateCartQty(productId, delta) {
  const item = currentCart.find(i => i.product_id === productId);
  if (!item) return;

  const product = currentProducts.find(p => p.id === productId);

  if (delta > 0 && product && item.quantity + delta > product.quantity) {
    alert(`Insufficient stock. Maximum available: ${product.quantity}`);
    return;
  }

  item.quantity += delta;
  if (item.quantity <= 0) {
    currentCart = currentCart.filter(i => i.product_id !== productId);
  } else {
    item.item_total = item.quantity * item.price;
  }
  renderCart();
}

function clearCart() {
  currentCart = [];
  renderCart();
}

function renderCart() {
  const container = document.getElementById('cart-items-container');
  container.innerHTML = '';

  if (currentCart.length === 0) {
    container.innerHTML = `
      <div class="empty-cart-state">
        <i class="fa-solid fa-basket-shopping"></i>
        <p>Cart is empty. Click on products to add.</p>
      </div>
    `;
    renderCartSummary();
    return;
  }

  currentCart.forEach(item => {
    const row = document.createElement('div');
    row.className = 'cart-item-row';
    row.innerHTML = `
      <div>
        <strong>${item.product_name}</strong>
        <div style="font-size:0.8rem;color:var(--text-muted);">₹${item.price.toFixed(2)} each</div>
      </div>
      <div class="qty-controls">
        <button class="qty-btn" onclick="updateCartQty(${item.product_id}, -1)">-</button>
        <strong>${item.quantity}</strong>
        <button class="qty-btn" onclick="updateCartQty(${item.product_id}, 1)">+</button>
      </div>
      <div style="font-weight:700;">₹${item.item_total.toFixed(2)}</div>
    `;
    container.appendChild(row);
  });

  renderCartSummary();
}

function calcCartTotals() {
  const subtotal = currentCart.reduce((sum, item) => sum + item.item_total, 0);
  const discount = parseFloat(document.getElementById('cart-discount').value) || 0;
  const taxRate = parseFloat(document.getElementById('cart-tax-rate').value) || 0;
  const tax = (subtotal - discount) * (taxRate / 100.0);
  const grandTotal = Math.max(0, subtotal - discount + tax);

  return { subtotal, discount, tax, grandTotal };
}

function renderCartSummary() {
  const { subtotal, discount, tax, grandTotal } = calcCartTotals();

  document.getElementById('cart-subtotal').textContent = `₹${subtotal.toFixed(2)}`;
  document.getElementById('cart-grand-total').textContent = `₹${grandTotal.toFixed(2)}`;
}

// Payment Modal Logic
function openPaymentModal() {
  if (currentCart.length === 0) {
    alert("Please add at least one item to the cart before checkout.");
    return;
  }

  const { grandTotal } = calcCartTotals();
  document.getElementById('modal-payable-amount').textContent = `₹${grandTotal.toFixed(2)}`;
  selectPaymentMethod('Cash');

  document.getElementById('payment-modal').classList.add('active');
}

function selectPaymentMethod(method) {
  selectedPaymentMethod = method;

  document.querySelectorAll('.pay-tab').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-method') === method);
  });

  document.getElementById('pay-sec-cash').classList.toggle('active', method === 'Cash');
  document.getElementById('pay-sec-online').classList.toggle('active', method === 'Online / UPI');
  document.getElementById('pay-sec-card').classList.toggle('active', method === 'Card');

  if (method === 'Cash') calcCashChange();
}

function calcCashChange() {
  const { grandTotal } = calcCartTotals();
  const tendered = parseFloat(document.getElementById('cash-tendered-input').value) || 0;
  const change = tendered - grandTotal;
  const changeEl = document.getElementById('cash-change-val');

  if (change >= 0) {
    changeEl.textContent = `₹${change.toFixed(2)}`;
    changeEl.style.color = 'var(--color-success)';
  } else {
    changeEl.textContent = `Short ₹${Math.abs(change).toFixed(2)}`;
    changeEl.style.color = 'var(--color-danger)';
  }
}

async function processCheckout() {
  const { subtotal, discount, tax, grandTotal } = calcCartTotals();
  const customerName = document.getElementById('cart-customer-name').value.trim() || 'Walk-in Customer';

  if (selectedPaymentMethod === 'Cash') {
    const tendered = parseFloat(document.getElementById('cash-tendered-input').value) || 0;
    if (tendered < grandTotal) {
      alert(`Cash tendered (₹${tendered.toFixed(2)}) is less than grand total (₹${grandTotal.toFixed(2)}).`);
      return;
    }
  }

  const payload = {
    cart_items: currentCart,
    payment_method: selectedPaymentMethod,
    discount: discount,
    tax: tax,
    customer_name: customerName
  };

  try {
    const res = await fetch('/api/sales', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok && data.success) {
      closeModal('payment-modal');
      showInvoiceReceipt(data.sale);
      clearCart();
      loadDashboardStats();
      loadProducts();
    } else {
      alert(`Checkout failed: ${data.error}`);
    }
  } catch (err) {
    alert("Failed to process checkout. Server error.");
  }
}

function showInvoiceReceipt(sale) {
  const content = document.getElementById('invoice-receipt-content');
  const itemsHtml = currentCart.map(item => `
    <tr>
      <td>${item.product_name}</td>
      <td class="text-center">${item.quantity}</td>
      <td class="text-right">₹${item.price.toFixed(2)}</td>
      <td class="text-right">₹${item.item_total.toFixed(2)}</td>
    </tr>
  `).join('');

  content.innerHTML = `
    <div style="text-align:center;margin-bottom:1rem;">
      <h2 style="margin:0;font-family:var(--font-heading);">GroceryHub Store</h2>
      <small>123 Main Street, Commerce Zone | Tel: +91 98765 00000</small>
    </div>
    <hr style="border-color:var(--border-color);" />
    <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin:0.75rem 0;">
      <div>
        <strong>Invoice No:</strong> ${sale.invoice_no}<br>
        <strong>Customer:</strong> ${sale.customer_name}
      </div>
      <div style="text-align:right;">
        <strong>Date:</strong> ${sale.sale_date}<br>
        <strong>Payment Method:</strong> <span class="badge badge-success">${sale.payment_method}</span>
      </div>
    </div>

    <table class="data-table" style="margin:1rem 0;">
      <thead>
        <tr>
          <th>Product</th>
          <th class="text-center">Qty</th>
          <th class="text-right">Price</th>
          <th class="text-right">Total</th>
        </tr>
      </thead>
      <tbody>
        ${itemsHtml}
      </tbody>
    </table>

    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.3rem;font-size:0.9rem;">
      <div>Subtotal: <strong>₹${sale.subtotal.toFixed(2)}</strong></div>
      <div>Discount: <strong>-₹${sale.discount.toFixed(2)}</strong></div>
      <div>Tax: <strong>+₹${sale.tax.toFixed(2)}</strong></div>
      <div style="font-size:1.2rem;color:var(--color-primary);margin-top:0.3rem;">
        Grand Total: <strong>₹${sale.grand_total.toFixed(2)}</strong>
      </div>
    </div>
  `;

  document.getElementById('invoice-modal').classList.add('active');
}

async function viewInvoiceModal(invoiceNo) {
  const res = await fetch(`/api/sales/${invoiceNo}`);
  const data = await res.json();
  if (res.ok) {
    const sale = data.sale;
    const items = data.items;

    const itemsHtml = items.map(item => `
      <tr>
        <td>${item.product_name}</td>
        <td class="text-center">${item.quantity}</td>
        <td class="text-right">₹${item.price.toFixed(2)}</td>
        <td class="text-right">₹${item.item_total.toFixed(2)}</td>
      </tr>
    `).join('');

    const content = document.getElementById('invoice-receipt-content');
    content.innerHTML = `
      <div style="text-align:center;margin-bottom:1rem;">
        <h2 style="margin:0;">GroceryHub Store</h2>
        <small>Invoice Audit Details</small>
      </div>
      <hr style="border-color:var(--border-color);" />
      <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin:0.75rem 0;">
        <div>
          <strong>Invoice No:</strong> ${sale.invoice_no}<br>
          <strong>Customer:</strong> ${sale.customer_name || 'Walk-in Customer'}
        </div>
        <div style="text-align:right;">
          <strong>Date:</strong> ${sale.sale_date}<br>
          <strong>Payment Method:</strong> <span class="badge badge-success">${sale.payment_method || 'Cash'}</span>
        </div>
      </div>

      <table class="data-table" style="margin:1rem 0;">
        <thead>
          <tr>
            <th>Product</th>
            <th class="text-center">Qty</th>
            <th class="text-right">Price</th>
            <th class="text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          ${itemsHtml}
        </tbody>
      </table>

      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.3rem;font-size:0.9rem;">
        <div style="font-size:1.2rem;color:var(--color-primary);">
          Grand Total: <strong>₹${sale.total_amount.toFixed(2)}</strong>
        </div>
      </div>
    `;

    document.getElementById('invoice-modal').classList.add('active');
  }
}

// Customers & Suppliers & Reports
async function loadCustomers() {
  try {
    const res = await fetch('/api/customers');
    const customers = await res.json();

    const tbody = document.getElementById('customers-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    customers.forEach(c => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>#${c.id}</td>
        <td><strong>${c.name}</strong></td>
        <td>${c.phone || '-'}</td>
        <td>${c.email || '-'}</td>
        <td><strong>₹${(c.total_purchases || 0).toFixed(2)}</strong></td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    console.error("Failed to load customers", err);
  }
}

async function loadSuppliers() {
  try {
    const res = await fetch('/api/suppliers');
    const suppliers = await res.json();

    const tbody = document.getElementById('suppliers-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    suppliers.forEach(s => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>#${s.id}</td>
        <td><strong>${s.name}</strong></td>
        <td>${s.contact_person || '-'}</td>
        <td>${s.phone || '-'}</td>
        <td>${s.email || '-'}</td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    console.error("Failed to load suppliers", err);
  }
}

async function loadReports() {
  try {
    const res = await fetch('/api/sales');
    const sales = await res.json();

    const tbody = document.getElementById('reports-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    sales.forEach(s => {
      const pMethod = s.payment_method || 'Cash';
      let badgeClass = 'badge-cash';
      if (pMethod.includes('Online')) badgeClass = 'badge-online';
      if (pMethod.includes('Card')) badgeClass = 'badge-card';

      const row = document.createElement('tr');
      row.innerHTML = `
        <td><strong>${s.invoice_no}</strong></td>
        <td>${s.sale_date}</td>
        <td>${s.customer_name || 'Walk-in Customer'}</td>
        <td>₹${(s.discount || 0).toFixed(2)}</td>
        <td>₹${(s.tax || 0).toFixed(2)}</td>
        <td><strong>₹${s.total_amount.toFixed(2)}</strong></td>
        <td><span class="badge ${badgeClass}">${pMethod}</span></td>
        <td><button class="btn btn-sm btn-secondary" onclick="viewInvoiceModal('${s.invoice_no}')"><i class="fa-solid fa-eye"></i></button></td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    console.error("Failed to load reports", err);
  }
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove('active');
}
