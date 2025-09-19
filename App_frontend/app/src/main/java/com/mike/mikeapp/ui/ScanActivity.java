package com.mike.mikeapp.ui;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.camera.core.Camera;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.content.ContextCompat;

import com.google.common.util.concurrent.ListenableFuture;
import com.mike.mikeapp.R;
import com.mike.mikeapp.model.Card;
import com.mike.mikeapp.service.OcrService;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutionException;

/**
 * 扫描Activity - 完整功能版本
 * 包含相机功能、图片选择和OCR集成
 */
public class ScanActivity extends AppCompatActivity {
    private static final String TAG = "ScanActivity";
    private static final String[] CAMERA_PERMISSIONS_LEGACY = {
            Manifest.permission.CAMERA,
            Manifest.permission.WRITE_EXTERNAL_STORAGE
    };

    private static final String[] CAMERA_PERMISSIONS_MODERN = {
            Manifest.permission.CAMERA,
            Manifest.permission.READ_MEDIA_IMAGES
    };

    private Button btnBack, btnCapture, btnGallery, btnProcessOcr, btnRetake;
    private TextView tvTitle, tvInstructions;
    private PreviewView previewView;
    private ImageView ivPreview;
    private View layoutCameraControls, layoutPreviewControls;

    private ProcessCameraProvider cameraProvider;
    private ImageCapture imageCapture;
    private Camera camera;
    private OcrService ocrService;

    private Uri currentImageUri;
    private File currentImageFile;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_scan);

        ocrService = new OcrService();
        initViews();
        setupClickListeners();

        // 检查是否是上传模式
        String mode = getIntent().getStringExtra("mode");
        String imageUriString = getIntent().getStringExtra("image_uri");

        if ("upload".equals(mode) && imageUriString != null) {
            // 上传模式：直接处理传入的图片
            handleUploadedImage(android.net.Uri.parse(imageUriString));
        } else {
            // 扫描模式：启动相机
            if (checkCameraPermissions()) {
                startCamera();
            } else {
                requestCameraPermissions();
            }
        }
    }

    private void initViews() {
        try {
            tvTitle = findViewById(R.id.tvTitle);
            tvInstructions = findViewById(R.id.tvInstructions);
            btnBack = findViewById(R.id.btnBack);
            btnCapture = findViewById(R.id.btnCapture);
            btnGallery = findViewById(R.id.btnGallery);
            btnProcessOcr = findViewById(R.id.btnProcessOcr);
            btnRetake = findViewById(R.id.btnRetake);

            previewView = findViewById(R.id.previewView);
            ivPreview = findViewById(R.id.ivPreview);
            layoutCameraControls = findViewById(R.id.layoutCameraControls);
            layoutPreviewControls = findViewById(R.id.layoutPreviewControls);

            if (tvTitle != null) {
                tvTitle.setText(R.string.scan_title);
            }

            // 確保關鍵元件存在
            if (previewView == null) {
                Log.e(TAG, "Critical view previewView is null");
                Toast.makeText(this, "界面初始化失敗", Toast.LENGTH_SHORT).show();
                finish();
                return;
            }

            showCameraMode();
        } catch (Exception e) {
            Log.e(TAG, "Error in initViews", e);
            Toast.makeText(this, "界面初始化錯誤: " + e.getMessage(), Toast.LENGTH_SHORT).show();
            finish();
        }
    }

    private void setupClickListeners() {
        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        if (btnCapture != null) {
            btnCapture.setOnClickListener(v -> capturePhoto());
        }

        if (btnGallery != null) {
            btnGallery.setOnClickListener(v -> openGallery());
        }

        if (btnProcessOcr != null) {
            btnProcessOcr.setOnClickListener(v -> processOcr());
        }

        if (btnRetake != null) {
            btnRetake.setOnClickListener(v -> showCameraMode());
        }
    }

    private boolean checkCameraPermissions() {
        String[] permissions = getRequiredPermissions();
        for (String permission : permissions) {
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                return false;
            }
        }
        return true;
    }

    private String[] getRequiredPermissions() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            return CAMERA_PERMISSIONS_MODERN;
        } else {
            return CAMERA_PERMISSIONS_LEGACY;
        }
    }

    private void requestCameraPermissions() {
        cameraPermissionLauncher.launch(getRequiredPermissions());
    }

    private final ActivityResultLauncher<String[]> cameraPermissionLauncher =
            registerForActivityResult(new ActivityResultContracts.RequestMultiplePermissions(), result -> {
                boolean allGranted = true;
                for (Boolean granted : result.values()) {
                    if (!granted) {
                        allGranted = false;
                        break;
                    }
                }

                if (allGranted) {
                    startCamera();
                } else {
                    showPermissionDeniedDialog();
                }
            });

    private void startCamera() {
        ListenableFuture<ProcessCameraProvider> cameraProviderFuture =
                ProcessCameraProvider.getInstance(this);

        cameraProviderFuture.addListener(() -> {
            try {
                cameraProvider = cameraProviderFuture.get();
                bindCameraUseCases();
            } catch (ExecutionException | InterruptedException e) {
                Log.e(TAG, "Error starting camera", e);
                Toast.makeText(this, "启动相机失败", Toast.LENGTH_SHORT).show();
            }
        }, ContextCompat.getMainExecutor(this));
    }

    private void bindCameraUseCases() {
        if (cameraProvider == null) {
            Log.e(TAG, "Camera provider is null");
            return;
        }

        if (previewView == null) {
            Log.e(TAG, "PreviewView is null");
            Toast.makeText(this, "相機預覽初始化失敗", Toast.LENGTH_SHORT).show();
            return;
        }

        // 预览
        Preview preview = new Preview.Builder().build();
        preview.setSurfaceProvider(previewView.getSurfaceProvider());

        // 图像捕获
        imageCapture = new ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                .build();

        // 选择后置摄像头
        CameraSelector cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA;

        try {
            // 绑定生命周期
            cameraProvider.unbindAll();
            camera = cameraProvider.bindToLifecycle(
                    this, cameraSelector, preview, imageCapture);
        } catch (Exception e) {
            Log.e(TAG, "Error binding camera use cases", e);
            Toast.makeText(this, "相机绑定失败", Toast.LENGTH_SHORT).show();
        }
    }

    private void capturePhoto() {
        if (imageCapture == null) return;

        // 创建输出文件
        String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(new Date());
        String fileName = "business_card_" + timeStamp + ".jpg";
        currentImageFile = new File(getExternalFilesDir("photos"), fileName);

        ImageCapture.OutputFileOptions outputOptions = new ImageCapture.OutputFileOptions.Builder(currentImageFile).build();

        imageCapture.takePicture(
                outputOptions,
                ContextCompat.getMainExecutor(this),
                new ImageCapture.OnImageSavedCallback() {
                    @Override
                    public void onImageSaved(ImageCapture.OutputFileResults output) {
                        currentImageUri = Uri.fromFile(currentImageFile);
                        showPreviewMode();
                        loadImagePreview();
                        Toast.makeText(ScanActivity.this, "照片已保存", Toast.LENGTH_SHORT).show();
                    }

                    @Override
                    public void onError(ImageCaptureException exception) {
                        Log.e(TAG, "Photo capture failed", exception);
                        Toast.makeText(ScanActivity.this, "拍照失败", Toast.LENGTH_SHORT).show();
                    }
                }
        );
    }

    private final ActivityResultLauncher<Intent> galleryLauncher =
            registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result -> {
                if (result.getResultCode() == RESULT_OK && result.getData() != null) {
                    currentImageUri = result.getData().getData();
                    if (currentImageUri != null) {
                        showPreviewMode();
                        loadImagePreview();
                    }
                }
            });

    private void openGallery() {
        Intent intent = new Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI);
        galleryLauncher.launch(intent);
    }

    private void loadImagePreview() {
        if (currentImageUri != null && ivPreview != null) {
            try {
                Bitmap bitmap = MediaStore.Images.Media.getBitmap(getContentResolver(), currentImageUri);
                ivPreview.setImageBitmap(bitmap);
            } catch (IOException e) {
                Log.e(TAG, "Error loading image preview", e);
                Toast.makeText(this, "加载图片失败", Toast.LENGTH_SHORT).show();
            }
        }
    }

    private void processOcr() {
        if (currentImageUri == null) {
            Toast.makeText(this, "请先选择或拍摄一张名片", Toast.LENGTH_SHORT).show();
            return;
        }

        btnProcessOcr.setEnabled(false);
        btnProcessOcr.setText("处理中...");

        ocrService.processBusinessCard(this, currentImageUri, new OcrService.OcrCallback() {
            @Override
            public void onSuccess(Card card) {
                runOnUiThread(() -> {
                    btnProcessOcr.setEnabled(true);
                    btnProcessOcr.setText("开始识别");

                    // 跳转到编辑页面
                    Intent intent = new Intent(ScanActivity.this, AddCardActivity.class);
                    intent.putExtra("ocr_result", card);
                    intent.putExtra("edit_mode", true);
                    startActivity(intent);
                    finish();
                });
            }

            @Override
            public void onError(String error) {
                runOnUiThread(() -> {
                    btnProcessOcr.setEnabled(true);
                    btnProcessOcr.setText("开始识别");
                    Toast.makeText(ScanActivity.this, "OCR识别失败: " + error, Toast.LENGTH_LONG).show();
                });
            }
        });
    }

    private void showCameraMode() {
        if (previewView != null) previewView.setVisibility(View.VISIBLE);
        if (ivPreview != null) ivPreview.setVisibility(View.GONE);
        if (layoutCameraControls != null) layoutCameraControls.setVisibility(View.VISIBLE);
        if (layoutPreviewControls != null) layoutPreviewControls.setVisibility(View.GONE);
        if (tvInstructions != null) tvInstructions.setText("将名片放入框内，点击拍照");
    }

    private void showPreviewMode() {
        if (previewView != null) previewView.setVisibility(View.GONE);
        if (ivPreview != null) ivPreview.setVisibility(View.VISIBLE);
        if (layoutCameraControls != null) layoutCameraControls.setVisibility(View.GONE);
        if (layoutPreviewControls != null) layoutPreviewControls.setVisibility(View.VISIBLE);
        if (tvInstructions != null) tvInstructions.setText("确认图片清晰，点击开始识别");
    }

    /**
     * 处理上传的图片
     */
    private void handleUploadedImage(android.net.Uri imageUri) {
        try {
            // 隐藏相机预览，显示图片预览
            if (previewView != null) previewView.setVisibility(View.GONE);

            // 加载并显示上传的图片
            if (ivPreview != null) {
                ivPreview.setVisibility(View.VISIBLE);
                // 使用Glide加载图片
                com.bumptech.glide.Glide.with(this)
                        .load(imageUri)
                        .into(ivPreview);
            }

            // 保存图片URI以便后续处理
            currentImageUri = imageUri;

            // 切换到预览模式
            showPreviewMode();

            // 更新标题和说明
            if (tvTitle != null) tvTitle.setText("圖片上傳");
            if (tvInstructions != null) tvInstructions.setText("確認圖片清晰，點擊開始識別");

            Log.d(TAG, "Uploaded image loaded: " + imageUri.toString());

        } catch (Exception e) {
            Log.e(TAG, "Failed to load uploaded image", e);
            Toast.makeText(this, "載入圖片失敗", Toast.LENGTH_SHORT).show();
            finish();
        }
    }

    private void showPermissionDeniedDialog() {
        new androidx.appcompat.app.AlertDialog.Builder(this)
                .setTitle("需要相機權限")
                .setMessage("掃描名片功能需要相機權限才能正常使用。請在設定中手動開啟相機權限。\n\n設定路徑：設定 → 應用程式 → MikeApp → 權限 → 相機")
                .setPositiveButton("去設定", (dialog, which) -> {
                    // 引導用戶到應用設定頁面
                    android.content.Intent intent = new android.content.Intent(
                            android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                    android.net.Uri uri = android.net.Uri.fromParts("package", getPackageName(), null);
                    intent.setData(uri);
                    startActivity(intent);
                    finish();
                })
                .setNegativeButton("返回", (dialog, which) -> {
                    dialog.dismiss();
                    finish();
                })
                .setCancelable(false)
                .show();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (cameraProvider != null) {
            cameraProvider.unbindAll();
        }
    }
}