from obscura_engine.distiller import DomDistiller


def test_distiller_strips_noise_and_svg():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title><style>body { color: red; }</style></head>
    <body>
        <script>console.log("noisy tracking script");</script>
        <svg viewBox="0 0 100 100"><path d="M10 10 H 90 V 90 H 10 L 10 10"/></svg>
        <h1>Main Heading</h1>
        <p>This is clean body text.</p>
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..." alt="Embedded Logo">
        <a href="https://example.com/docs">Documentation Link</a>
    </body>
    </html>
    """
    distiller = DomDistiller()
    snapshot = distiller.distill(html, url="https://example.com", title="Test Page")

    # Verify script, style, and svg are completely gone
    assert "console.log" not in snapshot.markdown
    assert "color: red" not in snapshot.markdown
    assert "M10 10" not in snapshot.markdown
    assert "base64" not in snapshot.markdown

    # Verify heading and text are preserved
    assert "# Main Heading" in snapshot.markdown
    assert "This is clean body text." in snapshot.markdown

    # Verify interactive element has deterministic @ref: tag
    assert "[[@ref:1] Documentation Link](https://example.com/docs)" in snapshot.markdown
    assert len(snapshot.interactive_elements) == 1
    assert snapshot.interactive_elements[0].ref_id == "1"
    assert snapshot.interactive_elements[0].text == "Documentation Link"

    # Verify token savings
    assert snapshot.token_savings_pct > 30.0


def test_distiller_form_controls():
    html = """
    <html><body>
        <form>
            <input type="text" placeholder="Username" name="user" value="alice" />
            <input type="password" placeholder="Password" name="pass" />
            <input type="checkbox" name="remember" checked />
            <button type="submit">Log In</button>
            <select name="country">
                <option value="US">United States</option>
                <option value="UK">United Kingdom</option>
            </select>
        </form>
    </body></html>
    """
    distiller = DomDistiller()
    snapshot = distiller.distill(html)

    assert len(snapshot.interactive_elements) == 5
    assert "[Input: [@ref:1] type='text' placeholder='Username' value='alice']" in snapshot.markdown
    assert "[Input: [@ref:2] type='password' placeholder='Password' value='']" in snapshot.markdown
    assert "[[@ref:3] [x] remember]" in snapshot.markdown
    assert "[[@ref:4] (Button: Log In)]" in snapshot.markdown
    assert "[Select: [@ref:5] options='United States | United Kingdom']" in snapshot.markdown


def test_distiller_markdown_table():
    html = """
    <html><body>
        <table>
            <tr><th>Item</th><th>Price</th></tr>
            <tr><td>Widget A</td><td>$10</td></tr>
            <tr><td>Widget B</td><td>$25</td></tr>
        </table>
    </body></html>
    """
    distiller = DomDistiller()
    snapshot = distiller.distill(html)

    assert "| Item | Price |" in snapshot.markdown
    assert "| --- | --- |" in snapshot.markdown
    assert "| Widget A | $10 |" in snapshot.markdown
    assert "| Widget B | $25 |" in snapshot.markdown
