import sqlite3
import os
import bcrypt

DB_PATH = os.environ.get("DB_PATH", "eleva.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Check if services column exists in clients table
    cursor = c.execute("PRAGMA table_info(clients)")
    columns = [row[1] for row in cursor.fetchall()]

    # Add services column if it doesn't exist
    if 'services' not in columns:
        try:
            c.execute("ALTER TABLE clients ADD COLUMN services TEXT DEFAULT '[]'")
            conn.commit()
        except:
            pass

    # Check if scheduled_posts table exists and make scheduled_for nullable
    try:
        cursor = c.execute("PRAGMA table_info(scheduled_posts)")
        sp_columns = [row[1] for row in cursor.fetchall()]
        # If table exists, recreate it without NOT NULL on scheduled_for
        if sp_columns:
            c.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_posts_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    client_name TEXT,
                    platform TEXT NOT NULL,
                    content TEXT NOT NULL,
                    image_url TEXT,
                    services TEXT,
                    scheduled_for TEXT,
                    status TEXT DEFAULT 'agendado',
                    posted_at TEXT,
                    responsible TEXT,
                    created_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            try:
                c.execute("""
                    INSERT INTO scheduled_posts_new
                    SELECT * FROM scheduled_posts
                """)
                c.execute("DROP TABLE scheduled_posts")
                c.execute("ALTER TABLE scheduled_posts_new RENAME TO scheduled_posts")
                conn.commit()
            except:
                c.execute("DROP TABLE IF EXISTS scheduled_posts_new")
    except:
        pass

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'ceo',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            company TEXT,
            segment TEXT,
            services TEXT,
            contract_value REAL DEFAULT 0,
            status TEXT DEFAULT 'ativo',
            entry_date TEXT DEFAULT (date('now','localtime')),
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            value REAL NOT NULL,
            date TEXT DEFAULT (date('now','localtime')),
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS prolabore (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ceo_name TEXT NOT NULL,
            value REAL NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            payment_date TEXT,
            status TEXT DEFAULT 'pendente',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            budget REAL NOT NULL,
            spent REAL DEFAULT 0,
            leads INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'ativo',
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS next_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            responsible TEXT,
            deadline TEXT,
            priority TEXT DEFAULT 'media',
            status TEXT DEFAULT 'aberto',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS pipeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_name TEXT NOT NULL,
            company TEXT,
            phone TEXT,
            email TEXT,
            service_type TEXT,
            stage TEXT DEFAULT 'prospecto',
            value REAL DEFAULT 0,
            responsible TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            client_name TEXT,
            title TEXT NOT NULL,
            service_type TEXT,
            status TEXT DEFAULT 'em_andamento',
            start_date TEXT,
            deadline TEXT,
            responsible TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS project_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',
            responsible TEXT,
            deadline TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS financial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            client_name TEXT,
            description TEXT NOT NULL,
            type TEXT DEFAULT 'receita',
            value REAL NOT NULL,
            due_date TEXT,
            paid_date TEXT,
            status TEXT DEFAULT 'pendente',
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS content_calendar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            client_name TEXT,
            title TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            copy_text TEXT,
            status TEXT DEFAULT 'planejado',
            scheduled_date TEXT,
            responsible TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS copies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            client_name TEXT,
            title TEXT NOT NULL,
            copy_type TEXT,
            platform TEXT,
            content TEXT,
            niche TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            action TEXT,
            entity_type TEXT,
            details TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_name TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            specialty TEXT,
            status TEXT DEFAULT 'ativo',
            hourly_rate REAL,
            avatar_color TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            client_name TEXT,
            title TEXT NOT NULL,
            description TEXT,
            services TEXT,
            total_value REAL NOT NULL,
            deadline TEXT,
            status TEXT DEFAULT 'rascunho',
            sent_date TEXT,
            accepted_date TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            client_name TEXT,
            platform TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            services TEXT,
            scheduled_for TEXT NOT NULL,
            status TEXT DEFAULT 'agendado',
            posted_at TEXT,
            responsible TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            client_name TEXT,
            title TEXT NOT NULL,
            description TEXT,
            content TEXT,
            status TEXT DEFAULT 'rascunho',
            sent_date TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            segment TEXT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            email TEXT,
            phone TEXT,
            whatsapp TEXT,
            status TEXT DEFAULT 'novo',
            message_sent TEXT,
            contacted_at TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS prospection_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            segment TEXT,
            location TEXT,
            radius_km INTEGER DEFAULT 5,
            message_template TEXT,
            status TEXT DEFAULT 'ativa',
            prospects_count INTEGER DEFAULT 0,
            messages_sent INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            can_view_dashboard BOOLEAN DEFAULT 0,
            can_view_atividades BOOLEAN DEFAULT 0,
            can_view_prospeccao BOOLEAN DEFAULT 0,
            can_view_pipeline BOOLEAN DEFAULT 0,
            can_view_clientes BOOLEAN DEFAULT 0,
            can_view_financeiro BOOLEAN DEFAULT 0,
            can_view_chat BOOLEAN DEFAULT 0,
            can_view_ia BOOLEAN DEFAULT 0,
            can_view_relatorios BOOLEAN DEFAULT 0,
            can_view_propostas BOOLEAN DEFAULT 0,
            can_view_agendador BOOLEAN DEFAULT 0,
            can_view_projetos BOOLEAN DEFAULT 0,
            can_view_calendario BOOLEAN DEFAULT 0,
            can_view_copys BOOLEAN DEFAULT 0,
            can_view_anuncios BOOLEAN DEFAULT 0,
            can_view_proximos_passos BOOLEAN DEFAULT 0,
            can_view_investimentos BOOLEAN DEFAULT 0,
            can_view_prolabore BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            related_entity TEXT,
            related_id INTEGER,
            is_read BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);

        CREATE TABLE IF NOT EXISTS revenue_distribution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_value REAL NOT NULL,
            client_name TEXT,
            related_entity TEXT,
            related_id INTEGER,
            ceo_prolabore REAL DEFAULT 0,
            company_cashbox REAL DEFAULT 0,
            investment_expansion REAL DEFAULT 0,
            accumulated_profit REAL DEFAULT 0,
            distributed_at TEXT DEFAULT (datetime('now','localtime')),
            created_by INTEGER,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS sector_balance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sector TEXT UNIQUE NOT NULL,
            total_accumulated REAL DEFAULT 0,
            last_updated TEXT DEFAULT (datetime('now','localtime'))
        );

        INSERT OR IGNORE INTO sector_balance (sector, total_accumulated) VALUES ('ceo_prolabore', 0);
        INSERT OR IGNORE INTO sector_balance (sector, total_accumulated) VALUES ('company_cashbox', 0);
        INSERT OR IGNORE INTO sector_balance (sector, total_accumulated) VALUES ('investment_expansion', 0);
        INSERT OR IGNORE INTO sector_balance (sector, total_accumulated) VALUES ('accumulated_profit', 0);
    """)

    row = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if row == 0:
        hashed = bcrypt.hashpw(b"eleva2024", bcrypt.gensalt()).decode()
        c.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Admin", "admin@eleva.com", hashed, "admin"),
        )
        admin_id = c.lastrowid
        create_user_permissions(conn, admin_id, is_admin=True)

    conn.commit()
    conn.close()


def log_action(conn, user, action: str, entity_type: str, details: str = ""):
    """Record every CEO action in the activity log."""
    try:
        conn.execute(
            "INSERT INTO activity_log (user_id, user_name, action, entity_type, details) VALUES (?,?,?,?,?)",
            (user["id"], user["name"], action, entity_type, details),
        )
    except Exception:
        pass


def create_user_permissions(conn, user_id: int, is_admin: bool = False):
    """Create permission record for a new user. Admin/CEO get all perms, others get none."""
    if is_admin:
        # Admin/CEO can view everything
        conn.execute(
            """INSERT INTO user_permissions (user_id, can_view_dashboard, can_view_atividades,
            can_view_prospeccao, can_view_pipeline, can_view_clientes, can_view_financeiro,
            can_view_chat, can_view_ia, can_view_relatorios, can_view_propostas,
            can_view_agendador, can_view_projetos, can_view_calendario, can_view_copys,
            can_view_anuncios, can_view_proximos_passos, can_view_investimentos, can_view_prolabore)
            VALUES (?, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)""",
            (user_id,),
        )
    else:
        # Funcionários começam com zero perms (CEO habilita depois)
        conn.execute(
            """INSERT INTO user_permissions (user_id) VALUES (?)""",
            (user_id,),
        )


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def create_notification(conn, user_id: int, title: str, message: str, notification_type: str = "info", related_entity: str = None, related_id: int = None):
    """Create a notification for a user."""
    conn.execute(
        "INSERT INTO notifications (user_id, title, message, type, related_entity, related_id) VALUES (?,?,?,?,?,?)",
        (user_id, title, message, notification_type, related_entity, related_id)
    )
    # Note: caller is responsible for commit()


def distribute_revenue(conn, contract_value: float, client_name: str = "", related_entity: str = None, related_id: int = None, user_id: int = None, notes: str = ""):
    """Distribute revenue according to policy: 40% CEO, 30% Cashbox, 20% Investment, 10% Profit."""
    ceo_prolabore = contract_value * 0.40
    company_cashbox = contract_value * 0.30
    investment_expansion = contract_value * 0.20
    accumulated_profit = contract_value * 0.10

    # Insert distribution record
    conn.execute(
        """INSERT INTO revenue_distribution
        (contract_value, client_name, related_entity, related_id, ceo_prolabore, company_cashbox, investment_expansion, accumulated_profit, created_by, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (contract_value, client_name, related_entity, related_id, ceo_prolabore, company_cashbox, investment_expansion, accumulated_profit, user_id, notes)
    )

    # Update sector balances
    conn.execute("UPDATE sector_balance SET total_accumulated = total_accumulated + ? WHERE sector = 'ceo_prolabore'", (ceo_prolabore,))
    conn.execute("UPDATE sector_balance SET total_accumulated = total_accumulated + ? WHERE sector = 'company_cashbox'", (company_cashbox,))
    conn.execute("UPDATE sector_balance SET total_accumulated = total_accumulated + ? WHERE sector = 'investment_expansion'", (investment_expansion,))
    conn.execute("UPDATE sector_balance SET total_accumulated = total_accumulated + ? WHERE sector = 'accumulated_profit'", (accumulated_profit,))

    # Note: caller is responsible for commit()

    return {
        "ceo_prolabore": ceo_prolabore,
        "company_cashbox": company_cashbox,
        "investment_expansion": investment_expansion,
        "accumulated_profit": accumulated_profit
    }
