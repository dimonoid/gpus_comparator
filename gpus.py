import pprint
import re

import matplotlib.pyplot as plt
import matplotlib.ticker
import requests
from bs4 import BeautifulSoup

from pcpartpicker import API


class Gpu:
    def __init__(self, name, price, fps):
        self.name = name
        self.price = price
        self.fps = fps
        try:
            self.fps_per_dollar = fps / price
        except ZeroDivisionError:
            self.fps_per_dollar = 0
        self.marginal_fps_per_extra_dollar = 0  # based on previous best gpu
        self.bad = False

    def __str__(self):
        return (str(self.name) + ' ' +
                str(self.price) + ' ' +
                str(self.fps) + ' ' +
                str(self.fps_per_dollar) + ' ' +
                str(self.marginal_fps_per_extra_dollar) + ' ' +
                str(self.bad)
                )


# AMD gpus from
# https://www.hardwaretimes.com/amd-radeon-rx-7900-xtx-offers-the-lowest-performance-dollar-rx-6800-xt-up-to-50-better/

gpus_example = [Gpu('RX7900XTX', 999, 372),
                Gpu('RX7900XT', 899, 355),
                Gpu('RX6950XT', 699, 338),
                Gpu('RX6800XT', 579, 328),
                Gpu('RX6800', 499, 327),
                Gpu('RX6750XT', 419, 277),
                Gpu('RX6700XT', 369, 268),
                Gpu('RX6650XT', 299, 208),
                Gpu('RX6600', 249, 174),
                Gpu('RX6500XT', 169, 126),
                Gpu('RX6400', 129, 110),
                ]


def main(gpus=None):
    if gpus is None:
        gpus = gpus_example

    # add zero
    gpus.append(Gpu('-', 0, 0))

    # sort by price:
    gpus.sort(key=lambda gpu: gpu.price, reverse=False)

    # calculate marginal fps per dollar
    previous_best_gpu = gpus[0]
    for gpu in gpus:
        try:
            gpu.marginal_fps_per_extra_dollar = (gpu.fps - previous_best_gpu.fps) / (
                    gpu.price - previous_best_gpu.price)
        except ZeroDivisionError:
            gpu.marginal_fps_per_extra_dollar = 0

        if gpu.fps > previous_best_gpu.fps:
            previous_best_gpu = gpu
        else:
            if gpu != gpus[0]:
                print(str(gpu.name) + ' not better than previous best gpu: ' + str(previous_best_gpu.name))
                gpu.bad = True  # when price increases, fps must also increase, otherwise it is bad gpu

        print(gpu)

    # use tkinter backend to plot the data
    plt.switch_backend('TkAgg')

    fig, ax1 = plt.subplots(figsize=(10, 10))  # create figure and axes
    # xticks must be before ax1.twinx()
    plt.xticks([gpu.price for gpu in gpus], [gpu.name + ', $' + str(gpu.price) for gpu in gpus], rotation='vertical')

    ax2 = ax1.twinx()

    ax1.plot([gpu.price for gpu in gpus], [gpu.fps for gpu in gpus], 'r+-')
    ax1.plot([], [], 'g+-')  # dummy plot to create a legend
    ax1.plot([], [], 'b+-')  # dummy plot to create a legend

    ax2.plot([gpu.price for gpu in gpus], [gpu.fps_per_dollar for gpu in gpus], 'g+-')
    ax2.plot([gpu.price for gpu in gpus], [gpu.marginal_fps_per_extra_dollar for gpu in gpus], 'b+-')

    ax1.legend(['FPS', 'FPS/$', 'Marginal FPS/$ (relative to previous best GPU)'], loc='upper left')

    ax1.set_xlabel('GPU, Price')
    ax1.set_ylabel('FPS')
    ax2.set_ylabel('FPS/$')

    # nticks = 11
    # ax1.yaxis.set_major_locator(matplotlib.ticker.LinearLocator(nticks))
    # ax2.yaxis.set_major_locator(matplotlib.ticker.LinearLocator(nticks))

    ax1.grid()
    # ax2.grid() # looks bad

    # ax1.set_ylim(bottom=0, top=400)  # modify this manually if needed, use top as number divisible by nticks-1
    # ax2.set_ylim(bottom=0, top=1)

    fig.tight_layout()

    plt.show()


def download_page(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def parse(url):
    content = download_page(url)
    soup = BeautifulSoup(content, 'html.parser')

    table = soup.findAll('table')

    table_data = [[cell.text for cell in row("td")] for row in table[0]("tr")]

    # with open('book_table.json', 'w') as storage_file:
    #    storage_file.write(json.dumps(result))

    parsed_gpus = []

    i = 2000

    for row in table_data:
        if len(row) == 0:
            continue
        name = re.match(r'^[ \t\r\n\f]*(.*)[ \t\r\n\f]+\(.*\)', row[0]).group(1)

        try:
            fps = re.match(r'^.*\((\d*\.\d*)fps\)', row[1]).group(1)
        except AttributeError:
            fps = 0
        # print(row)
        print((name, fps))
        parsed_gpus.append(Gpu(name, i, float(fps)))

        i -= 1

    return parsed_gpus


def pc_part_picker():
    api = API()
    api.set_region("us")
    gpu_data = api.retrieve("video-card", force_refresh=True)['video-card']
    # pprint.pprint(gpu_data)

    found = []

    unique_chipsets = set()
    for gpu in gpu_data:
        unique_chipsets.add(gpu.chipset)
        if "4090" in gpu.chipset:
            if gpu.price.amount.__float__() > 100:
                found.append(gpu)
                # found.append(Gpu(gpu.chipset, gpu.price.amount.__float__(), 0))

    # set to list and sort
    list_unique_chipsets = sorted(list(unique_chipsets), reverse=True)

    pprint.pprint(list_unique_chipsets)
    for gpu in found:
        pprint.pprint(gpu.__dict__)


if __name__ == '__main__':
    # pc_part_picker() # TODO fix this

    # parsed_gpus = parse('https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html')
    # main(parsed_gpus)

    main()
