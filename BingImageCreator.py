import os
import random
import asyncio
import aiohttp
import aiofiles
import time
import urllib.parse
import regex
from typing import Callable, List, Optional

BING_URL = os.getenv("BING_URL", "https://www.bing.com")
# Генерация случайного IP из диапазона 13.104.0.0/14
FORWARDED_IP = f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "referrer": "https://www.bing.com/images/create/",
    "origin": "https://www.bing.com",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63",
    "x-forwarded-for": FORWARDED_IP,
}

# Тексты ошибок
ERROR_TIMEOUT = "Ваш запрос превысил время ожидания."
ERROR_REDIRECT = "Ошибка перенаправления."
ERROR_BLOCKED_PROMPT = "Ваш запрос был заблокирован. Попробуйте изменить запрещённые слова и повторите попытку."
ERROR_BEING_REVIEWED_PROMPT = "Ваш запрос проходит проверку. Попробуйте изменить чувствительные слова и повторите попытку."
ERROR_NORESULTS = "Не удалось получить результаты."
ERROR_UNSUPPORTED_LANG = "Этот язык в настоящее время не поддерживается."
ERROR_BAD_IMAGES = "Некорректные изображения."
ERROR_NO_IMAGES = "Изображения отсутствуют."


class AsyncImageGen:
    """
    Генерация изображений с использованием Bing в асинхронном режиме.
    Для аутентификации используется auth cookie.
    """
    def __init__(self, auth_cookie: str, auth_cookie_SRCHHPGUSR: str):
        self.cookies = {"_U": auth_cookie, "SRCHHPGUSR": auth_cookie_SRCHHPGUSR}
        self.session = aiohttp.ClientSession(headers=HEADERS, cookies=self.cookies)

    async def get_images(self, prompt: str, status_callback: Optional[Callable[[str], None]] = None) -> List[str]:
        if status_callback:
            await status_callback("STATE_SENDING_REQUEST")
        url_encoded_prompt = urllib.parse.quote(prompt)
        payload = f"q={url_encoded_prompt}&qs=ds"
        url = f"{BING_URL}/images/create?q={url_encoded_prompt}&rt=4&FORM=GENCRE"
        timeout = aiohttp.ClientTimeout(total=200)
        try:
            async with self.session.post(url, allow_redirects=False, data=payload, timeout=timeout) as response:
                response_text = await response.text()
        except Exception as e:
            if status_callback:
                await status_callback(f"STATE_ERROR: {str(e)}")
            raise e

        lower_text = response_text.lower()
        if "this prompt is being reviewed" in lower_text:
            if status_callback:
                await status_callback(f"STATE_ERROR: {ERROR_BEING_REVIEWED_PROMPT}")
            raise Exception(ERROR_BEING_REVIEWED_PROMPT)
        if "this prompt has been blocked" in lower_text:
            if status_callback:
                await status_callback(f"STATE_ERROR: {ERROR_BLOCKED_PROMPT}")
            raise Exception(ERROR_BLOCKED_PROMPT)
        if "we're working hard to offer image creator in more languages" in lower_text:
            if status_callback:
                await status_callback(f"STATE_ERROR: {ERROR_UNSUPPORTED_LANG}")
            raise Exception(ERROR_UNSUPPORTED_LANG)
        if response.status != 302:
            # Если rt4 не сработал, пробуем rt3
            url = f"{BING_URL}/images/create?q={url_encoded_prompt}&rt=3&FORM=GENCRE"
            async with self.session.post(url, allow_redirects=False, timeout=timeout) as response:
                response_text = await response.text()
            if response.status != 302:
                if status_callback:
                    await status_callback(f"STATE_ERROR: {ERROR_REDIRECT}")
                raise Exception(ERROR_REDIRECT)
        # Получаем redirect URL
        redirect_url = response.headers.get("Location", "").replace("&nfy=1", "")
        request_id = redirect_url.split("id=")[-1]
        # Выполняем GET запрос по redirect URL
        async with self.session.get(f"{BING_URL}{redirect_url}", timeout=timeout) as _:
            pass
        polling_url = f"{BING_URL}/images/create/async/results/{request_id}?q={url_encoded_prompt}"
        if status_callback:
            await status_callback("STATE_WAITING_FOR_RESULTS")
        start_wait = time.time()
        poll_text = ""
        while True:
            if int(time.time() - start_wait) > 200:
                if status_callback:
                    await status_callback(f"STATE_ERROR: {ERROR_TIMEOUT}")
                raise Exception(ERROR_TIMEOUT)
            try:
                async with self.session.get(polling_url, timeout=timeout) as poll_response:
                    poll_text = await poll_response.text()
                    if poll_response.status != 200:
                        if status_callback:
                            await status_callback(f"STATE_ERROR: {ERROR_NORESULTS}")
                        raise Exception(ERROR_NORESULTS)
            except Exception as e:
                if status_callback:
                    await status_callback(f"STATE_ERROR: {str(e)}")
                raise e
            if not poll_text or poll_text.find("errorMessage") != -1:
                await asyncio.sleep(1)
                continue
            else:
                break
        if status_callback:
            await status_callback("STATE_PARSING_RESULTS")
        image_links = regex.findall(r'src="([^"]+)"', poll_text)
        normal_image_links = [link.split("?w=")[0] for link in image_links]
        normal_image_links = list(set(normal_image_links))
        if not normal_image_links:
            if status_callback:
                await status_callback(f"STATE_ERROR: {ERROR_NO_IMAGES}")
            raise Exception(ERROR_NO_IMAGES)
        if status_callback:
            await status_callback("STATE_RESULTS_RECEIVED")
        final_links = [link for link in normal_image_links if "r.bing.com/rp/" not in link]
        return final_links


async def generate_images(prompt: str, cookie_file: str = "U", status_callback: Optional[Callable[[str], None]] = None) -> List[str]:
    """
    Функция-модуль для генерации URL изображений по промту в асинхронном режиме.
    Читает auth cookie из файла, затем вызывает Bing AsyncImageGen.
    Возвращает список URL изображений.
    """
    try:
        async with aiofiles.open(cookie_file, "r", encoding="utf-8") as f:
            cookie_value = (await f.read()).strip()
    except Exception as e:
        if status_callback:
            await status_callback(f"STATE_ERROR: Could not load auth cookie from file: {str(e)}")
        raise Exception("Could not load auth cookie from file") from e

    image_generator = AsyncImageGen(auth_cookie=cookie_value, auth_cookie_SRCHHPGUSR=cookie_value)
    try:
        links = await image_generator.get_images(prompt, status_callback=status_callback)
        return links
    finally:
        await image_generator.session.close()


if __name__ == "__main__":
    async def main():
        def my_status_callback(status: str):
            print(f"Status update: {status}")

        prompt_input = "верстак"  # Пример промта
        try:
            links = await generate_images(prompt_input, cookie_file="U", status_callback=my_status_callback)
            print("Image URLs:")
            for link in links:
                print(link)
        except Exception as e:
            print(f"An error occurred: {e}")

    asyncio.run(main())
