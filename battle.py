import random


def do_battle(player, enemy, log=None):
    """
    Run a single turn-based battle between player and enemy.
    Returns True if player wins, False if player loses.
    log: optional list to append battle messages to
    """
    if log is None:
        log = []

    def msg(text):
        log.append(text)
        print(text)

    msg(f"\n{'='*50}")
    msg(f"⚔️  BATTLE: {player.name} vs {enemy.name}")
    msg(f"{'='*50}")
    msg(f"{player.name}: {player.hp_bar()}")
    msg(f"{enemy.name}: {enemy.hp_bar()}")

    round_num = 1

    while player.is_alive() and enemy.is_alive():
        msg(f"\n--- Round {round_num} ---")

        # Player attacks enemy
        base_dmg = player.attack_power()
        bonus = enemy.weakness_bonus(player)
        if bonus > 1.0:
            msg(f"💥 You exploit {enemy.name}'s weakness ({enemy.weakness})!")
        damage = int(base_dmg * bonus)
        actual = enemy.take_damage(damage)
        msg(f"➤ {player.name} attacks {enemy.name} for {actual} damage!")
        msg(f"  {enemy.name}: {enemy.hp_bar()}")

        if not enemy.is_alive():
            break

        # Enemy attacks player
        base_dmg = enemy.attack_power()
        bonus = player.weakness_bonus(enemy)
        if bonus > 1.0:
            msg(f"⚠️  {enemy.name} exploits your weakness ({player.weakness})!")
        damage = int(base_dmg * bonus)
        actual = player.take_damage(damage)
        msg(f"➤ {enemy.name} attacks {player.name} for {actual} damage!")
        msg(f"  {player.name}: {player.hp_bar()}")

        # Poison chance based on poison stat
        if random.randint(1, 100) < enemy.poison * 0.1:
            poison_dmg = random.randint(2, 8)
            player.hp = max(0, player.hp - poison_dmg)
            msg(f"☠️  Poison! {player.name} takes {poison_dmg} poison damage!")
            msg(f"  {player.name}: {player.hp_bar()}")

        round_num += 1

        # Safety valve — prevent infinite loops
        if round_num > 50:
            msg("⏱️  Battle timed out — it's a draw!")
            return False

    if player.is_alive():
        msg(f"\n🏆 {player.name} WINS!")
        # Partial HP restore between battles
        heal = int(player.max_hp * 0.3)
        player.hp = min(player.max_hp, player.hp + heal)
        msg(f"💊 Recovered {heal} HP. HP: {player.hp_bar()}")
        return True
    else:
        msg(f"\n💀 {player.name} has been defeated...")
        return False
