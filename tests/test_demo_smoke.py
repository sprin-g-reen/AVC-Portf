import unittest
from unittest.mock import patch

import app


class DemoSmokeTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    @patch("app.load_home_content")
    def test_homepage_loads(self, mock_home):
        mock_home.return_value = app.default_home_content()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ABC", response.data)

    @patch("app.load_home_content")
    @patch("app.load_shop_products")
    def test_shop_uses_product_route_links(self, mock_products, mock_home):
        mock_home.return_value = app.default_home_content()
        mock_products.return_value = {
            "D001": {
                "name": "Demo Product",
                "desc": "Demo description",
                "price": "$99",
                "image_path": "images/logo.png",
                "image_alt": "Demo Product",
                "category": "Demo",
                "Sizes": ["M", "L"],
                "images": [],
                "decorations": [],
                "instructions": [],
                "product_details": [],
            }
        }
        response = self.client.get("/shop")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/product/D001", response.data)

    @patch("app.load_home_content")
    @patch("app.load_shop_products")
    def test_product_detail_route_loads(self, mock_products, mock_home):
        mock_home.return_value = app.default_home_content()
        mock_products.return_value = {
            "D002": {
                "name": "Demo Detail Product",
                "desc": "Details",
                "description": "Details",
                "price": "$49",
                "image_path": "images/logo.png",
                "image_alt": "Demo Detail Product",
                "category": "Demo",
                "Sizes": ["S", "M"],
                "images": [{"color": "default", "image_path": "images/logo.png"}],
                "decorations": [],
                "instructions": [],
                "product_details": [],
            }
        }
        response = self.client.get("/product/D002")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Demo Detail Product", response.data)


if __name__ == "__main__":
    unittest.main()
