import pytest

from toddler_transducer.puck_creator.app import puck_creator_app


@pytest.fixture
def puck_client():
    puck_creator_app.config["TESTING"] = True
    with puck_creator_app.test_client() as c:
        yield c


class TestPuckCreatorPage:
    def test_designer_page_returns_200(self, puck_client):
        resp = puck_client.get("/")
        assert resp.status_code == 200
        assert b"Puck Creator" in resp.data

    def test_style_css_served(self, puck_client):
        resp = puck_client.get("/static/css/style.css")
        assert resp.status_code == 200
        assert b".controls-panel" in resp.data


class TestMobileControlsPanel:
    def test_hidden_by_default_on_mobile(self, puck_client):
        css = puck_client.get("/static/css/style.css").data.decode("utf-8")
        mobile_rule = css.split("@media screen and (max-width: 768px)")[1]
        assert "display: none;" in mobile_rule

    def test_visible_drawer_anchored_top_right(self, puck_client):
        css = puck_client.get("/static/css/style.css").data.decode("utf-8")
        mobile_rule = css.split("@media screen and (max-width: 768px)")[1]
        assert ".controls-panel.visible" in mobile_rule
        assert "position: fixed;" in mobile_rule
        assert "top: 60px;" in mobile_rule
        assert "right: 10px;" in mobile_rule
        assert "bottom: 10px;" in mobile_rule
        assert "z-index: 999;" in mobile_rule
