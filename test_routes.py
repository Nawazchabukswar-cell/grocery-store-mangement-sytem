import unittest
import json
from web_app import app

class WebAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_get_stats(self):
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)

    def test_get_products(self):
        response = self.client.get('/api/products')
        self.assertEqual(response.status_code, 200)

    def test_get_categories(self):
        response = self.client.get('/api/categories')
        self.assertEqual(response.status_code, 200)

    def test_customer_crud(self):
        # Create
        res = self.client.post('/api/customers', data=json.dumps({
            'name': 'Test Customer',
            'phone': '1234567890',
            'email': 'test@example.com'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        cust_id = data['id']

        # Read
        res = self.client.get('/api/customers')
        self.assertEqual(res.status_code, 200)

        # Delete
        res = self.client.delete(f'/api/customers/{cust_id}')
        self.assertEqual(res.status_code, 200)

    def test_supplier_crud(self):
        # Create
        res = self.client.post('/api/suppliers', data=json.dumps({
            'name': 'Test Supplier',
            'contact_person': 'Jane Doe',
            'phone': '0987654321',
            'email': 'supplier@example.com'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        supp_id = data['id']

        # Read
        res = self.client.get('/api/suppliers')
        self.assertEqual(res.status_code, 200)

        # Delete
        res = self.client.delete(f'/api/suppliers/{supp_id}')
        self.assertEqual(res.status_code, 200)

    def test_settings_save(self):
        res = self.client.post('/api/settings', data=json.dumps({
            'store_name': 'GroceryHub Test',
            'tax_rate': '5'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)

    def test_export_sales_csv(self):
        response = self.client.get('/api/reports/export')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
