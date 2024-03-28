# for graphics
import matplotlib.pyplot as plt

def plot_stats(stats, CONFIG):
    fig, ax = plt.subplots(ncols=1, nrows=1)

    fig.tight_layout(pad=10)

    actions, action_nums = stats["actions"].keys(), stats["actions"].values()

    tap_count = stats["actions"].get("Tap in", 0)+ stats["actions"].get("Tap out", 0) + stats["actions"].get("Transfer", 0)
    place_count = len(stats["place-breakdown"])

    load_count = stats["actions"].get("Loaded", 0)
    load_amount = stats["money"]["loaded"]

    spent_amount = stats["money"]["spent"]
    missed_count = stats["actions"].get("Missed Tap Out", 0)
    
    fig.text(x=0.05, y=0.75, s=f"You tapped {tap_count} times \nin {place_count} unique places\nand missed {missed_count} tap out(s) \
             \n\nYour card was loaded {load_count} times (${load_amount:.2f}) and \
             \nspent ${spent_amount:.2f} on fares")
    plt.pie(action_nums, labels=actions)


    plt.show()