import React, { useEffect } from 'react';
import { Modal, Form, Input, Button, Select, InputNumber } from 'antd';

const { Option } = Select;

interface IngredientItem {
  ingredient_id: string;
  ingredient_name: string;
  quantity: number;
  unit: string;
  price: number;
  date_created: string;
}

interface IngredientModalProps {
  visible: boolean;
  onCancel: () => void;
  onSave: (ingredient: IngredientItem) => void;
  ingredient?: IngredientItem;
  isNew?: boolean;
}

const IngredientModal: React.FC<IngredientModalProps> = ({
  visible,
  onCancel,
  onSave,
  ingredient,
  isNew = false
}) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (visible && ingredient) {
      form.setFieldsValue({
        ingredient_name: ingredient.ingredient_name,
        quantity: ingredient.quantity,
        unit: ingredient.unit,
        price: ingredient.price
      });
    } else if (visible && isNew) {
      form.resetFields();
    }
  }, [visible, ingredient, isNew, form]);

  const calculateUnitPrice = () => {
    const quantity = form.getFieldValue('quantity');
    const price = form.getFieldValue('price');
    
    if (!quantity || !price) return 'N/A';
    return `$${(price / quantity).toFixed(4)}`;
  };

  const handleSubmit = () => {
    form.validateFields()
      .then(values => {
        const newIngredient: IngredientItem = {
          ingredient_id: ingredient?.ingredient_id || `new-${Date.now()}`,
          ingredient_name: values.ingredient_name,
          quantity: values.quantity,
          unit: values.unit,
          price: values.price,
          date_created: ingredient?.date_created || new Date().toISOString().split('T')[0]
        };
        onSave(newIngredient);
        form.resetFields();
      })
      .catch(info => {
        console.log('Validate Failed:', info);
      });
  };

  return (
    <Modal
      title={isNew ? "Add New Ingredient" : "Edit Ingredient"}
      open={visible}
      onCancel={onCancel}
      width={600}
      footer={[
        <Button key="back" onClick={onCancel}>
          Cancel
        </Button>,
        <Button key="submit" type="primary" onClick={handleSubmit}>
          Save
        </Button>,
      ]}
    >
      <Form
        form={form}
        layout="vertical"
        name="ingredient_form"
      >
        <Form.Item
          name="ingredient_name"
          label="Ingredient Name"
          rules={[{ required: true, message: 'Please enter the ingredient name!' }]}
        >
          <Input placeholder="Enter ingredient name" />
        </Form.Item>

        <Form.Item
          name="quantity"
          label="Purchase Quantity"
          rules={[{ required: true, message: 'Please enter the purchase quantity!' }]}
        >
          <InputNumber min={0.01} step={0.01} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item
          name="unit"
          label="Unit of Measure"
          rules={[{ required: true, message: 'Please select a unit!' }]}
        >
          <Select placeholder="Select unit">
            <Option value="g">g (gram)</Option>
            <Option value="kg">kg (kilogram)</Option>
            <Option value="oz">oz (ounce)</Option>
            <Option value="ml">ml (milliliter)</Option>
            <Option value="l">l (liter)</Option>
            <Option value="pc">pc (piece)</Option>
            <Option value="tbsp">tbsp (tablespoon)</Option>
            <Option value="tsp">tsp (teaspoon)</Option>
            <Option value="cup">cup</Option>
            <Option value="gal">gal (gallon)</Option>
            <Option value="lb">lb (pound)</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="price"
          label="Purchase Price"
          rules={[{ required: true, message: 'Please enter the purchase price!' }]}
        >
          <InputNumber 
            min={0.01} 
            step={0.01} 
            style={{ width: '100%' }}
            prefix="$"
          />
        </Form.Item>

        <div style={{ marginTop: 16 }}>
          <strong>Unit Price: </strong> 
          {calculateUnitPrice()} per {form.getFieldValue('unit') || 'unit'}
        </div>
      </Form>
    </Modal>
  );
};

export default IngredientModal;
