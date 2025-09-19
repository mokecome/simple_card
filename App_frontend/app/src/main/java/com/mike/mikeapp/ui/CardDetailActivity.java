package com.mike.mikeapp.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

import com.mike.mikeapp.R;
import com.mike.mikeapp.model.Card;
import com.mike.mikeapp.repository.CardRepository;

/**
 * 名片详情Activity - 完整功能版本
 */
public class CardDetailActivity extends AppCompatActivity {
    private TextView tvDisplayName, tvDisplayPosition, tvDisplayCompany;
    private TextView tvMobilePhone, tvEmail, tvCreatedAt, tvSource;
    private TextView tvEdit, btnDelete, btnShare, btnEdit;
    private CardRepository cardRepository;
    private Card currentCard;
    private int cardId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_card_detail);

        cardRepository = CardRepository.getInstance(this);
        cardId = getIntent().getIntExtra("card_id", -1);

        if (cardId == -1) {
            Toast.makeText(this, "名片ID无效", Toast.LENGTH_SHORT).show();
            finish();
            return;
        }

        initViews();
        loadCardDetails();
    }

    private void initViews() {
        Button btnBack = findViewById(R.id.btnBack);
        TextView tvTitle = findViewById(R.id.tvTitle);
        tvEdit = findViewById(R.id.tvEdit);

        // 显示信息的TextViews
        tvDisplayName = findViewById(R.id.tvDisplayName);
        tvDisplayPosition = findViewById(R.id.tvDisplayPosition);
        tvDisplayCompany = findViewById(R.id.tvDisplayCompany);
        tvMobilePhone = findViewById(R.id.tvMobilePhone);
        tvEmail = findViewById(R.id.tvEmail);
        tvCreatedAt = findViewById(R.id.tvCreatedAt);
        tvSource = findViewById(R.id.tvSource);

        // 底部按钮
        btnDelete = findViewById(R.id.btnDelete);
        btnShare = findViewById(R.id.btnShare);
        btnEdit = findViewById(R.id.btnEdit);

        if (tvTitle != null) {
            tvTitle.setText(R.string.card_detail);
        }

        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        // 设置编辑按钮
        if (tvEdit != null) {
            tvEdit.setOnClickListener(v -> editCard());
        }

        if (btnEdit != null) {
            btnEdit.setOnClickListener(v -> editCard());
        }

        // 设置删除按钮
        if (btnDelete != null) {
            btnDelete.setOnClickListener(v -> showDeleteConfirmDialog());
        }

        // 设置分享按钮
        if (btnShare != null) {
            btnShare.setOnClickListener(v -> shareCard());
        }
    }

    private void loadCardDetails() {
        cardRepository.getCardById(cardId, new CardRepository.DataCallback<Card>() {
            @Override
            public void onSuccess(Card card) {
                if (card != null) {
                    currentCard = card;
                    displayCardInfo(card);
                } else {
                    Toast.makeText(CardDetailActivity.this, "名片不存在", Toast.LENGTH_SHORT).show();
                    finish();
                }
            }

            @Override
            public void onError(String error) {
                Toast.makeText(CardDetailActivity.this, "加载名片详情失败: " + error, Toast.LENGTH_SHORT).show();
                finish();
            }
        });
    }

    private void displayCardInfo(Card card) {
        // 显示基本信息
        String displayName = card.getDisplayName();
        tvDisplayName.setText(displayName.isEmpty() ? "未知姓名" : displayName);

        String displayPosition = card.getDisplayPosition();
        tvDisplayPosition.setText(displayPosition.isEmpty() ? "未知职位" : displayPosition);

        String displayCompany = card.getDisplayCompanyName();
        tvDisplayCompany.setText(displayCompany.isEmpty() ? "未知公司" : displayCompany);

        // 显示联系信息
        tvMobilePhone.setText(card.getMobilePhone() != null && !card.getMobilePhone().isEmpty()
                ? card.getMobilePhone() : "-");
        tvEmail.setText(card.getEmail() != null && !card.getEmail().isEmpty()
                ? card.getEmail() : "-");

        // 显示其他信息
        tvCreatedAt.setText(card.getCreatedAt() != null ? card.getCreatedAt() : "-");
        tvSource.setText("OCR扫描");
    }

    private void editCard() {
        Intent intent = new Intent(this, AddCardActivity.class);
        intent.putExtra("card_id", cardId);
        intent.putExtra("edit_mode", true);
        startActivity(intent);
    }

    private void showDeleteConfirmDialog() {
        new AlertDialog.Builder(this)
                .setTitle("删除名片")
                .setMessage("确定要删除这张名片吗？删除后无法恢复。")
                .setPositiveButton("删除", (dialog, which) -> deleteCard())
                .setNegativeButton("取消", null)
                .show();
    }

    private void deleteCard() {
        cardRepository.deleteCard(cardId, new CardRepository.SimpleCallback() {
            @Override
            public void onSuccess() {
                Toast.makeText(CardDetailActivity.this, "名片已删除", Toast.LENGTH_SHORT).show();
                finish();
            }

            @Override
            public void onError(String error) {
                Toast.makeText(CardDetailActivity.this, "删除失败: " + error, Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void shareCard() {
        if (currentCard == null) return;

        StringBuilder shareText = new StringBuilder();
        shareText.append("名片信息\n");
        shareText.append("姓名: ").append(currentCard.getDisplayName()).append("\n");
        shareText.append("公司: ").append(currentCard.getDisplayCompanyName()).append("\n");
        shareText.append("职位: ").append(currentCard.getDisplayPosition()).append("\n");

        if (currentCard.getMobilePhone() != null && !currentCard.getMobilePhone().isEmpty()) {
            shareText.append("手机: ").append(currentCard.getMobilePhone()).append("\n");
        }

        if (currentCard.getEmail() != null && !currentCard.getEmail().isEmpty()) {
            shareText.append("邮箱: ").append(currentCard.getEmail()).append("\n");
        }

        Intent shareIntent = new Intent(Intent.ACTION_SEND);
        shareIntent.setType("text/plain");
        shareIntent.putExtra(Intent.EXTRA_TEXT, shareText.toString());
        shareIntent.putExtra(Intent.EXTRA_SUBJECT, "名片分享");

        startActivity(Intent.createChooser(shareIntent, "分享名片"));
    }

    @Override
    protected void onResume() {
        super.onResume();
        // 从编辑页面返回时重新加载数据
        if (cardId != -1) {
            loadCardDetails();
        }
    }
}