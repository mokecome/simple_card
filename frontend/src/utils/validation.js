/**
 * 前端輸入驗證工具
 */

// 驗證規則
export const ValidationRules = {
  // 必填驗證
  required: (value, fieldName = '此欄位') => {
    if (!value || (typeof value === 'string' && !value.trim())) {
      return `${fieldName}為必填項目`;
    }
    return null;
  },

  // 最小長度驗證
  minLength: (value, minLen, fieldName = '此欄位') => {
    if (value && value.length < minLen) {
      return `${fieldName}最少需要 ${minLen} 個字符`;
    }
    return null;
  },

  // 最大長度驗證
  maxLength: (value, maxLen, fieldName = '此欄位') => {
    if (value && value.length > maxLen) {
      return `${fieldName}不能超過 ${maxLen} 個字符`;
    }
    return null;
  },

  // 電子郵件驗證
  email: (value, fieldName = 'Email') => {
    if (!value) return null;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      return `${fieldName}格式不正確`;
    }
    return null;
  },

  // 手機號碼驗證（台灣格式）
  phone: (value, fieldName = '電話號碼') => {
    if (!value) return null;
    const phoneRegex = /^[\d\s\-\+\(\)]+$/;
    if (!phoneRegex.test(value)) {
      return `${fieldName}只能包含數字、空格、連字符和括號`;
    }
    return null;
  },

  // 只包含英文字母驗證
  englishOnly: (value, fieldName = '此欄位') => {
    if (!value) return null;
    const englishRegex = /^[A-Za-z\s\.\-\']+$/;
    if (!englishRegex.test(value)) {
      return `${fieldName}只能包含英文字母、空格、點號、連字符和撇號`;
    }
    return null;
  },

  // 中文字符驗證
  containsChinese: (value, fieldName = '此欄位') => {
    if (!value) return null;
    const chineseRegex = /[\u4e00-\u9fff]/;
    if (!chineseRegex.test(value)) {
      return `${fieldName}應包含中文字符`;
    }
    return null;
  }
};

// 單個欄位驗證器
export class FieldValidator {
  constructor(rules = []) {
    this.rules = rules;
  }

  validate(value, fieldName) {
    for (const rule of this.rules) {
      const error = rule(value, fieldName);
      if (error) {
        return error;
      }
    }
    return null;
  }
}

// 表單驗證器
export class FormValidator {
  constructor(schema = {}) {
    this.schema = schema;
  }

  validate(data) {
    const errors = {};
    let hasErrors = false;

    Object.keys(this.schema).forEach(fieldName => {
      const fieldConfig = this.schema[fieldName];
      const value = data[fieldName];
      
      const validator = new FieldValidator(fieldConfig.rules || []);
      const error = validator.validate(value, fieldConfig.label || fieldName);
      
      if (error) {
        errors[fieldName] = error;
        hasErrors = true;
      }
    });

    return {
      isValid: !hasErrors,
      errors
    };
  }
}

// 名片表單驗證架構
export const cardValidationSchema = {
  name: {
    label: '姓名',
    rules: [
      (value) => ValidationRules.maxLength(value, 100, '姓名')
    ]
  },
  name_en: {
    label: '英文姓名',
    rules: [
      (value) => ValidationRules.maxLength(value, 100, '英文姓名'),
      (value) => ValidationRules.englishOnly(value, '英文姓名')
    ]
  },
  company_name: {
    label: '公司名稱',
    rules: [
      (value) => ValidationRules.maxLength(value, 200, '公司名稱')
    ]
  },
  company_name_en: {
    label: '英文公司名稱',
    rules: [
      (value) => ValidationRules.maxLength(value, 200, '英文公司名稱'),
      (value) => ValidationRules.englishOnly(value, '英文公司名稱')
    ]
  },
  position: {
    label: '職位1',
    rules: [
      (value) => ValidationRules.maxLength(value, 100, '職位1')
    ]
  },
  position_en: {
    label: '職位1英文',
    rules: [
      (value) => ValidationRules.maxLength(value, 100, '職位1英文'),
      (value) => ValidationRules.englishOnly(value, '職位1英文')
    ]
  },
  position1: {
    label: '職位2',
    rules: [
      (value) => ValidationRules.maxLength(value, 100, '職位2')
    ]
  },
  position1_en: {
    label: '職位2英文',
    rules: [
      (value) => ValidationRules.maxLength(value, 100, '職位2英文'),
      (value) => ValidationRules.englishOnly(value, '職位2英文')
    ]
  },
  mobile_phone: {
    label: '手機號碼',
    rules: [
      (value) => ValidationRules.phone(value, '手機號碼'),
      (value) => ValidationRules.maxLength(value, 50, '手機號碼')
    ]
  },
  company_phone1: {
    label: '公司電話1',
    rules: [
      (value) => ValidationRules.phone(value, '公司電話1'),
      (value) => ValidationRules.maxLength(value, 50, '公司電話1')
    ]
  },
  company_phone2: {
    label: '公司電話2',
    rules: [
      (value) => ValidationRules.phone(value, '公司電話2'),
      (value) => ValidationRules.maxLength(value, 50, '公司電話2')
    ]
  },
  email: {
    label: 'Email',
    rules: [
      ValidationRules.email
    ]
  },
  line_id: {
    label: 'Line ID',
    rules: [
      (value) => ValidationRules.maxLength(value, 50, 'Line ID')
    ]
  },
  company_address1: {
    label: '公司地址一',
    rules: [
      (value) => ValidationRules.maxLength(value, 200, '公司地址一')
    ]
  },
  company_address1_en: {
    label: '公司地址一英文',
    rules: [
      (value) => ValidationRules.maxLength(value, 200, '公司地址一英文')
    ]
  },
  company_address2: {
    label: '公司地址二',
    rules: [
      (value) => ValidationRules.maxLength(value, 200, '公司地址二')
    ]
  },
  company_address2_en: {
    label: '公司地址二英文',
    rules: [
      (value) => ValidationRules.maxLength(value, 200, '公司地址二英文')
    ]
  },
  note1: {
    label: '備註1',
    rules: [
      (value) => ValidationRules.maxLength(value, 500, '備註1')
    ]
  },
  note2: {
    label: '備註2',
    rules: [
      (value) => ValidationRules.maxLength(value, 500, '備註2')
    ]
  }
};

// 快速驗證方法
export const validateCardData = (data) => {
  const validator = new FormValidator(cardValidationSchema);
  return validator.validate(data);
};

// 驗證單個欄位的快速方法
export const validateField = (fieldName, value) => {
  const fieldSchema = cardValidationSchema[fieldName];
  if (!fieldSchema) return null;
  
  const validator = new FieldValidator(fieldSchema.rules);
  return validator.validate(value, fieldSchema.label);
};