import asyncio
import json
import os
import random
import string
import traceback
import qrcode
import discord
import requests
from discord import  Embed
from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv
from blockcypher import get_address_overview, generate_new_address, simple_spend, get_address_details
from crypto.utils import create_transaction

load_dotenv()


TOKEN = os.getenv('BOT_TOKEN')
BLOCKCYPHER_KEY = os.getenv('BLOCKCYPHER_KEY')
MM_CHANNEL = int(os.getenv('MM_CHANNEL'))

intents = discord.Intents.all()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


def generate_wallet(coin_type: str) -> dict | None:
    try:
        print(coin_type)
        a = generate_new_address(api_key=BLOCKCYPHER_KEY, coin_symbol=coin_type.lower())
        a["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if coin_type.lower() == "eth":
            a["address"] = "0x" + a["address"]

        file_name = f"data/wallets_{coin_type}.json"

        try:
            with open(file_name, 'r') as file:
                wallets = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            wallets = []

        wallets.append(a)

        with open(file_name, 'w') as file:
            json.dump(wallets, file, indent=4)

        return a
    except:
        return None


def generate_random_string(length=5):
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def create_qr_code(wallet_address):
    folder_path = "temp"
    file_name = generate_random_string(7) + ".png"

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    file_path = os.path.join(folder_path, file_name)

    qr = qrcode.make(
        data=wallet_address
    )

    qr.save(file_path)
    return file_path, file_name


def remove_image(file_path: str) -> bool:
    try:
        os.remove(file_path)
        return True
    except:
        return False


def parse_type(t: str) -> str:
    """

    :param t: Type of cryptocurrency.
    :return: Short version of cryptocurrency in upper letters
    """
    t = t.lower()
    if t == "bitcoin":
        return "BTC"
    elif t == "ethereum":
        return "ETH"
    elif t == "litecoin":
        return "LTC"
    elif t == "solana":
        return "SOL"
    return "-"


def get_crypto_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': 'bitcoin,ethereum,litecoin,solana',
        'vs_currencies': 'usd'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        prices = {
            'BTC': data['bitcoin']['usd'],
            'ETH': data['ethereum']['usd'],
            'LTC': data['litecoin']['usd'],
            'SOL': data['solana']['usd']
        }

        return prices
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, _, interaction: discord.Interaction):
        await interaction.response.send_message(content="Channel deleted.")
        await interaction.channel.delete()



async def create_private_channel(interaction, topic):
    guild = interaction.guild
    member = interaction.user
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(view_channel=True)
    }
    channel_name = f"ticket-{generate_random_string()}"

    channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites, topic=f"Private {topic} Channel")
    return channel


class RoleSelectionView(discord.ui.View):
    def __init__(self, message, t):
        super().__init__()
        self.sender = None  # Tracks the user who selected "Sending"
        self.receiver = None  # Tracks the user who selected "Receiving"
        self.message = message  # The message to be updated with roles
        self.t = t

    @discord.ui.button(label="Sending", style=discord.ButtonStyle.primary)
    async def sending(self, _: discord.ui.Button, interaction: discord.Interaction):
        if self.receiver == interaction.user:
            await interaction.response.send_message(content="You can't select both roles. Please reset and try again.", ephemeral=True)
            return
        if self.sender is None or self.sender == interaction.user:
            self.sender = interaction.user
        await self.update_message(interaction)

    @discord.ui.button(label="Receiving", style=discord.ButtonStyle.primary)
    async def receiving(self, _: discord.ui.Button, interaction: discord.Interaction):
        if self.sender == interaction.user:
            await interaction.response.send_message(content="You can't select both roles. Please reset and try again.", ephemeral=True)
            return

        if self.receiver is None or self.receiver == interaction.user:
            self.receiver = interaction.user
        await self.update_message(interaction)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset(self, _: discord.ui.Button, interaction: discord.Interaction):
        self.sender = None
        self.receiver = None
        await self.update_message(interaction)

    async def update_message(self, interaction):
        await interaction.response.defer()

        embed5 = discord.Embed(
            title="Role Assignment",
            description="Select one of the following buttons that corresponds to your role in this deal. Once selected, both user must confirm to proceed.",
            color=discord.Color.green()
        )

        if self.sender:
            embed5.add_field(name=f"Sending {self.t}", value=self.sender.mention, inline=True)
        else:
            embed5.add_field(name=f"Sending {self.t}", value="`None`", inline=True)
        if self.receiver:
            embed5.add_field(name=f"Receiving {self.t}", value=self.receiver.mention, inline=True)
        else:
            embed5.add_field(name=f"Receiving {self.t}", value="`None`", inline=True)

        await self.message.edit(embed=embed5)

        if self.sender and self.receiver:
            embed6 = discord.Embed(
                title="Confirm Roles",
            )
            embed6.add_field(name=f"Sender", value=self.sender.mention, inline=True)
            embed6.add_field(name=f"Receiver", value=self.receiver.mention, inline=True)
            embed6.set_footer(text="Selecting the wrong role can result in getting scammed.")

            msg = await interaction.channel.send(embed=embed6)
            confirmation_view = ConfirmationView(self.sender, self.receiver, self.message, msg, self.t)
            await msg.edit(view=confirmation_view)


class ConfirmationView2(discord.ui.View):
    def __init__(self, sender, receiver, msg, amount, t):
        super().__init__()
        self.sender = sender
        self.receiver = receiver
        self.sender_confirmed = False
        self.receiver_confirmed = False
        self.msg = msg
        self.amount = amount
        self.t = t

    @discord.ui.button(label="Correct", style=discord.ButtonStyle.success)
    async def confirm(self, _: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()

        if interaction.user == self.sender:
            self.sender_confirmed = True

        if interaction.user == self.receiver:
            self.receiver_confirmed = True

        if self.sender_confirmed and self.receiver_confirmed:
            await self.msg.edit(view=None)
            conv = parse_type(self.t)

            created_wallet = generate_wallet(conv)
            if not created_wallet:
                embed = discord.Embed(
                    title="Error",
                    description="The bot has had an error. Please contact the support team.",
                    color=discord.Color.red()
                )
                await interaction.channel.send(embed=embed)
                return

            wallet_addr = created_wallet["address"]

            qr_path, filename = create_qr_code(wallet_addr)

            embed = discord.Embed(
                title="📝 Deal Summary",
                description="Refer to this deal summary for any reaffirmations. Notify staff for any support required.",
                color=0xffffff
            )
            embed.add_field(name="Sender", value=self.sender.mention, inline=True)
            embed.add_field(name="Receiver", value=self.receiver.mention, inline=True)
            embed.add_field(name="Amount", value=f"`${self.amount} USD`", inline=True)
            embed.add_field(name="Coin", value=f"{self.t}", inline=False)
            await interaction.channel.send(embed=embed)

            await interaction.channel.send(content=self.sender.mention)

            file = discord.File(qr_path, filename=os.path.basename(qr_path))
            embed = discord.Embed(
                title="📩 Payment Invoice",
                description=f"{self.sender.mention} Send the funds as part of the deal to the Middleman address specified below. Please copy the amount provided.",
                color=0xffffff
            )
            embed.set_thumbnail(url=f"attachment://{filename}")
            prices = get_crypto_prices()

            to_send_crypto = self.amount / prices[conv]

            embed.add_field(name="Address", value=f"`{wallet_addr}`")
            embed.add_field(name="Amount", value=f"`{to_send_crypto}` {conv} (${self.amount} USD)")
            embed.set_footer(text=f"Exchange rate: 1 {conv} ≈ ${prices[conv]} USD")

            await interaction.channel.send(embed=embed, files=[file])

            remove_image(qr_path)

            embed = discord.Embed(
                title="",
                description="Awaiting transaction...",
                color=0xffffff
            )
            msg = await interaction.channel.send(embed=embed)

            while True:
                real_amount = 99999
                break
                o = get_address_details(created_wallet["address"], api_key=BLOCKCYPHER_KEY, coin_symbol=conv.lower())
                real_amount = 0
                if conv.lower() == "btc" or conv.lower() == "ltc":
                    real_amount = o["balance"] / 100_000_000
                elif conv.lower() == "eth":
                    real_amount = o["balance"] / 10**18

                if real_amount >= to_send_crypto:
                    break

                if o["txrefs"]:
                    embed = discord.Embed(
                        title="Partial Transaction Received",
                        description="Only a part of the needed crypto has been received. Still waiting till the amount has been reached.",
                        color=discord.Color.yellow()
                    )
                    embed.add_field(name="Current Amount", value=f"`{real_amount}` {conv}")
                    embed.add_field(name="Needed Amount", value=f"`{to_send_crypto}` {conv}")
                    embed.add_field(name="Difference", value=f"`{to_send_crypto - real_amount}` {conv}", inline=False)
                    await msg.edit(embed=embed)

                await asyncio.sleep(30)

            embed = discord.Embed(
                title="Full Transaction Received",
                description="The transaction has been received. All funds are stored securely on our side.",
                color=discord.Color.green()
            )
            await interaction.channel.send(content=self.receiver.mention, embed=embed)

            embed = discord.Embed(
                title="Closing of Deal",
                description="Please click below that the deal is finished.",
            )
            embed.add_field(name="Current Amount", value=f"`{real_amount}` {conv}")
            embed.add_field(name="Needed Amount", value=f"`{to_send_crypto}` {conv}")

            await msg.delete()

            msg2 = await interaction.channel.send(embed=embed)
            view = ConfirmationView3(self.sender, self.receiver, msg2, self.t, created_wallet)

            await msg2.edit(view=view)



    @discord.ui.button(label="Incorrect", style=discord.ButtonStyle.danger)
    async def incorrect(self, _: discord.ui.Button, interaction: discord.Interaction):
        await self.msg.delete()

        embed7 = discord.Embed(
            title="Error",
            description="Couldn't confirm the amount. Please reopen the ticket and try again."
        )
        await interaction.channel.send(embed=embed7)


class ConfirmationView4(discord.ui.View):
    def __init__(self, sender, receiver, msg, t, created_wallet, selected_wallet):
        super().__init__()
        self.sender = sender
        self.receiver = receiver
        self.msg = msg
        self.t = t
        self.created_wallet = created_wallet
        self.selected_wallet = selected_wallet

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def confirm(self, _: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()

        if interaction.user == self.receiver:
            embed = discord.Embed(
                title="Thank you",
                description="You should receive your funds shortly."
            )
            await interaction.followup.send(embed=embed)
            await self.msg.edit(view=None)

            try:
                ouput_transaction = create_transaction(parse_type(self.t), self.created_wallet["address"], self.selected_wallet, self.created_wallet["private"], BLOCKCYPHER_KEY)
                print(ouput_transaction)
            except:
                print(traceback.format_exc())
                embed = discord.Embed(
                    title="Error",
                    description="We couldn't transfer your funds safely. Please contact the support team for help. This is an error on our side.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)


    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def incorrect(self, _: discord.ui.Button, interaction: discord.Interaction):
        def check(m):
            return m.author == self.receiver and m.channel == interaction.channel

        await interaction.response.send_message(content="Please resend your wallet down below.")

        msg = await bot.wait_for('message', check=check)
        wallet_addr = msg.content

        embed = discord.Embed(
            title="Check Address",
            description=f"{self.receiver.mention} Is this your wallet? Please confirm below."
        )
        embed.add_field(name="Wallet Address", value=f"`{wallet_addr}`")
        msg2 = await interaction.channel.send(embed=embed)
        view = ConfirmationView4(self.sender, self.receiver, msg2, self.t, self.created_wallet, wallet_addr)
        await msg2.edit(view=view)


class ConfirmationView3(discord.ui.View):
    def __init__(self, sender, receiver, msg, t, created_wallet):
        super().__init__()
        self.sender = sender
        self.receiver = receiver
        self.sender_confirmed = False
        self.receiver_confirmed = False
        self.msg = msg
        self.t = t
        self.created_wallet = created_wallet

    @discord.ui.button(label="Done", style=discord.ButtonStyle.success)
    async def confirm(self, _: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()

        if interaction.user == self.sender:
            self.sender_confirmed = True

        if interaction.user == self.receiver:
            self.receiver_confirmed = True

        if self.sender_confirmed and self.receiver_confirmed:
            await self.msg.edit(view=None)

            def check(m):
                return m.author == self.receiver and m.channel == interaction.channel

            embed = discord.Embed(
                title="Wallet Address",
                description="Please enter your wallet address where the funds should be sent to."
            )
            await interaction.followup.send(content=f"{self.receiver.mention}", embed=embed)

            msg = await bot.wait_for('message', check=check)
            wallet_addr = msg.content

            embed = discord.Embed(
                title="Check Address",
                description=f"{self.receiver.mention} Is this really your wallet? Please check below."
            )
            embed.add_field(name="Wallet Address", value=f"`{wallet_addr}`")
            msg2 = await interaction.channel.send(embed=embed)
            view = ConfirmationView4(self.sender, self.receiver, msg2, self.t, self.created_wallet, wallet_addr)
            await msg2.edit(view=view)



    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def incorrect(self, _: discord.ui.Button, interaction: discord.Interaction):
        # await self.msg.edit(view=None)
        await interaction.response.defer()

        embed7 = discord.Embed(
            title="Error",
            description="Couldn't finish the deal. Please contact staff for further support."
        )
        await interaction.channel.send(embed=embed7)


class ConfirmationView(discord.ui.View):
    def __init__(self, sender, receiver, old_msg, msg, t):
        super().__init__()
        self.sender = sender
        self.receiver = receiver
        self.sender_confirmed = False
        self.receiver_confirmed = False
        self.msg = msg
        self.old_msg = old_msg
        self.t = t

    @discord.ui.button(label="Correct", style=discord.ButtonStyle.success)
    async def confirm(self, _: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()

        if interaction.user == self.sender:
            self.sender_confirmed = True

        if interaction.user == self.receiver:
            self.receiver_confirmed = True

        if self.sender_confirmed and self.receiver_confirmed:
            await self.msg.edit(view=None)
            await self.old_msg.edit(view=None)

            def check(m):
                return m.author == self.sender and m.channel == interaction.channel

            embed = discord.Embed(
                title="Deal Amount",
                description="Please state the amount the bot is excepted to receive in USD (eg. 100.59)"
            )
            await interaction.followup.send(content=f"{self.sender.mention}", embed=embed)

            final_amount = None
            for _ in range(5):
                try:
                    msg = await bot.wait_for('message', check=check, timeout=60 * 5)
                    try:
                        amount = float(msg.content)
                        final_amount = amount
                        break
                    except:
                        embed_f = discord.Embed(
                            title="Error",
                            description="Invalid amount provided. Please try again.",
                            color=discord.Color.red()
                        )
                        await interaction.channel.send(embed=embed_f)
                        continue
                except:
                    embed_f = discord.Embed(
                        title="Error",
                        description="You didn't respond in time. You have 5 minutes. Please reopen a ticket.",
                        color=discord.Color.red()
                    )
                    return await interaction.channel.send(embed=embed_f)

            if not final_amount:
                embed_f = discord.Embed(
                    title="Error",
                    description="You have provided no valid amount. Please reopen a ticket and try again.",
                    color=discord.Color.red()
                )
                return await interaction.channel.send(embed=embed_f)

            final_amount = round(final_amount, 2)

            embed = discord.Embed(
                title="Amount Confirmation",
                description="Confirm that the bot will receive the following USD value. Both the sender and the have to confirm.",
                color=discord.Color.green()
            )
            embed.add_field(name="Amount", value=f"`${final_amount}`")
            msg = await interaction.channel.send(embed=embed)
            view = ConfirmationView2(self.sender, self.receiver, msg, final_amount, self.t)
            await msg.edit(view=view)

    @discord.ui.button(label="Incorrect", style=discord.ButtonStyle.danger)
    async def incorrect(self, _: discord.ui.Button, interaction: discord.Interaction):
        await self.msg.delete()

        embed7 = discord.Embed(
            title="Error",
            description="Couldn't confirm the roles. Please reset the role assignment and try again."
        )
        await interaction.channel.send(embed=embed7)


async def init_channel(channel: discord.TextChannel, user: discord.User, t, interaction):
    await channel.send(content=f"{user.mention}", delete_after=1)

    embed1 = discord.Embed(
        title="Cryptocurrency Middleman system",
        description=f"> {t} Middleman request created successfully!\n\nWelcome to our automated Middleman system! Your cryptocurrency will be stored securely for the duration of this deal. Please notify support for assistance.",
        color=discord.Color.green()
    )
    embed1.set_footer(text=f"Ticket: {channel.name}")
    await channel.send(embed=embed1)

    embed2 = discord.Embed(
        title="Security Notification",
        description="Out bot and staff team will __NEVER__ direct message you. Ensure all conversations related to the deal are done within this ticket. Failure to do so may put you at risk of being scammed.",
        color=discord.Color.red()
    )
    await channel.send(embed=embed2, view=CloseTicketView())

    embed3 = discord.Embed(
        title="Who are you dealing with?",
        description="eg. @user\neg. 123456789123456789"
    )

    await channel.send(embed=embed3)

    def check(m):
        return m.author == user and m.channel == channel

    final_partner = None

    for _ in range(5):
        try:
            msg = await bot.wait_for('message', check=check, timeout=60*5)
            partner_inp = msg.content
            print(partner_inp)
            partner = discord.utils.get(interaction.guild.members, mention=partner_inp)
            print(partner)
            if not partner:
                partner = discord.utils.get(interaction.guild.members, id=int(partner_inp))
                print(partner)
                if not partner:
                    embed_f = discord.Embed(
                        title="Error",
                        description="The provided partner doesn't exist. Please retry.",
                        color=discord.Color.red()
                    )
                    await channel.send(embed=embed_f)
                    continue

                final_partner = partner
                break
            final_partner = partner
            break
        except:
            embed_f = discord.Embed(
                title="Error",
                description="You didn't respond in time. You have 5 minutes. Please reopen a ticket.",
                color=discord.Color.red()
            )
            return await channel.send(embed=embed_f)

    if not final_partner:
        embed_f = discord.Embed(
            title="Error",
            description="You didn't respond correctly. You have 5 tries. Please reopen a ticket.",
            color=discord.Color.red()
        )
        return await channel.send(embed=embed_f)

    overwrite = discord.PermissionOverwrite(view_channel=True)
    await channel.set_permissions(final_partner, overwrite=overwrite)

    embed4 = discord.Embed(
        title=None,
        description=f"Successfully added {final_partner.mention} to the ticket.",
        color=discord.Color.green()
    )
    await channel.send(embed=embed4)

    embed5 = discord.Embed(
        title="Role Assignment",
        description="Select one of the following buttons that corresponds to your role in this deal. Once selected, both user must confirm to proceed.",
        color=discord.Color.green()
    )
    embed5.add_field(name=f"Sending {t}", value="`None`", inline=True)
    embed5.add_field(name=f"Receiving {t}", value="`None`", inline=True)

    msg2 = await channel.send(embed=embed5)
    await msg2.edit(view=RoleSelectionView(message=msg2, t=t))


class CryptoSelectionView(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bitcoin"),
            discord.SelectOption(label="Ethereum"),
            discord.SelectOption(label="Litecoin"),
            discord.SelectOption(label="Solana"),
        ]
        super().__init__(placeholder="Make a selection", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_method = self.values[0]

        m = await create_private_channel(interaction, selected_method)

        embed = discord.Embed(
            title=f"Payment Method: {selected_method}",
            description=f"You have selected **{selected_method}** as your payment method. Your ticket has been created: {m.mention}",
            color=discord.Color.blue()
        )

        if selected_method == "Bitcoin":
            embed.set_thumbnail(url="https://cryptologos.cc/logos/bitcoin-btc-logo.png?v=035")
        elif selected_method == "Ethereum":
            embed.set_thumbnail(url="https://cryptologos.cc/logos/ethereum-eth-logo.png?v=035")
        elif selected_method == "Litecoin":
            embed.set_thumbnail(url="https://cryptologos.cc/logos/litecoin-ltc-logo.png?v=035")
        elif selected_method == "Solana":
            embed.set_thumbnail(url="https://cryptologos.cc/logos/solana-sol-logo.png?v=035")

        embed.set_footer(text="Thank you for your selection", icon_url=interaction.user.avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await init_channel(m, interaction.user, selected_method, interaction)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    channel = bot.get_channel(MM_CHANNEL)
    if channel:

        embed = Embed(
            title="Cryptocurrency",
            description="__Fees:__\nDeals $250+: 2%\nDeals under $250: 2$\n__Deals under $50 are **FREE**__\n\nPress the dropdown below to select and initiate a deal involving either **Bitcoin**, **Ethereum**, **Litecoin** or **Solana**.",
            color=discord.Color.green()
        )

        new_view = discord.ui.View()
        new_view.add_item(CryptoSelectionView())

        await channel.send(embed=embed, view=new_view)
    else:
        print(f"Channel with ID {MM_CHANNEL} not found.")


@bot.slash_command(name="recover", description="[ADMIN ONLY] Recovery Command")
@commands.has_permissions(administrator=True)
async def recover(ctx):
    await ctx.defer()

    embed = discord.Embed(
        title="Not Implemented",
        description="This command has not been implemented yet.",
        color=discord.Color.red()
    )
    await ctx.followup.send(embed=embed)


@recover.error
async def recover_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond(
            embed=discord.Embed(
                title="Permission Denied",
                description="You do not have permission to use this command.",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return

    await ctx.respond(
        embed=discord.Embed(
            title="Error",
            description="An error occurred using this command.",
            color=discord.Color.red()
        ),
        ephemeral=True
    )


bot.run(TOKEN)
