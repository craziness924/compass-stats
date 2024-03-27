# for graphics
import matplotlib.pyplot as plt

def plot_stats(stats):
    fig, ax = plt.subplots(ncols=1, nrows=1)
    
    actions, action_nums = stats["actions"].keys(), stats["actions"].values()
    
    fig.text(x=0.1, y=0.9, s=f"You tapped {421} times \nin \n{52} unique places")
    plt.pie(action_nums, labels=actions)
    plt.show()