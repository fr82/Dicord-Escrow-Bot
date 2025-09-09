import requests
import os
from dotenv import load_dotenv

load_dotenv()  


def get_current_price(coin_symbol):
    if coin_symbol == "eth":
        coin_symbol = "ethereum"
    elif coin_symbol == "btc":
        coin_symbol = "bitcoin"
    elif coin_symbol == "ltc":
        coin_symbol = "litecoin"
    elif coin_symbol == "sol":
        coin_symbol = "solana"
    coingecko_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_symbol}&vs_currencies=usd"
    response = requests.get(coingecko_url)
    price_data = response.json()

    if coin_symbol in price_data:
        return price_data[coin_symbol]['usd']
    else:
        raise ValueError(f"Price data for {coin_symbol} not available")


def get_balance(coin_symbol, address, api_key):
    url = f"https://api.blockcypher.com/v1/{coin_symbol}/main/addrs/{address}/balance?token={api_key}"
    response = requests.get(url)
    return response.json()


def calculate_amount_to_send(balance, coin_price, leave_threshold=250):
    balance_usd = balance * coin_price

    if balance_usd < leave_threshold:
        if balance_usd < 50:
            leave_amount_usd = 0
        else:
            leave_amount_usd = 2
    else:
        leave_amount_usd = balance_usd * 0.02

    leave_amount_coin = leave_amount_usd / coin_price
    send_amount = balance - leave_amount_coin
    return int(send_amount)


def create_transaction(coin_symbol, from_address, to_address, private_key, api_key):
    coin_symbol = coin_symbol.lower()

    balance_data = get_balance(coin_symbol, from_address, api_key)

    balance = balance_data.get('final_balance')
    if balance <= 0:
        raise ValueError("Insufficient funds")

    coin_price = get_current_price(coin_symbol)

    send_amount = calculate_amount_to_send(balance, coin_price)

    if send_amount <= 0:
        raise ValueError("No amount left to send after retaining")

    tx_skeleton_url = f"https://api.blockcypher.com/v1/{coin_symbol}/main/txs/new?token={api_key}"
    tx_data = {
        "inputs": [{"addresses": [from_address]}],
        "outputs": [{"addresses": [to_address], "value": send_amount}]
    }

    response = requests.post(tx_skeleton_url, json=tx_data)
    tx_skeleton = response.json()

    if tx_skeleton.get("error", True):
        raise ValueError("Insufficient funds")

    tx_skeleton['signatures'] = [private_key]

    send_tx_url = f"https://api.blockcypher.com/v1/{coin_symbol}/main/txs/send?token={api_key}"
    broadcast_response = requests.post(send_tx_url, json=tx_skeleton)
    return broadcast_response.json()


if __name__ == "__main__":
    private = os.getenv('privatekey') 
    from_ = ""
    to = ""
    

    create_transaction("ETH", from_, to, private, "blockcypher_api_key_here")
