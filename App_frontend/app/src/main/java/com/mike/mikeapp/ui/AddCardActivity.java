package com.mike.mikeapp.ui;

import android.os.Bundle;
import android.text.TextUtils;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.google.android.material.textfield.TextInputEditText;
import com.mike.mikeapp.R;
import com.mike.mikeapp.model.Card;
import com.mike.mikeapp.repository.CardRepository;

/**
 * 新增/编辑名片Activity - 完整功能版本
 */
public class AddCardActivity extends AppCompatActivity {
    private TextInputEditText etNameZh, etNameEn, etCompanyZh, etPositionZh;
    private TextInputEditText etMobilePhone, etEmail;
    private Button btnSave;
    private TextView tvSave;
    private CardRepository cardRepository;
    private boolean isEditMode = false;
    private int cardId = -1;
    private Card currentCard;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_add_card);

        cardRepository = CardRepository.getInstance(this);

        // 检查是否为编辑模式
        isEditMode = getIntent().getBooleanExtra("edit_mode", false);
        cardId = getIntent().getIntExtra("card_id", -1);

        // 检查是否有OCR结果
        Card ocrResult = (Card) getIntent().getSerializableExtra("ocr_result");
        if (ocrResult != null) {
            currentCard = ocrResult;
            isEditMode = true; // OCR结果需要用户确认和编辑
        }

        initViews();

        if (isEditMode && cardId != -1) {
            loadCardForEdit();
        } else if (currentCard != null) {
            // 已经有OCR结果，直接填充表单
            populateForm(currentCard);
        }
    }

    private void initViews() {
        Button btnBack = findViewById(R.id.btnBack);
        TextView tvTitle = findViewById(R.id.tvTitle);
        tvSave = findViewById(R.id.tvSave);
        btnSave = findViewById(R.id.btnSave);

        // 表单输入框
        etNameZh = findViewById(R.id.etNameZh);
        etNameEn = findViewById(R.id.etNameEn);
        etCompanyZh = findViewById(R.id.etCompanyZh);
        etPositionZh = findViewById(R.id.etPositionZh);
        etMobilePhone = findViewById(R.id.etMobilePhone);
        etEmail = findViewById(R.id.etEmail);

        // 设置标题
        if (tvTitle != null) {
            tvTitle.setText(isEditMode ? R.string.edit_card : R.string.add_card);
        }

        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        // 设置保存按钮
        if (tvSave != null) {
            tvSave.setOnClickListener(v -> saveCard());
        }

        if (btnSave != null) {
            btnSave.setOnClickListener(v -> saveCard());
        }
    }

    private void loadCardForEdit() {
        cardRepository.getCardById(cardId, new CardRepository.DataCallback<Card>() {
            @Override
            public void onSuccess(Card card) {
                if (card != null) {
                    currentCard = card;
                    populateForm(card);
                } else {
                    Toast.makeText(AddCardActivity.this, "名片不存在", Toast.LENGTH_SHORT).show();
                    finish();
                }
            }

            @Override
            public void onError(String error) {
                Toast.makeText(AddCardActivity.this, "加载名片失败: " + error, Toast.LENGTH_SHORT).show();
                finish();
            }
        });
    }

    private void populateForm(Card card) {
        if (etNameZh != null && card.getNameZh() != null) {
            etNameZh.setText(card.getNameZh());
        }
        if (etNameEn != null && card.getNameEn() != null) {
            etNameEn.setText(card.getNameEn());
        }
        if (etCompanyZh != null && card.getCompanyNameZh() != null) {
            etCompanyZh.setText(card.getCompanyNameZh());
        }
        if (etPositionZh != null && card.getPositionZh() != null) {
            etPositionZh.setText(card.getPositionZh());
        }
        if (etMobilePhone != null && card.getMobilePhone() != null) {
            etMobilePhone.setText(card.getMobilePhone());
        }
        if (etEmail != null && card.getEmail() != null) {
            etEmail.setText(card.getEmail());
        }
    }

    private void saveCard() {
        // 获取表单数据
        String nameZh = getText(etNameZh);
        String nameEn = getText(etNameEn);
        String companyZh = getText(etCompanyZh);
        String positionZh = getText(etPositionZh);
        String mobilePhone = getText(etMobilePhone);
        String email = getText(etEmail);

        // 验证必填字段
        if (TextUtils.isEmpty(nameZh) && TextUtils.isEmpty(nameEn)) {
            Toast.makeText(this, "请输入姓名", Toast.LENGTH_SHORT).show();
            return;
        }

        if (TextUtils.isEmpty(companyZh)) {
            Toast.makeText(this, "请输入公司名称", Toast.LENGTH_SHORT).show();
            return;
        }

        // 创建或更新Card对象
        Card card;
        if (isEditMode && currentCard != null) {
            card = currentCard;
        } else {
            card = new Card();
        }

        // 设置基本信息
        card.setNameZh(nameZh);
        card.setNameEn(nameEn);
        card.setCompanyNameZh(companyZh);
        card.setPositionZh(positionZh);
        card.setMobilePhone(mobilePhone);
        card.setEmail(email);

        // 保存到数据库
        if (isEditMode) {
            updateCard(card);
        } else {
            createCard(card);
        }
    }

    private void createCard(Card card) {
        cardRepository.insertCard(card, new CardRepository.SimpleCallback() {
            @Override
            public void onSuccess() {
                Toast.makeText(AddCardActivity.this, "名片保存成功", Toast.LENGTH_SHORT).show();
                finish();
            }

            @Override
            public void onError(String error) {
                Toast.makeText(AddCardActivity.this, "保存失败: " + error, Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void updateCard(Card card) {
        cardRepository.updateCard(card, new CardRepository.SimpleCallback() {
            @Override
            public void onSuccess() {
                Toast.makeText(AddCardActivity.this, "名片更新成功", Toast.LENGTH_SHORT).show();
                finish();
            }

            @Override
            public void onError(String error) {
                Toast.makeText(AddCardActivity.this, "更新失败: " + error, Toast.LENGTH_SHORT).show();
            }
        });
    }

    private String getText(TextInputEditText editText) {
        if (editText != null && editText.getText() != null) {
            return editText.getText().toString().trim();
        }
        return "";
    }
}