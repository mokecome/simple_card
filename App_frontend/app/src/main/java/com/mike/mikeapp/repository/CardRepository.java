package com.mike.mikeapp.repository;

import android.content.Context;
import android.util.Log;

import com.mike.mikeapp.database.CardDao;
import com.mike.mikeapp.database.CardDatabase;
import com.mike.mikeapp.model.ApiResponse;
import com.mike.mikeapp.model.Card;
import com.mike.mikeapp.model.StatisticsData;
import com.mike.mikeapp.network.ApiClient;
import com.mike.mikeapp.network.ApiService;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import retrofit2.Call;
import retrofit2.Response;

/**
 * 名片数据仓库
 * 负责协调本地数据库和远程API数据
 */
public class CardRepository {
    private static final String TAG = "CardRepository";
    private static CardRepository instance;

    private CardDao cardDao;
    private ApiService apiService;
    private ExecutorService executorService;
    private Context context;

    private CardRepository(Context context) {
        this.context = context.getApplicationContext();
        CardDatabase database = CardDatabase.getInstance(this.context);
        cardDao = database.cardDao();
        apiService = ApiClient.getInstance().getApiService();
        executorService = Executors.newFixedThreadPool(4);
    }

    public static synchronized CardRepository getInstance(Context context) {
        if (instance == null) {
            instance = new CardRepository(context);
        }
        return instance;
    }

    // ==================== 本地数据库操作 ====================

    /**
     * 插入名片到本地数据库
     */
    public void insertCard(Card card, RepositoryCallback<Long> callback) {
        executorService.execute(() -> {
            try {
                // 更新健康状态
                card.setHealthStatus(card.isHealthy() ? "normal" : "incomplete");
                long id = cardDao.insert(card);
                Log.d(TAG, "Card inserted with ID: " + id);
                if (callback != null) {
                    callback.onSuccess(id);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error inserting card", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    /**
     * 插入名片到本地数据库 (SimpleCallback版本)
     */
    public void insertCard(Card card, SimpleCallback callback) {
        insertCard(card, new RepositoryCallback<Long>() {
            @Override
            public void onSuccess(Long result) {
                if (callback != null) callback.onSuccess();
            }

            @Override
            public void onError(String error) {
                if (callback != null) callback.onError(error);
            }
        });
    }

    /**
     * 更新名片
     */
    public void updateCard(Card card, RepositoryCallback<Integer> callback) {
        executorService.execute(() -> {
            try {
                // 更新健康状态
                card.setHealthStatus(card.isHealthy() ? "normal" : "incomplete");
                int rows = cardDao.update(card);
                Log.d(TAG, "Card updated, rows affected: " + rows);
                if (callback != null) {
                    callback.onSuccess(rows);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error updating card", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    /**
     * 更新名片 (SimpleCallback版本)
     */
    public void updateCard(Card card, SimpleCallback callback) {
        updateCard(card, new RepositoryCallback<Integer>() {
            @Override
            public void onSuccess(Integer result) {
                if (callback != null) callback.onSuccess();
            }

            @Override
            public void onError(String error) {
                if (callback != null) callback.onError(error);
            }
        });
    }

    /**
     * 删除名片
     */
    public void deleteCard(int cardId, RepositoryCallback<Integer> callback) {
        executorService.execute(() -> {
            try {
                int rows = cardDao.deleteById(cardId);
                Log.d(TAG, "Card deleted, rows affected: " + rows);
                if (callback != null) {
                    callback.onSuccess(rows);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error deleting card", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    /**
     * 删除名片 (SimpleCallback版本)
     */
    public void deleteCard(int cardId, SimpleCallback callback) {
        deleteCard(cardId, new RepositoryCallback<Integer>() {
            @Override
            public void onSuccess(Integer result) {
                if (callback != null) callback.onSuccess();
            }

            @Override
            public void onError(String error) {
                if (callback != null) callback.onError(error);
            }
        });
    }

    /**
     * 根据ID获取名片
     */
    public void getCardById(int cardId, RepositoryCallback<Card> callback) {
        executorService.execute(() -> {
            try {
                Card card = cardDao.getCardById(cardId);
                if (callback != null) {
                    callback.onSuccess(card);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error getting card by ID", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    /**
     * 根据ID获取名片 (DataCallback版本)
     */
    public void getCardById(int cardId, DataCallback<Card> callback) {
        getCardById(cardId, new RepositoryCallback<Card>() {
            @Override
            public void onSuccess(Card result) {
                if (callback != null) callback.onSuccess(result);
            }

            @Override
            public void onError(String error) {
                if (callback != null) callback.onError(error);
            }
        });
    }

    /**
     * 获取所有名片
     */
    public void getAllCards(RepositoryCallback<List<Card>> callback) {
        executorService.execute(() -> {
            try {
                List<Card> cards = cardDao.getAllCards();
                Log.d(TAG, "Retrieved " + cards.size() + " cards from local database");
                if (callback != null) {
                    callback.onSuccess(cards);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error getting all cards", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    /**
     * 获取所有名片 (DataCallback版本)
     */
    public void getAllCards(DataCallback<List<Card>> callback) {
        getAllCards(new RepositoryCallback<List<Card>>() {
            @Override
            public void onSuccess(List<Card> result) {
                if (callback != null) callback.onSuccess(result);
            }

            @Override
            public void onError(String error) {
                if (callback != null) callback.onError(error);
            }
        });
    }

    /**
     * 搜索名片
     */
    public void searchCards(String query, RepositoryCallback<List<Card>> callback) {
        executorService.execute(() -> {
            try {
                List<Card> cards = cardDao.searchCards(query);
                Log.d(TAG, "Search found " + cards.size() + " cards for query: " + query);
                if (callback != null) {
                    callback.onSuccess(cards);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error searching cards", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    /**
     * 获取本地统计数据
     */
    public void getLocalStatistics(RepositoryCallback<StatisticsData> callback) {
        executorService.execute(() -> {
            try {
                int totalCards = cardDao.getTotalCount();
                int normalCards = cardDao.getNormalCardsCount();
                int incompleteCards = cardDao.getIncompleteCardsCount();

                StatisticsData statistics = new StatisticsData();
                statistics.setTotalCards(totalCards);
                statistics.setNormalCards(normalCards);
                statistics.setIncompleteCards(incompleteCards);

                if (totalCards > 0) {
                    double completionRate = (double) normalCards / totalCards * 100;
                    statistics.setCompletionRate(completionRate);
                } else {
                    statistics.setCompletionRate(0.0);
                }

                Log.d(TAG, "Local statistics: Total=" + totalCards + ", Normal=" + normalCards + ", Incomplete=" + incompleteCards);
                if (callback != null) {
                    callback.onSuccess(statistics);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error getting local statistics", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    // ==================== 网络API操作 ====================

    /**
     * 同步名片到服务器
     */
    public void syncCardToServer(Card card, RepositoryCallback<Card> callback) {
        executorService.execute(() -> {
            try {
                Call<ApiResponse<Card>> call;
                if (card.getId() > 0) {
                    // 更新现有名片
                    call = apiService.updateCard(card.getId(), card);
                } else {
                    // 创建新名片
                    call = apiService.createCard(card);
                }

                Response<ApiResponse<Card>> response = call.execute();
                if (response.isSuccessful() && response.body() != null) {
                    ApiResponse<Card> apiResponse = response.body();
                    if (apiResponse.isSuccess()) {
                        Card serverCard = apiResponse.getData();
                        Log.d(TAG, "Card synced to server successfully");
                        if (callback != null) {
                            callback.onSuccess(serverCard);
                        }
                    } else {
                        Log.e(TAG, "Server returned error: " + apiResponse.getMessage());
                        if (callback != null) {
                            callback.onError(apiResponse.getMessage());
                        }
                    }
                } else {
                    String errorMsg = "Server error: " + response.code();
                    Log.e(TAG, errorMsg);
                    if (callback != null) {
                        callback.onError(errorMsg);
                    }
                }
            } catch (IOException e) {
                Log.w(TAG, "Network error, working offline: " + e.getMessage());
                // 网络错误时仍然保存到本地
                if (callback != null) {
                    callback.onSuccess(card);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error syncing card to server", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    /**
     * 从服务器获取名片列表
     */
    public void fetchCardsFromServer(int skip, int limit, String search, RepositoryCallback<List<Card>> callback) {
        executorService.execute(() -> {
            try {
                Call<ApiResponse<List<Card>>> call = apiService.getCards(skip, limit, search);
                Response<ApiResponse<List<Card>>> response = call.execute();

                if (response.isSuccessful() && response.body() != null) {
                    ApiResponse<List<Card>> apiResponse = response.body();
                    if (apiResponse.isSuccess()) {
                        List<Card> serverCards = apiResponse.getData();
                        Log.d(TAG, "Fetched " + serverCards.size() + " cards from server");

                        // 保存到本地数据库
                        if (!serverCards.isEmpty()) {
                            cardDao.insertAll(serverCards);
                            Log.d(TAG, "Saved server cards to local database");
                        }

                        if (callback != null) {
                            callback.onSuccess(serverCards);
                        }
                    } else {
                        Log.e(TAG, "Server returned error: " + apiResponse.getMessage());
                        if (callback != null) {
                            callback.onError(apiResponse.getMessage());
                        }
                    }
                } else {
                    String errorMsg = "Server error: " + response.code();
                    Log.e(TAG, errorMsg);
                    if (callback != null) {
                        callback.onError(errorMsg);
                    }
                }
            } catch (IOException e) {
                Log.w(TAG, "Network error, falling back to local data: " + e.getMessage());
                // 网络错误时返回本地数据
                getAllCards(callback);
            } catch (Exception e) {
                Log.e(TAG, "Error fetching cards from server", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    /**
     * 从服务器获取统计数据
     */
    public void fetchStatisticsFromServer(RepositoryCallback<StatisticsData> callback) {
        executorService.execute(() -> {
            try {
                Call<ApiResponse<StatisticsData>> call = apiService.getStatistics();
                Response<ApiResponse<StatisticsData>> response = call.execute();

                if (response.isSuccessful() && response.body() != null) {
                    ApiResponse<StatisticsData> apiResponse = response.body();
                    if (apiResponse.isSuccess()) {
                        StatisticsData statistics = apiResponse.getData();
                        Log.d(TAG, "Fetched statistics from server");
                        if (callback != null) {
                            callback.onSuccess(statistics);
                        }
                    } else {
                        Log.e(TAG, "Server returned error: " + apiResponse.getMessage());
                        if (callback != null) {
                            callback.onError(apiResponse.getMessage());
                        }
                    }
                } else {
                    String errorMsg = "Server error: " + response.code();
                    Log.e(TAG, errorMsg);
                    if (callback != null) {
                        callback.onError(errorMsg);
                    }
                }
            } catch (IOException e) {
                Log.w(TAG, "Network error, falling back to local statistics: " + e.getMessage());
                // 网络错误时返回本地统计数据
                getLocalStatistics(callback);
            } catch (Exception e) {
                Log.e(TAG, "Error fetching statistics from server", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    /**
     * 删除服务器上的名片
     */
    public void deleteCardFromServer(int cardId, RepositoryCallback<String> callback) {
        executorService.execute(() -> {
            try {
                Call<ApiResponse<String>> call = apiService.deleteCard(cardId);
                Response<ApiResponse<String>> response = call.execute();

                if (response.isSuccessful() && response.body() != null) {
                    ApiResponse<String> apiResponse = response.body();
                    if (apiResponse.isSuccess()) {
                        Log.d(TAG, "Card deleted from server");
                        if (callback != null) {
                            callback.onSuccess(apiResponse.getMessage());
                        }
                    } else {
                        Log.e(TAG, "Server returned error: " + apiResponse.getMessage());
                        if (callback != null) {
                            callback.onError(apiResponse.getMessage());
                        }
                    }
                } else {
                    String errorMsg = "Server error: " + response.code();
                    Log.e(TAG, errorMsg);
                    if (callback != null) {
                        callback.onError(errorMsg);
                    }
                }
            } catch (IOException e) {
                Log.w(TAG, "Network error during delete: " + e.getMessage());
                if (callback != null) {
                    callback.onSuccess("Deleted locally (offline mode)");
                }
            } catch (Exception e) {
                Log.e(TAG, "Error deleting card from server", e);
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }
        });
    }

    // ==================== 回调接口 ====================

    public interface RepositoryCallback<T> {
        void onSuccess(T result);
        void onError(String error);
    }

    public interface DataCallback<T> {
        void onSuccess(T result);
        void onError(String error);
    }

    public interface SimpleCallback {
        void onSuccess();
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