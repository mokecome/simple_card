package com.mike.mikeapp.network;

import android.util.Log;

import java.util.concurrent.TimeUnit;

import okhttp3.Interceptor;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

/**
 * 网络客户端管理类
 * 单例模式管理Retrofit实例
 */
public class ApiClient {
    private static final String TAG = "ApiClient";
    private static ApiClient instance;
    private Retrofit retrofit;
    private ApiService apiService;

    private ApiClient() {
        initRetrofit();
    }

    public static synchronized ApiClient getInstance() {
        if (instance == null) {
            instance = new ApiClient();
        }
        return instance;
    }

    private void initRetrofit() {
        // 创建日志拦截器
        HttpLoggingInterceptor loggingInterceptor = new HttpLoggingInterceptor(new HttpLoggingInterceptor.Logger() {
            @Override
            public void log(String message) {
                Log.d(TAG, "HTTP: " + message);
            }
        });
        loggingInterceptor.setLevel(HttpLoggingInterceptor.Level.BODY);

        // 创建通用拦截器
        Interceptor commonInterceptor = chain -> {
            Request originalRequest = chain.request();
            Request.Builder requestBuilder = originalRequest.newBuilder()
                    .addHeader("Content-Type", "application/json")
                    .addHeader("Accept", "application/json")
                    .addHeader("User-Agent", "CardOCR-Android/1.0");

            Request request = requestBuilder.build();

            try {
                Response response = chain.proceed(request);
                Log.d(TAG, "Request: " + request.method() + " " + request.url());
                Log.d(TAG, "Response: " + response.code() + " " + response.message());
                return response;
            } catch (Exception e) {
                Log.e(TAG, "Network request failed: " + e.getMessage(), e);
                throw e;
            }
        };

        // 创建OkHttpClient
        OkHttpClient okHttpClient = new OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .addInterceptor(commonInterceptor)
                .addInterceptor(loggingInterceptor)
                .build();

        // 创建Retrofit实例
        retrofit = new Retrofit.Builder()
                .baseUrl(ApiService.BASE_URL)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build();

        // 创建API服务
        apiService = retrofit.create(ApiService.class);

        Log.d(TAG, "ApiClient initialized with base URL: " + ApiService.BASE_URL);
    }

    /**
     * 获取API服务实例
     */
    public ApiService getApiService() {
        return apiService;
    }

    /**
     * 获取Retrofit实例
     */
    public Retrofit getRetrofit() {
        return retrofit;
    }

    /**
     * 检查网络连接状态
     */
    public boolean isNetworkAvailable() {
        // 简单的网络检查，可以根据需要扩展
        try {
            Runtime runtime = Runtime.getRuntime();
            Process proc = runtime.exec("/system/bin/ping -c 1 127.0.0.1");
            int exitValue = proc.waitFor();
            return exitValue == 0;
        } catch (Exception e) {
            Log.w(TAG, "Network check failed: " + e.getMessage());
            return false;
        }
    }

    /**
     * 重新初始化网络客户端
     */
    public void reinitialize() {
        Log.d(TAG, "Reinitializing ApiClient");
        initRetrofit();
    }
}