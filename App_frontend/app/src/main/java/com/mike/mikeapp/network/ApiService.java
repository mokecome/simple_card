package com.mike.mikeapp.network;

import com.mike.mikeapp.model.ApiResponse;
import com.mike.mikeapp.model.Card;
import com.mike.mikeapp.model.StatisticsData;

import java.util.List;

import okhttp3.MultipartBody;
import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.DELETE;
import retrofit2.http.GET;
import retrofit2.http.Multipart;
import retrofit2.http.POST;
import retrofit2.http.PUT;
import retrofit2.http.Part;
import retrofit2.http.Path;
import retrofit2.http.Query;

/**
 * API服务接口定义
 * 对应后端FastAPI的接口
 */
public interface ApiService {

    // 基础URL
    String BASE_URL = "http://127.0.0.1:8006/";

    // ==================== 名片管理接口 ====================

    /**
     * 获取名片列表
     * GET /api/v1/cards
     */
    @GET("api/v1/cards")
    Call<ApiResponse<List<Card>>> getCards(
            @Query("skip") int skip,
            @Query("limit") int limit,
            @Query("search") String search
    );

    /**
     * 根据ID获取名片详情
     * GET /api/v1/cards/{card_id}
     */
    @GET("api/v1/cards/{card_id}")
    Call<ApiResponse<Card>> getCard(@Path("card_id") int cardId);

    /**
     * 创建新名片
     * POST /api/v1/cards
     */
    @POST("api/v1/cards")
    Call<ApiResponse<Card>> createCard(@Body Card card);

    /**
     * 更新名片
     * PUT /api/v1/cards/{card_id}
     */
    @PUT("api/v1/cards/{card_id}")
    Call<ApiResponse<Card>> updateCard(@Path("card_id") int cardId, @Body Card card);

    /**
     * 删除名片
     * DELETE /api/v1/cards/{card_id}
     */
    @DELETE("api/v1/cards/{card_id}")
    Call<ApiResponse<String>> deleteCard(@Path("card_id") int cardId);

    /**
     * 获取名片统计信息
     * GET /api/v1/cards/statistics
     */
    @GET("api/v1/cards/statistics")
    Call<ApiResponse<StatisticsData>> getStatistics();

    // ==================== OCR接口 ====================

    /**
     * 图片OCR识别
     * POST /api/v1/ocr/image
     */
    @Multipart
    @POST("api/v1/ocr/image")
    Call<ApiResponse<Card>> ocrImage(@Part MultipartBody.Part image);

    /**
     * 单个图片OCR处理 (processOcr方法)
     * POST /api/v1/ocr/process
     */
    @Multipart
    @POST("api/v1/ocr/process")
    Call<ApiResponse<Card>> processOcr(@Part MultipartBody.Part image);

    /**
     * 批量图片OCR识别
     * POST /api/v1/ocr/batch-images
     */
    @Multipart
    @POST("api/v1/ocr/batch-images")
    Call<ApiResponse<List<Card>>> batchOcrImages(@Part List<MultipartBody.Part> images);

    /**
     * 批量OCR处理 (processBatchOcr方法)
     * POST /api/v1/ocr/batch
     */
    @Multipart
    @POST("api/v1/ocr/batch")
    Call<ApiResponse<Card[]>> processBatchOcr(@Part("images") okhttp3.RequestBody requestBody);

    // ==================== 健康检查接口 ====================

    /**
     * 健康检查
     * GET /health
     */
    @GET("health")
    Call<ApiResponse<String>> healthCheck();

    /**
     * 获取配置信息
     * GET /config
     */
    @GET("config")
    Call<ResponseBody> getConfig();
}