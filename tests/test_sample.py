import os
import unittest
from unittest.mock import patch

import app
import strapi_client


class AppHelpersTests(unittest.TestCase):
    def test_description_to_text_from_blocks(self):
        blocks = [
            {"type": "paragraph", "children": [{"type": "text", "text": "Hello"}]},
            {"type": "paragraph", "children": [{"type": "text", "text": "World"}]},
        ]
        self.assertEqual(app.description_to_text(blocks), "Hello World")

    def test_resolve_media_url_for_relative_path(self):
        with app.app.test_request_context("/"):
            self.assertEqual(
                app.resolve_media_url("abc_upload/item/image.png"),
                "/static/abc_upload/item/image.png",
            )

    def test_resolve_media_url_for_absolute_url(self):
        with app.app.test_request_context("/"):
            url = "https://cdn.example.com/image.png"
            self.assertEqual(app.resolve_media_url(url), url)


class StrapiClientTests(unittest.TestCase):
    @patch.dict(os.environ, {"STRAPI_URL": "http://localhost:1337", "STRAPI_PRODUCTS_COLLECTION": "products"}, clear=False)
    @patch("strapi_client._fetch_json")
    def test_get_shop_products_ignores_missing_external_id(self, mock_fetch_json):
        mock_fetch_json.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "Keep Me",
                    "external_id": "000001",
                    "image_path": "https://cdn.example.com/ok.png",
                },
                {
                    "id": 2,
                    "name": "Skip Me",
                    "external_id": "",
                    "image_path": "https://cdn.example.com/skip.png",
                },
            ],
            "meta": {"pagination": {"pageCount": 1}},
        }

        products = strapi_client.get_shop_products()
        self.assertIsNotNone(products)
        self.assertEqual(len(products), 1)
        only_product = list(products.values())[0]
        self.assertEqual(only_product["name"], "Keep Me")
        self.assertEqual(only_product["external_id"], "000001")


if __name__ == "__main__":
    unittest.main()
