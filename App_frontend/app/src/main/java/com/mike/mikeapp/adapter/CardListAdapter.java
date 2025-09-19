package com.mike.mikeapp.adapter;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.mike.mikeapp.R;
import com.mike.mikeapp.model.Card;

import java.util.List;

/**
 * 名片列表适配器
 */
public class CardListAdapter extends RecyclerView.Adapter<CardListAdapter.CardViewHolder> {
    private List<Card> cards;
    private OnCardClickListener listener;

    public interface OnCardClickListener {
        void onCardClick(Card card);
    }

    public CardListAdapter(List<Card> cards, OnCardClickListener listener) {
        this.cards = cards;
        this.listener = listener;
    }

    @NonNull
    @Override
    public CardViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_card, parent, false);
        return new CardViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull CardViewHolder holder, int position) {
        Card card = cards.get(position);
        holder.bind(card, listener);
    }

    @Override
    public int getItemCount() {
        return cards.size();
    }

    public void updateCards(List<Card> newCards) {
        this.cards.clear();
        this.cards.addAll(newCards);
        notifyDataSetChanged();
    }

    static class CardViewHolder extends RecyclerView.ViewHolder {
        private TextView tvName;
        private TextView tvCompany;
        private TextView tvPosition;
        private TextView tvPhone;
        private TextView tvEmail;
        private TextView tvHealthStatus;

        public CardViewHolder(@NonNull View itemView) {
            super(itemView);
            tvName = itemView.findViewById(R.id.tvName);
            tvCompany = itemView.findViewById(R.id.tvCompany);
            tvPosition = itemView.findViewById(R.id.tvPosition);
            tvPhone = itemView.findViewById(R.id.tvPhone);
            tvEmail = itemView.findViewById(R.id.tvEmail);
            tvHealthStatus = itemView.findViewById(R.id.tvHealthStatus);
        }

        public void bind(Card card, OnCardClickListener listener) {
            // 设置姓名（优先显示中文）
            String displayName = card.getDisplayName();
            tvName.setText(displayName.isEmpty() ? "未知姓名" : displayName);

            // 设置公司（优先显示中文）
            String displayCompany = card.getDisplayCompanyName();
            tvCompany.setText(displayCompany.isEmpty() ? "未知公司" : displayCompany);

            // 设置职位（优先显示中文）
            String displayPosition = card.getDisplayPosition();
            tvPosition.setText(displayPosition.isEmpty() ? "未知职位" : displayPosition);

            // 设置联系信息
            tvPhone.setText(card.getMobilePhone() != null && !card.getMobilePhone().isEmpty()
                    ? card.getMobilePhone() : "无手机号");
            tvEmail.setText(card.getEmail() != null && !card.getEmail().isEmpty()
                    ? card.getEmail() : "无邮箱");

            // 设置健康状态
            String healthStatus = card.getHealthStatus();
            tvHealthStatus.setText(healthStatus);

            // 根据健康状态设置颜色
            int colorRes;
            switch (healthStatus) {
                case "完整":
                    colorRes = R.color.status_complete;
                    break;
                case "良好":
                    colorRes = R.color.status_good;
                    break;
                case "一般":
                    colorRes = R.color.status_fair;
                    break;
                case "不完整":
                    colorRes = R.color.status_incomplete;
                    break;
                default:
                    colorRes = R.color.status_incomplete;
                    break;
            }
            tvHealthStatus.setTextColor(itemView.getContext().getColor(colorRes));

            // 设置点击监听
            itemView.setOnClickListener(v -> {
                if (listener != null) {
                    listener.onCardClick(card);
                }
            });
        }
    }
}