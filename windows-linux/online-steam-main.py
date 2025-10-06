from textual.app import App
from textual.widgets import Static, Input, ListView, ListItem, Label, Button
from textual.containers import Container
from textual import on
from asyncio import sleep
import requests
import os


class OnlineSteam(App):
    page_index = 0  # current page number for pagination
    page_size = 10  # how many games to show per page
    last_selected_name = None
    str_last_selected_appid = None

    CSS = """
        #game_input {
            border: wide round #983bbb;
            background: black;
        }
        
        #loading {
            dock: bottom;
            align: center bottom;
            padding: 1;
            color: yellow;
        }
        
        #lists_and_output {
            layout: horizontal;
            height: 100%;
            margin: 1;
        }
        
        #left_panel {
            layout: vertical;
            width: 50;
            margin-right: 1;
        }
        
        #page_buttons {
            layout: horizontal;
            width: 100%;
            height: 3;
            margin-bottom: 1;
        }
        
        #page_buttons Button:last-child {
            margin-left: 1;
        }
        
        #assumed_game_list {
            border: round #b55dd6;
            padding: 1;
            height: 14;
        }
        
        #fav_buttons {
            layout: horizontal;
            width: 100%;
            height: 3;
            margin-top: 1;
        }
        
        #fav_buttons Button {
            width: 1fr;
            margin-right: 1;
        }
        
        #fav_buttons Button:last-child {
            margin-right: 0;
        }
        
        #right_panel {
            layout: vertical;
            width: 1fr;
        }
        
        #output {
            border: round #9902d1;
            padding: 1;
            height: 7;
        }
        
        #favorites {
            border: round #55aaff;
            padding: 1;
            height: 10;
            margin-top: 1;
        }
    """

    def compose(self):
        # define UI layout and components
        yield Input(placeholder='Enter a game name...', id='game_input')
        yield Static("", id='loading')
        with Container(id="lists_and_output"):
            with Container(id="left_panel"):
                with Container(id="page_buttons"):
                    yield Button('Previous page', id='prev_page_btn', disabled=True)
                    yield Button('Next page', id='next_page_btn', disabled=True)
                assumed_list = ListView(id='assumed_game_list')
                assumed_list.border_title = 'Assumed'
                assumed_list.border_subtitle = 'min. 3 symbols'
                yield assumed_list
                with Container(id="fav_buttons"):
                    yield Button('Add to favorite', id='add_to_fav_btn', disabled=True)
                    yield Button('Delete from favorite', id='del_from_fav_btn', disabled=True, variant="error")
            with Container(id="right_panel"):
                output_label = Static('', id='output')
                output_label.border_title = 'Output'
                yield output_label
                favorites_list = ListView(id='favorites')
                favorites_list.border_title = 'Favorites'
                yield favorites_list

    def on_mount(self):
        # runs once app is ready, loads all games from API
        loading_label = self.query_one("#loading", Static)
        loading_label.update("Loading list of games...")
        # get the app list from Steam API
        self.app_list = self.get_app_list()
        loading_label.update(f"Loaded {len(self.app_list)} games (and not) successfully.")
        self.assumed_list_view = self.query_one('#assumed_game_list')
        self.update_favorites_list()

    def update_favorites_list(self):
        self.favorites_list_view = self.query_one('#favorites', ListView)
        self.favorites_list_view.clear()
        favorite_game_ids = self.read_favorites_from_file()
        for game_id in favorite_game_ids:
            game_name = self.get_name_by_appid(self.app_list, game_id)
            if game_name is not None:
                self.favorites_list_view.append(ListItem(Label(game_name)))

    def get_appid_by_name(self, apps, name):
        # search for appid by game name in the apps list
        for app in apps:
            if app['name'].lower() == name.lower():
                return app['appid']
        return None

    def get_name_by_appid(self, apps, appid):
        for app in apps:
            if str(app['appid']) == appid:
                return app['name']
        return None

    def get_app_list(self):
        # fetch list of all steam apps from official API
        app_list_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        app_list_response = requests.get(app_list_url)
        apps_data = app_list_response.json()
        return apps_data['applist']['apps']

    def get_player_count(self, appid):
        url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={appid}"
        response = requests.get(url)
        data = response.json()
        return data['response'].get('player_count')

    def display_player_count(self, selected_game, player_count):
        output_label = self.query_one("#output", Static)
        if player_count is not None:
            output_label.update(f'{selected_game} — {player_count} players online!')

    def get_and_display_player_count(self, selected_game):
        selected_appid = self.get_appid_by_name(self.app_list, selected_game)
        self.str_last_selected_appid = str(selected_appid)
        player_count = self.get_player_count(selected_appid)
        self.display_player_count(selected_game, player_count)

    def show_selected_game_players(self, event: ListView.Selected):
        selected_item = event.item
        selected_label = selected_item.query_one(Label)
        selected_game_name = selected_label.content
        self.last_selected_name = selected_game_name
        self.get_and_display_player_count(selected_game_name)

    def write_favorites_to_file(self, favorites):
        with open('favorites.txt', 'w') as favorites_file:
            for favorite in favorites:
                favorites_file.write(str(favorite))
                favorites_file.write('\n')

    def create_file_if_not_exists(self, filename):
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                pass
            return []

    def read_favorites_from_file(self):
        self.create_file_if_not_exists('favorites.txt')
        with open("favorites.txt", "r") as favorites_file:
            return favorites_file.read().splitlines()

    def render_page(self):
        # show current page of filtered apps in the listview
        next_button = self.query_one('#next_page_btn')
        prev_button = self.query_one('#prev_page_btn')
        next_button.disabled = False
        prev_button.disabled = True
        start = self.page_index * self.page_size
        end = start + self.page_size
        self.assumed_list_view.clear()
        for app in self.filtered_app_list[start:end]:
            self.assumed_list_view.append(ListItem(Label(app['name'], markup=False)))
        if not self.filtered_app_list[start:end]:
            self.assumed_list_view.append(ListItem(Label('No suggested games')))
        max_page = len(self.filtered_app_list) // self.page_size
        if self.page_index >= max_page:
            next_button.disabled = True
        if self.page_index >= 1:
            prev_button.disabled = False

    def write_debug(self, record):
        self.create_file_if_not_exists('debug.txt')
        with open('debug.txt', 'a') as debug_file:
            debug_file.write(record)
            debug_file.write('\n')

    @on(Input.Submitted)
    def handle_game_input_submitted(self, event: Input.Submitted):
        # triggered when user submits a game name in input
        output = self.query_one("#output", Static)
        user_game = event.value
        appid = self.get_appid_by_name(self.app_list, user_game)

        if appid is None:
            output.update(f'There is no such game with name: {user_game}.')
            return

        self.get_and_display_player_count(user_game)

    @on(Input.Changed)
    def on_game_input_changed(self, event: Input.Changed):
        # triggered when user types in input, filters games list if 3+ chars typed
        query = event.value
        if len(query) >= 3:
            self.page_index = 0
            self.filtered_app_list = [app for app in self.app_list if query.lower() in app['name'].lower()]
            self.render_page()
        else:
            button = self.query_one('#next_page_btn')
            button.disabled = True
            self.assumed_list_view.clear()

    @on(ListView.Selected)
    def handle_assumed_selected(self, event: ListView.Selected):
        # triggered when user selects game from filtered list
        if event.list_view.id != 'assumed_game_list':
            return

        self.show_selected_game_players(event)
        # ability to add a game to favorites/activation of the add to favorites button
        add_to_fav_btn = self.query_one('#add_to_fav_btn')
        add_to_fav_btn.disabled = False
        del_from_fav_btn = self.query_one('#del_from_fav_btn')
        del_from_fav_btn.disabled = True

    @on(ListView.Selected)
    def handle_favorite_selected(self, event: ListView.Selected):
        # triggered when user selects game from favorited games list
        if event.list_view.id != 'favorites':
            return

        self.show_selected_game_players(event)
        add_to_fav_btn = self.query_one('#add_to_fav_btn')
        add_to_fav_btn.disabled = True
        del_from_fav_btn = self.query_one('#del_from_fav_btn')
        del_from_fav_btn.disabled = False

    @on(Button.Pressed)
    async def handle_button_pressed(self, event: Button.Pressed):
        # handle next/previous page button clicks
        if event.button.id == 'next_page_btn':
            max_page = len(self.filtered_app_list) // self.page_size
            if self.page_index < max_page:
                self.page_index += 1
                self.render_page()
        elif event.button.id == 'prev_page_btn':
            if self.page_index > 0:
                self.page_index -= 1
                self.render_page()

        # handle add to favorite button clicks
        elif event.button.id == 'add_to_fav_btn':
            existing_games = [item.query_one(Label).content for item in self.favorites_list_view.children]
            add_to_fav_btn = self.query_one('#add_to_fav_btn')
            if self.last_selected_name in existing_games:
                original_label = add_to_fav_btn.label
                add_to_fav_btn.label = "Already added!"
                await sleep(1)
                add_to_fav_btn.label = original_label
            else:
                last_selected_name_id = self.get_appid_by_name(self.app_list, self.last_selected_name)
                favorite_games_ids = self.read_favorites_from_file()
                favorite_games_ids.append(last_selected_name_id)
                self.write_favorites_to_file(favorite_games_ids)
                self.favorites_list_view.append(ListItem(Label(self.last_selected_name)))

        elif event.button.id == 'del_from_fav_btn':
            del_from_fav_btn = self.query_one('#del_from_fav_btn')
            favorite_games_ids = self.read_favorites_from_file()
            if self.str_last_selected_appid in favorite_games_ids:
                favorite_games_ids.remove(self.str_last_selected_appid)
                self.write_favorites_to_file(favorite_games_ids)

            self.update_favorites_list()


if __name__ == '__main__':
    OnlineSteam().run()
