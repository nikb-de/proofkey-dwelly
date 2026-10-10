"""New product routes retain the same explicit static and security boundary."""
import pytest

from .test_server import platform


@pytest.mark.parametrize("path,mime", [
    ("/customer.html", "text/html"),
    ("/customer.js", "text/javascript"),
    ("/customer-model.js", "text/javascript"),
    ("/customer.css", "text/css"),
    ("/preparation.html", "text/html"),
    ("/preparation.js", "text/javascript"),
    ("/preparation-model.js", "text/javascript"),
    ("/preparation.css", "text/css"),
    ("/product.js", "text/javascript"),
    ("/showcase.html", "text/html"),
    ("/showcase.js", "text/javascript"),
    ("/showcase.css", "text/css"),
    ("/showcase-data-llm.json", "application/json"),
    ("/showcase-data-synthetic.json", "application/json"),
])
def test_product_assets_are_served_with_the_platform_boundary(platform, path, mime):
    request, _, _ = platform
    code, body, headers = request(path)
    assert code == 200
    assert len(body) > 0
    assert headers['Content-Type'].startswith(mime)
    assert headers['Cache-Control'] == 'no-store'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert "connect-src 'self'" in headers['Content-Security-Policy']


@pytest.mark.parametrize("path", [
    "/../.env", "/%2e%2e/.env", "/customer.js/../.env",
    "/preparation/../../.env", "/unlisted.js", "/.env",
    "/showcase-data-private.json", "/showcase-data-llm.json/../.env",
])
def test_product_routes_do_not_introduce_generic_file_serving(platform, path):
    request, _, _ = platform
    code, _, _ = request(path)
    assert code == 404
