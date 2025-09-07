-- 名片系統欄位標準化遷移腳本
-- 將Card Model欄位名稱更新為與API格式匹配的標準命名
-- 
-- 執行前請務必備份資料庫！
-- 
-- 使用方法：
-- SQLite: sqlite3 database.db < migration_update_card_fields.sql
-- PostgreSQL: psql -d database_name -f migration_update_card_fields.sql

-- 開始事務
BEGIN;

-- 步驟1: 新增新的欄位 (使用標準化命名)
ALTER TABLE cards ADD COLUMN name_zh VARCHAR(100);
ALTER TABLE cards ADD COLUMN company_name_zh VARCHAR(200);
ALTER TABLE cards ADD COLUMN position_zh VARCHAR(100);
ALTER TABLE cards ADD COLUMN position1_zh VARCHAR(255);
ALTER TABLE cards ADD COLUMN department1_zh VARCHAR(100);
ALTER TABLE cards ADD COLUMN department2_zh VARCHAR(100);
ALTER TABLE cards ADD COLUMN department3_zh VARCHAR(100);
ALTER TABLE cards ADD COLUMN company_address1_zh VARCHAR(300);
ALTER TABLE cards ADD COLUMN company_address2_zh VARCHAR(300);

-- 新增API需要的額外欄位
ALTER TABLE cards ADD COLUMN fax VARCHAR(50);
ALTER TABLE cards ADD COLUMN wechat_id VARCHAR(100);

-- 步驟2: 複製舊欄位資料到新欄位
UPDATE cards SET 
    name_zh = name,
    company_name_zh = company_name,
    position_zh = position,
    position1_zh = position1,
    department1_zh = department1,
    department2_zh = department2,
    department3_zh = department3,
    company_address1_zh = company_address1,
    company_address2_zh = company_address2
WHERE name IS NOT NULL OR company_name IS NOT NULL;

-- 步驟3: 重建索引 (先刪除舊索引)
DROP INDEX IF EXISTS idx_name_company;
DROP INDEX IF EXISTS idx_name_phone;

-- 創建新的複合索引
CREATE INDEX idx_name_company ON cards(name_zh, company_name_zh);
CREATE INDEX idx_name_phone ON cards(name_zh, mobile_phone);

-- 為新欄位添加索引
CREATE INDEX idx_name_zh ON cards(name_zh);
CREATE INDEX idx_company_name_zh ON cards(company_name_zh);

-- 步驟4: 刪除舊欄位 (注意：這會永久刪除舊欄位資料！)
-- 取消註解以下語句以刪除舊欄位
-- ALTER TABLE cards DROP COLUMN name;
-- ALTER TABLE cards DROP COLUMN company_name;
-- ALTER TABLE cards DROP COLUMN position;
-- ALTER TABLE cards DROP COLUMN position1;
-- ALTER TABLE cards DROP COLUMN department1;
-- ALTER TABLE cards DROP COLUMN department2; 
-- ALTER TABLE cards DROP COLUMN department3;
-- ALTER TABLE cards DROP COLUMN company_address1;
-- ALTER TABLE cards DROP COLUMN company_address2;

-- 提交事務
COMMIT;

-- 驗證遷移結果
SELECT 
    COUNT(*) as total_records,
    COUNT(name_zh) as has_name_zh,
    COUNT(company_name_zh) as has_company_name_zh,
    COUNT(fax) as has_fax,
    COUNT(wechat_id) as has_wechat_id
FROM cards;

-- 顯示遷移後的表結構
-- SQLite: .schema cards
-- PostgreSQL: \d cards