from app.services.telegram_channels.mapper import (
    fix_telegram_listing_url,
    telegram_message_url,
)


def test_telegram_message_url_prefers_username():
    assert (
        telegram_message_url("@ua_autobazar", 618510, "https://t.me/-1001482923083/618510")
        == "https://t.me/ua_autobazar/618510"
    )


def test_fix_telegram_listing_url_from_listing_id():
    listing_id = "telegram_ua_autobazar_618510"
    bad = "https://t.me/-1001482923083/618510"
    assert fix_telegram_listing_url(listing_id, bad) == "https://t.me/ua_autobazar/618510"


def test_fix_telegram_listing_url_keeps_good_url():
    good = "https://t.me/ua_autobazar/618510"
    assert fix_telegram_listing_url("telegram_ua_autobazar_618510", good) == good


def test_fix_telegram_listing_url_from_images_path():
    bad = "https://t.me/-1001482923083/618510"
    images = ["/api/v1/telegram-media/ua_autobazar/618510.jpg"]
    assert (
        fix_telegram_listing_url("telegram_-1001482923083_618510", bad, images=images)
        == "https://t.me/ua_autobazar/618510"
    )
