# Revenue Distribution System - Complete Integration Guide

## ✅ Implementation Status

The revenue distribution system is now **fully integrated** with the clients page. The system allows you to distribute contract values across company sectors with a single button click.

---

## 🎯 Features

### 1. **Automatic Revenue Distribution per Client**
- Each client card displays a "Distribuir Receita" button (green with chart icon)
- Button only appears for clients with `contract_value > 0`
- One-click distribution with confirmation dialog showing the breakdown

### 2. **Revenue Split Policy (Automatic)**
When distributing a contract value, it's automatically split:
- **40%** → Pró-labore CEOs (CEO salary fund)
- **30%** → Company Cashbox (Operational funds)
- **20%** → Investment & Expansion (Growth funds)
- **10%** → Accumulated Profit (Reserved earnings)

### 3. **Data Flow**
```
Client List (clientes.html)
  ↓
[Click "Distribuir Receita" button]
  ↓
Confirmation Dialog (shows 40/30/20/10 breakdown)
  ↓
POST /api/clientes/{cid}/distribuir-receita
  ↓
Backend distributes revenue to sector_balance table
  ↓
Activity log records the action
  ↓
Dashboard updates automatically
```

---

## 📋 Files Modified

### **templates/clientes.html**
```html
<!-- Added in AÇÕES column (row 47-56) -->
{% if c.contract_value > 0 %}
<button class="btn btn-sm btn-success" onclick="distribuirReceita({{ c.id }}, '{{ c.name }}', {{ c.contract_value }})" title="Distribuir Receita">
  <i class="fa fa-chart-pie"></i>
</button>
{% endif %}
```

### **JavaScript Function Added**
```javascript
async function distribuirReceita(clientId, clientName, contractValue) {
  // Shows confirmation with breakdown
  // Calls /api/clientes/{clientId}/distribuir-receita
  // Reloads page on success
}
```

### **Backend Endpoint (Already Implemented)**
- **Route**: `POST /api/clientes/{cid}/distribuir-receita`
- **Location**: main.py (line 176)
- **Features**:
  - Fetches client from database
  - Validates contract_value > 0
  - Calls `distribute_revenue()` function
  - Updates sector_balance table
  - Logs action to activity_log
  - Returns JSON with distribution breakdown

---

## 🚀 How to Use

### Step 1: Navigate to Clientes (Clients)
```
Sidebar → COMERCIAL → Clientes
```

### Step 2: View Client with Contract Value
Look for clients with a non-zero "Valor Contrato" field. Each one will show a green button with a chart icon in the AÇÕES column.

### Step 3: Click "Distribuir Receita"
A confirmation dialog appears showing:
- Client name
- Total contract value
- Breakdown for each sector:
  - 💰 Pró-labore (40%): R$ X,XX
  - 🏦 Caixa (30%): R$ X,XX
  - 🚀 Investimento (20%): R$ X,XX
  - 📈 Lucro (10%): R$ X,XX

### Step 4: Confirm
Click OK to distribute, or Cancel to abort.

### Step 5: Verify
- Success message shows the distribution was recorded
- Page reloads to show updated state
- You can view historical distributions in "Distribuição de Receita" dashboard

---

## 📊 Viewing Distribution History

### Dashboard: Distribuição de Receita
```
Sidebar → EMPRESA → Distribuição de Receita
```

This dashboard shows:
1. **Sector Balance Cards** - Running totals for each of the 4 sectors
2. **Manual Distribution Form** - For manual entries (if needed)
3. **Distribution History Table** - Last 50 distributions with:
   - Date
   - Client name
   - Total value
   - Amount for each sector

---

## 🔐 Security & Validation

✅ **Implemented**:
- Client must exist in database
- Contract value must be > 0
- User must be authenticated (require_user())
- Action is logged to activity_log with:
  - User who distributed
  - Client name
  - Amount distributed
  - Timestamp

---

## 📱 Integration with Other Systems

### 1. **Activity Log**
Every distribution is automatically recorded:
```
Action: "distribuiu receita de"
Entity: "cliente"
Details: "{Client Name} - R$ {Amount}"
```

### 2. **Notifications (Future)**
Can be integrated to send notifications when:
- Revenue is distributed for a client
- A sector balance reaches a threshold
- Monthly/quarterly distribution summary

### 3. **Financeiro (Financial Module)**
The distribution data flows to:
- sector_balance table (running totals)
- revenue_distribution table (detailed history)

---

## 🧪 Testing Checklist

- [ ] Navigate to Clientes page
- [ ] Find a client with contract_value > 0
- [ ] Verify green "Distribuir Receita" button is visible
- [ ] Click button
- [ ] Confirm the breakdown dialog shows correct percentages
- [ ] Click OK to distribute
- [ ] Verify success message appears
- [ ] Check "Distribuição de Receita" dashboard
- [ ] Verify sector balances increased by expected amounts
- [ ] Check activity log shows the distribution action

---

## 🔄 Workflow Integration

### Recommended Workflow:
1. **Create Client** → Enter contract value when creating client
2. **Finalize Contract** → Client status changes to "ativo" or "fechado"
3. **Distribute Revenue** → Click "Distribuir Receita" button
4. **Monitor Sectors** → View "Distribuição de Receita" dashboard
5. **Plan Next Actions** → Use sector balances to make company decisions

### Alternative: Auto-Distribution
Future enhancement: Automatically distribute when client status changes to "fechado" (closed)

---

## 💡 Key Benefits

✅ **Automatic Splits** - No manual calculation needed
✅ **Transparent Policy** - Clear 40/30/20/10 breakdown
✅ **Historical Tracking** - All distributions recorded
✅ **Real-time Balances** - Sector totals always current
✅ **Audit Trail** - Activity log shows who did what and when
✅ **Single Click** - Fast and efficient distribution process

---

## 🚧 Future Enhancements

- [ ] Auto-distribution trigger on client status change
- [ ] Bulk distribution for multiple clients
- [ ] Custom percentage policies per contract type
- [ ] Distribution notifications/alerts
- [ ] Export distribution history as PDF/CSV
- [ ] Sector target goals and alerts when exceeded
- [ ] Quarterly/annual distribution summaries

---

## 📞 Support

If you need to:
- **Manually distribute** different amounts → Use "Distribuição de Receita" dashboard
- **Change the 40/30/20/10 policy** → Contact development team
- **View detailed breakdown** → Check "Histórico de Distribuições" table
- **Undo a distribution** → Contact database admin (distribution records are immutable)

---

**Last Updated**: 2026-06-01
**Status**: ✅ Ready for Production
**Version**: 1.0 (Client Integration Complete)
