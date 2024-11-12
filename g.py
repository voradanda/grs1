import asyncio
import random
import ssl
import json
import time
import uuid
import requests
import shutil
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

async def connect_to_wss(socks5_proxy, user_id):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(device_id)
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent,
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            urilist = ["wss://proxy2.wynd.network:4444/","wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(5)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "desktop",
                                "version": "4.28.2",
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            # Define the proxy to remove
            proxy_to_remove = socks5_proxy

            # Open the file in read mode
            with open('auto_proxies.txt', 'r') as file:
                # Read all lines from the file
                lines = file.readlines()

            # Filter out the line that contains the proxy to remove
            updated_lines = [line for line in lines if line.strip() != proxy_to_remove]

            # Open the file in write mode to overwrite with the filtered content
            with open('auto_proxies.txt', 'w') as file:
                # Write the updated lines back to the file
                file.writelines(updated_lines)

            print(f"Proxy '{proxy_to_remove}' has been removed from the file.")

async def main():
    try:
        with open('user.txt', 'r') as user_file:
            _user_id = user_file.readline().strip()
        print(f"User ID loaded: {_user_id}")
    except FileNotFoundError:
        print("Error: user.txt file not found.")
        return
    #put the proxy in a file in the format socks5://username:password@ip:port or socks5://ip:port
    r = requests.get("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text", stream=True)
    if r.status_code == 200:
       with open('auto_proxies.txt', 'wb') as f:
           for chunk in r:
               f.write(chunk)
       with open('auto_proxies.txt', 'r') as file:
               auto_proxy_list = file.read().splitlines()

    tasks = [asyncio.ensure_future(connect_to_wss(proxy, _user_id)) for proxy in auto_proxy_list]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    #letsgo
    asyncio.run(main())