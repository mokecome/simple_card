/**
 * 圖片路徑轉換工具
 * 統一處理名片圖片路徑，轉換為可訪問的URL
 */

/**
 * 將後端返回的圖片路徑轉換為前端可訪問的URL
 * @param {string|null} imagePath - 後端返回的圖片路徑
 * @returns {string|null} 可訪問的圖片URL，如果路徑為空則返回null
 *
 * @example
 * getImageUrl('card_data/image.jpg')  // => '/static/card_data/image.jpg'
 * getImageUrl('output/card_images/front.jpg')  // => '/static/uploads/front.jpg'
 * getImageUrl(null)  // => null
 */
export const getImageUrl = (imagePath) => {
  if (!imagePath) return null;

  // 處理 card_data/ 路徑（舊數據）
  if (imagePath.startsWith('card_data/')) {
    return `/static/${imagePath}`;
  }

  // 處理 output/card_images/ 路徑（新上傳）
  if (imagePath.startsWith('output/card_images/')) {
    return `/static/uploads/${imagePath.replace('output/card_images/', '')}`;
  }

  // 其他路徑直接返回
  return imagePath;
};

/**
 * 獲取名片的正反面圖片URL
 * @param {Object} card - 名片對象
 * @returns {Object} 包含front和back圖片URL的對象
 *
 * @example
 * const { front, back } = getCardImages(card);
 */
export const getCardImages = (card) => {
  return {
    front: getImageUrl(card?.front_image_path),
    back: getImageUrl(card?.back_image_path)
  };
};
