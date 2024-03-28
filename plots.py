# for graphics
import matplotlib.pyplot as plt

def plot_stats(stats, CONFIG):
    fig, (action_bars, place_bars) = plt.subplots(ncols=1, nrows=2)

    fig.tight_layout(pad=5)

    actions, action_nums = stats["actions"].keys(), stats["actions"].values()

    tap_count = stats["actions"].get("Tap in", 0)+ stats["actions"].get("Tap out", 0) + stats["actions"].get("Transfer", 0)
    # subtract 1 for Customer Service Centre
    place_count = len(stats["place-breakdown"])-1

    load_count = stats["actions"].get("Loaded", 0)
    load_amount = stats["money"]["loaded"]

    spent_amount = stats["money"]["spent"]
    missed_count = stats["actions"].get("Missed Tap Out", 0)
    
    fig.text(x=0.05, y=0.85, s=f"You tapped {tap_count} times \nin {place_count} unique places\nand missed {missed_count} tap out(s) \
             \n\nYour card was loaded {load_count} times (${load_amount:.2f}) and \
             \nyou spent ${spent_amount:.2f} on fares")
    
    action_bars.bar(x=list(actions), height=list(action_nums))

    # bar chart of favourite places

    action_count_place_breakdown = {}

    for k, v in stats["place-breakdown"].items():
        for action, count in v.items():
            if action in ["Purchase", "Loaded"]:
                continue
            action_count_place_breakdown.setdefault(k, 0)
            action_count_place_breakdown[k] += count
    
    unsorted_counts = list(action_count_place_breakdown.values())
    sorted_counts = sorted(unsorted_counts, reverse=True)

    # magic don't ask :(
    sorted_labels = sorted(action_count_place_breakdown, reverse=True, key=action_count_place_breakdown.get)
    
    place_bars.bar(x=sorted_labels, height=sorted_counts)
    plt.xticks(rotation=90)
    plt.grid(visible=True, which="both", axis="y")

    plt.show()