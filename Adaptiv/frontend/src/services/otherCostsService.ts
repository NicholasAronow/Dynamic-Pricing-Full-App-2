import api from './api';
import { AxiosResponse } from 'axios';

// Types for fixed costs
export interface FixedCost {
  id?: number;
  cost_type: string;
  amount: number;
  month: number;
  year: number;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

// Types for employees
export interface Employee {
  id?: number;
  name: string;
  pay_type: 'salary' | 'hourly';
  salary?: number;
  hourly_rate?: number;
  weekly_hours?: number;
  active?: boolean;
  created_at?: string;
  updated_at?: string;
}

// Fixed costs API calls
export const getFixedCosts = async (
  cost_type?: string,
  month?: number,
  year?: number
): Promise<FixedCost[]> => {
  let url = '/costs/other/fixed-costs';
  const params = new URLSearchParams();
  
  if (cost_type) params.append('cost_type', cost_type);
  if (month) params.append('month', month.toString());
  if (year) params.append('year', year.toString());
  
  const query = params.toString();
  if (query) url += `?${query}`;
  
  const response: AxiosResponse<FixedCost[]> = await api.get(url);
  return response.data;
};

export const createFixedCost = async (fixedCost: FixedCost): Promise<FixedCost> => {
  const response: AxiosResponse<FixedCost> = await api.post('/costs/other/fixed-costs', fixedCost);
  return response.data;
};

export const updateFixedCost = async (id: number, fixedCost: FixedCost): Promise<FixedCost> => {
  const response: AxiosResponse<FixedCost> = await api.put(`/costs/other/fixed-costs/${id}`, fixedCost);
  return response.data;
};

export const deleteFixedCost = async (id: number): Promise<void> => {
  await api.delete(`/costs/other/fixed-costs/${id}`);
};

// Employee API calls
export const getEmployees = async (activeOnly: boolean = true): Promise<Employee[]> => {
  const response: AxiosResponse<Employee[]> = await api.get(
    `/costs/other/employees?active_only=${activeOnly}`
  );
  return response.data;
};

export const getEmployee = async (id: number): Promise<Employee> => {
  const response: AxiosResponse<Employee> = await api.get(`/costs/other/employees/${id}`);
  return response.data;
};

export const createEmployee = async (employee: Employee): Promise<Employee> => {
  const response: AxiosResponse<Employee> = await api.post('/costs/other/employees', employee);
  return response.data;
};

export const updateEmployee = async (id: number, employee: Partial<Employee>): Promise<Employee> => {
  const response: AxiosResponse<Employee> = await api.put(`/costs/other/employees/${id}`, employee);
  return response.data;
};

export const deleteEmployee = async (id: number): Promise<void> => {
  await api.delete(`/costs/other/employees/${id}`);
};

// Helper function to calculate monthly employee cost
export const calculateMonthlyEmployeeCost = (employee: Employee): number => {
  if (employee.pay_type === 'salary' && employee.salary) {
    return employee.salary / 12; // Monthly cost from yearly salary
  } else if (employee.pay_type === 'hourly' && employee.hourly_rate && employee.weekly_hours) {
    // Calculate monthly cost from hourly rate
    // Assuming 4.33 weeks per month average
    return employee.hourly_rate * employee.weekly_hours * 4.33; 
  }
  return 0;
};

// Helper function to calculate total monthly employee costs
export const calculateTotalMonthlyEmployeeCosts = (employees: Employee[]): number => {
  return employees.reduce((total, employee) => {
    return total + calculateMonthlyEmployeeCost(employee);
  }, 0);
};
