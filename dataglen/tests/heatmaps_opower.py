import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from django.utils.dateparse import parse_datetime
from matplotlib.dates import MonthLocator
from matplotlib.dates import AutoDateFormatter, DateFormatter

def plot_heat_map(X, Y, Z, name):
    fig, ax = plt.subplots()
    fig.set_size_inches(8,3)
    ax.grid(True)
    min_z, max_z = (min(Z), max(Z))
    cm = plt.cm.get_cmap('PuBuGn')
    sc = plt.scatter(X, Y, c=Z, vmin=min_z, marker='s', edgecolors='none', vmax=max_z, s=40, cmap=cm)
    plt.colorbar(sc)
    ax.set_ylim(0,24)
    ax.xaxis.set_major_locator(MonthLocator(interval = 1))
    ax.xaxis.set_major_formatter(DateFormatter('%m-%Y'))
    plt.savefig(name, dpi=600, format='pdf', frameon=False, pad_inches=0.04, bbox_inches='tight')


if __name__ == '__main__':
    # 2014-03-31 18:37:16+05:30,1732.515
    lines = open("Bala-AC-debug.txt").readlines()
    data = {}
    for line in lines:
        info = line.strip().split(",")
        date = parse_datetime(info[0])
        date = date.replace(minute=0, second=0, microsecond=0)
        try :
            data[date]+=float(info[1])
        except KeyError:
            data[date] = float(info[1])

    X = []
    Y = []
    Z = []

    for key in sorted(data.keys()):
        X.append(key)
        Y.append(key.hour)
        Z.append(data[key])

    plot_heat_map(X, Y, Z, "Bala-AC.pdf")
