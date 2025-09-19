package com.mike.mikeapp.database;

import android.content.Context;

import androidx.room.Database;
import androidx.room.Room;
import androidx.room.RoomDatabase;
import androidx.room.migration.Migration;
import androidx.sqlite.db.SupportSQLiteDatabase;

import com.mike.mikeapp.model.Card;

/**
 * 名片数据库
 * Room数据库类
 */
@Database(
        entities = {Card.class},
        version = 1,
        exportSchema = false
)
public abstract class CardDatabase extends RoomDatabase {

    private static final String DATABASE_NAME = "card_database";
    private static volatile CardDatabase INSTANCE;

    /**
     * 获取CardDao实例
     */
    public abstract CardDao cardDao();

    /**
     * 获取数据库实例（单例模式）
     */
    public static CardDatabase getInstance(Context context) {
        if (INSTANCE == null) {
            synchronized (CardDatabase.class) {
                if (INSTANCE == null) {
                    INSTANCE = Room.databaseBuilder(
                            context.getApplicationContext(),
                            CardDatabase.class,
                            DATABASE_NAME
                    )
                    .allowMainThreadQueries() // 允许在主线程执行查询（开发阶段使用，生产环境建议移除）
                    .fallbackToDestructiveMigration() // 数据库版本升级时允许破坏性迁移
                    .build();
                }
            }
        }
        return INSTANCE;
    }

    /**
     * 关闭数据库
     */
    public static void closeDatabase() {
        if (INSTANCE != null && INSTANCE.isOpen()) {
            INSTANCE.close();
            INSTANCE = null;
        }
    }

    /**
     * 数据库迁移（如果需要）
     */
    static final Migration MIGRATION_1_2 = new Migration(1, 2) {
        @Override
        public void migrate(SupportSQLiteDatabase database) {
            // 版本1到版本2的迁移逻辑
            // 例如：database.execSQL("ALTER TABLE cards ADD COLUMN new_column TEXT");
        }
    };

    /**
     * 清空数据库
     */
    public void clearAllTables() {
        if (INSTANCE != null) {
            INSTANCE.clearAllTables();
        }
    }

    /**
     * 数据库创建回调
     */
    private static RoomDatabase.Callback roomCallback = new RoomDatabase.Callback() {
        @Override
        public void onCreate(SupportSQLiteDatabase db) {
            super.onCreate(db);
            // 数据库首次创建时的初始化操作
        }

        @Override
        public void onOpen(SupportSQLiteDatabase db) {
            super.onOpen(db);
            // 数据库每次打开时的操作
        }
    };
}