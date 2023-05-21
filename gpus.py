import datetime
import pprint
import re

import matplotlib.pyplot as plt
# import matplotlib.ticker
import requests
from bs4 import BeautifulSoup

import pypartpicker
from time import sleep

# from pcpartpicker import API

debug = False
region = 'us'  # 'us', 'ca', etc.
currency = 'USD$'  # 'USD$', 'CAD$', etc. Affects only labels.
limit = 100  # 20, 40, 60, 80, 100, etc. Affects speed, larger number is slower but less likely to miss a lower price.
table_N = 0  # 0 Regular, 1 Ray Tracing
column_N = 1  # 1, 2, 3, 4

columns = {
    1: '1080p Ultra',
    2: '1080p Medium',
    3: '1440p Ultra',
    4: '4K Ultra'
}


class Price:
    def __init__(self, price, currency='$USD'):
        self.price = price
        self.currency = currency

    def __str__(self):
        return ('Price(' +
                str(self.price) + ', ' +
                str(self.currency) +
                ')'
                )

    def __repr__(self):
        return self.__str__()

    def get(self, other_currency='$USD'):
        if self.currency == other_currency:
            return self.price
        else:
            return None  # TODO: implement currency conversion to estimate arbitrage opportunities
            # return (other_currency / self.currency) * self.price


class Gpu:
    def __init__(self, name, fps, prices=None):
        self.name = name
        self.fps = fps
        if prices is None:
            self.prices = []
        else:
            self.prices = prices
            self.prices.sort()

        self.marginal_fps_per_extra_dollar = 0  # based on previous best gpu
        self.bad = False

    def __str__(self):
        return ('Gpu(' +
                '\"' + str(self.name) + '\", ' +
                str(self.fps) + ', ' +
                str(self.prices) +
                ')'
                )

    def __repr__(self):
        return self.__str__()

    def best_price(self):
        if len(self.prices) == 0:
            return 0
        else:
            return min(self.prices)

    def fps_per_dollar(self):
        try:
            fps_per_dollar = self.fps / self.best_price()
        except ZeroDivisionError:
            fps_per_dollar = 0

        return fps_per_dollar

    def add_price(self, price):
        if price is not None:
            price = str(price)
            price = float(price.replace('$', ''))
            self.prices.append(price)
            self.prices.sort()


# AMD gpus from
# https://www.hardwaretimes.com/amd-radeon-rx-7900-xtx-offers-the-lowest-performance-dollar-rx-6800-xt-up-to-50-better/

gpus_example = [Gpu('RX7900XTX', 372, [999]),
                Gpu('RX7900XT', 355, [899]),
                Gpu('RX6950XT', 338, [699]),
                Gpu('RX6800XT', 328, [579]),
                Gpu('RX6800', 327, [499]),
                Gpu('RX6750XT', 277, [419]),
                Gpu('RX6700XT', 268, [369]),
                Gpu('RX6650XT', 208, [299]),
                Gpu('RX6600', 174, [249]),
                Gpu('RX6500XT', 126, [169]),
                Gpu('RX6400', 110, [129]),
                Gpu('-', 0)
                ]


def download_page(url):
    response = requests.get(url,
                            headers={"Cache-Control": "no-cache",
                                     "Pragma": "no-cache"})
    response.raise_for_status()
    return response.text


def parse(url):
    content = download_page(url)
    soup = BeautifulSoup(content, 'html.parser')

    table = soup.findAll('table')

    table_data = [[cell.text for cell in row("td")] for row in table[table_N]("tr")]

    parsed_gpus = []

    for row in table_data:
        if len(row) == 0:
            continue
        name = re.match(r'^[ \t\r\n\f]*(.*?)[ \t\r\n\f]*(\(.*\))?$', row[0]).group(1)

        try:
            fps = re.match(r'^.*\((\d*\.\d*)fps\)$', row[column_N]).group(1)  # eg. 1080p Ultra column
        except AttributeError:
            fps = 0
            continue
        # print(row)
        print((name, fps))
        parsed_gpus.append(Gpu(name=name, fps=float(fps)))

    return parsed_gpus


def pc_part_picker_2(parsed_gpus, region='us', limit=100):
    pcpp = pypartpicker.Scraper()

    for i, gpu in enumerate(parsed_gpus):
        # print(gpu)
        while True:
            try:
                parts = pcpp.part_search(gpu.name, region=region, limit=limit)  # 20 is 1 page
            except Exception as e:
                print(e)
                print("Retrying...")
                sleep(5)
            else:
                break

        for part in parts:
            if "Video Card" in part.name:
                # print(part.name, part.price)
                gpu.add_price(part.price)
            else:
                # print("Not a video card:", part.name, part.price)
                pass

        print(i, gpu)

        if i > 100:
            break

        # sleep(3)

    return parsed_gpus


def add_sale_prices_manually(gpus):
    for gpu in gpus:
        if region == "ca":
            if gpu.name == 'Radeon RX 7900 XT':
                gpu.add_price(1159)
                print('Added sale price for', gpu.name, gpu.best_price())

            if gpu.name == 'Radeon RX 6950 XT':
                gpu.add_price(955)
                print('Added sale price for', gpu.name, gpu.best_price())

            if gpu.name == 'Radeon RX 6750 XT':
                gpu.add_price(572)
                print('Added sale price for', gpu.name, gpu.best_price())

    return gpus


def clean_gpus(gpus):
    gpus_out = []

    for gpu in gpus:
        if gpu.best_price() > 0 and gpu.fps > 0:
            gpus_out.append(gpu)

    return gpus_out


def calculate_margin_gpus(gpus):
    # add zero
    gpus.append(Gpu('-', 0))

    # sort by price:
    gpus.sort(key=lambda gpu: gpu.best_price(), reverse=False)

    # calculate marginal fps per dollar
    previous_best_gpu = gpus[0]
    for gpu in gpus:
        try:
            gpu.marginal_fps_per_extra_dollar = (gpu.fps - previous_best_gpu.fps) / (
                    gpu.best_price() - previous_best_gpu.best_price())
        except ZeroDivisionError:
            gpu.marginal_fps_per_extra_dollar = 0

        if gpu.fps > previous_best_gpu.fps:
            previous_best_gpu = gpu
        else:
            if gpu != gpus[0]:
                print(str(gpu.name) + ' not better than previous best gpu: ' + str(previous_best_gpu.name))
                gpu.bad = True  # when price increases, fps must also increase, otherwise it is bad gpu

        print(gpu)

    return gpus


def remove_bad_gpus(gpus):
    gpus_out = []

    for gpu in gpus:
        if not gpu.bad:
            gpus_out.append(gpu)

    return gpus_out


def print_gpus(gpus):
    for gpu in gpus:
        print(gpu)


def plot(gpus=None, region='us', currency='$'):
    if gpus is None:
        gpus = gpus_example

    # use tkinter backend to plot the data
    plt.switch_backend('TkAgg')

    fig, ax1 = plt.subplots(figsize=(10, 10))  # create figure and axes
    # xticks must be before ax1.twinx()
    plt.xticks([gpu.best_price() for gpu in gpus], [gpu.name + ', ' + currency + str(gpu.best_price()) for gpu in gpus],
               rotation='vertical')

    ax2 = ax1.twinx()

    ax1.plot([gpu.best_price() for gpu in gpus], [gpu.fps for gpu in gpus], 'r+-')
    ax1.plot([], [], 'g+-')  # dummy plot to create a legend
    ax1.plot([], [], 'b+-')  # dummy plot to create a legend

    ax2.plot([gpu.best_price() for gpu in gpus], [gpu.fps_per_dollar() for gpu in gpus], 'g+-')
    ax2.plot([gpu.best_price() for gpu in gpus], [gpu.marginal_fps_per_extra_dollar for gpu in gpus], 'b+-')

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

    # header
    ax1.set_title(
        'Best GPUs money can buy, in ' + region.upper() + ', ' + currency + '. ' +
        'Suboptimal GPUs were omitted. ' +
        'Resolution: ' + columns[column_N] + '. ' +
        'Updated: ' + datetime.datetime.now().strftime("%Y-%m-%d") + '. '
    )

    fig.tight_layout()

    plt.show()


if __name__ == '__main__':
    if debug:
        print('Debug mode')
        print_gpus(gpus_example)
        plot()
    else:
        gpus = parse('https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html')
        gpus = pc_part_picker_2(gpus, region=region, limit=limit)
        gpus = add_sale_prices_manually(gpus)
        gpus = clean_gpus(gpus)
        gpus = calculate_margin_gpus(gpus)
        gpus = remove_bad_gpus(gpus)
        print_gpus(gpus)
        plot(gpus, region=region, currency=currency)
