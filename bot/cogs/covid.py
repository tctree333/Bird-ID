# covid.py | commands for data from the COVID-19 pandemic
# Copyright (C) 2019-2020  EraserBird, person_v1.32, hmmm

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import difflib

import requests
import discord
from discord.ext import commands

from bot.data import logger
from bot.functions import channel_setup, user_setup, CustomCooldown


class COVID(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_covid()

    def _request(self, endpoint, params=None):
        url = "https://coronavirus-tracker-api.herokuapp.com"
        response = requests.get(url + endpoint, params)
        response.raise_for_status()
        return response.json()

    def getLocations(self, rank_by: str = None, rank_amount: int = None):
        data = None
        world = [
            item
            for item in self._request("/v2/locations", {"source": "jhu"})["locations"]
            if not (item["country_code"] == "US" and "," in set(item["province"]))
        ]
        usa = self._request("/v2/locations", {"source": "csbs"})["locations"]
        for item in usa:
            item["province"] = f"{item['county']} County, {item['province']}"
        data = world + usa
        ranking_criteria = ["confirmed", "deaths", "recovered"]
        if rank_by is not None:
            if rank_by not in ranking_criteria:
                raise ValueError(
                    "Invalid ranking criteria. Expected one of: %s" % ranking_criteria
                )
            ranked = sorted(data, key=lambda i: i["latest"][rank_by], reverse=True)
            if rank_amount:
                data = ranked[:rank_amount]
            else:
                data = ranked
        return data

    def getLatest(self):
        data = self._request("/v2/latest")
        return data["latest"]

    def getCountryCode(self, country_code):
        if country_code == "US":
            data = self._request(
                "/v2/locations", {"source": "csbs", "country_code": country_code}
            )
        else:
            data = self._request(
                "/v2/locations", {"source": "jhu", "country_code": country_code}
            )
        if not data["locations"]:
            return None
        return data

    def getLocationById(self, country_id: int, us_county: bool = False):
        data = self._request(
            "/v2/locations/" + str(country_id), {"source": ("csbs" if us_county else "jhu")}
        )
        return data["location"]

    def update_covid(self):
        self.covid_location_ids = {
            f'{x["province"]}, {x["country_code"]}': x["id"]
            for x in self.getLocations()
        }

    def format_data(self, confirmed: int, died: int, recovered: int, location="Global"):
        embed = discord.Embed(
            title="COVID-19 Data:",
            description="Latest data on the COVID-19 pandemic.",
            type="rich",
            colour=discord.Color.blurple(),
        )
        embed.set_author(name="Bird ID - An Ornithology Bot")
        data = (
            f"**Confirmed Cases:** `{confirmed}`\n"
            + f"**Deaths:** `{died}` {f'*({round((died/confirmed)*100, 1)}%)*' if confirmed != 0 else ''}\n"
            + f"**Recovered:** `{recovered}` {f'*({round((recovered/confirmed)*100, 1)}%)*' if confirmed != 0 else ''}\n"
        )
        embed.add_field(name=location, value=data, inline=False)
        return embed

    def format_leaderboard(self, data, ranked):
        embed = discord.Embed(
            title="COVID-19 Top:",
            description="Latest data on the COVID-19 pandemic.",
            type="rich",
            colour=discord.Color.blurple(),
        )
        embed.set_author(name="Bird ID - An Ornithology Bot")
        for item in data:
            c, d, r = item["latest"].values()
            location = f'{(item["province"] + ", " if item["province"] else "")}{item["country"]}'
            data = (
                f"**Confirmed Cases:** `{c}`\n"
                + f"**Deaths:** `{d}`\n"
                + f"**Recovered:** `{r}`\n"
            )
            embed.add_field(name=location, value=data, inline=False)
        return embed

    # give data
    @commands.group(
        brief="- Gives updated info on the COVID-19 pandemic.",
        help="- Gives updated info on the COVID-19 pandemic. "
        + "This fetches data from ExpDev07's Coronavirus tracker API, "
        + "which fetches data from Johns Hopkins, with county data from CSBS. "
        + "More info: (https://github.com/ExpDev07/coronavirus-tracker-api)",
        aliases=["corona", "coronavirus", "covid19"],
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.default))
    async def covid(self, ctx):
        if ctx.invoked_subcommand is None:
            logger.info("command: covid")
            location = await commands.clean_content(
                fix_channel_mentions=True, use_nicknames=True, escape_markdown=True
            ).convert(ctx, " ".join(ctx.message.content.split(" ")[1:]))

            await channel_setup(ctx)
            await user_setup(ctx)
            await ctx.trigger_typing()

            if not location:
                c, d, r = self.getLatest().values()
                embed = self.format_data(c, d, r)
                await ctx.send(embed=embed)
                return

            if len(location) == 2:
                data = self.getCountryCode(location.upper())
                if data:
                    country = data["locations"][0]["country"]
                    await ctx.send(f"Fetching data for location `{country}`.")

                    c, d, r = data["latest"].values()
                    embed = self.format_data(c, d, r, country)
                    await ctx.send(embed=embed)
                    return

            location_matches = difflib.get_close_matches(
                location, self.covid_location_ids.keys(), n=1, cutoff=0.4
            )
            if location_matches:
                await ctx.send(f"Fetching data for location `{location_matches[0]}`.")
                location_id = self.covid_location_ids[location_matches[0]]
                us_county = location_matches[0].split(", ")[-1] == "US" and location_matches[0].count(",") == 2
                c, d, r = self.getLocationById(location_id, us_county)["latest"].values()
                embed = self.format_data(c, d, r, location_matches[0])
                await ctx.send(embed=embed)
                return
            else:
                await ctx.send(f"No location `{location}` found.")
                return

    # top countries
    @covid.command(
        brief="- Gets locations with the most cases",
        help="- Gets locations with the most cases. "
        + "This fetches data from ExpDev07's Coronavirus tracker API, "
        + "which fetches data from Johns Hopkins, with county data from CSBS. "
        + "More info: (https://github.com/ExpDev07/coronavirus-tracker-api)",
        aliases=["leaderboard"],
    )
    async def top(self, ctx, ranking: str = "confirmed", amt: int = 3):
        logger.info("command: covid top")

        await channel_setup(ctx)
        await user_setup(ctx)
        await ctx.trigger_typing()
        
        if amt > 10:
            await ctx.send("**Invalid amount!** Defaulting to 10.")
            amt = 10
        if amt < 1:
            await ctx.send("**Invalid amount!** Defaulting to 1.")
            amt = 1

        if ranking in ("confirmed", "confirm", "cases", "c"):
            ranking = "confirmed"
        elif ranking in ("deaths", "death", "dead", "d"):
            ranking = "deaths"
        elif ranking in ("recovered", "recover", "better", "r"):
            ranking = "recovered"
        else:
            await ctx.send("Invalid argument!")
            return

        data = self.getLocations(ranking, amt)
        embed = self.format_leaderboard(data, ranking)

        await ctx.send(embed=embed)

    # update data
    @covid.command(
        brief="- Updates data.",
        help="- Updates data. "
        + "This fetches data from ExpDev07's Coronavirus tracker API, "
        + "which fetches data from Johns Hopkins, with county data from CSBS. "
        + "More info: (https://github.com/ExpDev07/coronavirus-tracker-api)",
    )
    @commands.check(CustomCooldown(3600.0, bucket=commands.BucketType.default))
    async def update(self, ctx):
        logger.info("command: update_covid")

        await channel_setup(ctx)
        await user_setup(ctx)

        await ctx.trigger_typing()
        self.update_covid()

        await ctx.send("Ok, done!")


def setup(bot):
    bot.add_cog(COVID(bot))
