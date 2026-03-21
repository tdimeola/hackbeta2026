import csv
import random

DATA_FILE = "data.csv"


class Character:
    def __init__(self, row):
        self.name = row['Name'].strip()
        self.power = float(row['Power'])
        self.strength = float(row['Strength'])
        self.magic = float(row['Magic'])
        self.intelligence = float(row['Intelligence'])
        self.speed = float(row['Speed'])
        self.defense = float(row['Defense'])
        self.poison = float(row['Poison'])
        self.rage = float(row['Rage'])
        self.corrupted = float(row['Corrupted'])
        self.evilness = float(row['Evilness'])
        self.age = float(row['Age'])
        self.personality = row['Personality'].strip()
        self.hometown = row['Hometown'].strip()
        self.favorite_color = row['Favorite_Color'].strip()
        self.weakness = row['Weakness'].strip()
        self.height = row['Height'].strip()
        self.weight = float(row['Weight'])
        self.is_villain = row['isVillain'].strip() == 'True'
        self.is_living = row['isLiving'].strip() == 'True'
        self.is_employed = row['isEmployed'].strip() == 'True'
        self.is_human = row['isHuman'].strip() == 'True'

        # Derived stats
        self.max_hp = int(50 + self.defense + self.strength * 0.5)
        self.hp = self.max_hp

    def attack_power(self):
        """Base attack: combination of power, strength, magic with some randomness."""
        base = (self.power * 0.4 + self.strength * 0.4 + self.magic * 0.2)
        variance = random.uniform(0.8, 1.2)
        return max(1, int(base * variance * 0.15))

    def defend(self):
        """Damage reduction from defense stat."""
        return int(self.defense * 0.1)

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, damage):
        actual = max(1, damage - self.defend())
        self.hp = max(0, self.hp - actual)
        return actual

    def weakness_bonus(self, attacker):
        """If attacker's personality or type exploits this character's weakness, return bonus multiplier."""
        weakness_lower = self.weakness.lower()
        if 'fire' in weakness_lower and attacker.rage > 70:
            return 1.5
        if 'ice' in weakness_lower and attacker.magic > 70:
            return 1.5
        if 'radiation' in weakness_lower and attacker.power > 70:
            return 1.5
        if 'soft heart' in weakness_lower and attacker.intelligence > 70:
            return 1.3
        if 'fear' in weakness_lower and attacker.evilness > 70:
            return 1.3
        return 1.0

    def hp_bar(self, width=20):
        filled = int((self.hp / self.max_hp) * width)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {self.hp}/{self.max_hp}"

    def summary(self):
        villain_tag = "VILLAIN" if self.is_villain else "HERO"
        return (f"{self.name} [{villain_tag}]\n"
                f"  HP: {self.hp_bar()}\n"
                f"  Power:{self.power:.0f} Str:{self.strength:.0f} "
                f"Magic:{self.magic:.0f} Spd:{self.speed:.0f} Def:{self.defense:.0f}\n"
                f"  Personality: {self.personality} | Weakness: {self.weakness}\n"
                f"  From: {self.hometown}")


def load_characters(filepath=DATA_FILE):
    heroes = []
    villains = []
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            try:
                char = Character(row)
                if char.is_villain:
                    villains.append(char)
                else:
                    heroes.append(char)
            except (ValueError, KeyError):
                continue  # skip malformed rows
    return heroes, villains


def get_boss(villains):
    """Boss = villain with highest combined evilness + power."""
    return max(villains, key=lambda v: v.evilness + v.power)


def get_enemies(villains, boss, count=3):
    """Random selection of non-boss villains for regular encounters."""
    pool = [v for v in villains if v.name != boss.name]
    return random.sample(pool, min(count, len(pool)))
