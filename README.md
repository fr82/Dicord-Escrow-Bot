# Crypto Middleman Bot

![Crypto Middleman Bot](https://img.shields.io/badge/version-1.0-blue.svg) 

## Overview

The **Crypto Middleman Bot** is an automated Discord bot designed to facilitate cryptocurrency transactions for BTC, SOL, ETH, and LTC. This bot acts as a middleman between users, allowing them to trade and transact with ease while ensuring secure and seamless exchanges.

## Features
- Accepts major cryptocurrencies: Bitcoin (BTC), Solana (SOL), Ethereum (ETH), and Litecoin (LTC).
- Automated transaction management.
- User-friendly commands for managing transactions.
- Secure and reliable operation.
- Programmed in OOP-style, so it's easier to read / understand
- All created wallets get saved for easy access and problem solvage

## Getting Started

### Prerequisites

Before you begin, ensure you have the following:

- A Discord account.
- Python (> 3.6) installed
- A valid cryptocurrency wallet for each supported currency.

### Installation

1. Open the directory:

   ```bash
   cd Crypto-MM
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your Discord bot token and any other necessary configurations:

   ```plaintext
   BOT_TOKEN=your_discord_bot_token
   ```
   Now you need to set the channel, where the inital embed is sent:
   ```plaintext
   MM_CHANNEL=channel_id
   ```
   Now you need to configure your BlockCypher api key. Generate your account [here](https://accounts.blockcypher.com/) and get your key [here](https://accounts.blockcypher.com/tokens)
   ```plaintext
   BLOCKCYPHER_KEY=your_key
   ```
   Lastly set your wallet addresses, where the fees will be sent to:
   ```plaintext
    FEE_RECIPIENT_BTC=
    FEE_RECIPIENT_ETH=
    FEE_RECIPIENT_LTC=
    FEE_RECIPIENT_SOL=
   ```

### Running the Bot

To start the bot, run the following command:

```bash
python3 main.py
```

## Commands

Here are some commands you can use with the bot:
- **/recover** - [Not implemented yet] Recovers all previous exchanges. Admin Only.

## Usage
The bot sends the inital embed in the channel you provided in the config. Users then can choose from there. The rest of the process should be known to you.