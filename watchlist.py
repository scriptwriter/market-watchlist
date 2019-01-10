from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

import boto
from boto.s3.key import Key
from boto.s3.connection import S3Connection
import json
import os
import requests
import sys

# download cookies.txt using the chrome browser plugin
WATCHLIST_URL = 'https://www.screener.in/watchlist/'
if len(sys.argv) > 1 and sys.argv[1] == 'portfolio':
    WATCHLIST_URL = 'https://www.screener.in/watchlist/2798/'

# print(len(sys.argv))
# print(WATCHLIST_URL)
# sys.exit(1)


WATCHLIST_LOC = '/tmp/watchlist.txt'
INDEX_PAGE_LOC = '/tmp/index.html'
S3_BUCKET = 'umarye.com'
SALES_NUMBERS_POS = (14, 17, 20, 23)
PROFIT_NUMBERS_POS = (122, 125, 128, 131)
HIGH_LOW_DIVIATION_PERC = 4

# download watchlist data from screener passing the cookie file
BASH_CMD = 'curl -s --cookie /Users/amit/Downloads/cookies.txt ' + WATCHLIST_URL + '>' + WATCHLIST_LOC
os.system(BASH_CMD)

mappings = json.loads(open("mappings.txt").read())
creds = json.loads(open("credentials.txt").read())
names = json.loads(open("names.json").read())
ratestar_urls = json.loads(open("screener_ratestar_map.json").read())

conn = boto.connect_s3(creds["access_key"], creds["secret_key"],
                       calling_format=boto.s3.connection.OrdinaryCallingFormat())

ENV = Environment(loader=FileSystemLoader('./templates'))
template = ENV.get_template('index.html')

soup = BeautifulSoup(open(WATCHLIST_LOC), "lxml")
items = soup.findAll('tr')
if len(items) > 0:
    items.pop(0)
else:
    print("Its time to download the cookies again.")
    sys.exit(0)

auto_2w, auto_4w, auto_ancillary, alcohol, bluechips, chemicals, electronics, fmcg, fastfood, materials, midcaps, misc, roofing, tyres, utilities, diagonistic = [
], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []


count = 0
count_52w_high = 0
count_52w_low = 0


def extract_qtr_numbers(soup, result_type='tblQtyCons'):
    qtr_sales_growth, qtr_profit_growth = [], []
    for i in SALES_NUMBERS_POS:
        qtr_sales_growth.append(soup.find("table", {"id": result_type}).find_all(
            "div", {"class": "float-lt in-tab-col2-2"})[i].contents[0].strip())
        # print(qtr_sales_growth)

    for j in PROFIT_NUMBERS_POS:
        qtr_profit_growth.append(soup.find("table", {"id": result_type}).find_all(
            "div", {"class": "float-lt in-tab-col2-2"})[j].contents[0].strip())
        # print(qtr_profit_growth)

    if len(set(qtr_sales_growth)) == 1:
        # return is used to break out of the recursion.
        # else the main function returns twice - onec from inside and then outside
        return extract_qtr_numbers(soup, 'tblQtyStd')

    # convert float string numbers to ints
    return [int(float(x.replace("%", ""))) if x != '-' else x for x in qtr_sales_growth], [int(float(x.replace("%", ""))) if x != '-' else x for x in qtr_profit_growth]


def convert_to_int(val):
    return int(float(val))


for item in items:
    elements = item.findAll('td')
    if len(elements) > 0:
        stock_name = elements[1].text.strip().split(" ")[0]
        if stock_name in names:
            stock_name = names[stock_name]
        print(stock_name)
        price_to_earnings_bg = "white"
        return_on_equity_bg = "white"
        price_to_earnings = convert_to_int(elements[7].text.strip())
        price_to_earnings_3y = convert_to_int(elements[8].text.strip())
        price_to_earnings_5y = convert_to_int(elements[9].text.strip())
        return_on_equity = convert_to_int(elements[11].text.strip())
        return_on_equity_3y = convert_to_int(elements[12].text.strip())
        return_on_equity_5y = convert_to_int(elements[13].text.strip())
        try:
            if price_to_earnings <= min(price_to_earnings_3y, price_to_earnings_5y):
                price_to_earnings_bg = "yellow"
            if return_on_equity >= max(return_on_equity_3y, return_on_equity_5y):
                return_on_equity_bg = "yellow"
        except:
            pass

        from_52w_high = float(elements[14].text.strip())
        from_52w_low = float(elements[15].text.strip())
        if from_52w_high <= HIGH_LOW_DIVIATION_PERC:
            from_52w_high = '52w HIGH'
            count_52w_high += 1
        if from_52w_low <= HIGH_LOW_DIVIATION_PERC:
            from_52w_low = '52w LOW'
            count_52w_low += 1

        # extract qtr nums from ratestar
        qtr_sales_growth = []
        qtr_profit_growth = []
        qtr_growth_bg = "white"
        if stock_name in ratestar_urls:
            resp = requests.get(ratestar_urls[stock_name])
            ratestar_soup = BeautifulSoup(resp.text, 'lxml')
            qtr_sales_growth, qtr_profit_growth = extract_qtr_numbers(ratestar_soup)
            try:
                if all(i >= 0 for i in qtr_sales_growth) and all(i >= 0 for i in qtr_profit_growth):
                    qtr_growth_bg = "yellow"
            except:
                # in case any of the numbers are strings like "-", give it a pass
                pass

        an_item = dict(stock_name=stock_name,
                       current_price=elements[2].text.strip(),
                       market_cap=elements[3].text.strip(),
                       debt=elements[4].text.strip(),
                       dividend=elements[5].text.strip(),
                       promoter=convert_to_int(elements[6].text.strip()),
                       price_to_earnings=str(price_to_earnings) +
                       ' ('+str(price_to_earnings_3y)+', ' + str(price_to_earnings_5y)+' )',
                       price_to_earnings_bg=price_to_earnings_bg,
                       price_to_sales=elements[10].text.strip(),
                       return_on_equity=str(return_on_equity) +
                       ' ('+str(return_on_equity_3y)+', ' + str(return_on_equity_5y)+')',
                       return_on_equity_bg=return_on_equity_bg,
                       from_52w_high=from_52w_high,
                       from_52w_low=from_52w_low,
                       peg=elements[16].text.strip(),
                       opm=elements[17].text.strip(),
                       qtr_sales_growth=qtr_sales_growth,
                       qtr_profit_growth=qtr_profit_growth,
                       qtr_growth_bg=qtr_growth_bg
                       )

        if stock_name in mappings["auto_2w"]:
            auto_2w.append(an_item)
        elif stock_name in mappings["auto_4w"]:
            auto_4w.append(an_item)
        elif stock_name in mappings["auto_ancillary"]:
            auto_ancillary.append(an_item)
        elif stock_name in mappings["bluechips"]:
            bluechips.append(an_item)
        elif stock_name in mappings["misc"]:
            misc.append(an_item)
        elif stock_name in mappings["fmcg"]:
            fmcg.append(an_item)
        elif stock_name in mappings["fastfood"]:
            fastfood.append(an_item)
        elif stock_name in mappings["electronics"]:
            electronics.append(an_item)
        elif stock_name in mappings["tyres"]:
            tyres.append(an_item)
        elif stock_name in mappings["materials"]:
            materials.append(an_item)
        elif stock_name in mappings["roofing"]:
            roofing.append(an_item)
        elif stock_name in mappings["utilities"]:
            utilities.append(an_item)
        elif stock_name in mappings["chemicals"]:
            chemicals.append(an_item)
        elif stock_name in mappings["midcaps"]:
            midcaps.append(an_item)
        elif stock_name in mappings["alcohol"]:
            alcohol.append(an_item)
        elif stock_name in mappings["diagonistic"]:
            diagonistic.append(an_item)
        count += 1

html = template.render(data=[bluechips, midcaps, fmcg, fastfood, alcohol, electronics, auto_2w, auto_4w, auto_ancillary, tyres, materials, roofing, utilities, chemicals, diagonistic, misc],
                       count=count, count_52w_high=count_52w_high, count_52w_low=count_52w_low)


with open(INDEX_PAGE_LOC, 'w') as fh:
    fh.write(html)

# upload index.html to s3 bucket=market-watchlist
bucket = conn.lookup(S3_BUCKET)
key = Key(bucket)
key.name = 'index.html'
key.set_contents_from_filename(INDEX_PAGE_LOC)
