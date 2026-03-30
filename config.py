import os

class SystemConfig:
    COMPANY_NAME = "ABC - Apparel Branding Company"
    COMPANY_ADDRESS = "123, Main Street, Anytown, India"
    COMPANY_PHONE = "9600645456"
    COMPANY_EMAIL = "info@abcuniforms.com"
    MAIL_USERNAME = "info@abcuniforms.com"
    MAIL_PASSWORD = "your_email_password"
    ADMIN_EMAIL = "admin@abcuniforms.com"
    MAIL_URL = "smtp.gmail.com"
    COMPANY_LOGO = "/static/images/logo.png"
    CRISP_WEBSITE_ID = os.getenv("CRISP_WEBSITE_ID", "").strip()

class SocialConfig:
    FACEBOOK_URL = "https://www.facebook.com/abcuniforms"
    TWITTER_URL = "https://www.twitter.com/abcuniforms"
    INSTAGRAM_URL = "https://www.instagram.com/abcuniforms"
    YOUTUBE_URL = "https://www.youtube.com/abcuniforms"

