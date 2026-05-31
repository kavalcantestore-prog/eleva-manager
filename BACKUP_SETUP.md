# 🔄 Sistema de Backup Automático - ELEVA

## 📋 O que foi criado?

1. **`backup_db.py`** - Script que copia o banco de dados
2. **`setup_backup_scheduler.bat`** - Configura agendamento automático
3. **Pasta `backups/`** - Onde os backups são salvos (criada automaticamente)

---

## 🚀 Como ativar o Backup Automático

### **Passo 1: Executar como ADMINISTRADOR**

1. **Clique com botão direito** em `setup_backup_scheduler.bat`
2. Selecione **"Executar como administrador"**
3. Pressione **ENTER** para confirmar

```
========================================
ELEVA - Setup Agendador de Backup
========================================

Criando tarefa agendada: ELEVA-Backup-Database
...
SUCCESS! ✅

Tarefa agendada com sucesso!
Nome: ELEVA-Backup-Database
Horario: 23:00 (11:00 PM) todos os dias
```

### **Passo 2: Verificar se funcionou**

Abra **Agendador de Tarefas** (Task Scheduler):
1. Pressione `Win + R`
2. Digite: `taskmgr`
3. Procure pela aba **"Tarefas Agendadas"**
4. Procure por: **ELEVA-Backup-Database** ✅

---

## 📦 Como usar Manualmente

Se quiser fazer backup **agora** (sem esperar as 23:00):

```cmd
cd Desktop\eleva-manager
python backup_db.py
```

**Output esperado:**
```
✅ Backup criado: eleva_backup_2026-05-31_23-45-12.db (0.05 MB)

📋 Backups Disponíveis:
------------------------------------------------------------
  📦 eleva_backup_2026-05-31_23-45-12.db
     Tamanho: 0.05 MB | Data: 31/05/2026 23:45:12
------------------------------------------------------------
✅ Total: 1 backups (mantendo os últimos 30)
```

---

## 📁 Estrutura de Backups

```
eleva-manager/
├── eleva.db                    ← Banco atual (em produção)
├── backups/                    ← Pasta de backups
│   ├── eleva_backup_2026-05-31_23-00-00.db
│   ├── eleva_backup_2026-05-30_23-00-00.db
│   ├── eleva_backup_2026-05-29_23-00-00.db
│   └── ... (até 30 backups)
├── backup_db.py                ← Script de backup
└── setup_backup_scheduler.bat  ← Agendador
```

---

## ⏰ Agendamento

| Configuração | Valor |
|-------------|-------|
| **Frequência** | Diária |
| **Horário** | 23:00 (11:00 PM) |
| **Retenção** | Últimos 30 backups |
| **Pasta** | `backups/` |

---

## 🔍 Verificar Backups Existentes

Para listar todos os backups criados:

```cmd
python backup_db.py
```

Isso vai mostrar a lista com tamanho e data de cada backup.

---

## 💾 Restaurar de um Backup

Se precisar restaurar:

1. **Parar a aplicação** no Railway
2. **Copiar o arquivo de backup** da pasta `backups/`
3. **Renomear para** `eleva.db`
4. **Fazer upload** para o Railway
5. **Reiniciar** o serviço

---

## 🛡️ Segurança & Dicas

### ✅ Boas Práticas
- ✅ Manter os últimos 30 backups (automático)
- ✅ Rodar backup todo dia (23:00)
- ✅ Verificar a pasta `backups/` regularmente
- ✅ Fazer backup mensal para pendrive/nuvem

### ⚠️ Cuidados
- ⚠️ Não deletar a pasta `backups/` acidentalmente
- ⚠️ Manter espaço em disco disponível (cada backup ~0.05 MB)
- ⚠️ Se houver erro, verificar o Event Viewer do Windows

---

## 🆘 Troubleshooting

### "Erro: Permission Denied"
**Solução:** Execute como ADMINISTRADOR (clique direito → "Executar como administrador")

### "Erro: Python not found"
**Solução:** Instale Python ou adicione ao PATH do Windows

### "A tarefa não rodou"
**Solução:** Verifique em Task Scheduler se a tarefa está **ATIVADA** (deve estar com ✅)

---

## 📞 Próximos Passos

- [ ] Executar `setup_backup_scheduler.bat` como administrador
- [ ] Verificar em Task Scheduler se tarefa foi criada
- [ ] Rodar `python backup_db.py` manualmente para testar
- [ ] Aguardar 23:00 para ver o backup automático
- [ ] Fazer backup semanal para nuvem (Google Drive/OneDrive)

---

**Seu banco de dados está seguro! 🔒**
