from hero import load_characters, get_boss, get_enemies
from battle import do_battle


TREASURE = "🏆 THE INFINITY CODEX 🏆"


def print_header():
    print("\n" + "="*50)
    print("   ⚡ CODEVERSE: HERO BATTLE ⚡")
    print("   HackBeta 2026 — Into the Codeverse")
    print("="*50)


def pick_hero(heroes):
    print("\nChoose your hero:\n")
    # Show first 10 heroes for readability
    choices = heroes[:10]
    for i, h in enumerate(choices):
        print(f"  [{i+1}] {h.name}")
        print(f"      Power:{h.power:.0f} Str:{h.strength:.0f} "
              f"Magic:{h.magic:.0f} Def:{h.defense:.0f} Spd:{h.speed:.0f}")
        print(f"      Personality: {h.personality} | Weakness: {h.weakness}\n")

    while True:
        try:
            choice = int(input("Enter number: ")) - 1
            if 0 <= choice < len(choices):
                return choices[choice]
            print("Invalid choice, try again.")
        except ValueError:
            print("Enter a number.")


def main():
    print_header()

    print("\nLoading heroes and villains from the Codeverse...")
    heroes, villains = load_characters("data.csv")
    print(f"  {len(heroes)} heroes | {len(villains)} villains loaded.")

    boss = get_boss(villains)
    enemies = get_enemies(villains, boss, count=3)

    print(f"\n⚠️  INTEL: The boss villain is {boss.name} "
          f"(Evilness: {boss.evilness:.0f}, Power: {boss.power:.0f})")
    print(f"   Weakness: {boss.weakness}")
    print(f"   Defeat {len(enemies)} enemies to reach the boss!")

    player = pick_hero(heroes)
    print(f"\n✅ You chose: {player.name} from {player.hometown}!")
    print(f"   {player.summary()}")

    input("\nPress Enter to begin your adventure...")

    # Fight through enemies
    for i, enemy in enumerate(enemies):
        print(f"\n🌍 Encounter {i+1} of {len(enemies)}: {enemy.name} appears!")
        print(f"   {enemy.personality} villain from {enemy.hometown}")

        won = do_battle(player, enemy)
        if not won:
            print("\n💀 GAME OVER. The Codeverse falls to darkness.")
            print(f"   You were defeated by {enemy.name}.")
            return

        input("\nPress Enter to continue...")

    # Boss fight
    print(f"\n🔥 YOU HAVE REACHED THE BOSS: {boss.name}!")
    print(f"   {boss.summary()}")
    input("\nPress Enter to face the boss...")

    # Boss gets a HP boost
    boss.max_hp = int(boss.max_hp * 1.5)
    boss.hp = boss.max_hp

    won = do_battle(player, boss)

    if won:
        print("\n" + "="*50)
        print("🎉 YOU WIN! THE CODEVERSE IS SAVED!")
        print(f"   {player.name} has defeated {boss.name}!")
        print(f"\n   You have claimed the {TREASURE}")
        print("="*50)
    else:
        print("\n💀 GAME OVER. The boss was too powerful.")
        print(f"   {boss.name} now rules the Codeverse.")


if __name__ == "__main__":
    main()
