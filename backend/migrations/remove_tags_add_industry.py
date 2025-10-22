"""
移除标签系统，添加 AI 产业分类字段

执行方式：
python -c "from backend.migrations.remove_tags_add_industry import upgrade; upgrade()"

回滚方式（谨慎使用）：
python -c "from backend.migrations.remove_tags_add_industry import downgrade; downgrade()"
"""

from sqlalchemy import create_engine, text
import os
import sys

def upgrade():
    """升级数据库：删除标签表，添加产业分类字段"""
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./cards.db')
    engine = create_engine(database_url)

    print("🚀 开始数据库迁移...")

    with engine.connect() as conn:
        # 1. 删除 card_tags 表
        print("📝 删除 card_tags 表...")
        try:
            conn.execute(text("DROP TABLE IF EXISTS card_tags"))
            conn.commit()
            print("✅ card_tags 表已删除")
        except Exception as e:
            print(f"⚠️  删除 card_tags 表失败（可能不存在）: {e}")

        # 2. 在 cards 表添加新字段
        print("\n📝 添加产业分类字段...")

        fields_to_add = [
            ("industry_category", "VARCHAR(50)", "产业分类"),
            ("classification_confidence", "FLOAT", "分类信心度"),
            ("classification_reason", "TEXT", "分类理由"),
            ("classified_at", "DATETIME", "分类时间")
        ]

        for field_name, field_type, field_desc in fields_to_add:
            try:
                conn.execute(text(f"ALTER TABLE cards ADD COLUMN {field_name} {field_type}"))
                conn.commit()
                print(f"✅ 已添加字段: {field_name} ({field_desc})")
            except Exception as e:
                print(f"⚠️  字段 {field_name} 已存在，跳过")

        # 3. 创建索引
        print("\n📝 创建索引...")

        indexes_to_create = [
            ("idx_industry", "industry_category", "产业分类索引"),
            ("idx_classified_at", "classified_at", "分类时间索引")
        ]

        for index_name, column_name, index_desc in indexes_to_create:
            try:
                conn.execute(text(f"CREATE INDEX {index_name} ON cards ({column_name})"))
                conn.commit()
                print(f"✅ 已创建索引: {index_name} ({index_desc})")
            except Exception as e:
                print(f"⚠️  索引 {index_name} 已存在，跳过")

        conn.commit()

    print("\n✅ 数据库迁移完成！")
    print("\n📊 迁移总结:")
    print("  - 已删除: card_tags 表")
    print("  - 已添加: 4 个产业分类字段")
    print("  - 已创建: 2 个索引")
    print("\n⚠️  提醒: 原标签数据已永久删除，如需恢复请使用备份文件 cards.db.backup")

def downgrade():
    """
    回滚数据库（谨慎使用）
    注意：无法恢复已删除的 card_tags 表数据
    """
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./cards.db')
    engine = create_engine(database_url)

    print("⚠️  警告: 即将回滚数据库变更...")
    response = input("确定要继续吗？这将删除所有产业分类数据。(yes/no): ")

    if response.lower() != 'yes':
        print("❌ 回滚已取消")
        return

    print("\n🔄 开始回滚...")

    with engine.connect() as conn:
        # 删除索引
        print("📝 删除索引...")
        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_industry"))
            conn.execute(text("DROP INDEX IF EXISTS idx_classified_at"))
            print("✅ 索引已删除")
        except Exception as e:
            print(f"⚠️  删除索引失败: {e}")

        # 删除字段（SQLite 不支持 DROP COLUMN，需要重建表）
        print("\n⚠️  SQLite 不支持直接删除列")
        print("请使用备份文件恢复: cp cards.db.backup cards.db")

        conn.commit()

    print("\n⚠️  回滚部分完成，请手动恢复备份文件以完全回滚")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
