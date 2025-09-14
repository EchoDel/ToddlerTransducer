def setup_webpage(html_path, **kwargs):
    with open(html_path) as f:
        text = f.read()
    return text.format(kwargs)
