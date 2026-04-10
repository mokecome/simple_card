"""
新增名片重複檢測相關欄位

執行：
python -c "from backend.migrations.add_duplicate_fields import upgrade; upgrade()"
"""

from sqlalchemy import create_engine, text
import hashlib
import os
import sys


def compute_duplicate_group_id(name_zh, company_name_zh):
    """計算重複組 ID：md5(name_zh|company_name_zh)"""
    key = f"{name_zh or ''}|{company_name_zh or ''}"
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def upgrade():
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./cards.db')
    engine = create_engine(database_url)

    print("開始新增重複檢測欄位...")

    # Step 1: Add new columns
    fields_to_add = [
        ("duplicate_group_id", "VARCHAR(32)", "重複群組ID (md5 hash)"),
        ("reviewed_at", "DATETIME", "已審核時間"),
    ]

    with engine.connect() as conn:
        for field_name, field_type, field_desc in fields_to_add:
            try:
                conn.execute(text(f"ALTER TABLE cards ADD COLUMN {field_name} {field_type}"))
                conn.commit()
                print(f"已新增欄位: {field_name} ({field_desc})")
            except Exception:
                print(f"略過欄位: {field_name}，可能已存在")

        # Step 2: Create index on duplicate_group_id
        try:
            conn.execute(text("CREATE INDEX idx_duplicate_group_id ON cards (duplicate_group_id)"))
            conn.commit()
            print("已建立索引: idx_duplicate_group_id")
        except Exception:
            print("略過索引: idx_duplicate_group_id，可能已存在")

        # Step 3: Initialize duplicate_group_id for existing duplicate groups
        print("開始掃描現有重複名片...")

        # Find all duplicate groups: same name_zh + company_name_zh with count > 1
        # Treat NULL as empty string for grouping purposes
        rows = conn.execute(text("""
            SELECT COALESCE(name_zh, '') AS nz, COALESCE(company_name_zh, '') AS cz, COUNT(*) AS cnt
            FROM cards
            WHERE NOT (COALESCE(name_zh, '') = '' AND COALESCE(company_name_zh, '') = '')
            GROUP BY COALESCE(name_zh, ''), COALESCE(company_name_zh, '')
            HAVING COUNT(*) > 1
        """)).fetchall()

        print(f"找到 {len(rows)} 組重複名片")

        updated_count = 0
        for row in rows:
            name_zh = row[0]  # already coalesced to ''
            company_name_zh = row[1]
            group_hash = compute_duplicate_group_id(name_zh, company_name_zh)

            # Update all cards in this group
            # Match using COALESCE to handle both NULL and empty string consistently
            result = conn.execute(
                text("""
                    UPDATE cards
                    SET duplicate_group_id = :group_hash
                    WHERE COALESCE(name_zh, '') = :name_zh
                      AND COALESCE(company_name_zh, '') = :company_name_zh
                """),
                {"group_hash": group_hash, "name_zh": name_zh, "company_name_zh": company_name_zh}
            )
            updated_count += result.rowcount

        conn.commit()
        print(f"已更新 {updated_count} 張名片的重複群組ID")

    print("重複檢測欄位新增完成")


def downgrade():
    print("SQLite 不方便直接 DROP COLUMN。")
    print("如需回退，建議先還原資料庫備份。")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
