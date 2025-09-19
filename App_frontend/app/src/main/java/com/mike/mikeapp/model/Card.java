package com.mike.mikeapp.model;

import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.PrimaryKey;
import com.google.gson.annotations.SerializedName;
import java.io.Serializable;

/**
 * 名片数据模型类
 * 对应后端API的25个标准字段
 */
@Entity(tableName = "cards")
public class Card implements Serializable {
    @PrimaryKey(autoGenerate = true)
    private int id;

    // 基本信息 (8字段)
    @ColumnInfo(name = "name_zh")
    @SerializedName("name_zh")
    private String nameZh;

    @ColumnInfo(name = "name_en")
    @SerializedName("name_en")
    private String nameEn;

    @ColumnInfo(name = "company_name_zh")
    @SerializedName("company_name_zh")
    private String companyNameZh;

    @ColumnInfo(name = "company_name_en")
    @SerializedName("company_name_en")
    private String companyNameEn;

    @ColumnInfo(name = "position_zh")
    @SerializedName("position_zh")
    private String positionZh;

    @ColumnInfo(name = "position_en")
    @SerializedName("position_en")
    private String positionEn;

    @ColumnInfo(name = "position1_zh")
    @SerializedName("position1_zh")
    private String position1Zh;

    @ColumnInfo(name = "position1_en")
    @SerializedName("position1_en")
    private String position1En;

    // 组织架构 (6字段)
    @ColumnInfo(name = "department1_zh")
    @SerializedName("department1_zh")
    private String department1Zh;

    @ColumnInfo(name = "department1_en")
    @SerializedName("department1_en")
    private String department1En;

    @ColumnInfo(name = "department2_zh")
    @SerializedName("department2_zh")
    private String department2Zh;

    @ColumnInfo(name = "department2_en")
    @SerializedName("department2_en")
    private String department2En;

    @ColumnInfo(name = "department3_zh")
    @SerializedName("department3_zh")
    private String department3Zh;

    @ColumnInfo(name = "department3_en")
    @SerializedName("department3_en")
    private String department3En;

    // 联系信息 (5字段)
    @ColumnInfo(name = "mobile_phone")
    @SerializedName("mobile_phone")
    private String mobilePhone;

    @ColumnInfo(name = "company_phone1")
    @SerializedName("company_phone1")
    private String companyPhone1;

    @ColumnInfo(name = "company_phone2")
    @SerializedName("company_phone2")
    private String companyPhone2;

    @ColumnInfo(name = "email")
    @SerializedName("email")
    private String email;

    @ColumnInfo(name = "line_id")
    @SerializedName("line_id")
    private String lineId;

    // 地址信息 (4字段)
    @ColumnInfo(name = "company_address1_zh")
    @SerializedName("company_address1_zh")
    private String companyAddress1Zh;

    @ColumnInfo(name = "company_address1_en")
    @SerializedName("company_address1_en")
    private String companyAddress1En;

    @ColumnInfo(name = "company_address2_zh")
    @SerializedName("company_address2_zh")
    private String companyAddress2Zh;

    @ColumnInfo(name = "company_address2_en")
    @SerializedName("company_address2_en")
    private String companyAddress2En;

    // 备注信息 (2字段)
    @ColumnInfo(name = "note1")
    @SerializedName("note1")
    private String note1;

    @ColumnInfo(name = "note2")
    @SerializedName("note2")
    private String note2;

    // 系统字段
    @ColumnInfo(name = "created_at")
    @SerializedName("created_at")
    private String createdAt;

    @ColumnInfo(name = "updated_at")
    @SerializedName("updated_at")
    private String updatedAt;

    @ColumnInfo(name = "health_status")
    @SerializedName("health_status")
    private String healthStatus; // "normal" 或 "incomplete"

    @ColumnInfo(name = "image_path")
    private String imagePath; // 本地图片路径

    // 构造函数
    public Card() {
        // 默认值为空字符串
        this.nameZh = "";
        this.nameEn = "";
        this.companyNameZh = "";
        this.companyNameEn = "";
        this.positionZh = "";
        this.positionEn = "";
        this.position1Zh = "";
        this.position1En = "";
        this.department1Zh = "";
        this.department1En = "";
        this.department2Zh = "";
        this.department2En = "";
        this.department3Zh = "";
        this.department3En = "";
        this.mobilePhone = "";
        this.companyPhone1 = "";
        this.companyPhone2 = "";
        this.email = "";
        this.lineId = "";
        this.companyAddress1Zh = "";
        this.companyAddress1En = "";
        this.companyAddress2Zh = "";
        this.companyAddress2En = "";
        this.note1 = "";
        this.note2 = "";
        this.healthStatus = "incomplete";
        this.imagePath = "";
    }

    // Getter and Setter methods
    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public String getNameZh() {
        return nameZh != null ? nameZh : "";
    }

    public void setNameZh(String nameZh) {
        this.nameZh = nameZh != null ? nameZh : "";
    }

    public String getNameEn() {
        return nameEn != null ? nameEn : "";
    }

    public void setNameEn(String nameEn) {
        this.nameEn = nameEn != null ? nameEn : "";
    }

    public String getCompanyNameZh() {
        return companyNameZh != null ? companyNameZh : "";
    }

    public void setCompanyNameZh(String companyNameZh) {
        this.companyNameZh = companyNameZh != null ? companyNameZh : "";
    }

    public String getCompanyNameEn() {
        return companyNameEn != null ? companyNameEn : "";
    }

    public void setCompanyNameEn(String companyNameEn) {
        this.companyNameEn = companyNameEn != null ? companyNameEn : "";
    }

    public String getPositionZh() {
        return positionZh != null ? positionZh : "";
    }

    public void setPositionZh(String positionZh) {
        this.positionZh = positionZh != null ? positionZh : "";
    }

    public String getPositionEn() {
        return positionEn != null ? positionEn : "";
    }

    public void setPositionEn(String positionEn) {
        this.positionEn = positionEn != null ? positionEn : "";
    }

    public String getPosition1Zh() {
        return position1Zh != null ? position1Zh : "";
    }

    public void setPosition1Zh(String position1Zh) {
        this.position1Zh = position1Zh != null ? position1Zh : "";
    }

    public String getPosition1En() {
        return position1En != null ? position1En : "";
    }

    public void setPosition1En(String position1En) {
        this.position1En = position1En != null ? position1En : "";
    }

    public String getDepartment1Zh() {
        return department1Zh != null ? department1Zh : "";
    }

    public void setDepartment1Zh(String department1Zh) {
        this.department1Zh = department1Zh != null ? department1Zh : "";
    }

    public String getDepartment1En() {
        return department1En != null ? department1En : "";
    }

    public void setDepartment1En(String department1En) {
        this.department1En = department1En != null ? department1En : "";
    }

    public String getDepartment2Zh() {
        return department2Zh != null ? department2Zh : "";
    }

    public void setDepartment2Zh(String department2Zh) {
        this.department2Zh = department2Zh != null ? department2Zh : "";
    }

    public String getDepartment2En() {
        return department2En != null ? department2En : "";
    }

    public void setDepartment2En(String department2En) {
        this.department2En = department2En != null ? department2En : "";
    }

    public String getDepartment3Zh() {
        return department3Zh != null ? department3Zh : "";
    }

    public void setDepartment3Zh(String department3Zh) {
        this.department3Zh = department3Zh != null ? department3Zh : "";
    }

    public String getDepartment3En() {
        return department3En != null ? department3En : "";
    }

    public void setDepartment3En(String department3En) {
        this.department3En = department3En != null ? department3En : "";
    }

    public String getMobilePhone() {
        return mobilePhone != null ? mobilePhone : "";
    }

    public void setMobilePhone(String mobilePhone) {
        this.mobilePhone = mobilePhone != null ? mobilePhone : "";
    }

    public String getCompanyPhone1() {
        return companyPhone1 != null ? companyPhone1 : "";
    }

    public void setCompanyPhone1(String companyPhone1) {
        this.companyPhone1 = companyPhone1 != null ? companyPhone1 : "";
    }

    public String getCompanyPhone2() {
        return companyPhone2 != null ? companyPhone2 : "";
    }

    public void setCompanyPhone2(String companyPhone2) {
        this.companyPhone2 = companyPhone2 != null ? companyPhone2 : "";
    }

    public String getEmail() {
        return email != null ? email : "";
    }

    public void setEmail(String email) {
        this.email = email != null ? email : "";
    }

    public String getLineId() {
        return lineId != null ? lineId : "";
    }

    public void setLineId(String lineId) {
        this.lineId = lineId != null ? lineId : "";
    }

    public String getCompanyAddress1Zh() {
        return companyAddress1Zh != null ? companyAddress1Zh : "";
    }

    public void setCompanyAddress1Zh(String companyAddress1Zh) {
        this.companyAddress1Zh = companyAddress1Zh != null ? companyAddress1Zh : "";
    }

    public String getCompanyAddress1En() {
        return companyAddress1En != null ? companyAddress1En : "";
    }

    public void setCompanyAddress1En(String companyAddress1En) {
        this.companyAddress1En = companyAddress1En != null ? companyAddress1En : "";
    }

    public String getCompanyAddress2Zh() {
        return companyAddress2Zh != null ? companyAddress2Zh : "";
    }

    public void setCompanyAddress2Zh(String companyAddress2Zh) {
        this.companyAddress2Zh = companyAddress2Zh != null ? companyAddress2Zh : "";
    }

    public String getCompanyAddress2En() {
        return companyAddress2En != null ? companyAddress2En : "";
    }

    public void setCompanyAddress2En(String companyAddress2En) {
        this.companyAddress2En = companyAddress2En != null ? companyAddress2En : "";
    }

    public String getNote1() {
        return note1 != null ? note1 : "";
    }

    public void setNote1(String note1) {
        this.note1 = note1 != null ? note1 : "";
    }

    public String getNote2() {
        return note2 != null ? note2 : "";
    }

    public void setNote2(String note2) {
        this.note2 = note2 != null ? note2 : "";
    }

    public String getCreatedAt() {
        return createdAt != null ? createdAt : "";
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }

    public String getUpdatedAt() {
        return updatedAt != null ? updatedAt : "";
    }

    public void setUpdatedAt(String updatedAt) {
        this.updatedAt = updatedAt;
    }

    public String getHealthStatus() {
        return healthStatus != null ? healthStatus : "incomplete";
    }

    public void setHealthStatus(String healthStatus) {
        this.healthStatus = healthStatus != null ? healthStatus : "incomplete";
    }

    public String getImagePath() {
        return imagePath != null ? imagePath : "";
    }

    public void setImagePath(String imagePath) {
        this.imagePath = imagePath != null ? imagePath : "";
    }

    /**
     * 获取显示用的姓名（优先中文，其次英文）
     */
    public String getDisplayName() {
        if (!getNameZh().isEmpty()) {
            return getNameZh();
        }
        return getNameEn();
    }

    /**
     * 获取显示用的公司名称（优先中文，其次英文）
     */
    public String getDisplayCompanyName() {
        if (!getCompanyNameZh().isEmpty()) {
            return getCompanyNameZh();
        }
        return getCompanyNameEn();
    }

    /**
     * 获取显示用的职位（优先中文，其次英文）
     */
    public String getDisplayPosition() {
        if (!getPositionZh().isEmpty()) {
            return getPositionZh();
        }
        if (!getPositionEn().isEmpty()) {
            return getPositionEn();
        }
        if (!getPosition1Zh().isEmpty()) {
            return getPosition1Zh();
        }
        return getPosition1En();
    }

    /**
     * 获取显示用的部门（优先中文，其次英文）
     */
    public String getDisplayDepartment() {
        if (!getDepartment1Zh().isEmpty()) {
            return getDepartment1Zh();
        }
        if (!getDepartment1En().isEmpty()) {
            return getDepartment1En();
        }
        if (!getDepartment2Zh().isEmpty()) {
            return getDepartment2Zh();
        }
        return getDepartment2En();
    }

    /**
     * 获取主要联系方式
     */
    public String getPrimaryContact() {
        if (!getMobilePhone().isEmpty()) {
            return getMobilePhone();
        }
        if (!getCompanyPhone1().isEmpty()) {
            return getCompanyPhone1();
        }
        if (!getEmail().isEmpty()) {
            return getEmail();
        }
        return getLineId();
    }

    /**
     * 检查名片健康状态
     */
    public boolean isHealthy() {
        // 姓名：中英文任一有值即可
        boolean hasName = !getNameZh().isEmpty() || !getNameEn().isEmpty();

        // 公司：中英文任一有值即可
        boolean hasCompany = !getCompanyNameZh().isEmpty() || !getCompanyNameEn().isEmpty();

        // 职位或部门：至少有一个有值
        boolean hasPositionOrDept = !getPositionZh().isEmpty() || !getPositionEn().isEmpty() ||
                                   !getPosition1Zh().isEmpty() || !getPosition1En().isEmpty() ||
                                   !getDepartment1Zh().isEmpty() || !getDepartment1En().isEmpty() ||
                                   !getDepartment2Zh().isEmpty() || !getDepartment2En().isEmpty() ||
                                   !getDepartment3Zh().isEmpty() || !getDepartment3En().isEmpty();

        // 联系方式：手机/电话/Email/Line ID至少一个有值
        boolean hasContact = !getMobilePhone().isEmpty() || !getCompanyPhone1().isEmpty() ||
                            !getCompanyPhone2().isEmpty() || !getEmail().isEmpty() || !getLineId().isEmpty();

        return hasName && hasCompany && hasPositionOrDept && hasContact;
    }
}