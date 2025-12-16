# sunsynk-api
Get inverter stats via the current api.sunsynk.net


# New API Login trick
https://api.sunsynk.net/static/js/app.30ef39c7.js here the JavaScript code reveals that the signature uses the first 10 characters of the base64-encoded RSA public key appended to the nonce string. This is the missing piece!
The signature calculation is:
MD5("nonce={nonce}&source={source}" + first_10_chars_of_base64_key)

# Remember to export your api.sunsynk.net credentials as enviroment variables eg.
```bash
SUNSYNK_USERNAME=XXXX@example.com
SUNSYNK_PASSWORD=XXXX
SUNSYNK_INVERTER_SN=25XXXXXXX
```

