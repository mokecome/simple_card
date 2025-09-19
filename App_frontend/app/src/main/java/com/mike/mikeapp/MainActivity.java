package com.mike.mikeapp;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.cardview.widget.CardView;
import androidx.core.content.ContextCompat;

import com.mike.mikeapp.model.ApiResponse;
import com.mike.mikeapp.model.StatisticsData;
import com.mike.mikeapp.network.ApiClient;
import com.mike.mikeapp.network.ApiService;
import com.mike.mikeapp.repository.CardRepository;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;
import com.mike.mikeapp.ui.AddCardActivity;
import com.mike.mikeapp.ui.CardListActivity;
import com.mike.mikeapp.ui.ScanActivity;

/**
 * 主界面Activity
 * 显示应用首页，包含功能入口和统计信息
 */
public class MainActivity extends AppCompatActivity {
    private static final String TAG = "MainActivity";

    // UI 组件
    private CardView cardScanCard;
    private CardView cardUploadCard;
    private CardView cardManagementCard;
    private CardView cardAddCard;
    private Button btnStartScan;
    private TextView tvTotalCards;
    private TextView tvNormalCards;
    private TextView tvProblemCards;

    // 数据仓库
    private CardRepository cardRepository;
    private ApiService apiService;

    // 权限请求启动器
    private ActivityResultLauncher<String[]> permissionLauncher;

    // 图片选择器启动器
    private ActivityResultLauncher<String> imagePickerLauncher;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        initViews();
        initData();
        initPermissions();
        initImagePicker();
        setupClickListeners();
        loadStatistics();
    }

    @Override
    protected void onResume() {
        super.onResume();
        // 每次回到主页面时刷新统计数据
        loadStatistics();
    }

    /**
     * 初始化视图组件
     */
    private void initViews() {
        cardScanCard = findViewById(R.id.cardScanCard);
        cardUploadCard = findViewById(R.id.cardUploadCard);
        cardManagementCard = findViewById(R.id.cardManagementCard);
        cardAddCard = findViewById(R.id.cardAddCard);
        btnStartScan = findViewById(R.id.btnStartScan);

        tvTotalCards = findViewById(R.id.tvTotalCards);
        tvNormalCards = findViewById(R.id.tvNormalCards);
        tvProblemCards = findViewById(R.id.tvProblemCards);
    }

    /**
     * 初始化数据仓库
     */
    private void initData() {
        cardRepository = CardRepository.getInstance(this);
        apiService = ApiClient.getInstance().getApiService();

        // 测试后端连接
        testBackendConnection();
    }

    /**
     * 初始化权限请求
     */
    private void initPermissions() {
        permissionLauncher = registerForActivityResult(
                new ActivityResultContracts.RequestMultiplePermissions(),
                result -> {
                    boolean cameraGranted = Boolean.TRUE.equals(result.get(Manifest.permission.CAMERA));
                    boolean storageGranted;

                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
                        storageGranted = Boolean.TRUE.equals(result.get(Manifest.permission.READ_MEDIA_IMAGES));
                    } else {
                        storageGranted = Boolean.TRUE.equals(result.get(Manifest.permission.READ_EXTERNAL_STORAGE));
                    }

                    if (cameraGranted && storageGranted) {
                        Toast.makeText(this, R.string.permission_granted, Toast.LENGTH_SHORT).show();
                        openScanActivity();
                    } else {
                        Toast.makeText(this, R.string.permission_denied, Toast.LENGTH_SHORT).show();
                        showPermissionExplanation();
                    }
                }
        );
    }

    /**
     * 设置点击监听器
     */
    private void setupClickListeners() {
        // 扫描名片
        cardScanCard.setOnClickListener(v -> checkPermissionsAndScan());

        // 上传图片
        cardUploadCard.setOnClickListener(v -> openImagePicker());

        // 名片管理
        cardManagementCard.setOnClickListener(v -> openCardListActivity());

        // 手动新增
        cardAddCard.setOnClickListener(v -> openAddCardActivity());

        // 开始扫描按钮
        btnStartScan.setOnClickListener(v -> checkPermissionsAndScan());
    }

    /**
     * 检查权限并扫描
     */
    private void checkPermissionsAndScan() {
        if (checkPermissions()) {
            openScanActivity();
        } else {
            requestPermissions();
        }
    }

    /**
     * 检查是否有必要的权限
     */
    private boolean checkPermissions() {
        boolean cameraPermission = ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED;

        boolean storagePermission;
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            // Android 13+ 使用新的媒体权限
            storagePermission = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_MEDIA_IMAGES)
                    == PackageManager.PERMISSION_GRANTED;
        } else {
            // Android 12 及以下使用传统存储权限
            storagePermission = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                    == PackageManager.PERMISSION_GRANTED;
        }

        return cameraPermission && storagePermission;
    }

    /**
     * 请求权限
     */
    private void requestPermissions() {
        String[] permissions;
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            // Android 13+ 请求新的权限
            permissions = new String[]{
                    Manifest.permission.CAMERA,
                    Manifest.permission.READ_MEDIA_IMAGES,
                    Manifest.permission.POST_NOTIFICATIONS
            };
        } else {
            // Android 12 及以下请求传统权限
            permissions = new String[]{
                    Manifest.permission.CAMERA,
                    Manifest.permission.READ_EXTERNAL_STORAGE,
                    Manifest.permission.WRITE_EXTERNAL_STORAGE
            };
        }
        permissionLauncher.launch(permissions);
    }

    /**
     * 显示权限说明对话框
     */
    private void showPermissionExplanation() {
        new AlertDialog.Builder(this)
                .setTitle(R.string.permission_camera_title)
                .setMessage("应用需要相机和存储权限来扫描和保存名片图片。请在设置中手动授予权限。")
                .setPositiveButton(R.string.confirm, (dialog, which) -> {
                    // 可以引导用户到设置页面
                    dialog.dismiss();
                })
                .setNegativeButton(R.string.cancel, (dialog, which) -> dialog.dismiss())
                .show();
    }

    /**
     * 打开扫描Activity
     */
    private void openScanActivity() {
        Intent intent = new Intent(this, ScanActivity.class);
        startActivity(intent);
    }

    /**
     * 打开名片列表Activity
     */
    private void openCardListActivity() {
        Intent intent = new Intent(this, CardListActivity.class);
        startActivity(intent);
    }

    /**
     * 打开新增名片Activity
     */
    private void openAddCardActivity() {
        Intent intent = new Intent(this, AddCardActivity.class);
        startActivity(intent);
    }

    /**
     * 加载统计数据
     */
    private void loadStatistics() {
        Log.d(TAG, "Loading statistics...");

        // 优先尝试从服务器获取统计数据，失败则使用本地数据
        cardRepository.fetchStatisticsFromServer(new CardRepository.RepositoryCallback<StatisticsData>() {
            @Override
            public void onSuccess(StatisticsData result) {
                runOnUiThread(() -> updateStatisticsUI(result));
            }

            @Override
            public void onError(String error) {
                Log.w(TAG, "Failed to fetch statistics from server: " + error);
                // 从本地数据库获取统计数据
                cardRepository.getLocalStatistics(new CardRepository.RepositoryCallback<StatisticsData>() {
                    @Override
                    public void onSuccess(StatisticsData result) {
                        runOnUiThread(() -> updateStatisticsUI(result));
                    }

                    @Override
                    public void onError(String error) {
                        Log.e(TAG, "Failed to get local statistics: " + error);
                        runOnUiThread(() -> {
                            // 显示默认统计数据
                            StatisticsData defaultStats = new StatisticsData();
                            updateStatisticsUI(defaultStats);
                        });
                    }
                });
            }
        });
    }

    /**
     * 更新统计数据UI
     */
    private void updateStatisticsUI(StatisticsData statistics) {
        tvTotalCards.setText(String.valueOf(statistics.getTotalCards()));
        tvNormalCards.setText(String.valueOf(statistics.getNormalCards()));
        tvProblemCards.setText(String.valueOf(statistics.getIncompleteCards()));

        Log.d(TAG, String.format("Updated statistics: Total=%d, Normal=%d, Incomplete=%d",
                statistics.getTotalCards(), statistics.getNormalCards(), statistics.getIncompleteCards()));
    }

    /**
     * 测试后端API连接
     */
    private void testBackendConnection() {
        apiService.healthCheck().enqueue(new Callback<ApiResponse<String>>() {
            @Override
            public void onResponse(Call<ApiResponse<String>> call, Response<ApiResponse<String>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    Log.d(TAG, "Backend connection successful: " + response.body().getMessage());
                } else {
                    Log.w(TAG, "Backend health check failed, using local data only");
                }
            }

            @Override
            public void onFailure(Call<ApiResponse<String>> call, Throwable t) {
                Log.w(TAG, "Backend connection failed, working offline: " + t.getMessage());
                // 离线模式，只使用本地数据
            }
        });
    }

    /**
     * 初始化图片选择器
     */
    private void initImagePicker() {
        imagePickerLauncher = registerForActivityResult(
                new ActivityResultContracts.GetContent(),
                uri -> {
                    if (uri != null) {
                        // 启动ScanActivity并传递图片URI
                        Intent intent = new Intent(this, ScanActivity.class);
                        intent.putExtra("image_uri", uri.toString());
                        intent.putExtra("mode", "upload");
                        startActivity(intent);
                    }
                }
        );
    }

    /**
     * 打开图片选择器
     */
    private void openImagePicker() {
        // 检查存储权限
        if (checkStoragePermissions()) {
            imagePickerLauncher.launch("image/*");
        } else {
            requestStoragePermissions();
        }
    }

    /**
     * 检查存储权限
     */
    private boolean checkStoragePermissions() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            return ContextCompat.checkSelfPermission(this, Manifest.permission.READ_MEDIA_IMAGES)
                    == PackageManager.PERMISSION_GRANTED;
        } else {
            return ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                    == PackageManager.PERMISSION_GRANTED;
        }
    }

    /**
     * 请求存储权限
     */
    private void requestStoragePermissions() {
        String[] permissions;
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            permissions = new String[]{Manifest.permission.READ_MEDIA_IMAGES};
        } else {
            permissions = new String[]{Manifest.permission.READ_EXTERNAL_STORAGE};
        }

        permissionLauncher.launch(permissions);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // 清理资源
        if (cardRepository != null) {
            cardRepository.cleanup();
        }
    }
}