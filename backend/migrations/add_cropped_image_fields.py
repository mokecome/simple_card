"""
新增名片裁切相關欄位

執行：
python -c "from backend.migrations.add_cropped_image_fields import upgrade; upgrade()"
"""

from sqlalchemy import create_engine, text
import os
import sys


def upgrade():
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./cards.db')
    #database_url = 'sqlite:///./cards_backup_20260309_162728.db'
    engine = create_engine(database_url)

    print("開始新增裁切欄位...")

    fields_to_add = [
        ("front_cropped_image_path", "VARCHAR(500)", "正面裁切後圖片路徑"),
        ("back_cropped_image_path", "VARCHAR(500)", "反面裁切後圖片路徑"),
        ("front_crop_corners", "TEXT", "正面裁切四點座標"),
        ("back_crop_corners", "TEXT", "反面裁切四點座標"),
    ]

    with engine.connect() as conn:
        for field_name, field_type, field_desc in fields_to_add:
            try:
                conn.execute(text(f"ALTER TABLE cards ADD COLUMN {field_name} {field_type}"))
                conn.commit()
                print(f"已新增欄位: {field_name} ({field_desc})")
            except Exception:
                print(f"略過欄位: {field_name}，可能已存在")

    print("裁切欄位新增完成")


def downgrade():
    print("SQLite 不方便直接 DROP COLUMN。")
    print("如需回退，建議先還原資料庫備份。")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
