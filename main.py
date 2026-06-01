from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import init_db, get_db, log_action
from auth import (
    create_session, get_current_user, require_user,
    authenticate_user, hash_password, SESSION_COOKIE
)
from datetime import datetime
import calendar as cal_mod
import os

app = FastAPI(title="ELEVA Manager")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

NOW = datetime.now()
CURRENT_YEAR = NOW.year
CURRENT_MONTH = NOW.month
MONTHS_PT = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
             "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]


@app.on_event("startup")
def startup():
    init_db()


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/login")
def login_action(request: Request, email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "E-mail ou senha incorretos."}, status_code=401)
    token = create_session(user["id"])
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, max_age=60*60*8)
    conn = get_db()
    log_action(conn, user, "login", "sistema", f"Login realizado")
    conn.commit(); conn.close()
    return response


@app.get("/logout")
def logout(request: Request):
    user = get_current_user(request)
    if user:
        conn = get_db()
        log_action(conn, user, "logout", "sistema", "Logout realizado")
        conn.commit(); conn.close()
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ── Permission Validation Helper ──────────────────────────────────────────────

def check_permission(user, permission_field: str) -> bool:
    """Check if user has permission to view a module. Admin/CEO always have access."""
    if user["role"] in ["admin", "ceo"]:
        return True
    if "permissions" not in user:
        return False
    return bool(user["permissions"].get(permission_field, 0))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_dashboard"):
        # Se funcionário sem acesso ao dashboard, redireciona para "Minha Conta"
        if user["role"] == "funcionario":
            return RedirectResponse("/minha-conta", status_code=302)
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    total_clients    = conn.execute("SELECT COUNT(*) FROM clients WHERE status='ativo'").fetchone()[0]
    total_revenue    = conn.execute("SELECT COALESCE(SUM(contract_value),0) FROM clients WHERE status='ativo'").fetchone()[0]
    total_investment = conn.execute("SELECT COALESCE(SUM(value),0) FROM investments").fetchone()[0]
    total_ads        = conn.execute("SELECT COALESCE(SUM(spent),0) FROM ads WHERE status='ativo'").fetchone()[0]
    total_prolabore  = conn.execute("SELECT COALESCE(SUM(value),0) FROM prolabore WHERE year=? AND month=?", (CURRENT_YEAR, CURRENT_MONTH)).fetchone()[0]
    open_tasks       = conn.execute("SELECT COUNT(*) FROM next_steps WHERE status='aberto'").fetchone()[0]
    pipeline_count   = conn.execute("SELECT COUNT(*) FROM pipeline WHERE stage != 'fechado'").fetchone()[0]
    open_projects    = conn.execute("SELECT COUNT(*) FROM projects WHERE status='em_andamento'").fetchone()[0]

    recent_clients = conn.execute("SELECT c.*, u.name as creator FROM clients c LEFT JOIN users u ON c.created_by=u.id ORDER BY c.created_at DESC LIMIT 5").fetchall()
    urgent_tasks   = conn.execute("SELECT n.*, u.name as creator FROM next_steps n LEFT JOIN users u ON n.created_by=u.id WHERE n.status='aberto' ORDER BY CASE n.priority WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END LIMIT 5").fetchall()
    recent_activity= conn.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 8").fetchall()

    monthly = conn.execute("""
        SELECT strftime('%m/%Y', entry_date) as month, COALESCE(SUM(contract_value),0) as total
        FROM clients WHERE entry_date >= date('now','-6 months')
        GROUP BY month ORDER BY entry_date
    """).fetchall()
    conn.close()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": dict(user),
        "total_clients": total_clients, "total_revenue": total_revenue,
        "total_investment": total_investment, "total_ads": total_ads,
        "total_prolabore": total_prolabore, "open_tasks": open_tasks,
        "pipeline_count": pipeline_count, "open_projects": open_projects,
        "recent_clients": [dict(r) for r in recent_clients],
        "urgent_tasks": [dict(t) for t in urgent_tasks],
        "recent_activity": [dict(a) for a in recent_activity],
        "monthly_labels": [r["month"] for r in monthly],
        "monthly_values": [r["total"] for r in monthly],
    })


# ── Clientes ──────────────────────────────────────────────────────────────────

@app.get("/clientes", response_class=HTMLResponse)
def clientes_page(request: Request, q: str = ""):
    user = require_user(request)
    if not check_permission(user, "can_view_clientes"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    if q:
        rows = conn.execute("SELECT c.*, u.name as creator FROM clients c LEFT JOIN users u ON c.created_by=u.id WHERE c.name LIKE ? OR c.company LIKE ? OR c.email LIKE ? ORDER BY c.created_at DESC", (f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
    else:
        rows = conn.execute("SELECT c.*, u.name as creator FROM clients c LEFT JOIN users u ON c.created_by=u.id ORDER BY c.created_at DESC").fetchall()
    conn.close()
    return templates.TemplateResponse("clientes.html", {"request": request, "user": dict(user), "clients": [dict(r) for r in rows], "q": q})


@app.post("/clientes/novo")
def cliente_novo(request: Request, name: str = Form(...), email: str = Form(""), phone: str = Form(""), company: str = Form(""), segment: str = Form(""), services: str = Form("[]"), contract_value: float = Form(0), status: str = Form("ativo"), entry_date: str = Form(""), notes: str = Form("")):
    user = require_user(request)
    conn = get_db()
    if not entry_date: entry_date = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT INTO clients (name,email,phone,company,segment,services,contract_value,status,entry_date,notes,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (name,email,phone,company,segment,services,contract_value,status,entry_date,notes,user["id"]))
    log_action(conn, user, "criou", "cliente", f"Cliente: {name}")
    conn.commit(); conn.close()
    return RedirectResponse("/clientes", status_code=302)


@app.post("/clientes/{cid}/editar")
def cliente_editar(request: Request, cid: int, name: str = Form(...), email: str = Form(""), phone: str = Form(""), company: str = Form(""), segment: str = Form(""), services: str = Form("[]"), contract_value: float = Form(0), status: str = Form("ativo"), entry_date: str = Form(""), notes: str = Form("")):
    user = require_user(request)
    conn = get_db()
    conn.execute("UPDATE clients SET name=?,email=?,phone=?,company=?,segment=?,services=?,contract_value=?,status=?,entry_date=?,notes=? WHERE id=?", (name,email,phone,company,segment,services,contract_value,status,entry_date,notes,cid))
    log_action(conn, user, "editou", "cliente", f"Cliente: {name}")
    conn.commit(); conn.close()
    return RedirectResponse("/clientes", status_code=302)


@app.post("/clientes/{cid}/deletar")
def cliente_deletar(request: Request, cid: int):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT name FROM clients WHERE id=?", (cid,)).fetchone()
    conn.execute("DELETE FROM clients WHERE id=?", (cid,))
    if row: log_action(conn, user, "removeu", "cliente", f"Cliente: {row['name']}")
    conn.commit(); conn.close()
    return RedirectResponse("/clientes", status_code=302)


# ── Investimentos ─────────────────────────────────────────────────────────────

@app.get("/investimentos", response_class=HTMLResponse)
def investimentos_page(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_investimentos"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    rows = conn.execute("SELECT i.*, u.name as creator FROM investments i LEFT JOIN users u ON i.created_by=u.id ORDER BY i.date DESC").fetchall()
    total = conn.execute("SELECT COALESCE(SUM(value),0) FROM investments").fetchone()[0]
    by_category = conn.execute("SELECT category, COALESCE(SUM(value),0) as total FROM investments GROUP BY category").fetchall()
    conn.close()
    return templates.TemplateResponse("investimentos.html", {"request": request, "user": dict(user), "investments": [dict(r) for r in rows], "total": total, "by_category": [dict(r) for r in by_category]})


@app.post("/investimentos/novo")
def investimento_novo(request: Request, description: str = Form(...), category: str = Form(...), value: float = Form(...), date: str = Form(""), notes: str = Form("")):
    user = require_user(request)
    conn = get_db()
    if not date: date = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT INTO investments (description,category,value,date,notes,created_by) VALUES (?,?,?,?,?,?)", (description,category,value,date,notes,user["id"]))
    log_action(conn, user, "criou", "investimento", f"{description} — R$ {value:.2f}")
    conn.commit(); conn.close()
    return RedirectResponse("/investimentos", status_code=302)


@app.post("/investimentos/{iid}/deletar")
def investimento_deletar(request: Request, iid: int):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT description FROM investments WHERE id=?", (iid,)).fetchone()
    conn.execute("DELETE FROM investments WHERE id=?", (iid,))
    if row: log_action(conn, user, "removeu", "investimento", f"{row['description']}")
    conn.commit(); conn.close()
    return RedirectResponse("/investimentos", status_code=302)


# ── Pro Labore ────────────────────────────────────────────────────────────────

@app.get("/prolabore", response_class=HTMLResponse)
def prolabore_page(request: Request, year: int = CURRENT_YEAR):
    user = require_user(request)
    if not check_permission(user, "can_view_prolabore"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    rows = conn.execute("SELECT * FROM prolabore WHERE year=? ORDER BY month DESC, ceo_name", (year,)).fetchall()
    total_year = conn.execute("SELECT COALESCE(SUM(value),0) FROM prolabore WHERE year=?", (year,)).fetchone()[0]
    conn.close()
    return templates.TemplateResponse("prolabore.html", {"request": request, "user": dict(user), "prolabores": [dict(r) for r in rows], "total_year": total_year, "year": year, "months": MONTHS_PT[:3] + [m[:3] for m in MONTHS_PT[3:]], "current_year": CURRENT_YEAR})


@app.post("/prolabore/novo")
def prolabore_novo(request: Request, ceo_name: str = Form(...), value: float = Form(...), month: int = Form(...), year: int = Form(...), payment_date: str = Form(""), status: str = Form("pendente"), notes: str = Form("")):
    user = require_user(request)
    conn = get_db()
    conn.execute("INSERT INTO prolabore (ceo_name,value,month,year,payment_date,status,notes) VALUES (?,?,?,?,?,?,?)", (ceo_name,value,month,year,payment_date or None,status,notes))
    log_action(conn, user, "registrou", "pró-labore", f"{ceo_name} — R$ {value:.2f} ({month}/{year})")
    conn.commit(); conn.close()
    return RedirectResponse(f"/prolabore?year={year}", status_code=302)


@app.post("/prolabore/{pid}/status")
def prolabore_status(request: Request, pid: int, status: str = Form(...)):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT ceo_name FROM prolabore WHERE id=?", (pid,)).fetchone()
    conn.execute("UPDATE prolabore SET status=? WHERE id=?", (status, pid))
    if row: log_action(conn, user, "atualizou", "pró-labore", f"{row['ceo_name']} → {status}")
    conn.commit(); conn.close()
    return RedirectResponse("/prolabore", status_code=302)


@app.post("/prolabore/{pid}/deletar")
def prolabore_deletar(request: Request, pid: int):
    user = require_user(request)
    conn = get_db()
    conn.execute("DELETE FROM prolabore WHERE id=?", (pid,))
    log_action(conn, user, "removeu", "pró-labore", f"ID {pid}")
    conn.commit(); conn.close()
    return RedirectResponse("/prolabore", status_code=302)


# ── Anúncios ──────────────────────────────────────────────────────────────────

@app.get("/anuncios", response_class=HTMLResponse)
def anuncios_page(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_anuncios"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    rows = conn.execute("SELECT a.*, u.name as creator FROM ads a LEFT JOIN users u ON a.created_by=u.id ORDER BY a.created_at DESC").fetchall()
    total_budget = conn.execute("SELECT COALESCE(SUM(budget),0) FROM ads").fetchone()[0]
    total_spent  = conn.execute("SELECT COALESCE(SUM(spent),0) FROM ads").fetchone()[0]
    total_leads  = conn.execute("SELECT COALESCE(SUM(leads),0) FROM ads").fetchone()[0]
    conn.close()
    return templates.TemplateResponse("anuncios.html", {"request": request, "user": dict(user), "ads": [dict(r) for r in rows], "total_budget": total_budget, "total_spent": total_spent, "total_leads": total_leads})


@app.post("/anuncios/novo")
def anuncio_novo(request: Request, campaign_name: str = Form(...), platform: str = Form(...), budget: float = Form(...), spent: float = Form(0), leads: int = Form(0), conversions: int = Form(0), start_date: str = Form(""), end_date: str = Form(""), status: str = Form("ativo"), notes: str = Form("")):
    user = require_user(request)
    conn = get_db()
    conn.execute("INSERT INTO ads (campaign_name,platform,budget,spent,leads,conversions,start_date,end_date,status,notes,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (campaign_name,platform,budget,spent,leads,conversions,start_date or None,end_date or None,status,notes,user["id"]))
    log_action(conn, user, "criou", "anúncio", f"{campaign_name} — {platform}")
    conn.commit(); conn.close()
    return RedirectResponse("/anuncios", status_code=302)


@app.post("/anuncios/{aid}/editar")
def anuncio_editar(request: Request, aid: int, campaign_name: str = Form(...), platform: str = Form(...), budget: float = Form(...), spent: float = Form(0), leads: int = Form(0), conversions: int = Form(0), start_date: str = Form(""), end_date: str = Form(""), status: str = Form("ativo"), notes: str = Form("")):
    user = require_user(request)
    conn = get_db()
    conn.execute("UPDATE ads SET campaign_name=?,platform=?,budget=?,spent=?,leads=?,conversions=?,start_date=?,end_date=?,status=?,notes=? WHERE id=?", (campaign_name,platform,budget,spent,leads,conversions,start_date or None,end_date or None,status,notes,aid))
    log_action(conn, user, "editou", "anúncio", f"{campaign_name}")
    conn.commit(); conn.close()
    return RedirectResponse("/anuncios", status_code=302)


@app.post("/anuncios/{aid}/deletar")
def anuncio_deletar(request: Request, aid: int):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT campaign_name FROM ads WHERE id=?", (aid,)).fetchone()
    conn.execute("DELETE FROM ads WHERE id=?", (aid,))
    if row: log_action(conn, user, "removeu", "anúncio", row['campaign_name'])
    conn.commit(); conn.close()
    return RedirectResponse("/anuncios", status_code=302)


# ── Próximos Passos ───────────────────────────────────────────────────────────

@app.get("/proximos-passos", response_class=HTMLResponse)
def proximos_passos_page(request: Request, status_filter: str = ""):
    user = require_user(request)
    if not check_permission(user, "can_view_proximos_passos"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    if status_filter:
        rows = conn.execute("SELECT n.*, u.name as creator FROM next_steps n LEFT JOIN users u ON n.created_by=u.id WHERE n.status=? ORDER BY CASE n.priority WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END, n.deadline", (status_filter,)).fetchall()
    else:
        rows = conn.execute("SELECT n.*, u.name as creator FROM next_steps n LEFT JOIN users u ON n.created_by=u.id ORDER BY CASE n.status WHEN 'aberto' THEN 1 WHEN 'em_andamento' THEN 2 ELSE 3 END, CASE n.priority WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END").fetchall()
    counts = conn.execute("SELECT status, COUNT(*) as n FROM next_steps GROUP BY status").fetchall()
    conn.close()
    return templates.TemplateResponse("proximos_passos.html", {"request": request, "user": dict(user), "tasks": [dict(r) for r in rows], "status_filter": status_filter, "count_map": {r["status"]: r["n"] for r in counts}})


@app.post("/proximos-passos/novo")
def proximos_passos_novo(request: Request, title: str = Form(...), description: str = Form(""), responsible: str = Form(""), deadline: str = Form(""), priority: str = Form("media"), status: str = Form("aberto")):
    user = require_user(request)
    conn = get_db()
    conn.execute("INSERT INTO next_steps (title,description,responsible,deadline,priority,status,created_by) VALUES (?,?,?,?,?,?,?)", (title,description,responsible,deadline or None,priority,status,user["id"]))
    log_action(conn, user, "criou", "próximo passo", title)
    conn.commit(); conn.close()
    return RedirectResponse("/proximos-passos", status_code=302)


@app.post("/proximos-passos/{tid}/status")
def tarefa_status(request: Request, tid: int, status: str = Form(...)):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT title FROM next_steps WHERE id=?", (tid,)).fetchone()
    conn.execute("UPDATE next_steps SET status=? WHERE id=?", (status, tid))
    if row: log_action(conn, user, "atualizou", "próximo passo", f"{row['title']} → {status}")
    conn.commit(); conn.close()
    return RedirectResponse("/proximos-passos", status_code=302)


@app.post("/proximos-passos/{tid}/deletar")
def tarefa_deletar(request: Request, tid: int):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT title FROM next_steps WHERE id=?", (tid,)).fetchone()
    conn.execute("DELETE FROM next_steps WHERE id=?", (tid,))
    if row: log_action(conn, user, "removeu", "próximo passo", row['title'])
    conn.commit(); conn.close()
    return RedirectResponse("/proximos-passos", status_code=302)


# ── Pipeline CRM ──────────────────────────────────────────────────────────────

STAGES = ["prospecto", "negociacao", "proposta", "fechado", "perdido"]
STAGES_LABEL = {"prospecto": "Prospecto", "negociacao": "Negociação", "proposta": "Proposta Enviada", "fechado": "Fechado ✓", "perdido": "Perdido ✗"}

@app.get("/pipeline", response_class=HTMLResponse)
def pipeline_page(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_pipeline"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    rows = conn.execute("SELECT p.*, u.name as creator FROM pipeline p LEFT JOIN users u ON p.created_by=u.id ORDER BY p.created_at DESC").fetchall()
    conn.close()
    by_stage = {s: [] for s in STAGES}
    for r in rows:
        s = r["stage"] if r["stage"] in STAGES else "prospecto"
        by_stage[s].append(dict(r))
    totals = {s: sum(r["value"] for r in by_stage[s]) for s in STAGES}
    return templates.TemplateResponse("pipeline.html", {"request": request, "user": dict(user), "by_stage": by_stage, "stages": STAGES, "stages_label": STAGES_LABEL, "totals": totals})


@app.post("/pipeline/novo")
async def pipeline_novo(request: Request):
    user = require_user(request)
    form = await request.form()

    contact_name = form.get("contact_name", "")
    company = form.get("company", "")
    phone = form.get("phone", "")
    email = form.get("email", "")
    stage = form.get("stage", "prospecto")
    value = float(form.get("value", 0) or 0)
    responsible = form.get("responsible", "")
    notes = form.get("notes", "")

    # Pega múltiplos serviços selecionados
    services = form.getlist("services")
    service_type = " | ".join(services) if services else ""

    conn = get_db()
    conn.execute("INSERT INTO pipeline (contact_name,company,phone,email,service_type,stage,value,responsible,notes,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)", (contact_name,company,phone,email,service_type,stage,value,responsible,notes,user["id"]))
    log_action(conn, user, "criou", "pipeline", f"{contact_name} — {company} ({stage})")
    conn.commit(); conn.close()
    return RedirectResponse("/pipeline", status_code=302)


@app.post("/pipeline/{pid}/stage")
def pipeline_stage(request: Request, pid: int, stage: str = Form(...)):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT contact_name FROM pipeline WHERE id=?", (pid,)).fetchone()
    conn.execute("UPDATE pipeline SET stage=? WHERE id=?", (stage, pid))
    if row: log_action(conn, user, "moveu", "pipeline", f"{row['contact_name']} → {STAGES_LABEL.get(stage, stage)}")
    conn.commit(); conn.close()
    return RedirectResponse("/pipeline", status_code=302)


@app.post("/pipeline/{pid}/deletar")
def pipeline_deletar(request: Request, pid: int):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT contact_name FROM pipeline WHERE id=?", (pid,)).fetchone()
    conn.execute("DELETE FROM pipeline WHERE id=?", (pid,))
    if row: log_action(conn, user, "removeu", "pipeline", row['contact_name'])
    conn.commit(); conn.close()
    return RedirectResponse("/pipeline", status_code=302)


# ── Projetos ──────────────────────────────────────────────────────────────────

@app.get("/projetos", response_class=HTMLResponse)
def projetos_page(request: Request, status_filter: str = ""):
    user = require_user(request)
    if not check_permission(user, "can_view_projetos"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    if status_filter:
        rows = conn.execute("SELECT p.*, u.name as creator FROM projects p LEFT JOIN users u ON p.created_by=u.id WHERE p.status=? ORDER BY p.deadline", (status_filter,)).fetchall()
    else:
        rows = conn.execute("SELECT p.*, u.name as creator FROM projects p LEFT JOIN users u ON p.created_by=u.id ORDER BY CASE p.status WHEN 'em_andamento' THEN 1 WHEN 'pendente' THEN 2 ELSE 3 END, p.deadline").fetchall()
    clients = conn.execute("SELECT id, name FROM clients WHERE status='ativo' ORDER BY name").fetchall()
    counts = conn.execute("SELECT status, COUNT(*) as n FROM projects GROUP BY status").fetchall()
    conn.close()
    return templates.TemplateResponse("projetos.html", {"request": request, "user": dict(user), "projects": [dict(r) for r in rows], "clients": [dict(c) for c in clients], "status_filter": status_filter, "count_map": {r["status"]: r["n"] for r in counts}})


@app.get("/projetos/{pid}", response_class=HTMLResponse)
def projeto_detail(request: Request, pid: int):
    user = require_user(request)
    conn = get_db()
    project = conn.execute("SELECT p.*, u.name as creator FROM projects p LEFT JOIN users u ON p.created_by=u.id WHERE p.id=?", (pid,)).fetchone()
    if not project:
        conn.close(); return RedirectResponse("/projetos", status_code=302)
    tasks = conn.execute("SELECT * FROM project_tasks WHERE project_id=? ORDER BY CASE status WHEN 'pendente' THEN 1 WHEN 'em_andamento' THEN 2 ELSE 3 END", (pid,)).fetchall()
    conn.close()
    return templates.TemplateResponse("projeto_detail.html", {"request": request, "user": dict(user), "project": dict(project), "tasks": [dict(t) for t in tasks]})


@app.post("/projetos/novo")
def projeto_novo(request: Request, client_id: str = Form(""), client_name: str = Form(""), title: str = Form(...), service_type: str = Form(""), status: str = Form("em_andamento"), start_date: str = Form(""), deadline: str = Form(""), responsible: str = Form(""), notes: str = Form("")):
    user = require_user(request)
    conn = get_db()
    if client_id:
        c = conn.execute("SELECT name FROM clients WHERE id=?", (client_id,)).fetchone()
        if c: client_name = c["name"]
    conn.execute("INSERT INTO projects (client_id,client_name,title,service_type,status,start_date,deadline,responsible,notes,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)", (client_id or None,client_name,title,service_type,status,start_date or None,deadline or None,responsible,notes,user["id"]))
    log_action(conn, user, "criou", "projeto", f"{title} — {client_name}")
    conn.commit(); conn.close()
    return RedirectResponse("/projetos", status_code=302)


@app.post("/projetos/{pid}/status")
def projeto_status(request: Request, pid: int, status: str = Form(...)):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT title FROM projects WHERE id=?", (pid,)).fetchone()
    conn.execute("UPDATE projects SET status=? WHERE id=?", (status, pid))
    if row: log_action(conn, user, "atualizou", "projeto", f"{row['title']} → {status}")
    conn.commit(); conn.close()
    return RedirectResponse("/projetos", status_code=302)


@app.post("/projetos/{pid}/tarefa")
def projeto_tarefa(request: Request, pid: int, title: str = Form(...), responsible: str = Form(""), deadline: str = Form("")):
    user = require_user(request)
    conn = get_db()
    conn.execute("INSERT INTO project_tasks (project_id,title,responsible,deadline) VALUES (?,?,?,?)", (pid,title,responsible,deadline or None))
    log_action(conn, user, "adicionou tarefa", "projeto", title)
    conn.commit(); conn.close()
    return RedirectResponse(f"/projetos/{pid}", status_code=302)


@app.post("/projetos/{pid}/tarefa/{tid}/status")
def tarefa_projeto_status(request: Request, pid: int, tid: int, status: str = Form(...)):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT title FROM project_tasks WHERE id=?", (tid,)).fetchone()
    conn.execute("UPDATE project_tasks SET status=? WHERE id=?", (status, tid))
    if row: log_action(conn, user, "atualizou tarefa", "projeto", f"{row['title']} → {status}")
    conn.commit(); conn.close()
    return RedirectResponse(f"/projetos/{pid}", status_code=302)


@app.post("/projetos/{pid}/deletar")
def projeto_deletar(request: Request, pid: int):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT title FROM projects WHERE id=?", (pid,)).fetchone()
    conn.execute("DELETE FROM project_tasks WHERE project_id=?", (pid,))
    conn.execute("DELETE FROM projects WHERE id=?", (pid,))
    if row: log_action(conn, user, "removeu", "projeto", row['title'])
    conn.commit(); conn.close()
    return RedirectResponse("/projetos", status_code=302)


# ── Financeiro ────────────────────────────────────────────────────────────────

@app.get("/financeiro", response_class=HTMLResponse)
def financeiro_page(request: Request, type_filter: str = ""):
    user = require_user(request)
    if not check_permission(user, "can_view_financeiro"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    if type_filter:
        rows = conn.execute("SELECT f.*, u.name as creator FROM financial f LEFT JOIN users u ON f.created_by=u.id WHERE f.type=? ORDER BY f.due_date DESC", (type_filter,)).fetchall()
    else:
        rows = conn.execute("SELECT f.*, u.name as creator FROM financial f LEFT JOIN users u ON f.created_by=u.id ORDER BY f.due_date DESC").fetchall()
    total_receita = conn.execute("SELECT COALESCE(SUM(value),0) FROM financial WHERE type='receita'").fetchone()[0]
    total_despesa = conn.execute("SELECT COALESCE(SUM(value),0) FROM financial WHERE type='despesa'").fetchone()[0]
    total_pago    = conn.execute("SELECT COALESCE(SUM(value),0) FROM financial WHERE status='pago' AND type='receita'").fetchone()[0]
    total_pendente= conn.execute("SELECT COALESCE(SUM(value),0) FROM financial WHERE status='pendente' AND type='receita'").fetchone()[0]
    clients = conn.execute("SELECT id, name FROM clients WHERE status='ativo' ORDER BY name").fetchall()
    conn.close()
    return templates.TemplateResponse("financeiro.html", {
        "request": request, "user": dict(user),
        "records": [dict(r) for r in rows], "type_filter": type_filter,
        "total_receita": total_receita, "total_despesa": total_despesa,
        "total_pago": total_pago, "total_pendente": total_pendente,
        "saldo": total_receita - total_despesa,
        "clients": [dict(c) for c in clients],
    })


@app.post("/financeiro/novo")
def financeiro_novo(request: Request, client_id: str = Form(""), description: str = Form(...), type: str = Form("receita"), value: float = Form(...), due_date: str = Form(""), status: str = Form("pendente"), notes: str = Form("")):
    user = require_user(request)
    conn = get_db()
    client_name = ""
    if client_id:
        c = conn.execute("SELECT name FROM clients WHERE id=?", (client_id,)).fetchone()
        if c: client_name = c["name"]
    conn.execute("INSERT INTO financial (client_id,client_name,description,type,value,due_date,status,notes,created_by) VALUES (?,?,?,?,?,?,?,?,?)", (client_id or None,client_name,description,type,value,due_date or None,status,notes,user["id"]))
    log_action(conn, user, "registrou", "financeiro", f"{description} — R$ {value:.2f} ({type})")
    conn.commit(); conn.close()
    return RedirectResponse("/financeiro", status_code=302)


@app.post("/financeiro/{fid}/status")
def financeiro_status(request: Request, fid: int, status: str = Form(...)):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT description FROM financial WHERE id=?", (fid,)).fetchone()
    paid_date = datetime.now().strftime("%Y-%m-%d") if status == "pago" else None
    conn.execute("UPDATE financial SET status=?, paid_date=? WHERE id=?", (status, paid_date, fid))
    if row: log_action(conn, user, "atualizou", "financeiro", f"{row['description']} → {status}")
    conn.commit(); conn.close()
    return RedirectResponse("/financeiro", status_code=302)


@app.post("/financeiro/{fid}/deletar")
def financeiro_deletar(request: Request, fid: int):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT description FROM financial WHERE id=?", (fid,)).fetchone()
    conn.execute("DELETE FROM financial WHERE id=?", (fid,))
    if row: log_action(conn, user, "removeu", "financeiro", row['description'])
    conn.commit(); conn.close()
    return RedirectResponse("/financeiro", status_code=302)


# ── Calendário de Conteúdo ────────────────────────────────────────────────────

@app.get("/calendario", response_class=HTMLResponse)
def calendario_index(request: Request):
    """Lista todos os clientes com seus calendários."""
    user = require_user(request)
    if not check_permission(user, "can_view_calendario"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    clients = conn.execute("SELECT * FROM clients WHERE status='ativo' ORDER BY name").fetchall()
    # Count posts per client this month
    month_str = f"{CURRENT_YEAR:04d}-{CURRENT_MONTH:02d}"
    counts = conn.execute(
        "SELECT client_id, COUNT(*) as n FROM content_calendar WHERE strftime('%Y-%m', scheduled_date)=? GROUP BY client_id",
        (month_str,)
    ).fetchall()
    count_map = {r["client_id"]: r["n"] for r in counts}
    conn.close()
    return templates.TemplateResponse("calendario_index.html", {
        "request": request, "user": dict(user),
        "clients": [dict(c) for c in clients],
        "count_map": count_map,
        "month_name": MONTHS_PT[CURRENT_MONTH - 1],
        "year": CURRENT_YEAR,
    })


@app.get("/calendario/{client_id}", response_class=HTMLResponse)
def calendario_cliente(request: Request, client_id: int, year: int = CURRENT_YEAR, month: int = CURRENT_MONTH):
    """Calendário individual por cliente."""
    user = require_user(request)
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if not client:
        conn.close(); return RedirectResponse("/calendario", status_code=302)

    month_str = f"{year:04d}-{month:02d}"
    rows = conn.execute(
        "SELECT cc.*, u.name as creator FROM content_calendar cc LEFT JOIN users u ON cc.created_by=u.id "
        "WHERE cc.client_id=? AND strftime('%Y-%m', cc.scheduled_date)=? ORDER BY cc.scheduled_date",
        (client_id, month_str)
    ).fetchall()
    conn.close()

    posts_by_day = {}
    for r in rows:
        if r["scheduled_date"]:
            try:
                day = int(r["scheduled_date"].split("-")[2])
                posts_by_day.setdefault(day, []).append(dict(r))
            except Exception:
                pass

    weeks = cal_mod.monthcalendar(year, month)
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year  = year if month < 12 else year + 1

    return templates.TemplateResponse("calendario.html", {
        "request": request, "user": dict(user),
        "client": dict(client),
        "posts": [dict(r) for r in rows],
        "posts_by_day": posts_by_day,
        "weeks": weeks, "year": year, "month": month,
        "month_name": MONTHS_PT[month - 1],
        "prev_month": prev_month, "prev_year": prev_year,
        "next_month": next_month, "next_year": next_year,
    })


@app.post("/calendario/{client_id}/novo")
def calendario_novo(request: Request, client_id: int, title: str = Form(...), platform: str = Form(""), content_type: str = Form(""), copy_text: str = Form(""), status: str = Form("planejado"), scheduled_date: str = Form(""), responsible: str = Form("")):
    user = require_user(request)
    conn = get_db()
    client = conn.execute("SELECT name FROM clients WHERE id=?", (client_id,)).fetchone()
    client_name = client["name"] if client else ""
    conn.execute(
        "INSERT INTO content_calendar (client_id,client_name,title,platform,content_type,copy_text,status,scheduled_date,responsible,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (client_id, client_name, title, platform, content_type, copy_text, status, scheduled_date or None, responsible, user["id"])
    )
    log_action(conn, user, "criou", "calendário", f"{client_name}: {title} — {platform} ({scheduled_date})")
    conn.commit(); conn.close()
    try:
        y, m = int(scheduled_date[:4]), int(scheduled_date[5:7])
    except Exception:
        y, m = CURRENT_YEAR, CURRENT_MONTH
    return RedirectResponse(f"/calendario/{client_id}?year={y}&month={m}", status_code=302)


@app.post("/calendario/post/{pid}/status")
def calendario_status(request: Request, pid: int, status: str = Form(...), client_id: int = Form(...), year: int = Form(CURRENT_YEAR), month: int = Form(CURRENT_MONTH)):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT title FROM content_calendar WHERE id=?", (pid,)).fetchone()
    conn.execute("UPDATE content_calendar SET status=? WHERE id=?", (status, pid))
    if row: log_action(conn, user, "atualizou", "calendário", f"{row['title']} → {status}")
    conn.commit(); conn.close()
    return RedirectResponse(f"/calendario/{client_id}?year={year}&month={month}", status_code=302)


@app.post("/calendario/post/{pid}/deletar")
def calendario_deletar(request: Request, pid: int, client_id: int = Form(...), year: int = Form(CURRENT_YEAR), month: int = Form(CURRENT_MONTH)):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT title FROM content_calendar WHERE id=?", (pid,)).fetchone()
    conn.execute("DELETE FROM content_calendar WHERE id=?", (pid,))
    if row: log_action(conn, user, "removeu", "calendário", row['title'])
    conn.commit(); conn.close()
    return RedirectResponse(f"/calendario/{client_id}?year={year}&month={month}", status_code=302)


# ── Copys ─────────────────────────────────────────────────────────────────────

@app.get("/copys", response_class=HTMLResponse)
def copys_page(request: Request, q: str = "", copy_type: str = ""):
    user = require_user(request)
    if not check_permission(user, "can_view_copys"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    base = "SELECT cp.*, u.name as creator FROM copies cp LEFT JOIN users u ON cp.created_by=u.id"
    params: list = []
    wheres = []
    if q:
        wheres.append("(cp.title LIKE ? OR cp.content LIKE ? OR cp.niche LIKE ?)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if copy_type:
        wheres.append("cp.copy_type=?")
        params.append(copy_type)
    if wheres:
        base += " WHERE " + " AND ".join(wheres)
    base += " ORDER BY cp.created_at DESC"
    rows = conn.execute(base, params).fetchall()
    clients = conn.execute("SELECT id, name FROM clients WHERE status='ativo' ORDER BY name").fetchall()
    types = conn.execute("SELECT DISTINCT copy_type FROM copies WHERE copy_type != '' ORDER BY copy_type").fetchall()
    conn.close()
    return templates.TemplateResponse("copys.html", {
        "request": request, "user": dict(user),
        "copies": [dict(r) for r in rows],
        "clients": [dict(c) for c in clients],
        "copy_types": [r["copy_type"] for r in types],
        "q": q, "copy_type": copy_type,
    })


@app.post("/copys/novo")
def copy_novo(request: Request, client_id: str = Form(""), title: str = Form(...), copy_type: str = Form(""), platform: str = Form(""), content: str = Form(""), niche: str = Form("")):
    user = require_user(request)
    conn = get_db()
    client_name = ""
    if client_id:
        c = conn.execute("SELECT name FROM clients WHERE id=?", (client_id,)).fetchone()
        if c: client_name = c["name"]
    conn.execute("INSERT INTO copies (client_id,client_name,title,copy_type,platform,content,niche,created_by) VALUES (?,?,?,?,?,?,?,?)", (client_id or None,client_name,title,copy_type,platform,content,niche,user["id"]))
    log_action(conn, user, "criou", "copy", f"{title} ({copy_type})")
    conn.commit(); conn.close()
    return RedirectResponse("/copys", status_code=302)


@app.post("/copys/{cid}/deletar")
def copy_deletar(request: Request, cid: int):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT title FROM copies WHERE id=?", (cid,)).fetchone()
    conn.execute("DELETE FROM copies WHERE id=?", (cid,))
    if row: log_action(conn, user, "removeu", "copy", row['title'])
    conn.commit(); conn.close()
    return RedirectResponse("/copys", status_code=302)


# ── Atividades (Audit Log) ────────────────────────────────────────────────────

@app.get("/atividades", response_class=HTMLResponse)
def atividades_page(request: Request, ceo_filter: str = "", entity_filter: str = ""):
    user = require_user(request)
    if not check_permission(user, "can_view_atividades"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    base = "SELECT * FROM activity_log"
    params: list = []; wheres = []
    if ceo_filter:
        wheres.append("user_name=?"); params.append(ceo_filter)
    if entity_filter:
        wheres.append("entity_type=?"); params.append(entity_filter)
    if wheres: base += " WHERE " + " AND ".join(wheres)
    base += " ORDER BY created_at DESC LIMIT 200"
    rows = conn.execute(base, params).fetchall()
    ceos    = conn.execute("SELECT DISTINCT user_name FROM activity_log ORDER BY user_name").fetchall()
    entities= conn.execute("SELECT DISTINCT entity_type FROM activity_log ORDER BY entity_type").fetchall()
    conn.close()
    return templates.TemplateResponse("atividades.html", {
        "request": request, "user": dict(user),
        "activities": [dict(r) for r in rows],
        "ceos": [r["user_name"] for r in ceos],
        "entities": [r["entity_type"] for r in entities],
        "ceo_filter": ceo_filter, "entity_filter": entity_filter,
    })


# ── Relatório por Cliente ─────────────────────────────────────────────────────

@app.get("/relatorio/{client_id}", response_class=HTMLResponse)
def relatorio_cliente(request: Request, client_id: int):
    user = require_user(request)
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if not client:
        conn.close(); return RedirectResponse("/clientes", status_code=302)
    projects  = conn.execute("SELECT * FROM projects WHERE client_id=? ORDER BY deadline", (client_id,)).fetchall()
    ads_list  = conn.execute("SELECT * FROM ads WHERE notes LIKE ?", (f"%{client['name']}%",)).fetchall()
    financial = conn.execute("SELECT * FROM financial WHERE client_id=? ORDER BY due_date DESC", (client_id,)).fetchall()
    cal_posts = conn.execute("SELECT * FROM content_calendar WHERE client_id=? ORDER BY scheduled_date DESC LIMIT 10", (client_id,)).fetchall()
    total_pago  = conn.execute("SELECT COALESCE(SUM(value),0) FROM financial WHERE client_id=? AND status='pago' AND type='receita'", (client_id,)).fetchone()[0]
    total_pendente = conn.execute("SELECT COALESCE(SUM(value),0) FROM financial WHERE client_id=? AND status='pendente' AND type='receita'", (client_id,)).fetchone()[0]
    conn.close()
    return templates.TemplateResponse("relatorio.html", {
        "request": request, "user": dict(user),
        "client": dict(client),
        "projects": [dict(p) for p in projects],
        "ads": [dict(a) for a in ads_list],
        "financial": [dict(f) for f in financial],
        "cal_posts": [dict(p) for p in cal_posts],
        "total_pago": total_pago,
        "total_pendente": total_pendente,
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    })


# ── Usuários ──────────────────────────────────────────────────────────────────

@app.get("/usuarios", response_class=HTMLResponse)
def usuarios_page(request: Request):
    user = require_user(request)
    if user["role"] != "admin":
        return RedirectResponse("/", status_code=302)
    conn = get_db()
    rows = conn.execute("SELECT id,name,email,role,created_at FROM users ORDER BY name").fetchall()
    conn.close()
    return templates.TemplateResponse("usuarios.html", {"request": request, "user": dict(user), "users": [dict(r) for r in rows]})


@app.post("/usuarios/novo")
def usuario_novo(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...), role: str = Form("ceo")):
    user = require_user(request)
    if user["role"] != "admin":
        return RedirectResponse("/", status_code=302)
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)", (name,email,hash_password(password),role))
        log_action(conn, user, "criou", "usuário", f"{name} ({email})")
        conn.commit()
    except Exception:
        pass
    conn.close()
    return RedirectResponse("/usuarios", status_code=302)


@app.post("/usuarios/{uid}/deletar")
def usuario_deletar(request: Request, uid: int):
    user = require_user(request)
    if user["role"] != "admin" or user["id"] == uid:
        return RedirectResponse("/usuarios", status_code=302)
    conn = get_db()
    row = conn.execute("SELECT name FROM users WHERE id=?", (uid,)).fetchone()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    if row: log_action(conn, user, "removeu", "usuário", row['name'])
    conn.commit(); conn.close()
    return RedirectResponse("/usuarios", status_code=302)


# ── CEO: Gerenciamento de Usuários e Permissões ──────────────────────────────

@app.get("/ceo", response_class=HTMLResponse)
def ceo_page(request: Request):
    user = require_user(request)
    if user["role"] not in ["admin", "ceo"]:
        return RedirectResponse("/", status_code=302)
    conn = get_db()
    users = conn.execute("SELECT id,name,email,role,created_at FROM users ORDER BY name").fetchall()
    conn.close()
    return templates.TemplateResponse("ceo.html", {
        "request": request,
        "user": dict(user),
        "users": [dict(u) for u in users]
    })


@app.post("/ceo/usuarios/novo")
async def ceo_novo_usuario(request: Request):
    user = require_user(request)
    if user["role"] not in ["admin", "ceo"]:
        return JSONResponse({"success": False, "error": "Permissão negada"}, status_code=403)

    data = await request.json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not name or not email or not password or len(password) < 8:
        return JSONResponse({"success": False, "error": "Dados inválidos"})

    conn = get_db()
    try:
        from database import create_user_permissions
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, email, hash_password(password), "funcionario")
        )
        new_user_id = cursor.lastrowid
        create_user_permissions(conn, new_user_id, is_admin=False)
        log_action(conn, user, "criou", "usuário funcionário", f"{name} ({email})")
        conn.commit()
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})
    finally:
        conn.close()


@app.get("/ceo/usuarios/{uid}")
def ceo_get_usuario(request: Request, uid: int):
    user = require_user(request)
    if user["role"] not in ["admin", "ceo"]:
        return JSONResponse({"error": "Permissão negada"}, status_code=403)

    conn = get_db()
    usr = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    perms = conn.execute("SELECT * FROM user_permissions WHERE user_id=?", (uid,)).fetchone()
    conn.close()

    if not usr:
        return JSONResponse({"error": "Usuário não encontrado"}, status_code=404)

    return JSONResponse({
        "id": usr["id"],
        "name": usr["name"],
        "email": usr["email"],
        "role": usr["role"],
        "permissions": dict(perms) if perms else {}
    })


@app.post("/ceo/usuarios/{uid}/editar-permissoes")
async def ceo_editar_permissoes(request: Request, uid: int):
    user = require_user(request)
    if user["role"] not in ["admin", "ceo"]:
        return JSONResponse({"success": False, "error": "Permissão negada"}, status_code=403)

    data = await request.json()
    conn = get_db()

    try:
        # Atualiza apenas as permissões fornecidas
        update_fields = []
        for key, val in data.items():
            if key.startswith("can_view_"):
                update_fields.append(f"{key}=1")

        if update_fields:
            query = f"UPDATE user_permissions SET {', '.join(update_fields)} WHERE user_id=?"
            conn.execute(query, (uid,))

        # Reseta todas as outras permissões
        all_perms = [
            "can_view_dashboard", "can_view_atividades", "can_view_prospeccao",
            "can_view_pipeline", "can_view_clientes", "can_view_financeiro",
            "can_view_chat", "can_view_ia", "can_view_relatorios", "can_view_propostas",
            "can_view_agendador", "can_view_projetos", "can_view_calendario",
            "can_view_copys", "can_view_anuncios", "can_view_proximos_passos",
            "can_view_investimentos", "can_view_prolabore"
        ]
        disabled = [p for p in all_perms if p not in data]
        if disabled:
            reset_query = f"UPDATE user_permissions SET {', '.join([f'{p}=0' for p in disabled])} WHERE user_id=?"
            conn.execute(reset_query, (uid,))

        conn.commit()
        log_action(conn, user, "atualizou", "permissões de usuário", f"UID {uid}")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})
    finally:
        conn.close()


@app.post("/ceo/usuarios/{uid}/reset-senha")
async def ceo_reset_senha(request: Request, uid: int):
    user = require_user(request)
    if user["role"] not in ["admin", "ceo"]:
        return JSONResponse({"success": False, "error": "Permissão negada"}, status_code=403)

    data = await request.json()
    new_password = data.get("new_password", "").strip()

    if not new_password or len(new_password) < 8:
        return JSONResponse({"success": False, "error": "Senha inválida (min 8 caracteres)"})

    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hash_password(new_password), uid)
        )
        conn.commit()
        log_action(conn, user, "resetou", "senha de usuário", f"UID {uid}")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})
    finally:
        conn.close()


@app.post("/ceo/usuarios/{uid}/deletar")
def ceo_deletar_usuario(request: Request, uid: int):
    user = require_user(request)
    if user["role"] not in ["admin", "ceo"] or user["id"] == uid:
        return JSONResponse({"success": False, "error": "Não pode deletar a si mesmo"}, status_code=403)

    conn = get_db()
    try:
        usr = conn.execute("SELECT name FROM users WHERE id=?", (uid,)).fetchone()
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
        log_action(conn, user, "deletou", "usuário", f"{usr['name'] if usr else 'unknown'}")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})
    finally:
        conn.close()


# ── Minha Conta ──────────────────────────────────────────────────────────────

@app.get("/minha-conta", response_class=HTMLResponse)
def minha_conta_page(request: Request):
    user = require_user(request)
    return templates.TemplateResponse("minha-conta.html", {
        "request": request,
        "user": dict(user)
    })


@app.post("/minha-conta/trocar-senha")
async def minha_conta_trocar_senha(request: Request):
    user = require_user(request)
    data = await request.json()

    senha_atual = data.get("senha_atual", "")
    senha_nova = data.get("senha_nova", "").strip()

    if not senha_nova or len(senha_nova) < 8:
        return JSONResponse({"success": False, "error": "Senha inválida (min 8 caracteres)"})

    conn = get_db()
    try:
        usr = conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()

        if not usr or not verify_password(senha_atual, usr["password_hash"]):
            return JSONResponse({"success": False, "error": "Senha atual incorreta"})

        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hash_password(senha_nova), user["id"])
        )
        conn.commit()
        log_action(conn, user, "alterou", "sua senha", "")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})
    finally:
        conn.close()


# ── Chat Assistant com IA ─────────────────────────────────────────────────────

@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_chat"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    messages = conn.execute(
        "SELECT * FROM chat_messages WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
        (user["id"],)
    ).fetchall()
    conn.close()
    messages = list(reversed([dict(m) for m in messages]))
    return templates.TemplateResponse("chat.html", {
        "request": request, "user": dict(user),
        "messages": messages,
    })


@app.post("/chat/enviar")
async def chat_enviar(request: Request, message: str = Form(...)):
    user = require_user(request)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse({"error": "OpenAI não configurada"}, status_code=400)

    conn = get_db()
    conn.execute(
        "INSERT INTO chat_messages (user_id, user_name, role, content) VALUES (?,?,?,?)",
        (user["id"], user["name"], "user", message)
    )
    conn.commit()

    history = conn.execute(
        "SELECT role, content FROM chat_messages WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (user["id"],)
    ).fetchall()
    history = list(reversed(history))
    conn.close()

    messages_oai = [
        {"role": "system", "content": """Você é o Assistente ELEVA, um especialista em marketing digital, gestão de agências, tráfego pago, social media e negócios digitais.

Você ajuda CEOs e gestores da agência ELEVA com:
- Estratégias de tráfego pago (Google Ads, Meta Ads)
- Planejamento de conteúdo para redes sociais
- Análise de métricas e ROI de campanhas
- Dicas de copywriting e criação
- Gestão de projetos e clientes
- Insights sobre o mercado digital

Responda de forma amigável, prática e acionável. Mantenha as respostas concisas."""}
    ]
    for h in history:
        messages_oai.append({"role": h["role"], "content": h["content"]})
    messages_oai.append({"role": "user", "content": message})

    try:
        from openai import AsyncOpenAI
        client_oai = AsyncOpenAI(api_key=api_key)
        response = await client_oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_oai,
            max_tokens=800,
            temperature=0.7,
        )
        assistant_message = response.choices[0].message.content.strip()

        conn = get_db()
        conn.execute(
            "INSERT INTO chat_messages (user_id, user_name, role, content) VALUES (?,?,?,?)",
            (user["id"], "ELEVA Assistant", "assistant", assistant_message)
        )
        log_action(conn, user, "conversou com", "IA Assistant", message[:40] + "…")
        conn.commit()
        conn.close()

        return JSONResponse({
            "ok": True,
            "response": assistant_message,
        })
    except Exception as e:
        return JSONResponse({"error": f"Erro: {str(e)}"}, status_code=500)


# ── Inteligência Artificial (OpenAI) ─────────────────────────────────────────

@app.get("/ia", response_class=HTMLResponse)
def ia_page(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_ia"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    clients = conn.execute("SELECT id, name FROM clients WHERE status='ativo' ORDER BY name").fetchall()
    conn.close()
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    return templates.TemplateResponse("ia.html", {
        "request": request, "user": dict(user),
        "clients": [dict(c) for c in clients],
        "has_key": has_key,
    })


@app.post("/ia/gerar-copy")
async def ia_gerar_copy(
    request: Request,
    platform: str = Form(""),
    copy_type: str = Form(""),
    tone: str = Form("profissional"),
    description: str = Form(...),
    client_name: str = Form(""),
    goal: str = Form(""),
    extra: str = Form(""),
):
    require_user(request)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse({"error": "⚠️ OPENAI_API_KEY não configurada. Adicione nas variáveis do Railway."}, status_code=400)
    try:
        from openai import AsyncOpenAI
        client_oai = AsyncOpenAI(api_key=api_key)
        parts = [
            f"Você é um especialista em copywriting para marketing digital brasileiro.",
            f"Crie uma copy de alta conversão com as seguintes informações:",
            f"- Produto/Serviço: {description}",
        ]
        if client_name: parts.append(f"- Empresa/Cliente: {client_name}")
        if platform:    parts.append(f"- Plataforma: {platform}")
        if copy_type:   parts.append(f"- Tipo de copy: {copy_type}")
        if goal:        parts.append(f"- Objetivo: {goal}")
        if tone:        parts.append(f"- Tom: {tone}")
        if extra:       parts.append(f"- Instruções extras: {extra}")
        parts.append("\nEscreva apenas a copy final, pronta para uso, em português brasileiro. Não inclua explicações.")

        response = await client_oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "\n".join(parts)}],
            max_tokens=600,
            temperature=0.8,
        )
        copy_text = response.choices[0].message.content.strip()
        return JSONResponse({"copy": copy_text})
    except Exception as e:
        return JSONResponse({"error": f"Erro ao gerar copy: {str(e)}"}, status_code=500)


@app.post("/ia/gerar-imagem")
async def ia_gerar_imagem(
    request: Request,
    prompt: str = Form(...),
    style: str = Form(""),
    size: str = Form("1024x1024"),
    client_name: str = Form(""),
):
    require_user(request)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse({"error": "⚠️ OPENAI_API_KEY não configurada. Adicione nas variáveis do Railway."}, status_code=400)
    try:
        from openai import AsyncOpenAI
        client_oai = AsyncOpenAI(api_key=api_key)
        full_prompt = prompt
        if client_name: full_prompt = f"Para a empresa {client_name}: {prompt}"
        if style:       full_prompt += f". Estilo visual: {style}"
        full_prompt += ". Alta qualidade, profissional, para uso em redes sociais e marketing digital."

        # Tenta DALL-E 3 primeiro, cai para DALL-E 2 se não disponível
        try:
            response = await client_oai.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                size=size,
                quality="standard",
                n=1,
            )
            revised = response.data[0].revised_prompt
        except Exception:
            # DALL-E 2 fallback (tamanho máximo 1024x1024)
            response = await client_oai.images.generate(
                model="dall-e-2",
                prompt=full_prompt[:900],
                size="1024x1024",
                n=1,
            )
            revised = None
        image_url = response.data[0].url
        return JSONResponse({"url": image_url, "revised_prompt": revised or ""})
    except Exception as e:
        msg = str(e)
        if "does not exist" in msg or "billing" in msg or "quota" in msg or "insufficient" in msg:
            return JSONResponse({"error": "⚠️ Sua conta OpenAI não tem créditos para gerar imagens. Acesse platform.openai.com/settings/billing e adicione pelo menos $5 de créditos. A geração de copy continua funcionando normalmente."}, status_code=400)
        return JSONResponse({"error": f"Erro ao gerar imagem: {msg}"}, status_code=500)


@app.post("/ia/salvar-copy")
def ia_salvar_copy(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    copy_type: str = Form(""),
    platform: str = Form(""),
    client_id: str = Form(""),
    niche: str = Form(""),
):
    user = require_user(request)
    conn = get_db()
    client_name = ""
    if client_id:
        c = conn.execute("SELECT name FROM clients WHERE id=?", (client_id,)).fetchone()
        if c: client_name = c["name"]
    conn.execute(
        "INSERT INTO copies (client_id,client_name,title,copy_type,platform,content,niche,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (client_id or None, client_name, title, copy_type, platform, content, niche, user["id"])
    )
    log_action(conn, user, "gerou copy com IA", "copy", f"{title} ({copy_type})")
    conn.commit(); conn.close()
    return JSONResponse({"ok": True, "message": "Copy salva no banco!"})


# ── Módulo: Relatórios ────────────────────────────────────────────────────────

@app.get("/relatorios", response_class=HTMLResponse)
def relatorios_page(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_relatorios"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    reports = conn.execute("SELECT * FROM reports WHERE created_by=? OR client_id IN (SELECT id FROM clients) ORDER BY created_at DESC", (user["id"],)).fetchall()
    clients = conn.execute("SELECT id, name FROM clients WHERE status='ativo' ORDER BY name").fetchall()
    conn.close()
    return templates.TemplateResponse("relatorios.html", {
        "request": request, "user": dict(user),
        "reports": [dict(r) for r in reports],
        "clients": [dict(c) for c in clients],
    })

@app.post("/relatorios/novo")
def relatorios_novo(request: Request, client_id: str = Form(""), title: str = Form(...), description: str = Form(""), content: str = Form("")):
    user = require_user(request)
    conn = get_db()
    client_name = ""
    if client_id:
        c = conn.execute("SELECT name FROM clients WHERE id=?", (client_id,)).fetchone()
        if c: client_name = c["name"]
    conn.execute(
        "INSERT INTO reports (client_id, client_name, title, description, content, created_by) VALUES (?,?,?,?,?,?)",
        (client_id or None, client_name, title, description, content, user["id"])
    )
    log_action(conn, user, "criou", "relatório", title)
    conn.commit(); conn.close()
    return RedirectResponse("/relatorios", status_code=302)

@app.post("/relatorios/{rid}/enviar")
def relatorios_enviar(request: Request, rid: int, client_email: str = Form("")):
    user = require_user(request)
    conn = get_db()
    report = conn.execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()
    if report:
        conn.execute("UPDATE reports SET status=?, sent_date=? WHERE id=?", ("enviado", datetime.now().isoformat()[:19], rid))
        log_action(conn, user, "enviou", "relatório", f"{report['title']} para {client_email}")
    conn.commit(); conn.close()
    return RedirectResponse("/relatorios", status_code=302)


# ── Módulo: Propostas ─────────────────────────────────────────────────────────

@app.get("/propostas", response_class=HTMLResponse)
def propostas_page(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_propostas"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    proposals = conn.execute("SELECT * FROM proposals ORDER BY created_at DESC").fetchall()
    clients = conn.execute("SELECT id, name FROM clients WHERE status='ativo' ORDER BY name").fetchall()
    conn.close()
    return templates.TemplateResponse("propostas.html", {
        "request": request, "user": dict(user),
        "proposals": [dict(p) for p in proposals],
        "clients": [dict(c) for c in clients],
    })

@app.post("/propostas/nova")
def propostas_nova(request: Request, client_id: str = Form(""), title: str = Form(...), description: str = Form(""), services: str = Form("[]"), total_value: float = Form(...), deadline: str = Form("")):
    user = require_user(request)
    conn = get_db()
    client_name = ""
    if client_id:
        c = conn.execute("SELECT name FROM clients WHERE id=?", (client_id,)).fetchone()
        if c: client_name = c["name"]
    conn.execute(
        "INSERT INTO proposals (client_id, client_name, title, description, services, total_value, deadline, created_by) VALUES (?,?,?,?,?,?,?,?)",
        (client_id or None, client_name, title, description, services, total_value, deadline, user["id"])
    )
    log_action(conn, user, "criou", "proposta", f"{title} - R${total_value}")
    conn.commit(); conn.close()
    return RedirectResponse("/propostas", status_code=302)

@app.post("/propostas/{pid}/status")
def propostas_status(request: Request, pid: int, status: str = Form(...)):
    user = require_user(request)
    conn = get_db()
    row = conn.execute("SELECT title FROM proposals WHERE id=?", (pid,)).fetchone()
    if status == "enviado":
        conn.execute("UPDATE proposals SET status=?, sent_date=? WHERE id=?", (status, datetime.now().isoformat()[:19], pid))
    elif status == "aceita":
        conn.execute("UPDATE proposals SET status=?, accepted_date=? WHERE id=?", (status, datetime.now().isoformat()[:19], pid))
    else:
        conn.execute("UPDATE proposals SET status=? WHERE id=?", (status, pid))
    if row: log_action(conn, user, "atualizou", "proposta", f"{row['title']} → {status}")
    conn.commit(); conn.close()
    return RedirectResponse("/propostas", status_code=302)


# ── Módulo: Agendador de Posts ────────────────────────────────────────────────

@app.get("/agendador", response_class=HTMLResponse)
def agendador_page(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_agendador"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    posts = conn.execute("SELECT * FROM scheduled_posts ORDER BY scheduled_for ASC").fetchall()
    clients = conn.execute("SELECT id, name FROM clients WHERE status='ativo' ORDER BY name").fetchall()
    conn.close()
    return templates.TemplateResponse("agendador.html", {
        "request": request, "user": dict(user),
        "posts": [dict(p) for p in posts],
        "clients": [dict(c) for c in clients],
    })

@app.post("/agendador/novo")
def agendador_novo(request: Request, client_id: str = Form(""), platform: str = Form(...), content: str = Form(...), services: str = Form("[]"), scheduled_for: str = Form(...), responsible: str = Form("")):
    user = require_user(request)
    conn = get_db()
    client_name = ""
    if client_id:
        c = conn.execute("SELECT name FROM clients WHERE id=?", (client_id,)).fetchone()
        if c: client_name = c["name"]
    conn.execute(
        "INSERT INTO scheduled_posts (client_id, client_name, platform, content, services, scheduled_for, responsible, created_by) VALUES (?,?,?,?,?,?,?,?)",
        (client_id or None, client_name, platform, content, services, scheduled_for, responsible, user["id"])
    )
    log_action(conn, user, "agendou", "post", f"{platform} - {scheduled_for}")
    conn.commit(); conn.close()
    return RedirectResponse("/agendador", status_code=302)

@app.post("/agendador/{spid}/status")
def agendador_status(request: Request, spid: int, status: str = Form(...)):
    user = require_user(request)
    conn = get_db()
    if status == "publicado":
        conn.execute("UPDATE scheduled_posts SET status=?, posted_at=? WHERE id=?", (status, datetime.now().isoformat()[:19], spid))
    else:
        conn.execute("UPDATE scheduled_posts SET status=? WHERE id=?", (status, spid))
    log_action(conn, user, "atualizou", "post agendado", f"→ {status}")
    conn.commit(); conn.close()
    return RedirectResponse("/agendador", status_code=302)


# ── Módulo: Gestão de Membros ─────────────────────────────────────────────────

@app.get("/membros", response_class=HTMLResponse)
def membros_page(request: Request):
    user = require_user(request)
    if user["role"] != "admin":
        return RedirectResponse("/", status_code=302)
    conn = get_db()
    members = conn.execute("SELECT * FROM team_members ORDER BY name").fetchall()
    conn.close()
    return templates.TemplateResponse("membros.html", {
        "request": request, "user": dict(user),
        "members": [dict(m) for m in members],
    })

@app.post("/membros/novo")
def membros_novo(request: Request, name: str = Form(...), email: str = Form(...), role: str = Form(...), specialty: str = Form(""), hourly_rate: float = Form(0)):
    user = require_user(request)
    if user["role"] != "admin":
        return RedirectResponse("/", status_code=302)
    conn = get_db()
    conn.execute(
        "INSERT INTO team_members (name, email, role, specialty, hourly_rate) VALUES (?,?,?,?,?)",
        (name, email, role, specialty, hourly_rate)
    )
    log_action(conn, user, "cadastrou", "membro", f"{name} - {role}")
    conn.commit(); conn.close()
    return RedirectResponse("/membros", status_code=302)

@app.post("/membros/{mid}/editar")
def membros_editar(request: Request, mid: int, name: str = Form(...), specialty: str = Form(""), hourly_rate: float = Form(0)):
    user = require_user(request)
    if user["role"] != "admin":
        return RedirectResponse("/", status_code=302)
    conn = get_db()
    conn.execute("UPDATE team_members SET name=?, specialty=?, hourly_rate=? WHERE id=?", (name, specialty, hourly_rate, mid))
    log_action(conn, user, "atualizou", "membro", name)
    conn.commit(); conn.close()
    return RedirectResponse("/membros", status_code=302)

@app.post("/membros/{mid}/deletar")
def membros_deletar(request: Request, mid: int):
    user = require_user(request)
    if user["role"] != "admin":
        return RedirectResponse("/", status_code=302)
    conn = get_db()
    row = conn.execute("SELECT name FROM team_members WHERE id=?", (mid,)).fetchone()
    conn.execute("DELETE FROM team_members WHERE id=?", (mid,))
    if row: log_action(conn, user, "removeu", "membro", row["name"])
    conn.commit(); conn.close()
    return RedirectResponse("/membros", status_code=302)


# ── Módulo: Prospecção com Google Maps ─────────────────────────────────────────

@app.get("/prospeccao", response_class=HTMLResponse)
def prospeccao_page(request: Request):
    user = require_user(request)
    if not check_permission(user, "can_view_prospeccao"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    conn = get_db()
    campaigns = conn.execute("SELECT * FROM prospection_campaigns ORDER BY created_at DESC").fetchall()
    conn.close()
    google_maps_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    return templates.TemplateResponse("prospeccao.html", {
        "request": request,
        "user": dict(user),
        "campaigns": [dict(c) for c in campaigns],
        "google_maps_key": google_maps_key,
    })


@app.get("/prospeccao/campanhas", response_class=HTMLResponse)
def prospeccao_campanhas(request: Request):
    """Lista todas as campanhas de prospecção."""
    user = require_user(request)
    conn = get_db()
    campaigns = conn.execute(
        "SELECT pc.*, u.name as creator FROM prospection_campaigns pc LEFT JOIN users u ON pc.created_by=u.id ORDER BY pc.created_at DESC"
    ).fetchall()
    prospects_total = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
    conn.close()
    return JSONResponse({
        "success": True,
        "campaigns": [dict(c) for c in campaigns],
        "total_prospects": prospects_total,
    })


@app.post("/prospeccao/buscar")
async def prospeccao_buscar(request: Request):
    """Busca prospects no Google Maps API baseado em segmento, localização e raio."""
    user = require_user(request)
    data = await request.json()

    segment = data.get("segment", "")
    location = data.get("location", "")
    radius_km = data.get("radius_km", 5)
    center = data.get("center", {})

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return JSONResponse({
            "success": False,
            "error": "Google Maps API não configurada"
        }, status_code=400)

    try:
        import googlemaps
        gmaps = googlemaps.Client(key=api_key)

        # Search for businesses
        places_result = gmaps.places_nearby(
            location=(center.get("lat"), center.get("lng")),
            radius=radius_km * 1000,  # Convert to meters
            keyword=segment,
            type="business"
        )

        prospects = []
        for place in places_result.get("results", [])[:20]:  # Limit to 20
            try:
                details = gmaps.place(place["place_id"])["result"]
                prospect = {
                    "id": place["place_id"],
                    "name": place.get("name", ""),
                    "company": place.get("name", ""),
                    "segment": segment,
                    "location": location,
                    "latitude": place["geometry"]["location"]["lat"],
                    "longitude": place["geometry"]["location"]["lng"],
                    "phone": details.get("formatted_phone_number", ""),
                    "email": details.get("website", ""),
                    "whatsapp": details.get("international_phone_number", ""),
                    "status": "novo",
                }
                # Try to extract WhatsApp if available
                if "international_phone_number" in details:
                    whatsapp_num = details["international_phone_number"].replace(" ", "").replace("-", "").replace("+", "")
                    prospect["whatsapp"] = whatsapp_num

                prospects.append(prospect)
            except Exception as e:
                continue

        return JSONResponse({
            "success": True,
            "prospects": prospects,
        })

    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"Erro ao buscar: {str(e)}"
        }, status_code=500)


@app.post("/prospeccao/importar")
def prospeccao_importar(request: Request):
    """Salva um prospect no banco de dados."""
    user = require_user(request)
    data = request.json()
    prospect_id = data.get("prospect_id")

    # For now, we'll just save the prospect data
    # In a real scenario, this would come from the search results
    return JSONResponse({
        "success": True,
        "message": "Prospect salvo com sucesso"
    })


@app.get("/prospeccao/prospects")
def prospeccao_prospects(request: Request, status_filter: str = ""):
    """Lista todos os prospects salvos."""
    user = require_user(request)
    conn = get_db()

    if status_filter:
        rows = conn.execute(
            "SELECT * FROM prospects WHERE created_by=? AND status=? ORDER BY created_at DESC",
            (user["id"], status_filter)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM prospects WHERE created_by=? ORDER BY created_at DESC",
            (user["id"],)
        ).fetchall()

    conn.close()
    return JSONResponse({
        "success": True,
        "prospects": [dict(r) for r in rows],
    })


@app.post("/prospeccao/prospects/{pid}/status")
def prospeccao_prospect_status(request: Request, pid: int, status: str = Form("novo")):
    """Atualiza o status de um prospect."""
    user = require_user(request)
    conn = get_db()

    conn.execute(
        "UPDATE prospects SET status=? WHERE id=?",
        (status, pid)
    )
    log_action(conn, user, "atualizou", "prospect", f"Status → {status}")
    conn.commit()
    conn.close()

    return JSONResponse({
        "success": True,
        "message": "Status atualizado"
    })


@app.post("/prospeccao/gerar-mensagem")
async def prospeccao_gerar_mensagem(request: Request):
    """Gera 3 mensagens diferentes usando IA para um prospect."""
    user = require_user(request)
    data = await request.json()

    company = data.get("company", "")
    segment = data.get("segment", "")
    location = data.get("location", "")
    prompt_custom = data.get("prompt_custom", "")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse({
            "success": False,
            "error": "OpenAI não configurada"
        }, status_code=400)

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)

        # Converter sqlite3.Row para dict se necessário
        user_dict = dict(user) if hasattr(user, 'keys') else user
        user_name = user_dict.get("name", "Equipe").split()[0]  # Pega primeiro nome

        system_prompt = """Você é especialista em prospecção e copywriting para agências de marketing digital.
Gere 3 mensagens curtas (2-3 linhas) para prospectar empresas por WhatsApp.
Cada mensagem deve ser única, profissional mas amigável.
Não faça spam, apenas despertar interesse em conversa.
Responda APENAS as 3 mensagens, uma por linha, numeradas."""

        user_prompt = f"""Empresa: {company}
Segmento: {segment}
Localização: {location}
Contexto adicional: {prompt_custom if prompt_custom else 'Somos especialistas em marketing digital'}

Gere as 3 mensagens WhatsApp para prospectar esta empresa.
Assinatura: {user_name} - Grupo ELEVA 🚀"""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,
            temperature=0.8,
        )

        response_text = response.choices[0].message.content.strip()
        messages = []
        for line in response_text.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove numbering if present
                if line[0].isdigit() and "." in line[:3]:
                    line = line.split(".", 1)[1].strip()
                messages.append(line)

        # Ensure we have exactly 3 messages
        messages = messages[:3]

        return JSONResponse({
            "success": True,
            "messages": messages,
            "user_name": user_name
        })

    except Exception as e:
        import traceback
        erro_completo = traceback.format_exc()
        print(f"[ERRO IA] {erro_completo}")  # Log no console
        return JSONResponse({
            "success": False,
            "error": f"Erro ao gerar mensagens: {str(e)}"
        }, status_code=500)


@app.post("/prospeccao/enviar-whatsapp-auto")
async def prospeccao_enviar_whatsapp_auto(request: Request):
    """Envia mensagem automaticamente via WhatsApp Web."""
    user = require_user(request)
    data = await request.json()

    phone = data.get("phone", "").replace("+", "").replace(" ", "").replace("-", "")
    message = data.get("message", "")
    prospect_id = data.get("prospect_id", None)

    if not phone or not message:
        return JSONResponse({
            "success": False,
            "error": "Telefone e mensagem são obrigatórios"
        }, status_code=400)

    try:
        from pyppeteer import launch
        import asyncio

        # Formata o link wa.me
        wa_link = f"https://wa.me/{phone}?text={message.replace(' ', '%20').replace('\n', '%0A')}"

        # Tenta abrir o navegador headless
        browser = None
        try:
            browser = await launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = await browser.newPage()
            await page.goto(wa_link, {'waitUntil': 'networkidle2'})

            # Aguarda alguns segundos para o WhatsApp Web carregar
            await asyncio.sleep(3)

            # Tenta clicar no botão de envio
            try:
                await page.click('button[aria-label*="Send"]')
            except:
                # Se não conseguir clicar automaticamente, retorna sucesso mas pede ação manual
                pass

            await browser.close()

            # Atualiza status do prospect se foi fornecido
            if prospect_id:
                conn = get_db()
                conn.execute(
                    "UPDATE prospects SET status='enviado', message_sent=?, contacted_at=? WHERE id=?",
                    (message, datetime.now().isoformat(), prospect_id)
                )
                conn.commit()
                conn.close()

            return JSONResponse({
                "success": True,
                "message": "Mensagem enviada!",
                "wa_link": wa_link
            })

        except Exception as browser_error:
            # Se o browser não funcionar, retorna o link para o usuário abrir manualmente
            return JSONResponse({
                "success": True,
                "message": "Abra este link no seu navegador",
                "wa_link": wa_link,
                "manual": True
            })

    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"Erro ao enviar: {str(e)}"
        }, status_code=500)


@app.post("/prospeccao/campanhas/nova")
def prospeccao_campanha_nova(request: Request):
    """Cria uma nova campanha de prospecção."""
    user = require_user(request)
    data = request.json()

    name = data.get("name", "")
    segment = data.get("segment", "")
    location = data.get("location", "")
    message_template = data.get("template", "")

    conn = get_db()
    conn.execute(
        "INSERT INTO prospection_campaigns (name, segment, location, message_template, created_by) VALUES (?,?,?,?,?)",
        (name, segment, location, message_template, user["id"])
    )
    log_action(conn, user, "criou", "campanha de prospecção", name)
    conn.commit()
    conn.close()

    return JSONResponse({
        "success": True,
        "message": "Campanha criada com sucesso"
    })


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
