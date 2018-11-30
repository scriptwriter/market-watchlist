from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

import boto
from boto.s3.key import Key
from boto.s3.connection import S3Connection
import json
import os

# download cookies.txt using the chrome browser plugin

WATCHLIST_LOC = '/tmp/watchlist.txt'
INDEX_PAGE_LOC = '/tmp/index.html'
S3_BUCKET = 'umarye.com'
# download watchlist data from screener passing the cookie file
BASH_CMD = 'curl -s --cookie /Users/amit/Downloads/cookies.txt "https://www.screener.in/watchlist/" >' + WATCHLIST_LOC
os.system(BASH_CMD)

mappings = json.loads(open("mappings.txt").read())
creds = json.loads(open("credentials.txt").read())
names = json.loads(open("names.json").read())

conn = boto.connect_s3(creds["access_key"], creds["secret_key"],
                       calling_format=boto.s3.connection.OrdinaryCallingFormat())

ENV = Environment(loader=FileSystemLoader('./templates'))
template = ENV.get_template('index.html')

soup = BeautifulSoup(open(WATCHLIST_LOC), "lxml")
items = soup.findAll('tr')
items.pop(0)

auto_2w, auto_4w, auto_ancillary, bluechips, chemicals, electronics, fmcg, fastfood, materials, midcaps, misc, roofing, tyres, utilities = [
], [], [], [], [], [], [], [], [], [], [], [], [], []
count = 0


def convert_to_int(val):
    return int(float(val))


for item in items:
    elements = item.findAll('td')
    if len(elements) > 0:
        stock_name = elements[1].text.strip().split(" ")[0]
        if stock_name in names:
            stock_name = names[stock_name]
        price_to_earnings_bg = "white"
        return_on_equity_bg = "white"
        price_to_earnings = convert_to_int(elements[7].text.strip())
        price_to_earnings_3y = convert_to_int(elements[8].text.strip())
        price_to_earnings_5y = convert_to_int(elements[9].text.strip())
        return_on_equity = convert_to_int(elements[11].text.strip())
        return_on_equity_3y = convert_to_int(elements[12].text.strip())
        return_on_equity_5y = convert_to_int(elements[13].text.strip())
        if price_to_earnings <= min(price_to_earnings_3y, price_to_earnings_5y):
            price_to_earnings_bg = "yellow"
        if return_on_equity >= max(return_on_equity_3y, return_on_equity_5y):
            return_on_equity_bg = "yellow"

        from_52w_high = float(elements[14].text.strip())
        from_52w_low = float(elements[15].text.strip())

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
                       from_52w_high='52w HIGH' if from_52w_high <= 2 else from_52w_high,
                       from_52w_low='52w LOW' if from_52w_low <= 2 else from_52w_low
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
        count += 1

html = template.render(data=[bluechips, midcaps, fmcg, fastfood, electronics, auto_2w, auto_4w, auto_ancillary, tyres, materials, roofing, utilities, chemicals, misc],
                       count=count)


with open(INDEX_PAGE_LOC, 'w') as fh:
    fh.write(html)

# upload index.html to s3 bucket=market-watchlist
bucket = conn.lookup(S3_BUCKET)
key = Key(bucket)
key.name = 'index.html'
key.set_contents_from_filename(INDEX_PAGE_LOC)
