# -*- coding: utf-8 -*-
"""
文本導入服務
支持Excel和CSV文件的自動欄位識別和批量導入
"""

import pandas as pd
import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextImportService:
    """文本導入服務類"""
    
    def __init__(self):
        """初始化文本導入服務"""
        # 名片欄位映射表 - 將各種可能的欄位名稱映射到標準欄位
        self.field_mappings = {
            # 姓名相關 - 大幅擴展
            '姓名': ['姓名', 'name', '名字', '真實姓名', '聯絡人', '聯繫人', '人名', '名稱', '全名', 
                   '聯絡人姓名', '客戶姓名', '负责人', '責任人', '姓氏', '名', '先生', '小姐', '女士'],
            'name_en': ['name_en', 'english_name', 'eng_name', 'firstname', 'lastname', 'full_name',
                       'englishname', 'en_name', 'name_english', 'fullname'],
            
            # 公司相關 - 添加更多變體
            '公司名稱': ['公司名稱', 'company', '公司', '企業', '單位', 'organization', '機構', '公司名',
                      '企業名稱', '單位名稱', '組織', '工作單位', '服務單位', '所屬公司', '任職公司'],
            'company_name_en': ['company_name_en', 'company_en', 'company_english', 'org_en', 'organization_en'],
            
            # 職位相關 - 擴展職位描述
            '職位': ['職位', 'position', '職務', '崗位', 'title', 'job_title', 'role', '工作', '職稱',
                   '角色', '職業', '工作職位', '職務名稱', '工作崗位', '職責', '頭銜'],
            'position_en': ['position_en', 'position_english', 'title_en', 'jobtitle_en', 'role_en'],
            '職位1': ['職位1', 'position1', '主要職位', 'main_position', '第一職位', '主職'],
            'position1_en': ['position1_en', 'main_position_en', 'primary_position_en'],
            
            # 部門相關 - 添加組織結構變體  
            '部門1': ['部門1', 'department1', '部門', 'department', '科室', '組織', 'division', '所屬部門',
                    '一級部門', '主部門', '工作部門', '業務部門', '職能部門'],
            'department1_en': ['department1_en', 'department_en', 'dept_en', 'division_en'],
            '部門2': ['部門2', 'department2', '二級部門', 'sub_department', '子部門', '下屬部門'],
            'department2_en': ['department2_en', 'subdepartment_en'],
            '部門3': ['部門3', 'department3', '三級部門', '小組', '團隊', 'team', 'group'],
            'department3_en': ['department3_en', 'team_en', 'group_en'],
            
            # 聯絡方式 - 添加更多電話號碼變體
            '手機': ['手機', 'mobile', '手機號', '行動電話', 'cellphone', 'cell', '移動電話', '手機號碼',
                   '行動號碼', '個人電話', '私人電話', '手提電話', 'phone', '電話'],
            '公司電話1': ['公司電話1', 'office_phone', '辦公電話', '座機', 'tel', 'phone', '電話',
                        '辦公室電話', '工作電話', '公司電話', '辦公號碼', '總機', '分機'],
            '公司電話2': ['公司電話2', 'office_phone2', '辦公電話2', '副電話', 'phone2', '第二電話', '備用電話'],
            'email': ['email', 'e-mail', '郵箱', '電子郵件', '電郵', 'mail', '郵件地址', '電子信箱',
                     '電子郵箱', 'e_mail', 'emailaddress'],
            'line_id': ['line_id', 'line', 'lineid', 'line帳號', 'line號', 'line_account'],
            
            # 地址相關 - 擴展地址描述
            '公司地址一': ['公司地址一', 'address1', '地址1', '地址', 'address', '辦公地址', '工作地址',
                        '公司地址', '辦公室地址', '營業地址', '註冊地址', '總部地址'],
            'company_address1_en': ['company_address1_en', 'address1_en', 'address_en', 'office_address_en'],
            '公司地址二': ['公司地址二', 'address2', '地址2', '第二地址', '分公司地址', '其他地址'],
            'company_address2_en': ['company_address2_en', 'address2_en', 'second_address_en'],
            
            # 備註相關 - 添加更多備註變體
            'note1': ['note1', '備註1', '備註', 'note', 'memo', '說明', '註記', '補充說明', '額外信息',
                     '其他', '特殊說明', '重要備註'],
            'note2': ['note2', '備註2', '額外備註', 'memo2', '說明2', '補充備註', '其他備註']
        }
        
        # 支持的文件格式
        self.supported_formats = ['.xlsx', '.xls', '.csv']
    
    def log_message(self, message):
        """輸出信息到控制台"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [TextImport] {message}"
        print(log_entry)
        logger.info(message)
    
    def normalize_column_name(self, col_name: str) -> str:
        """標準化欄位名稱，移除特殊字符和空格"""
        if not col_name:
            return ""
        
        # 移除前後空格
        normalized = str(col_name).strip()
        
        # 移除常見的特殊字符和數字後綴
        normalized = re.sub(r'[_\-\s\(\)\[\]（）【】：:；;，,。.！!？?\d+]', '', normalized)
        
        # 轉換為小寫以便比較
        normalized = normalized.lower()
        
        return normalized
    
    def map_columns_to_fields(self, columns: List[str]) -> Dict[str, str]:
        """將文件欄位映射到標準名片欄位"""
        column_mapping = {}
        
        self.log_message(f"開始映射欄位，文件包含欄位: {columns}")
        
        for col in columns:
            if not col or pd.isna(col):
                continue
                
            original_col = str(col).strip()
            normalized_col = self.normalize_column_name(original_col)
            
            if not normalized_col:
                continue
            
            # 嘗試匹配每個標準欄位
            best_match = None
            best_match_field = None
            max_similarity = 0
            
            for standard_field, possible_names in self.field_mappings.items():
                for possible_name in possible_names:
                    normalized_possible = self.normalize_column_name(possible_name)
                    
                    # 精確匹配
                    if normalized_col == normalized_possible:
                        column_mapping[original_col] = standard_field
                        self.log_message(f"精確匹配: '{original_col}' -> '{standard_field}'")
                        best_match = standard_field
                        break
                    
                    # 包含匹配
                    elif (normalized_col in normalized_possible or 
                          normalized_possible in normalized_col):
                        similarity = min(len(normalized_col), len(normalized_possible)) / max(len(normalized_col), len(normalized_possible))
                        if similarity > max_similarity:
                            max_similarity = similarity
                            best_match = standard_field
                            best_match_field = possible_name
                
                if original_col in column_mapping:
                    break
            
            # 如果沒有精確匹配，使用最佳部分匹配
            if original_col not in column_mapping and best_match and max_similarity > 0.5:
                column_mapping[original_col] = best_match
                self.log_message(f"部分匹配: '{original_col}' -> '{best_match}' (通過 '{best_match_field}', 相似度: {max_similarity:.2f})")
        
        self.log_message(f"欄位映射完成，成功映射 {len(column_mapping)}/{len(columns)} 個欄位")
        return column_mapping
    
    def clean_cell_value(self, value) -> str:
        """清理單元格數值"""
        if pd.isna(value) or value is None:
            return ""
        
        # 轉換為字符串並移除前後空格
        cleaned = str(value).strip()
        
        # 移除常見的無效值
        invalid_values = ['nan', 'null', 'none', '#n/a', '#value!', '#ref!', 'na', '無', '沒有', '空', '']
        if cleaned.lower() in invalid_values:
            return ""
        
        return cleaned
    
    def validate_required_fields(self, mapped_data: Dict[str, str]) -> Tuple[bool, str]:
        """驗證必要欄位，返回是否有效和原因"""
        # 放寬驗證條件：只要有姓名或公司名稱之一即可
        name = mapped_data.get('姓名', '').strip()
        name_en = mapped_data.get('name_en', '').strip()
        company = mapped_data.get('公司名稱', '').strip()
        company_en = mapped_data.get('company_name_en', '').strip()
        
        has_name = bool(name or name_en)
        has_company = bool(company or company_en)
        
        if not has_name and not has_company:
            return False, "缺少必要欄位：姓名和公司名稱至少需要其中一個"
        
        return True, ""
    
    def read_file(self, file_path: str) -> pd.DataFrame:
        """讀取文件內容"""
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.csv':
                # 嘗試不同的編碼
                encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-8-sig']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        self.log_message(f"成功使用 {encoding} 編碼讀取CSV文件")
                        break
                    except (UnicodeDecodeError, UnicodeError):
                        continue
                
                if df is None:
                    raise ValueError("無法使用支持的編碼讀取CSV文件")
                    
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, engine='openpyxl' if file_extension == '.xlsx' else 'xlrd')
                self.log_message(f"成功讀取Excel文件")
            else:
                raise ValueError(f"不支持的文件格式: {file_extension}")
            
            self.log_message(f"文件讀取完成，共 {len(df)} 行，{len(df.columns)} 列")
            return df
            
        except Exception as e:
            self.log_message(f"讀取文件失敗: {str(e)}")
            raise
    
    def process_file(self, file_path: str) -> Tuple[List[Dict], Dict]:
        """處理文件並返回處理結果"""
        try:
            self.log_message(f"開始處理文件: {os.path.basename(file_path)}")
            
            # 讀取文件
            df = self.read_file(file_path)
            
            if df.empty:
                raise ValueError("文件內容為空")
            
            # 獲取欄位映射
            columns = df.columns.tolist()
            column_mapping = self.map_columns_to_fields(columns)
            
            if not column_mapping:
                raise ValueError("未能識別任何有效的名片欄位")
            
            # 處理數據
            processed_records = []
            error_records = []
            
            for index, row in df.iterrows():
                try:
                    # 映射數據到標準欄位
                    mapped_data = {}
                    for original_col, standard_field in column_mapping.items():
                        cell_value = self.clean_cell_value(row[original_col])
                        if cell_value:
                            mapped_data[standard_field] = cell_value
                    
                    # 驗證必要欄位
                    valid, reason = self.validate_required_fields(mapped_data)
                    if not valid:
                        error_records.append({
                            'row': index + 2,  # Excel行號從2開始（排除標題行）
                            'reason': reason
                        })
                        continue
                    
                    # 添加處理信息
                    mapped_data['note1'] = mapped_data.get('note1', '') + f" 文本導入 - 第{index + 2}行"
                    
                    processed_records.append(mapped_data)
                    
                except Exception as e:
                    error_records.append({
                        'row': index + 2,
                        'reason': f'處理錯誤: {str(e)}'
                    })
            
            # 處理結果統計
            result_stats = {
                'total_rows': len(df),
                'processed_count': len(processed_records),
                'error_count': len(error_records),
                'column_mapping': column_mapping,
                'error_details': error_records[:10]  # 只返回前10個錯誤
            }
            
            self.log_message(f"文件處理完成: 成功 {len(processed_records)} 條，錯誤 {len(error_records)} 條")
            
            return processed_records, result_stats
            
        except Exception as e:
            self.log_message(f"文件處理失敗: {str(e)}")
            raise
    
    def preview_file_structure(self, file_path: str, max_rows: int = 5) -> Dict:
        """預覽文件結構"""
        try:
            df = self.read_file(file_path)
            
            if df.empty:
                return {'error': '文件內容為空'}
            
            # 獲取前幾行數據作為預覽
            preview_data = df.head(max_rows).fillna('').to_dict('records')
            
            # 獲取欄位映射
            columns = df.columns.tolist()
            column_mapping = self.map_columns_to_fields(columns)
            
            return {
                'total_rows': len(df),
                'columns': columns,
                'column_mapping': column_mapping,
                'preview_data': preview_data,
                'mapped_fields': list(column_mapping.values()),
                'unmapped_columns': [col for col in columns if col not in column_mapping]
            }
            
        except Exception as e:
            return {'error': f'預覽失敗: {str(e)}'}