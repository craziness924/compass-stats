# for graphics
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

def plot_stats(stats, show_plots, save_plots, output_file):
    fig, axes = plt.subplots(ncols=2, nrows=1, figsize=(16, 8), facecolor="#009ddc")
    
    earliest_time = min(list(stats["journeys"].keys())).split("T")[0]
    latest_time = max(list(stats["journeys"].keys())).split("T")[0]

    fig.suptitle(f"Compass Card Stats from {earliest_time} to {latest_time}", 
                 color="White", size=28, font="Liberation Sans", fontweight="bold")

    # recognize axes
    action_bars: Axes = axes[0]
    place_bars: Axes = axes[1]

    # setup font_dict for various titles
    subplot_title_font_dict = {
        "family": "sans serif",
        "color": "white",
        "weight": "bold",
        "size": 18
    }

    # calculate numbers to display in a text box
    actions, action_nums = stats["actions"].keys(), stats["actions"].values()

    tap_count = stats["actions"].get("Tap in", 0)+ stats["actions"].get("Tap out", 0) + stats["actions"].get("Transfer", 0)
    
    place_count = len(stats["place-breakdown"])

    load_count = stats["actions"].get("Loaded", 0)
    load_amount = stats["money"]["loaded"]

    spent_amount = stats["money"]["spent"]
    missed_count = stats["actions"].get("Missed Tap Out", 0)
    
    ab_bbox = action_bars.get_position()
    fig.text(x=ab_bbox.min[0]-0.089, y=ab_bbox.min[1], s=f"You tapped {tap_count} times in {place_count} unique places\nand missed {missed_count} tap out(s) \
             \n\nYour card was loaded {load_count} times (${load_amount:.2f}) and \
             \nyou spent ${spent_amount:.2f} on fares",
             fontdict={
                 "family": "sans serif",
                 "color": "black",
                 "weight": "bold",
                 "size": 14,
             }, bbox={
                 "facecolor": "white",
                 "edgecolor": "black",
                 "pad": 10
             })
    
    # depict number of actions broken down by action type
    action_bars.bar(x=list(actions), height=list(action_nums))
    action_bars.xaxis.label.set_backgroundcolor("white")
    action_bars.set_title("Action Breakdown", fontdict=subplot_title_font_dict)
    action_bars.grid(visible=True, which="both", axis="y")
    plt.xticks(rotation=45, ha="right")

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
    place_bars.set_title("Favourite Places by Action Count\n(excluding Purchasing and Loading)", fontdict=subplot_title_font_dict)
    place_bars.xaxis.label.set_fontsize(4.0)

    plt.xticks(rotation=90, ha="right")
    place_bars.grid(visible=True, which="both", axis="y")

    plt.tight_layout()

    if save_plots:
        plt.savefig(output_file+"-plot.png")
    if show_plots:
        plt.show()