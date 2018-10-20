
import requests
from resela.app import APP


class RecaptchaModel:
    """ Defines functionallity for reCAPTCHA """

    @staticmethod
    def validate(captcha_response):
        """  Sends a post request to Google to validate captcha, returns response
        :return: A json object containing success(true|false), allowing or disallowing a user
                 to login
        """

        post_url = 'https://www.google.com/recaptcha/api/siteverify'
        post_values = {
            'secret': APP.iniconfig.get('captcha', 'captcha_secret_key'),
            'response': captcha_response
        }

        request = requests.post(post_url, post_values)
        post_response = request.json()

        return post_response
