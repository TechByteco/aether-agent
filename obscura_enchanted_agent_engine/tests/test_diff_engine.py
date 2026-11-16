from obscura_engine.diff_engine import DomDiffEngine
from obscura_engine.distiller import DomDistiller


def test_diff_engine_detects_mutations():
    distiller = DomDistiller()
    diff_engine = DomDiffEngine()

    html_v1 = """
    <html><body>
        <h1>Store</h1>
        <button id="cart-btn">View Cart (0 items)</button>
        <button id="buy-1">Buy Item 1</button>
    </body></html>
    """
    snap_v1 = distiller.distill(html_v1, url="https://store.test/shop")
    diff_v1 = diff_engine.compute_diff(snap_v1)

    assert diff_v1.has_changed is True
    assert len(diff_v1.added_elements) == 2

    # Version 2: user clicked Buy Item 1, cart updated to 1 item and item 1 disabled
    html_v2 = """
    <html><body>
        <h1>Store</h1>
        <button id="cart-btn">View Cart (1 item)</button>
        <div class="alert">Added to Cart!</div>
        <a id="checkout" href="/checkout">Proceed to Checkout</a>
    </body></html>
    """
    snap_v2 = distiller.distill(html_v2, url="https://store.test/shop")
    diff_v2 = diff_engine.compute_diff(snap_v2)

    assert diff_v2.has_changed is True
    assert len(diff_v2.added_elements) == 1
    assert diff_v2.added_elements[0].selector == "#checkout"
    assert "Proceed to Checkout" in diff_v2.diff_markdown
    assert "cart-btn" in diff_v2.diff_markdown


def test_diff_engine_no_change():
    distiller = DomDistiller()
    diff_engine = DomDiffEngine()

    html = "<html><body><p>Static Content</p><button id='b1'>Click</button></body></html>"
    snap = distiller.distill(html, url="https://static.test")

    diff_1 = diff_engine.compute_diff(snap)
    assert diff_1.has_changed is True

    # Same snapshot again
    diff_2 = diff_engine.compute_diff(snap)
    assert diff_2.has_changed is False
    assert "No DOM mutations" in diff_2.summary
