# Скрипт проверки подключения к PostgreSQL. Запуск: python check_db.py
import os
import sys

# Задать кодировку до импорта psycopg2 (фикс UnicodeDecodeError на Windows)
os.environ.setdefault("PGCLIENTENCODING", "UTF8")

def main():
    try:
        from config import settings
        print("Config loaded. DB params:", {k: v for k, v in [
            ("DB_HOST", settings.DB_HOST),
            ("DB_PORT", settings.DB_PORT),
            ("DB_NAME", settings.DB_NAME),
            ("DB_USER", settings.DB_USER),
            ("DB_PASS", "***" if settings.DB_PASS else "(empty)"),
        ]})
    except Exception as e:
        print(f"Config load failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        import psycopg2
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASS,
            connect_timeout=5,
        )
        conn.close()
        print("OK: PostgreSQL connection successful")
        sys.exit(0)
    except Exception as e:
        print(f"Connection failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
