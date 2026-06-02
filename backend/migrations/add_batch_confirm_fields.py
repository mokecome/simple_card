"""
新增名片批次上傳與確認相關欄位

執行：
python -c "from backend.migrations.add_batch_confirm_fields import upgrade; upgrade()"
或
python backend/migrations/add_batch_confirm_fields.py
回退（僅提示，SQLite 不便直接 DROP COLUMN）：
python backend/migrations/add_batch_confirm_fields.py downgrade
"""

from sqlalchemy import create_engine, text
import os
import sys


def upgrade():
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./cards.db')
    engine = create_engine(database_url)

    print("開始新增批次上傳與確認欄位...")

    # Step 1: Add new columns
    fields_to_add = [
        ("batch_id", "VARCHAR(64)", "批次上傳 UUID，同批次共用"),
        ("confirmed_at", "DATETIME", "確認時間，NULL 表示待確認"),
    ]

    with engine.connect() as conn:
        for field_name, field_type, field_desc in fields_to_add:
            try:
                conn.execute(text(f"ALTER TABLE cards ADD COLUMN {field_name} {field_type}"))
                conn.commit()
                print(f"已新增欄位: {field_name} ({field_desc})")
            except Exception:
                print(f"略過欄位: {field_name}，可能已存在")

        # Step 2: Create indexes on new columns
        indexes_to_create = [
            ("idx_batch_id", "batch_id"),
            ("idx_confirmed_at", "confirmed_at"),
        ]
        for index_name, column_name in indexes_to_create:
            try:
                conn.execute(text(f"CREATE INDEX {index_name} ON cards ({column_name})"))
                conn.commit()
                print(f"已建立索引: {index_name}")
            except Exception:
                print(f"略過索引: {index_name}，可能已存在")

    print("批次上傳與確認欄位新增完成")


def downgrade():
    print("SQLite 不方便直接 DROP COLUMN。")
    print("如需回退，建議先還原資料庫備份。")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
