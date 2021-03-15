import re

import gspread
# from os import environ, path
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
# from google.auth.transport.requests import Request
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from oauth2client.service_account import ServiceAccountCredentials
# import pickle
from fake_useragent import UserAgent
import ast

SHEET_NAME = 'price_tracker'  # Google Sheet Name
GAPP_PASSWD = os.environ.get('GAPP_PASSWD')  # Derive Google app password from Environment variable
USER_AGENT_HDR = None


def get_sheet():
    """ This method will Authorize the google drive and will fetch the Sheet"""
    # scopes = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
    #           "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

    # # The file token.pickle stores the user's access and refresh tokens, and is
    # # created automatically when the authorization flow completes for the first
    # # time.
    # creds = None
    # if os.path.exists('token.pickle'):
    #     with open('token.pickle', 'rb') as token:
    #         creds = pickle.load(token)
    # # If there are no (valid) credentials available, let the user log in.
    # if not creds or not creds.valid:
    #     if creds and creds.expired and creds.refresh_token:
    #         creds.refresh(Request())
    #     else:
    #         flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    #         creds = flow.run_local_server(port=0)
    #     # Save the credentials for the next run
    #     with open('token.pickle', 'wb') as token:
    #         pickle.dump(creds, token)

    # service = build('sheets', 'v4', credentials=creds)

    # sheet = service.spreadsheets()

    # credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, SCOPES)
    # gc = gspread.authorize(credentials)

    from google.auth.exceptions import RefreshError
    # Credentials will be referred from %APPDATA%/gspread/credentials.json
    # User interaction will be asked for the first time after that it will be stored in authorized_user.json
    auth_file = os.path.join(os.getenv('APPDATA'), 'gspread','authorized_user.json')
    gc = None
    try:
        gc = gspread.oauth()
    except RefreshError as e:
        # remove auth file and re-authorize
        print("Re-Authorizing the credentials ...")
        os.remove(auth_file)
        gc = gspread.oauth()

    print('User authorized.')
    # Return the First sheet
    return gc.open(SHEET_NAME).sheet1


def get_ua_hdr():
    """Create Fake user agent and its header"""
    global USER_AGENT_HDR
    if USER_AGENT_HDR is None:
        ua = UserAgent()
        hdr = {'User-Agent': ua.random,
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
               'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
               'Accept-Encoding': 'none',
               'Accept-Language': 'en-US,en;q=0.8',
               'Connection': 'keep-alive'}
        USER_AGENT_HDR = hdr
    return USER_AGENT_HDR


def save_soup(soup_content, filename="output.html"):
    """Save the soup content to HTML file"""
    with open(filename, "w", encoding="utf-8") as file:
        file.write(str(soup_content))


def get_tag_json(block):
    """ 
    This method will return the json content of the tag as JSON object. 
    Many tags have JSON as string in them 
    """
    text = block.decode()
    start, end = text.find('{'), text.rfind('}')
    # Import json and extract the values
    import json
    json_value = json.loads(text[start:end + 1])
    return json_value


def get_request_soup(url, use_agent=False):
    """ This method will fetch the request content from passed url and will return the soup element"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/76.0.3809.132 Safari/537.36"}
    url_hdr = headers 

    # Check if use fake agent is to be used, saves time
    if use_agent:
        url_hdr = get_ua_hdr()
    page_content = requests.get(url=url, headers=url_hdr).content
    return BeautifulSoup(page_content, 'html.parser')

def clean_price(price):
    checked_price = price
    # Check if it is a price range
    if "-" in price:
        checked_price = float(price[price.find('-') + 3:])
    # else:
    #     checked_price = float(price[2:])
    
    checked_price = re.sub('[^0-9\.]', '', price) # remove any chars except numbers

    return float(checked_price)

def get_amazon_price(url):
    """ This method will return the price details from Amazon"""
    soup = get_request_soup(url)
    soup.prettify()
    # save_soup(soup, 'amazon_item.html') # Save output to html for debugging purpose
    
    # Find the Item and Price
    item = soup.find(id='productTitle').get_text().strip()
    price = soup.find('span', {'id': "priceblock_ourprice"}).get_text().replace(',', '').strip().replace(' ', '')
    checked_price = clean_price(price)
    brand = soup.find(id='bylineInfo').get_text().split(':')[1].strip()

    item_dp = soup.find(id='imgTagWrapperId').find('img')['data-a-dynamic-image']
    item_dp = list(ast.literal_eval(item_dp).keys())[0]


    # print("Item : {} - Price {}".format(item, checked_price))
    return item, checked_price, brand, item_dp


def get_myntra_price(url):
    """ This method will return the price details from Myntra"""
    soup = get_request_soup(url)
    soup.prettify()
    # save_soup(block, 'myntra_item.html') # Save output to html for debugging purpose
    
    # Get the JSON block in the page having all attributes
    block = soup.findAll('script', {'type': 'application/ld+json'})[1]
    json_value = get_tag_json(block)
    item, dp_link, price, brand = json_value["name"], json_value['image'], json_value["offers"]["price"], json_value["brand"]["name"]
    price=clean_price(price)

    # print("Item : {} and its Price {}".format(item, price))
    return item, float(price), brand, dp_link


def get_decathlon_price(url):
    """ This method will return the price details from Decathlon"""
    soup = get_request_soup(url)
    soup.prettify()
    # save_soup(soup, 'decathlon.html') # Save output to html for debugging purpose

    # derive attributes - price
    block = soup.body.find('span', {'class': 'price_tag'})
    price = re.sub('[^0-9\.]', '', block.get_text())
    # derive other information - others
    block = soup.body.find(id='__next').findAll('script', {'type': 'application/ld+json'})[1]
    json_value = get_tag_json(block)
    item, dp_link, brand = json_value['name'], json_value['image'][0], json_value['brand']['name']

    # print("Item : {} - {} and its Price {}".format(brand, item, price))
    return item, float(price), brand, dp_link


def get_flipkart_price(url):
    """ This method will return the price details from Flipkart"""
    soup = get_request_soup(url)
    soup.prettify()
    
    # save_soup(soup, 'flipkart.html') # Save output to html for debugging purpose

    # derive attributes
    blocks = ast.literal_eval(soup.find(id='jsonLD').decode_contents())
    block = blocks[0]
    item, dp_link, brand = blocks[0]['name'], blocks[0]['image'], blocks[0]['brand']['name']
    price = 0

    # print("Item : {} - {} and its Price {}".format(brand, item, price))
    return item, float(price), brand, dp_link


def get_ajio_price(url):
    """ This method will return the price details from Decathlon"""
    soup = get_request_soup(url)
    soup.prettify()
    # save_soup(soup) # Save output to html for debugging purpose

    # Get the JSON block in the page having price details
    item = soup.find(id='product_title').get_text().strip()
    price = soup.find('div', {'class': 'product-price'}).get_text().replace(',', '').strip().replace(' ', '')
    brand = soup.find('span', {'class': 'mtitle'}).get_text().strip().replace(' ', '')


def send_notification(to_email, item, item_url,
                      old_price, new_price,
                      item_dp=None):
    """This method will send the Notification to the user
    @param to_email: Receiver's email address
    @param item: Item name
    @param item_url: Item URL
    @param old_price: Old price of the item
    @param new_price: New price of the item
    @param item_dp: Item Display Picture url
    """
    if to_email is not None:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        sender = "maindola.amit@gmail.com"
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=60)
            # server.set_debuglevel(1)  # Uncomment to debug
            # handshake
            server.ehlo()
            server.starttls()
            server.ehlo()
            # Login to the server
            server.login(sender, GAPP_PASSWD)
            # form the message
            message = MIMEMultipart("alternative")
            message["subject"] = "{}  - price has dropped !!!".format(item)
            message["from"] = sender
            message["to"] = to_email
            # Create the text and HTML version of your message
            message_html = f"""\
            <html>
                <body>
                    Hello Subscriber,<br><br>
                    One item in Item in you Wishlist is now available at <b>{new_price}</b> <del>{old_price}</del>.<br>
                    <a href={item_url}>
                        <img alt='{item}' src='{item_dp}' height='300px' width='300px'></img>
                        <br><b><i>{item}</i></b>
                    </a>
                    <br><br>Thanks,<br>Amit Maindola
                    <br><b>Note : This is a system generated email, please do not respond</b>
                </body>
            <html>
            """
            
            # save_soup(message_html, 'mail.html') # Save output to html for debugging purpose

            message.attach(MIMEText(message_html, "html"))
            server.sendmail(sender, to_email, message.as_string())
            print("Notification sent successfully")
            
        except Exception as e:
            # Print any exception TODO
            raise Exception(f"Error while sending notification : {e}. Item : '{item}', new_price: {new_price}")
        finally:
            server.quit()


def check_price():
    """ This method will access the google sheet and will fetch the details
            Item link will be used to fetch the details and then comparision will be made
            A notification will be sent to given email if price has dropped
     """
    # Get the Google Sheet having items information
    price_tracker = get_sheet()
    all_records = price_tracker.get_all_records()
    print(f"No. of rows in the sheet {len(all_records)}")

    # Loop for each row in the sheet
    for i, row in enumerate(all_records):
        # pprint(row)
        row_num = i + 2  # Add two, one for 0 index and then one for Header
        item_link = row['Item Link']
        desired_price = int(row['Desired Price'])
        orignal_price = row['Orignal Price']
        item_name = checked_price = item_brand = itme_dp_link = ""

        if item_link is None:
            continue  # Skip if item link is not given

        try:
            # Check which brand details to be fetched
            if "myntra" in item_link:
                item_name, checked_price, item_brand, itme_dp_link = get_myntra_price(item_link)
            elif "amazon" in item_link:
                item_name, checked_price, item_brand, itme_dp_link = get_amazon_price(item_link)
            elif "decathlon" in item_link:
                item_name, checked_price, item_brand, itme_dp_link = get_decathlon_price(item_link)
            elif "flipkart" in item_link:
                item_name, checked_price, item_brand, itme_dp_link = get_decathlon_price(item_link)
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
                send_notification(row['Notification To'], item_name, item_link, orignal_price, checked_price, itme_dp_link)
        except Exception as e:
            print(e)


def test():
    # Get the sheet
    # price_tracker = get_sheet()
    item_name = checked_price = item_brand = dp_link = ""
    orignal_price = 1299

    # Amazon Block
    item_link = 'https://www.amazon.in/gp/product/B08P4H4D2Y/ref=ox_sc_saved_title_1?smid=A7B41PSBGW6EO&psc=1'
    item_name, checked_price, brand, dp_link = get_amazon_price(item_link)
    # # Myntra Block
    # item_link = 'https://www.myntra.com/1852066'
    # item_name, checked_price, brand, dp_link = get_myntra_price(item_link)
    # # Decathlon Block
    # item_link = 'https://www.decathlon.in/p/8388642/gym-wear-for-men/men-s-gym-t-shirt-regular-fit-sportee-100-black'
    # item_name, checked_price, brand, dp_link = get_decathlon_price(item_link)
    # # Flipkart Block
    # item_link = 'https://www.flipkart.com/asian-fitch-men-striped-casual-pink-shirt/p/itm7fb6b47259db5?pid=SHTFUC3FHPBM2NQZ&lid=LSTSHTFUC3FHPBM2NQZI3NC18&marketplace=FLIPKART&store=clo%2Fash&srno=b_1_1&otracker=browse&fm=organic&iid=en_kpTYYGUvACcxBoG84t1nNVR7GcW4ZBOBnM7qLpNOQjak4Xx2NLdOkkiYUp%2B1acwAhzGCbLnSLXyRG9lXwcH8%2FA%3D%3D&ppt=browse&ppn=browse&ssid=g8skrwky0w0000001615746304807'
    # item_name, checked_price, brand, dp_link = get_flipkart_price(item_link)

    print(f"Item Name : {item_name} | Price : {checked_price} | Brand : {brand}")
    send_notification('maindola.amit@gmail.com', item_name, item_link, orignal_price, checked_price, dp_link)


# Check the price and update
if __name__ == '__main__':
    # test()
    check_price() # Check prices of all items in the sheet
