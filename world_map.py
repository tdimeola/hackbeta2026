from ursina import *
from ursina.prefabs.button import Button
import random


class LocationNode(Button):
    def __init__(self, character, position, on_click_callback, **kwargs):
        # Convert hex color string to Ursina color
        hex_str = character.favorite_color.replace('0x', '').replace('#', '')
        try:
            r = int(hex_str[0:2], 16) / 255
            g = int(hex_str[2:4], 16) / 255
            b = int(hex_str[4:6], 16) / 255
            node_color = color.rgb(r, g, b)
        except Exception:
            node_color = color.gray

        super().__init__(
            model='circle',
            color=node_color,
            scale=0.06,
            position=position,
            highlight_color=color.white,
            **kwargs
        )

        self.character = character
        self.on_click_callback = on_click_callback
        self.visited = False
        self.locked = False
        self.original_color = node_color

        # Label below node
        self.label = Text(
            text=character.name,
            position=position + Vec3(0, -0.07, 0),
            scale=0.7,
            color=color.white,
            origin=(0, 0)
        )

        # Villain marker
        if character.is_villain:
            self.villain_marker = Text(
                text='☠',
                position=position + Vec3(0.05, 0.05, 0),
                scale=1.2,
                color=color.red,
                origin=(0, 0)
            )
        else:
            self.villain_marker = None

    def on_click(self):
        if not self.visited and not self.locked:
            self.on_click_callback(self.character, self)

    def mark_visited(self):
        self.visited = True
        self.color = color.gray
        self.label.color = color.dark_gray
        if self.villain_marker:
            self.villain_marker.color = color.dark_gray

    def lock(self):
        self.locked = True
        self.color = color.black
        self.label.color = color.dark_gray

    def unlock_boss(self):
        self.locked = False
        # Pulse red for boss
        self.color = color.red
        self.label.color = color.red
        self.label.text = f"⚡ {self.character.name} ⚡"


class WorldMap(Entity):
    def __init__(self, characters, player, on_location_selected, on_boss_ready):
        super().__init__()

        self.player = player
        self.on_location_selected = on_location_selected
        self.on_boss_ready = on_boss_ready
        self.map_nodes = []
        self.visits = 0
        self.visits_needed = 4  # fights before boss unlocks
        self.boss_node = None

        # Background
        self.bg = Entity(
            model='quad',
            color=color.rgb(10, 10, 30),
            scale=(2, 1),
            z=1
        )

        # Title
        self.title = Text(
            text='⚡ CODEVERSE WORLD MAP ⚡',
            position=(-0, 0.45),
            scale=1.5,
            color=color.yellow,
            origin=(0, 0)
        )

        # Player info
        self.player_info = Text(
            text=self._player_text(),
            position=(-0.85, 0.4),
            scale=0.8,
            color=color.cyan,
            origin=(-0.5, 0)
        )

        # Status text
        self.status = Text(
            text=f'Visit {self.visits_needed} locations to unlock the boss!',
            position=(0, -0.45),
            scale=0.9,
            color=color.orange,
            origin=(0, 0)
        )

        # Legend
        Text(text='☠ = Villain   ● = Hero/Ally   GRAY = Visited',
             position=(0, -0.48), scale=0.7, color=color.light_gray, origin=(0, 0))

        # Place nodes — scatter across screen
        self._place_nodes(characters)

    def _player_text(self):
        return (f"HERO: {self.player.name}\n"
                f"HP: {self.player.hp}/{self.player.max_hp}\n"
                f"From: {self.player.hometown}")

    def _place_nodes(self, characters):
        # Separate boss from others
        from hero import get_boss
        villains = [c for c in characters if c.is_villain]
        non_boss = [c for c in characters if not c.is_villain]

        boss = get_boss(villains)
        others = [c for c in characters if c.name != boss.name]

        # Shuffle and pick 12 locations
        random.shuffle(others)
        locations = others[:12]

        # Grid layout — 4 columns x 3 rows
        cols = 4
        rows = 3
        x_start = -0.6
        y_start = 0.3
        x_gap = 0.4
        y_gap = 0.25

        for i, char in enumerate(locations):
            col = i % cols
            row = i // cols
            x = x_start + col * x_gap + random.uniform(-0.03, 0.03)
            y = y_start - row * y_gap + random.uniform(-0.02, 0.02)

            node = LocationNode(
                character=char,
                position=Vec3(x, y, 0),
                on_click_callback=self._location_clicked
            )
            self.map_nodes.append(node)

        # Boss node — bottom center, locked
        self.boss_node = LocationNode(
            character=boss,
            position=Vec3(0, -0.35, 0),
            on_click_callback=self._boss_clicked
        )
        self.boss_node.lock()
        self.map_nodes.append(self.boss_node)

    def _location_clicked(self, character, node):
        node.mark_visited()
        self.visits += 1
        self.player_info.text = self._player_text()

        remaining = self.visits_needed - self.visits
        if remaining > 0:
            self.status.text = f'{remaining} more location(s) until the boss unlocks!'
        else:
            self.status.text = '⚡ THE BOSS HAS BEEN UNLEASHED! ⚡'
            self.status.color = color.red
            self.boss_node.unlock_boss()

        self.on_location_selected(character, node)

    def _boss_clicked(self, character, node):
        if self.visits >= self.visits_needed:
            self.on_boss_ready(character, node)

    def destroy_map(self):
        for node in self.map_nodes:
            destroy(node.label)
            if node.villain_marker:
                destroy(node.villain_marker)
            destroy(node)
        destroy(self.bg)
        destroy(self.title)
        destroy(self.player_info)
        destroy(self.status)
        destroy(self)

    def update_player_info(self):
        self.player_info.text = self._player_text()
