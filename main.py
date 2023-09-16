#!/bin/env -S poetry run python

import json
import datetime
import requests
import os
import interactions

if os.path.exists("config.json"):
    with open("config.json") as file:
        config = json.loads(file.read())
else:
    config = {
        "menu_id": os.environ["MENU_ID"],
        "location_id": os.environ["LOCATION_ID"],
        "where_am_i": os.environ["WHERE_AM_I"],
        "bot_token": os.environ["BOT_TOKEN"],
    }


def get_menu_data(query_day: str):
    base_url = "http://menus.sodexomyway.com/BiteMenu/MenuOnly?menuId={menu_id}&locationId={location_id}&whereami={where_am_i}&startDate={date}"

    # cache responses
    try:
        os.mkdir("cached")
    except FileExistsError:
        pass

    output = {}
    file_name = "cached/" + query_day.replace("/", "_") + ".json"
    if os.path.exists(file_name):
        # if data for today exists, just use that
        with open(file_name) as file:
            output = json.loads(file.read())
    else:
        # if no file for today exists, pull the data from sodexo
        response = requests.get(base_url.format(**config, date=query_day))
        if not response.ok:
            raise Exception  # TODO: make this error useful later
        html = response.text
        with open(file_name, "w+") as file:
            file.write(html)

        # this is a hack to pull the json data out of the html
        # TODO: make this less shit
        data = json.loads(
            html.split("<div id='nutData' data-schools='False' class='hide'>")[1].split(
                "</div>"
            )[0]
        )

        for menu in data:
            # if something goes wrong and we don't have a menu for today, raise an exception
            if menu == {}:
                raise Exception

            # clean up the menu data, sorting it first by meal and then by course
            clean_menu = {}
            for item in menu["menuItems"]:
                meal = item["meal"]
                course = item["course"]

                if meal not in clean_menu:
                    clean_menu[meal] = {}
                if course not in clean_menu[meal]:
                    clean_menu[meal][course] = []

                clean_menu[meal][course].append(
                    {
                        "name": item["formalName"],
                        "description": item["description"],
                    }
                )
            year, month, day = menu["date"].split("T")[0].split("-")
            date = f"{month}/{day}/{year}"
            if date == query_day:
                output = clean_menu

            with open(f"cached/{date.replace('/', '_')}.json", "w+") as file:
                file.write(json.dumps(clean_menu))

    return output


bot = interactions.Client()


@interactions.listen()
async def on_startup():
    print("Bot is ready!")


@interactions.slash_command(
    name="menu",
    description="Get today's menu",
    options=[
        interactions.SlashCommandOption(
            name="date",
            type=interactions.OptionType.STRING,
            description="Date to get the menu for in the format `MM/DD/YYYY`.",
            required=False,
        )
    ],
)
async def menu(ctx: interactions.SlashContext, date: str = ""):
    await ctx.defer()

    if date == "":
        today = datetime.datetime.now()
        date = f"{('0' + str(today.month))[-2:]}/{('0' + str(today.day))[-2:]}/{today.year}"

    data = get_menu_data(date)
    embed = interactions.Embed(
        f"Menu for {date}",
        description="Press a button to get started!",
        color="#184ed7",
    )
    # create a button for each meal
    buttons = interactions.spread_to_rows(
        *[
            interactions.Button(
                style=interactions.ButtonStyle.PRIMARY,
                label=x.lower(),
                custom_id=f"{date}.{x}",
            )
            for x in data
        ]
    )

    await ctx.send(embed=embed, components=buttons)


@interactions.listen()
async def button_pressed(event: interactions.events.ButtonPressed):
    ctx = event.ctx
    # get the button's info from its custom id
    custom_id = ctx.custom_id.split(".")
    date = custom_id[0]
    meal_name = custom_id[1]
    menu = get_menu_data(date)

    meal = menu[meal_name]

    if len(custom_id) == 2:
        # this branch runs when a meal button is pressed
        embed = interactions.Embed(
            f"Entrees for {date}'s {meal_name.lower()}",
            description="Press a button to get your menu!",
            color="#184ed7",
        )
        # add a button for each entree
        buttons = interactions.spread_to_rows(
            *[
                interactions.Button(
                    style=interactions.ButtonStyle.PRIMARY,
                    label=x.lower(),
                    custom_id=f"{date}.{meal_name}.{x}",
                )
                for x in meal
            ]
        )
        await ctx.send(embed=embed, components=buttons, ephemeral=True)
    elif len(custom_id) == 3:
        # this branch runs when a course button is pressed
        course_name = custom_id[2]
        course = meal[course_name]

        embed = interactions.Embed(
            f"{course_name.lower()} menu for {date}'s {meal_name.lower()}",
            color="#184ed7",
        )

        food_list = ""
        for food in course:
            food_list += f"- **{food['name']}**"
            if food["description"]:
                food_list += f" - *{food['description']}*"
            food_list += "\n"
        embed.description = food_list

        await ctx.send(embed=embed, ephemeral=True)


def main():
    bot.start(config["bot_token"])


if __name__ == "__main__":
    main()
