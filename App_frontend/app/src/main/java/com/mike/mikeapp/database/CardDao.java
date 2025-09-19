package com.mike.mikeapp.database;

import androidx.room.Dao;
import androidx.room.Delete;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;
import androidx.room.Update;

import com.mike.mikeapp.model.Card;

import java.util.List;

/**
 * 名片数据访问对象
 * Room DAO接口
 */
@Dao
public interface CardDao {

    /**
     * 插入名片
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    long insert(Card card);

    /**
     * 插入多张名片
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    List<Long> insertAll(List<Card> cards);

    /**
     * 更新名片
     */
    @Update
    int update(Card card);

    /**
     * 删除名片
     */
    @Delete
    int delete(Card card);

    /**
     * 根据ID删除名片
     */
    @Query("DELETE FROM cards WHERE id = :id")
    int deleteById(int id);

    /**
     * 删除所有名片
     */
    @Query("DELETE FROM cards")
    int deleteAll();

    /**
     * 根据ID获取名片
     */
    @Query("SELECT * FROM cards WHERE id = :id")
    Card getCardById(int id);

    /**
     * 获取所有名片
     */
    @Query("SELECT * FROM cards ORDER BY id DESC")
    List<Card> getAllCards();

    /**
     * 分页获取名片
     */
    @Query("SELECT * FROM cards ORDER BY id DESC LIMIT :limit OFFSET :offset")
    List<Card> getCardsPage(int limit, int offset);

    /**
     * 搜索名片
     */
    @Query("SELECT * FROM cards WHERE " +
            "name_zh LIKE '%' || :query || '%' OR " +
            "name_en LIKE '%' || :query || '%' OR " +
            "company_name_zh LIKE '%' || :query || '%' OR " +
            "company_name_en LIKE '%' || :query || '%' OR " +
            "position_zh LIKE '%' || :query || '%' OR " +
            "position_en LIKE '%' || :query || '%' OR " +
            "position1_zh LIKE '%' || :query || '%' OR " +
            "position1_en LIKE '%' || :query || '%' OR " +
            "department1_zh LIKE '%' || :query || '%' OR " +
            "department1_en LIKE '%' || :query || '%' OR " +
            "mobile_phone LIKE '%' || :query || '%' OR " +
            "company_phone1 LIKE '%' || :query || '%' OR " +
            "email LIKE '%' || :query || '%' OR " +
            "line_id LIKE '%' || :query || '%' " +
            "ORDER BY id DESC")
    List<Card> searchCards(String query);

    /**
     * 根据健康状态获取名片
     */
    @Query("SELECT * FROM cards WHERE health_status = :healthStatus ORDER BY id DESC")
    List<Card> getCardsByHealthStatus(String healthStatus);

    /**
     * 获取名片总数
     */
    @Query("SELECT COUNT(*) FROM cards")
    int getTotalCount();

    /**
     * 根据健康状态获取名片数量
     */
    @Query("SELECT COUNT(*) FROM cards WHERE health_status = :healthStatus")
    int getCountByHealthStatus(String healthStatus);

    /**
     * 获取正常名片数量
     */
    @Query("SELECT COUNT(*) FROM cards WHERE health_status = 'normal'")
    int getNormalCardsCount();

    /**
     * 获取问题名片数量
     */
    @Query("SELECT COUNT(*) FROM cards WHERE health_status = 'incomplete'")
    int getIncompleteCardsCount();

    /**
     * 检查名片是否存在（根据姓名和公司）
     */
    @Query("SELECT COUNT(*) FROM cards WHERE " +
            "(name_zh = :nameZh OR name_en = :nameEn) AND " +
            "(company_name_zh = :companyZh OR company_name_en = :companyEn)")
    int checkCardExists(String nameZh, String nameEn, String companyZh, String companyEn);

    /**
     * 更新名片健康状态
     */
    @Query("UPDATE cards SET health_status = :healthStatus WHERE id = :id")
    int updateHealthStatus(int id, String healthStatus);

    /**
     * 批量更新健康状态
     */
    @Query("UPDATE cards SET health_status = " +
            "CASE " +
            "WHEN (name_zh != '' OR name_en != '') AND " +
            "(company_name_zh != '' OR company_name_en != '') AND " +
            "(position_zh != '' OR position_en != '' OR position1_zh != '' OR position1_en != '' OR " +
            " department1_zh != '' OR department1_en != '' OR department2_zh != '' OR department2_en != '' OR " +
            " department3_zh != '' OR department3_en != '') AND " +
            "(mobile_phone != '' OR company_phone1 != '' OR company_phone2 != '' OR email != '' OR line_id != '') " +
            "THEN 'normal' " +
            "ELSE 'incomplete' " +
            "END")
    int updateAllHealthStatus();

    /**
     * 获取最近添加的名片
     */
    @Query("SELECT * FROM cards ORDER BY id DESC LIMIT :limit")
    List<Card> getRecentCards(int limit);

    /**
     * 根据公司分组获取名片数量
     */
    @Query("SELECT company_name_zh as company, COUNT(*) as count FROM cards " +
            "WHERE company_name_zh != '' " +
            "GROUP BY company_name_zh " +
            "ORDER BY count DESC " +
            "LIMIT :limit")
    List<CompanyCount> getTopCompanies(int limit);

    /**
     * 公司统计内部类
     */
    class CompanyCount {
        public String company;
        public int count;
    }
}