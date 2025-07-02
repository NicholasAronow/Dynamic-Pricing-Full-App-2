import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Button, Select, InputNumber, Space, Table, Typography, Divider } from 'antd';
import { PlusOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { Item } from '../../services/itemService';

const { Text } = Typography;
const { Option } = Select;

interface RecipeIngredient {
  ingredient_id: string;
  quantity: number;
  unit: string;
}

interface RecipeItem {
  item_id: string;
  item_name: string;
  menu_item_id?: string; // ID of the menu item this recipe is linked to
  ingredients: RecipeIngredient[];
  date_created: string;
}

interface IngredientItem {
  ingredient_id: string;
  ingredient_name: string;
  quantity: number;
  unit: string;
  price: number;
  date_created: string;
}

interface RecipeModalProps {
  visible: boolean;
  onCancel: () => void;
  onSave: (recipe: RecipeItem) => void;
  recipe?: RecipeItem;
  ingredients: IngredientItem[];
  menuItems: Item[]; // Added menu items prop
  isNew?: boolean;
}

const RecipeModal: React.FC<RecipeModalProps> = ({
  visible,
  onCancel,
  onSave,
  recipe,
  ingredients,
  menuItems,
  isNew = false
}) => {
  const [form] = Form.useForm();
  const [selectedIngredients, setSelectedIngredients] = useState<RecipeIngredient[]>([]);

  // Calculate the cost of the recipe based on ingredients
  const calculateRecipeCost = () => {
    let totalCost = 0;
    
    if (!selectedIngredients || !ingredients.length) return totalCost;
    
    selectedIngredients.forEach(recipeIngredient => {
      const ingredient = ingredients.find(i => i.ingredient_id === recipeIngredient.ingredient_id);
      if (ingredient) {
        const unitCost = ingredient.price / ingredient.quantity;
        totalCost += unitCost * recipeIngredient.quantity;
      }
    });
    
    return totalCost.toFixed(2);
  };

  useEffect(() => {
    if (visible && recipe) {
      form.setFieldsValue({
        item_name: recipe.item_name,
        menu_item_id: recipe.menu_item_id,
        ingredients: recipe.ingredients
      });
      setSelectedIngredients(recipe.ingredients);
    } else if (visible && isNew) {
      form.resetFields();
      setSelectedIngredients([]);
    }
  }, [visible, recipe, isNew, form]);

  const handleValuesChange = (changedValues: any) => {
    if (changedValues.ingredients) {
      setSelectedIngredients(changedValues.ingredients.filter((i: any) => i && i.ingredient_id));
    }
  };

  const columns = [
    {
      title: 'Ingredient',
      dataIndex: 'ingredient_id',
      key: 'ingredient_id',
      render: (ingredient_id: string) => {
        const ingredient = ingredients.find(i => i.ingredient_id === ingredient_id);
        return ingredient ? ingredient.ingredient_name : 'Unknown';
      }
    },
    {
      title: 'Quantity',
      dataIndex: 'quantity',
      key: 'quantity',
      render: (quantity: number, record: RecipeIngredient) => `${quantity} ${record.unit}`
    },
    {
      title: 'Unit Cost',
      key: 'unit_cost',
      render: (_: any, record: RecipeIngredient) => {
        const ingredient = ingredients.find(i => i.ingredient_id === record.ingredient_id);
        if (!ingredient) return 'N/A';
        
        const unitPrice = ingredient.price / ingredient.quantity;
        return `$${unitPrice.toFixed(4)} / ${ingredient.unit}`;
      }
    },
    {
      title: 'Cost',
      key: 'cost',
      render: (_: any, record: RecipeIngredient) => {
        const ingredient = ingredients.find(i => i.ingredient_id === record.ingredient_id);
        if (!ingredient) return 'N/A';
        
        const unitPrice = ingredient.price / ingredient.quantity;
        const cost = unitPrice * record.quantity;
        return `$${cost.toFixed(2)}`;
      }
    }
  ];

  const handleSubmit = () => {
    form.validateFields()
      .then(values => {
        const newRecipe: RecipeItem = {
          item_id: recipe?.item_id || `new-${Date.now()}`,
          item_name: values.item_name,
          menu_item_id: values.menu_item_id,
          ingredients: values.ingredients,
          date_created: recipe?.date_created || new Date().toISOString().split('T')[0]
        };
        onSave(newRecipe);
        form.resetFields();
      })
      .catch(info => {
        console.log('Validate Failed:', info);
      });
  };

  return (
    <Modal
      title={isNew ? "Add New Recipe" : "Edit Recipe"}
      open={visible}
      onCancel={onCancel}
      width={1200}
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
        name="recipe_form"
        onValuesChange={handleValuesChange}
      >
        <Form.Item
          name="item_name"
          label="Recipe Name"
          rules={[{ required: true, message: 'Please enter the recipe name!' }]}
        >
          <Input placeholder="Enter recipe name" />
        </Form.Item>
        
        <Form.Item
          name="menu_item_id"
          label="Link to Menu Item"
          tooltip="Associate this recipe with a menu item from your menu"
        >
          <Select 
            placeholder="Select a menu item to link (optional)" 
            allowClear
            showSearch
            optionFilterProp="children"
            filterOption={(input, option) =>
              (option?.children as unknown as string)?.toLowerCase().indexOf(input.toLowerCase()) >= 0
            }
          >
            {menuItems.map(item => (
              <Select.Option key={item.id} value={item.id.toString()}>
                {item.name} (${item.current_price.toFixed(2)})
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Divider orientation="left">Ingredients</Divider>

        <Form.List name="ingredients">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...restField }) => (
                <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                  <Form.Item
                    {...restField}
                    name={[name, 'ingredient_id']}
                    rules={[{ required: true, message: 'Select an ingredient' }]}
                  >
                    <Select 
                      placeholder="Select ingredient"
                      style={{ width: 200 }}
                    >
                      {ingredients.map(ingredient => (
                        <Option key={ingredient.ingredient_id} value={ingredient.ingredient_id}>
                          {ingredient.ingredient_name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, 'quantity']}
                    rules={[{ required: true, message: 'Enter quantity' }]}
                  >
                    <InputNumber min={0.01} step={0.01} placeholder="Quantity" />
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, 'unit']}
                    rules={[{ required: true, message: 'Enter unit' }]}
                  >
                    <Select 
                      placeholder="Select unit"
                      style={{ width: 100 }}
                    >
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
                      <Option value="whole">whole item</Option>
                    </Select>
                  </Form.Item>
                  <MinusCircleOutlined onClick={() => remove(name)} />
                </Space>
              ))}
              <Form.Item>
                <Button 
                  type="dashed" 
                  onClick={() => add()} 
                  block 
                  icon={<PlusOutlined />}
                >
                  Add Ingredient
                </Button>
              </Form.Item>
            </>
          )}
        </Form.List>
      </Form>

      {selectedIngredients.length > 0 && (
        <>
          <Divider orientation="left">Recipe Summary</Divider>
          <Table 
            dataSource={selectedIngredients} 
            columns={columns} 
            pagination={false} 
            rowKey={(record) => record.ingredient_id}
          />
          <div style={{ marginTop: 16, textAlign: 'right' }}>
            <Text strong>Total Recipe Cost: ${calculateRecipeCost()}</Text>
          </div>
        </>
      )}
    </Modal>
  );
};

export default RecipeModal;
