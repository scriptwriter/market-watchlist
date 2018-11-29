from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

import boto
from boto.s3.key import Key
import json


mappings = json.loads(open("mappings.txt").read())
creds = json.loads(open("credentials.txt").read())

conn = boto.connect_s3(creds["access_key"], creds["secret_key"])

ENV = Environment(loader=FileSystemLoader('./templates'))
template = ENV.get_template('index.html')

soup = BeautifulSoup(open("/tmp/watchlist.txt"), "lxml")
items = soup.findAll('tr')
items.pop(0)

auto_2w, auto_4w, auto_ancillary = [], [], []
count = 0

for item in items:
    elements = item.findAll('td')

    stock_name = elements[1].text.strip().split(" ")[0]
    an_item = dict(stock_name=stock_name,
                   current_price=elements[2].text.strip(),
                   market_cap=elements[3].text.strip(),
                   debt=elements[4].text.strip(),
                   dividend=elements[5].text.strip(),
                   promoter=elements[6].text.strip(),
                   price_to_earnings=elements[7].text.strip(),
                   price_to_earnings_3yr=elements[8].text.strip(),
                   price_to_earnings_5yr=elements[9].text.strip(),
                   price_to_sales=elements[10].text.strip(),
                   return_on_equity=elements[11].text.strip(),
                   return_on_equity_3yr=elements[12].text.strip(),
                   return_on_equity_5yr=elements[13].text.strip(),
                   from_52w_high=elements[14].text.strip(),
                   from_52w_low=elements[15].text.strip()
                   )

    if stock_name in mappings["auto_2w"]:
        auto_2w.append(an_item)
    elif stock_name in mappings["auto_4w"]:
        auto_4w.append(an_item)
    elif stock_name in mappings["auto_ancillary"]:
        auto_ancillary.append(an_item)
    count += 1

html = template.render(data=[auto_2w, auto_4w, auto_ancillary], count=count)

with open('/tmp/index.html', 'w') as fh:
    fh.write(html)

# upload index.html to s3 bucket
bucket = conn.lookup('market-watchlist')
key = Key(bucket)
key.name = 'index.html'
key.set_contents_from_filename('/tmp/index.html')
