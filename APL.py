from pFactor import getPFactorData


def APL():
    user = input("AniList username: ")

    def progress(current, total, message):
        print(f"\r[{current}/{total}] {message}", end='', flush=True)

    results = getPFactorData(user, progress_callback=progress)
    print()

    if not results:
        print("No anime found in planning list.")
        return

    print(f"\n{'#':>3} {'Title':<40} {'APL':>6} {'Score':>5} {'Eps':>4} {'Hours':>6} {'Relation'}")
    print("-" * 110)
    for i, anime in enumerate(results, 1):
        rel = anime.get('relation') or ''
        title = anime['title'][:39]
        print(f"{i:>3} {title:<40} {anime['APL']:>6} {anime['averageScore']:>5} {anime['episodes']:>4} {anime['watchTime']:>5}h {rel}")


if __name__ == '__main__':
    APL()
