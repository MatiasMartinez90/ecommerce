export type Category = {
  slug: string;
  name: string;
  description: string;
  product_count: number;
};

export type Product = {
  slug: string;
  name: string;
  sku: string;
  description: string;
  short_description: string;
  category_slug: string | null;
  category_name: string | null;
  image_url: string | null;
  gallery: string[];
  price: number;
  available_qty: number;
  in_stock: boolean;
  featured: boolean;
};

export type ProductList = {
  items: Product[];
  total: number;
  limit: number;
  offset: number;
};

export type Cart = {
  token: string;
  status: string;
  currency: string;
  items: Array<{ product: Product; quantity: number; line_total: number }>;
  subtotal: number;
  total_quantity: number;
  expires_at: string;
};

export type Order = {
  id: string;
  order_number: number;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  status: string;
  payment_method: string;
  payment_status: string;
  currency: string;
  subtotal: number;
  total: number;
  pickup_location: string;
  customer_notes: string;
  created_at: string;
  updated_at: string;
  items: Array<{
    product_slug: string;
    product_name: string;
    sku: string;
    unit_price: number;
    quantity: number;
    line_total: number;
  }>;
};

export type PaymentPreference = {
  checkout_url: string;
  status_token: string;
  status: string;
  amount: number;
  currency: string;
  expires_at: string;
  sandbox: boolean;
};

export type PaymentStatus = {
  purpose: string;
  status: string;
  amount: number;
  currency: string;
  expires_at: string;
  sandbox: boolean;
};
