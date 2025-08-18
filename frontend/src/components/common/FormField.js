import React from 'react';
import { Form, Input, TextArea } from 'antd-mobile';

/**
 * 統一的表單欄位組件
 * @param {Object} props
 * @param {string} props.label - 欄位標籤
 * @param {string} props.value - 欄位值
 * @param {function} props.onChange - 值變更回調
 * @param {string} props.placeholder - 占位符文字
 * @param {boolean} props.required - 是否必填
 * @param {string} props.type - 欄位類型：'input', 'textarea'
 * @param {number} props.rows - textarea 行數
 * @param {number} props.maxLength - 最大長度
 * @param {boolean} props.disabled - 是否禁用
 */
const FormField = ({
  label,
  value,
  onChange,
  placeholder,
  required = false,
  type = 'input',
  rows = 3,
  maxLength,
  disabled = false,
  ...props
}) => {
  const handleChange = (val) => {
    if (onChange) {
      onChange(val);
    }
  };

  const renderInput = () => {
    const commonProps = {
      placeholder,
      value: value || '',
      onChange: handleChange,
      disabled,
      maxLength,
      ...props
    };

    switch (type) {
      case 'textarea':
        return (
          <TextArea
            {...commonProps}
            rows={rows}
            autoSize={false}
          />
        );
      case 'input':
      default:
        return (
          <Input {...commonProps} />
        );
    }
  };

  return (
    <Form.Item 
      label={label} 
      required={required}
    >
      {renderInput()}
    </Form.Item>
  );
};

export default FormField;