package com.mike.mikeapp.model;

import com.google.gson.annotations.SerializedName;

/**
 * 统计数据模型类
 */
public class StatisticsData {
    @SerializedName("total_cards")
    private int totalCards;

    @SerializedName("normal_cards")
    private int normalCards;

    @SerializedName("incomplete_cards")
    private int incompleteCards;

    @SerializedName("completion_rate")
    private double completionRate;

    public StatisticsData() {
    }

    public int getTotalCards() {
        return totalCards;
    }

    public void setTotalCards(int totalCards) {
        this.totalCards = totalCards;
    }

    public int getNormalCards() {
        return normalCards;
    }

    public void setNormalCards(int normalCards) {
        this.normalCards = normalCards;
    }

    public int getIncompleteCards() {
        return incompleteCards;
    }

    public void setIncompleteCards(int incompleteCards) {
        this.incompleteCards = incompleteCards;
    }

    public double getCompletionRate() {
        return completionRate;
    }

    public void setCompletionRate(double completionRate) {
        this.completionRate = completionRate;
    }
}