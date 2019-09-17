import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from os import environ

SHEET_NAME = 'price_tracker'  # Google Sheet Name
GAPP_PASSWD = environ.get('GAPP_PASSWD')  # Derive Google app password from Environment variable


def get_sheet():
    """ This method will Authorize the google drive and will fetch the Sheet"""
    SCOPE = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPE)
    gc = gspread.authorize(credentials)
    # Return the First sheet
    return gc.open(SHEET_NAME).sheet1


def get_request_soup(url):
    """ This method will fetch the request content from passed url and will return the soup element"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/76.0.3809.132 Safari/537.36"}
    # Get the Page value
    page_content = requests.get(url=url, headers=headers).content
    return BeautifulSoup(page_content, 'html.parser')


def get_amazon_price(url):
    """ This method will return the price details from Amazon"""
    soup = get_request_soup(url)
    soup.prettify()
    # Find the Item and Price
    item = soup.find(id='productTitle').get_text().strip()
    price = soup.find('span', {'id': "priceblock_ourprice"}).get_text().replace(',', '').strip().replace(' ', '')
    checked_price = 0
    # Check if it is a price range
    if "-" in price:
        print("Taking maximum price")
        checked_price = float(price[price.find('-') + 3:])
    else:
        checked_price = float(price[2:])

    # print("Item : {} - Price {}".format(item, checked_price))
    return item, checked_price


def get_myntra_price(url):
    """ This method will return the price details from Myntra"""
    soup = get_request_soup(url)
    soup.prettify()
    # print(soup)
    # Get the JSON block in the page having price details
    block = soup.findAll('script', {'type': 'application/ld+json'})[1]
    # Import json and extract the values
    import json
    json_value = json.loads(block.text)
    item = json_value["name"]
    price = json_value["offers"]["price"]
    brand = json_value["brand"]["name"]

    # print("Item : {} and its Price {}".format(item, price))
    return item, float(price), brand


def send_notification(to_email, item, url, new_price):
    """This method will send the Notification to the user"""
    if to_email is not None:
        import smtplib
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=60)
        server.set_debuglevel(1)

        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login("maindola.amit@gmail.com", GAPP_PASSWD)

        subject = "{}  - price has dropped !!!"
        body = "Hello, \nPrices for your Item : {} has dropped down. New price : {}, check the below link\n{" \
               "}\n\nThanks,\nAmit".format(
            item, new_price, url)
        msg = f"Subject: {subject}\n\n{body}"

        server.sendmail(to_email, msg)
        print("Notification sent successfully")
        server.quit()


def check_price():
    """ This method will access the google sheet and will fetch the details
            Item link will be used to fetch the details and then comparision will be made
            A notification will be sent to given email if price has dropped
     """
    # Get the Google Sheet having items information
    price_tracker = get_sheet()
    print("No. of rows in the sheet {}".format(len(price_tracker.get_all_records())))
    # Loop for each row in the sheet
    for i, row in enumerate(price_tracker.get_all_records()):
        # pprint(row)
        row_num = i + 2  # Add two, one for 0 index and then one for Header
        item_link = row['Item Link']
        desired_price = int(row['Desired Price'])
        item_name = checked_price = item_brand = ""
        if item_link is None:
            continue  # Skip if item link is not given
        # Check which brand details to be fetched
        if "myntra" in item_link:
            item_name, checked_price, item_brand = get_myntra_price(item_link)
        elif "amazon" in item_link:
            item_name, checked_price = get_amazon_price(item_link)
        else:
            exit(0)
        # Update the Last checked details
        now = datetime.today().strftime("%d-%b-%Y %I:%M %p")
        price_tracker.update_cell(row_num, 4, item_name)
        price_tracker.update_cell(row_num, 5, checked_price)
        price_tracker.update_cell(row_num, 6, now)
        print("Updated Row {} for item {} .".format(row_num, item_name))
        # Send notification if current price is less than the desired price
        if desired_price is not None and checked_price <= desired_price:
            send_notification(row['Notification To'], item_name, item_link, checked_price)


send_notification('maindola.amit@gmail.com', 'Item', 'www.amazon.com', 55)
# Check the price and update
# check_price()
