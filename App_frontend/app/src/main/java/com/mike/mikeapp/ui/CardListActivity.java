package com.mike.mikeapp.ui;

import android.content.Intent;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.mike.mikeapp.R;
import com.mike.mikeapp.adapter.CardListAdapter;
import com.mike.mikeapp.model.Card;
import com.mike.mikeapp.repository.CardRepository;

import java.util.ArrayList;
import java.util.List;

/**
 * 名片列表Activity - 完整功能版本
 */
public class CardListActivity extends AppCompatActivity implements CardListAdapter.OnCardClickListener {
    private RecyclerView recyclerView;
    private CardListAdapter adapter;
    private EditText etSearch;
    private TextView tvEmptyState;
    private CardRepository cardRepository;
    private List<Card> allCards = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_card_list);

        cardRepository = CardRepository.getInstance(this);
        initViews();
        loadCards();
    }

    private void initViews() {
        Button btnBack = findViewById(R.id.btnBack);
        TextView tvTitle = findViewById(R.id.tvTitle);
        etSearch = findViewById(R.id.etSearch);
        recyclerView = findViewById(R.id.recyclerViewCards);
        tvEmptyState = findViewById(R.id.tvEmptyState);

        if (tvTitle != null) {
            tvTitle.setText(R.string.card_list);
        }

        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        // 设置RecyclerView
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        adapter = new CardListAdapter(new ArrayList<>(), this);
        recyclerView.setAdapter(adapter);

        // 设置搜索功能
        if (etSearch != null) {
            etSearch.addTextChangedListener(new TextWatcher() {
                @Override
                public void beforeTextChanged(CharSequence s, int start, int count, int after) {}

                @Override
                public void onTextChanged(CharSequence s, int start, int before, int count) {
                    filterCards(s.toString());
                }

                @Override
                public void afterTextChanged(Editable s) {}
            });
        }
    }

    private void loadCards() {
        cardRepository.getAllCards(new CardRepository.DataCallback<List<Card>>() {
            @Override
            public void onSuccess(List<Card> cards) {
                allCards.clear();
                allCards.addAll(cards);
                adapter.updateCards(cards);
                updateEmptyState(cards.isEmpty());
            }

            @Override
            public void onError(String error) {
                Toast.makeText(CardListActivity.this, "加载名片失败: " + error, Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void filterCards(String query) {
        if (query.trim().isEmpty()) {
            adapter.updateCards(allCards);
            updateEmptyState(allCards.isEmpty());
            return;
        }

        List<Card> filteredCards = new ArrayList<>();
        String lowerQuery = query.toLowerCase();

        for (Card card : allCards) {
            if (cardMatchesQuery(card, lowerQuery)) {
                filteredCards.add(card);
            }
        }

        adapter.updateCards(filteredCards);
        updateEmptyState(filteredCards.isEmpty());
    }

    private boolean cardMatchesQuery(Card card, String query) {
        return (card.getNameZh() != null && card.getNameZh().toLowerCase().contains(query)) ||
                (card.getNameEn() != null && card.getNameEn().toLowerCase().contains(query)) ||
                (card.getCompanyNameZh() != null && card.getCompanyNameZh().toLowerCase().contains(query)) ||
                (card.getCompanyNameEn() != null && card.getCompanyNameEn().toLowerCase().contains(query)) ||
                (card.getPositionZh() != null && card.getPositionZh().toLowerCase().contains(query)) ||
                (card.getPositionEn() != null && card.getPositionEn().toLowerCase().contains(query)) ||
                (card.getMobilePhone() != null && card.getMobilePhone().toLowerCase().contains(query)) ||
                (card.getEmail() != null && card.getEmail().toLowerCase().contains(query));
    }

    private void updateEmptyState(boolean isEmpty) {
        if (tvEmptyState != null) {
            tvEmptyState.setVisibility(isEmpty ? View.VISIBLE : View.GONE);
        }
        recyclerView.setVisibility(isEmpty ? View.GONE : View.VISIBLE);
    }

    @Override
    public void onCardClick(Card card) {
        Intent intent = new Intent(this, CardDetailActivity.class);
        intent.putExtra("card_id", card.getId());
        startActivity(intent);
    }

    @Override
    protected void onResume() {
        super.onResume();
        // 重新加载数据以反映可能的更改
        loadCards();
    }
}