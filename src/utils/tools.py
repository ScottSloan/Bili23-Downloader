def get_exclimbwuzhi_header():
    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json;charset=UTF-8",
        "Cookie": get_login_cookies(),
        "Origin": "https://www.bilibili.com",
        "Priority": "u=1, i",
        "Referer": "https://www.bilibili.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
    }

def get_login_header():
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": get_login_cookies(),
        "Origin": "https://www.bilibili.com",
        "Priority": "u=1, i",
        "Referer": "https://www.bilibili.com/",
        "Sec-Ch-Ua": '"Chromium";v="130", "Microsoft Edge";v="130", "Not?A_Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    }

def get_login_cookies():
    from utils.login import LoginCookies

    cookie_dict = {
        "buvid3": LoginCookies.buvid3,
        "b_lsid": LoginCookies.b_lsid,
        "b_nut": LoginCookies.b_nut,
        "_uuid": LoginCookies.uuid,
        "buvid_fp": "a22acd07567177ce6984b9e995a4a6fb",
        "enable_web_push": "DISABLE",
        "home_feed_column": "5",
        "buvid4": LoginCookies.buvid4,
    }

    return "; ".join([f"{key}={value}" for key, value in cookie_dict.items()])
