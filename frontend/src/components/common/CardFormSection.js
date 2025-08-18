import React from 'react';
import { Divider } from 'antd-mobile';
import FormField from './FormField';

/**
 * 名片表單區段組件
 * @param {Object} props
 * @param {string} props.title - 區段標題
 * @param {Array} props.fields - 欄位配置數組
 * @param {Object} props.data - 表單數據
 * @param {function} props.onChange - 數據變更回調
 * @param {boolean} props.disabled - 是否禁用
 */
const CardFormSection = ({ 
  title, 
  fields = [], 
  data = {}, 
  onChange, 
  disabled = false 
}) => {
  const handleFieldChange = (fieldName, value) => {
    if (onChange) {
      onChange(fieldName, value);
    }
  };

  const renderField = (field) => {
    const {
      name,
      label,
      placeholder,
      required = false,
      type = 'input',
      rows = 3,
      maxLength,
      span = 1 // 1: 全寬, 2: 半寬
    } = field;

    return (
      <div 
        key={name}
        style={{ 
          gridColumn: span === 2 ? 'span 1' : 'span 2'
        }}
      >
        <FormField
          label={label}
          value={data[name]}
          onChange={(value) => handleFieldChange(name, value)}
          placeholder={placeholder}
          required={required}
          type={type}
          rows={rows}
          maxLength={maxLength}
          disabled={disabled}
        />
      </div>
    );
  };

  return (
    <div className="form-section">
      <Divider>{title}</Divider>
      
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr', 
        gap: '12px' 
      }}>
        {fields.map(renderField)}
      </div>
    </div>
  );
};

// 預定義的欄位配置
export const BASIC_INFO_FIELDS = [
  {
    name: 'name',
    label: '姓名',
    placeholder: '請輸入中文姓名',
    required: true,
    span: 2
  },
  {
    name: 'name_en',
    label: 'name_en',
    placeholder: 'English Name',
    span: 2
  },
  {
    name: 'company_name',
    label: '公司名稱',
    placeholder: '請輸入公司名稱',
    span: 2
  },
  {
    name: 'company_name_en',
    label: 'company_name_en',
    placeholder: 'Company Name (English)',
    span: 2
  }
];

export const POSITION_FIELDS = [
  {
    name: 'position',
    label: '職位1',
    placeholder: '請輸入職位1',
    span: 2
  },
  {
    name: 'position_en',
    label: 'position_en',
    placeholder: 'Position (English)',
    span: 2
  },
  {
    name: 'position1',
    label: '職位2',
    placeholder: '請輸入職位2',
    span: 2
  },
  {
    name: 'position1_en',
    label: 'position1_en',
    placeholder: 'Position 2 (English)',
    span: 2
  }
];

export const DEPARTMENT_FIELDS = [
  {
    name: 'department1',
    label: '部門1(單位1)',
    placeholder: '請輸入第一層部門',
    span: 2
  },
  {
    name: 'department1_en',
    label: 'Department1',
    placeholder: 'Department Level 1',
    span: 2
  },
  {
    name: 'department2',
    label: '部門2(單位2)',
    placeholder: '請輸入第二層部門',
    span: 2
  },
  {
    name: 'department2_en',
    label: 'Department2',
    placeholder: 'Department Level 2',
    span: 2
  },
  {
    name: 'department3',
    label: '部門3(單位3)',
    placeholder: '請輸入第三層部門',
    span: 2
  },
  {
    name: 'department3_en',
    label: 'Department3',
    placeholder: 'Department Level 3',
    span: 2
  }
];

export const CONTACT_FIELDS = [
  {
    name: 'mobile_phone',
    label: '手機',
    placeholder: '請輸入手機號碼',
    span: 1
  },
  {
    name: 'company_phone1',
    label: '公司電話1',
    placeholder: '請輸入公司電話',
    span: 2
  },
  {
    name: 'company_phone2',
    label: '公司電話2',
    placeholder: '請輸入第二組電話',
    span: 2
  },
  {
    name: 'email',
    label: 'Email',
    placeholder: '請輸入Email地址',
    span: 1
  },
  {
    name: 'line_id',
    label: 'Line ID',
    placeholder: '請輸入Line ID',
    span: 1
  }
];

export const ADDRESS_FIELDS = [
  {
    name: 'company_address1',
    label: '公司地址一',
    placeholder: '請輸入公司地址',
    span: 2
  },
  {
    name: 'company_address1_en',
    label: 'company_address1_en',
    placeholder: 'Company Address 1 (English)',
    span: 2
  },
  {
    name: 'company_address2',
    label: '公司地址二',
    placeholder: '請輸入公司地址（補充）',
    span: 2
  },
  {
    name: 'company_address2_en',
    label: 'company_address2_en',
    placeholder: 'Company Address 2 (English)',
    span: 2
  }
];

export const NOTE_FIELDS = [
  {
    name: 'note1',
    label: 'note1',
    placeholder: '請輸入備註資訊',
    type: 'textarea',
    rows: 3,
    span: 2
  },
  {
    name: 'note2',
    label: 'note2',
    placeholder: '請輸入額外備註',
    type: 'textarea',
    rows: 3,
    span: 2
  }
];

export default CardFormSection;