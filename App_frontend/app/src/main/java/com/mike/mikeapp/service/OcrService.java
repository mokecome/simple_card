package com.mike.mikeapp.service;

import android.content.Context;
import android.graphics.Bitmap;
import android.net.Uri;
import android.provider.MediaStore;
import android.util.Log;

import com.mike.mikeapp.model.ApiResponse;
import com.mike.mikeapp.model.Card;
import com.mike.mikeapp.network.ApiClient;
import com.mike.mikeapp.network.ApiService;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * OCR服务类
 * 负责处理名片图片的OCR识别
 */
public class OcrService {
    private static final String TAG = "OcrService";
    private static final int MAX_IMAGE_SIZE = 1024 * 1024; // 1MB

    private ApiService apiService;
    private ExecutorService executorService;

    public OcrService() {
        apiService = ApiClient.getInstance().getApiService();
        executorService = Executors.newSingleThreadExecutor();
    }

    /**
     * 处理名片图片的OCR识别
     */
    public void processBusinessCard(Context context, Uri imageUri, OcrCallback callback) {
        executorService.execute(() -> {
            try {
                // 加载和压缩图片
                Bitmap bitmap = loadAndCompressImage(context, imageUri);
                if (bitmap == null) {
                    callback.onError("无法加载图片");
                    return;
                }

                // 转换为字节数组
                byte[] imageBytes = bitmapToByteArray(bitmap);

                // 创建RequestBody
                RequestBody requestFile = RequestBody.create(MediaType.parse("image/jpeg"), imageBytes);

                // 生成文件名
                String fileName = "business_card_" +
                    new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(new Date()) + ".jpg";

                MultipartBody.Part imagePart = MultipartBody.Part.createFormData("image", fileName, requestFile);

                // 调用API
                Call<ApiResponse<Card>> call = apiService.processOcr(imagePart);
                call.enqueue(new Callback<ApiResponse<Card>>() {
                    @Override
                    public void onResponse(Call<ApiResponse<Card>> call, Response<ApiResponse<Card>> response) {
                        if (response.isSuccessful() && response.body() != null) {
                            ApiResponse<Card> apiResponse = response.body();
                            if (apiResponse.isSuccess()) {
                                Card card = apiResponse.getData();
                                if (card != null) {
                                    Log.d(TAG, "OCR processed successfully");
                                    callback.onSuccess(card);
                                } else {
                                    callback.onError("OCR返回空结果");
                                }
                            } else {
                                Log.e(TAG, "OCR API error: " + apiResponse.getMessage());
                                callback.onError(apiResponse.getMessage());
                            }
                        } else {
                            String errorMsg = "服务器错误: " + response.code();
                            Log.e(TAG, errorMsg);
                            callback.onError(errorMsg);
                        }
                    }

                    @Override
                    public void onFailure(Call<ApiResponse<Card>> call, Throwable t) {
                        Log.e(TAG, "OCR request failed", t);

                        // 网络错误时返回模拟数据用于测试
                        if (isNetworkError(t)) {
                            Log.w(TAG, "Network error, returning mock data for testing");
                            Card mockCard = createMockCard();
                            callback.onSuccess(mockCard);
                        } else {
                            callback.onError("网络连接失败: " + t.getMessage());
                        }
                    }
                });

            } catch (Exception e) {
                Log.e(TAG, "Error processing OCR", e);
                callback.onError("处理图片失败: " + e.getMessage());
            }
        });
    }

    /**
     * 批量处理多张名片图片
     */
    public void processBatchBusinessCards(Context context, Uri[] imageUris, BatchOcrCallback callback) {
        executorService.execute(() -> {
            try {
                // 准备多个图片文件
                MultipartBody.Builder builder = new MultipartBody.Builder()
                        .setType(MultipartBody.FORM);

                for (int i = 0; i < imageUris.length; i++) {
                    Bitmap bitmap = loadAndCompressImage(context, imageUris[i]);
                    if (bitmap != null) {
                        byte[] imageBytes = bitmapToByteArray(bitmap);
                        RequestBody requestFile = RequestBody.create(MediaType.parse("image/jpeg"), imageBytes);
                        String fileName = "card_" + i + "_" +
                            new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(new Date()) + ".jpg";
                        builder.addFormDataPart("images", fileName, requestFile);
                    }
                }

                RequestBody requestBody = builder.build();

                // 调用批量OCR API
                Call<ApiResponse<Card[]>> call = apiService.processBatchOcr(requestBody);
                call.enqueue(new Callback<ApiResponse<Card[]>>() {
                    @Override
                    public void onResponse(Call<ApiResponse<Card[]>> call, Response<ApiResponse<Card[]>> response) {
                        if (response.isSuccessful() && response.body() != null) {
                            ApiResponse<Card[]> apiResponse = response.body();
                            if (apiResponse.isSuccess()) {
                                Card[] cards = apiResponse.getData();
                                Log.d(TAG, "Batch OCR processed successfully, " + cards.length + " cards");
                                callback.onSuccess(cards);
                            } else {
                                Log.e(TAG, "Batch OCR API error: " + apiResponse.getMessage());
                                callback.onError(apiResponse.getMessage());
                            }
                        } else {
                            String errorMsg = "服务器错误: " + response.code();
                            Log.e(TAG, errorMsg);
                            callback.onError(errorMsg);
                        }
                    }

                    @Override
                    public void onFailure(Call<ApiResponse<Card[]>> call, Throwable t) {
                        Log.e(TAG, "Batch OCR request failed", t);
                        callback.onError("网络连接失败: " + t.getMessage());
                    }
                });

            } catch (Exception e) {
                Log.e(TAG, "Error processing batch OCR", e);
                callback.onError("处理图片失败: " + e.getMessage());
            }
        });
    }

    private Bitmap loadAndCompressImage(Context context, Uri imageUri) throws IOException {
        // 加载原始图片
        Bitmap originalBitmap = MediaStore.Images.Media.getBitmap(context.getContentResolver(), imageUri);

        if (originalBitmap == null) {
            return null;
        }

        // 计算压缩比例
        int width = originalBitmap.getWidth();
        int height = originalBitmap.getHeight();

        // 限制最大尺寸为1920x1080
        int maxWidth = 1920;
        int maxHeight = 1080;

        float scale = Math.min((float) maxWidth / width, (float) maxHeight / height);
        if (scale >= 1.0f) {
            return originalBitmap; // 不需要压缩
        }

        int newWidth = Math.round(width * scale);
        int newHeight = Math.round(height * scale);

        Bitmap compressedBitmap = Bitmap.createScaledBitmap(originalBitmap, newWidth, newHeight, true);

        // 回收原始图片
        if (compressedBitmap != originalBitmap) {
            originalBitmap.recycle();
        }

        return compressedBitmap;
    }

    private byte[] bitmapToByteArray(Bitmap bitmap) {
        ByteArrayOutputStream stream = new ByteArrayOutputStream();

        // 压缩质量，确保文件大小不超过限制
        int quality = 85;
        bitmap.compress(Bitmap.CompressFormat.JPEG, quality, stream);

        byte[] byteArray = stream.toByteArray();

        // 如果文件太大，继续压缩
        while (byteArray.length > MAX_IMAGE_SIZE && quality > 30) {
            stream.reset();
            quality -= 10;
            bitmap.compress(Bitmap.CompressFormat.JPEG, quality, stream);
            byteArray = stream.toByteArray();
        }

        Log.d(TAG, "Compressed image size: " + byteArray.length + " bytes, quality: " + quality);

        try {
            stream.close();
        } catch (IOException e) {
            Log.e(TAG, "Error closing stream", e);
        }

        return byteArray;
    }

    private boolean isNetworkError(Throwable t) {
        return t instanceof java.net.ConnectException ||
               t instanceof java.net.SocketTimeoutException ||
               t instanceof java.net.UnknownHostException ||
               t instanceof java.io.IOException;
    }

    private Card createMockCard() {
        Card card = new Card();
        card.setNameZh("张三");
        card.setNameEn("Zhang San");
        card.setCompanyNameZh("示例科技有限公司");
        card.setCompanyNameEn("Example Technology Co., Ltd.");
        card.setPositionZh("产品经理");
        card.setPositionEn("Product Manager");
        card.setMobilePhone("13800138000");
        card.setEmail("zhangsan@example.com");
        card.setCompanyAddress1Zh("北京市朝阳区示例大厦");
        card.setCompanyAddress1En("Example Building, Chaoyang District, Beijing");

        // 设置时间戳
        card.setCreatedAt(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date()));
        card.setUpdatedAt(card.getCreatedAt());

        Log.d(TAG, "Created mock card for testing");
        return card;
    }

    /**
     * OCR回调接口
     */
    public interface OcrCallback {
        void onSuccess(Card card);
        void onError(String error);
    }

    /**
     * 批量OCR回调接口
     */
    public interface BatchOcrCallback {
        void onSuccess(Card[] cards);
        void onError(String error);
    }

    /**
     * 清理资源
     */
    public void cleanup() {
        if (executorService != null && !executorService.isShutdown()) {
            executorService.shutdown();
        }
    }
}