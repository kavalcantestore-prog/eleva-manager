#!/usr/bin/env python3
"""
Script de backup automático do banco de dados ELEVA
Faz backup diário e mantém os últimos 30 dias
"""

import shutil
import os
from datetime import datetime
from pathlib import Path

# Configurações
DB_FILE = "eleva.db"
BACKUP_DIR = Path("backups")
MAX_BACKUPS = 30  # Manter últimos 30 backups

def create_backup():
    """Cria backup do banco de dados"""

    # Criar pasta de backups se não existir
    BACKUP_DIR.mkdir(exist_ok=True)

    if not os.path.exists(DB_FILE):
        print(f"❌ Banco de dados '{DB_FILE}' não encontrado!")
        return False

    # Nome do arquivo com data/hora
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"eleva_backup_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_filename

    try:
        # Copiar banco para backup
        shutil.copy2(DB_FILE, backup_path)
        file_size = os.path.getsize(backup_path) / (1024 * 1024)  # MB
        print(f"✅ Backup criado: {backup_filename} ({file_size:.2f} MB)")

        # Limpar backups antigos
        cleanup_old_backups()

        return True
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        return False

def cleanup_old_backups():
    """Remove backups mais antigos que MAX_BACKUPS"""

    if not BACKUP_DIR.exists():
        return

    backups = sorted(BACKUP_DIR.glob("eleva_backup_*.db"))

    if len(backups) > MAX_BACKUPS:
        to_delete = backups[:-MAX_BACKUPS]
        for backup in to_delete:
            try:
                backup.unlink()
                print(f"🗑️  Backup antigo removido: {backup.name}")
            except Exception as e:
                print(f"⚠️  Erro ao remover {backup.name}: {e}")

def list_backups():
    """Lista todos os backups existentes"""

    if not BACKUP_DIR.exists():
        print("📁 Nenhum backup encontrado ainda.")
        return

    backups = sorted(BACKUP_DIR.glob("eleva_backup_*.db"))

    if not backups:
        print("📁 Nenhum backup encontrado.")
        return

    print("\n📋 Backups Disponíveis:")
    print("-" * 60)

    for backup in backups:
        size = os.path.getsize(backup) / (1024 * 1024)
        mod_time = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"  📦 {backup.name}")
        print(f"     Tamanho: {size:.2f} MB | Data: {mod_time.strftime('%d/%m/%Y %H:%M:%S')}")

    print("-" * 60)
    print(f"✅ Total: {len(backups)} backups (mantendo os últimos {MAX_BACKUPS})\n")

if __name__ == "__main__":
    print("=" * 60)
    print("ELEVA - Backup Database System 🔄")
    print("=" * 60)
    print()

    # Criar backup
    if create_backup():
        print()
        list_backups()
    else:
        print("\n❌ Falha ao criar backup!")
