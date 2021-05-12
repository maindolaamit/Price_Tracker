import re, traceback
import gspread
# from os import environ, path
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from fake_useragent import UserAgent
import ast

SHEET_NAME = 'price_tracker'  # Google Sheet Name
# Derive Google app password from Environment variable
GAPP_PASSWD = os.environ.get('GAPP_PASSWD')
USER_AGENT_HDR = None
OUTPUT_FILE = open('output.log', 'w')


def print_msg(message, level=0):
    """ Print the message in formatted way and writes to the log """
    seprator = '\t'
    fmt_msg = f'{level * seprator}{message}'
    print(fmt_msg)
    print(fmt_msg, file=OUTPUT_FILE)


def get_sheet():
    """ 
    This method will Authorize the google drive and will fetch the Sheet
    Credentials will be referred from %APPDATA%/gspread/credentials.json
    User interaction will be asked for the first time after that it will be stored in authorized_user.json
    """
    from google.auth.exceptions import RefreshError
     
    auth_file = os.path.join(os.getenv('APPDATA'),
                             'gspread', 'authorized_user.json')
    gc = None
    try:
        gc = gspread.oauth()
    except RefreshError as e:
        # remove auth file and re-authorize
        print_msg("Re-Authorizing the credentials ...", 1)
        os.remove(auth_file)
        gc = gspread.oauth()

    print_msg('User authorized.')
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

    # remove any chars except numbers
    checked_price = re.sub('[^0-9\.]', '', price)

    return float(checked_price)


def get_amazon_price(url):
    """ This method will return the price details from Amazon"""
    soup = get_request_soup(url)
    soup.prettify()
    # save_soup(soup, 'amazon_item.html') # Save output to html for debugging purpose

    # Find the Item and Price
    item = soup.find(id='productTitle').get_text().strip()
    price = soup.find('span', {'id': "priceblock_ourprice"}).get_text().replace(
        ',', '').strip().replace(' ', '')
    checked_price = clean_price(price)
    try:
        brand = soup.find(id='bylineInfo').get_text().split(':')[1].strip()
    except Exception as e:  # Exception in getting brand
        print_msg(f"*** Error getting brand, {e} ***", 2)
        brand = "UKN"

    item_dp = soup.find(id='imgTagWrapperId').find('img')[
        'data-a-dynamic-image']
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
    item, dp_link, price, brand = json_value["name"], json_value[
        'image'], json_value["offers"]["price"], json_value["brand"]["name"]
    price = clean_price(price)

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
    block = soup.body.find(id='__next').findAll(
        'script', {'type': 'application/ld+json'})[1]
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
    price = soup.find('div', {'class': 'product-price'}
                      ).get_text().replace(',', '').strip().replace(' ', '')
    brand = soup.find('span', {'class': 'mtitle'}
                      ).get_text().strip().replace(' ', '')


def get_email_html(item, item_url, item_dp_link, old_price, new_price):
    greet_snippet = f"""
            <div style="height:10%">
                Hello Subscriber,<br><br> One item in you Wishlist is now available at 
                <b style="color:#9b59b6">{new_price}</b> <del style="color:#2980b9">{old_price}</del>.
            </div>
            """
    btn_snippet = f"""
            <a style="background: #2abc68; color: #ecf0f1; border-radius: 5em; width: 70%; 
                                height: 10%; padding: 0.6em 2em; margin-bottom: .4em; text-decoration: none;
                                transition: background-color 0.5s, border 0.2s, color 0.2s;"
               href='{item_url}'>Buy Now</a>
            """
    content_snippet = f"""
            <div style="text-align: center; border: 1px dashed #e67e22; margin: 1em 0; height:70%; width:50%">
                <div style="border: 2px red;padding: 2px;">
                    <a
                        href="{item_url}">
                        <img class="content-image" alt="{item}" src="{item_dp_link}"
                            height='70%' width='60%'></img>
                    </a>
                    <div style="font-weight: bold; color: #2c3e50;margin:5%">{item}</div>
                </div>
                """ + btn_snippet + """
            </div>"""
    footer_snippet = """<div style="margin-top:2em; height:10%">Thanks,<br>Amit Maindola<br>
            <div style="color:#e74c3c; font-weight:bold">Note : This is a system generated email, please do not respond</div>
            </div>"""
    main_html = """\
    <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet">
        </head>
        <body style="background-color: #fcfffe;color: #555;font-family:'Roboto',sans-serif;
                        font-weight:300;margin: 0.7em 0.5em">""" + greet_snippet + content_snippet + footer_snippet + """            
        </body>
    <html>
    """
    return main_html


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
            message_html = get_email_html(item, item_url, item_dp, old_price, new_price)
            # Save output to html for debugging purpose
            # save_soup(message_html, 'mail.html')

            message.attach(MIMEText(message_html, "html"))
            server.sendmail(sender, to_email, message.as_string())
            print_msg("Notification sent successfully", 2)

        except Exception as e:
            # Print any exception
            raise Exception(f"Error while sending notification : {e}. Item : '{item}', new_price: {new_price}")
        finally:
            server.quit()


def main():
    """ Main method will access the google sheet and will fetch the details
        Item link will be used to fetch the details and then comparison will be made
        A notification will be sent to given email if price has dropped below or at par to Desired price
     """
    # Get the Google Sheet having items information
    now = datetime.today().strftime("%d-%b-%Y %I:%M %p")
    print_msg(f"Starting Program {now}")
    price_tracker = get_sheet()
    all_records = price_tracker.get_all_records()
    print_msg(f"No. of rows in the sheet {len(all_records)}")
    print_msg('')
    # Loop for each row in the sheet
    print_msg("=" * 50, 1)
    for i, row in enumerate(all_records):
        row_num = i + 2  # Add two, one for 0 index and then one for Header
        item_link = row['Item Link']
        desired_price = int(row['Desired Price'])
        orignal_price = int(row['Orignal Price'])
        item_name = checked_price = item_brand = itme_dp_link = ""

        if item_link is None:
            continue  # Skip if item link is not given

        try:
            # Check which brand details to be fetched
            if "myntra" in item_link:
                item_name, checked_price, item_brand, itme_dp_link = get_myntra_price(
                    item_link)
            elif "amazon" in item_link:
                item_name, checked_price, item_brand, itme_dp_link = get_amazon_price(
                    item_link)
            elif "decathlon" in item_link:
                item_name, checked_price, item_brand, itme_dp_link = get_decathlon_price(
                    item_link)
            elif "flipkart" in item_link:
                item_name, checked_price, item_brand, itme_dp_link = get_decathlon_price(
                    item_link)
            else:
                exit(0)
            # Update the Last checked details
            print_msg(f"Row num : {row_num} - Item : {item_name[:40]} - Checked price : {checked_price}", 1)
            price_tracker.update_cell(row_num, 5, item_name)
            price_tracker.update_cell(row_num, 6, checked_price)
            price_tracker.update_cell(row_num, 7, now)
            print_msg("Row updated.", 2)

            # Send notification if current price is less than the desired price
            if desired_price is not None and checked_price <= desired_price:
                send_notification(row['Notification To'], item_name,
                                  item_link, orignal_price, checked_price, itme_dp_link)
        except Exception as e:
            # raise e
            traceback.print_exc(file=OUTPUT_FILE)
    print_msg("=" * 50, 1)


def test():
    # Get the sheet
    # price_tracker = get_sheet()
    item_name = checked_price = item_brand = dp_link = ""
    orignal_price = 1299

    # Amazon Block
    # item_link = 'https://www.amazon.in/gp/product/B08P4H4D2Y/ref=ox_sc_saved_title_1?smid=A7B41PSBGW6EO&psc=1'
    # item_name, checked_price, brand, dp_link = get_amazon_price(item_link)
    # # Myntra Block
    # item_link = 'https://www.myntra.com/1852066'
    # item_name, checked_price, brand, dp_link = get_myntra_price(item_link)
    # Decathlon Block
    item_link = 'https://www.decathlon.in/p/8388642/gym-wear-for-men/men-s-gym-t-shirt-regular-fit-sportee-100-black'
    item_name, checked_price, brand, dp_link = get_decathlon_price(item_link)
    # # Flipkart Block
    # item_link = 'https://www.flipkart.com/asian-fitch-men-striped-casual-pink-shirt/p/itm7fb6b47259db5?pid=SHTFUC3FHPBM2NQZ&lid=LSTSHTFUC3FHPBM2NQZI3NC18&marketplace=FLIPKART&store=clo%2Fash&srno=b_1_1&otracker=browse&fm=organic&iid=en_kpTYYGUvACcxBoG84t1nNVR7GcW4ZBOBnM7qLpNOQjak4Xx2NLdOkkiYUp%2B1acwAhzGCbLnSLXyRG9lXwcH8%2FA%3D%3D&ppt=browse&ppn=browse&ssid=g8skrwky0w0000001615746304807'
    # item_name, checked_price, brand, dp_link = get_flipkart_price(item_link)

    print(f"Item Name : {item_name} | Price : {checked_price} | Brand : {brand}")
    send_notification('maindola.amit@gmail.com', item_name,
                      item_link, orignal_price, checked_price, dp_link)


def check_enviorn():    
    global GAPP_PASSWD
    if GAPP_PASSWD == None:
        print_msg()
        GAPP_PASSWD = input('Creating Enviornment variable GAPP_PASSWD. Enter the passcode generated in Google Account Security for Application use :')
        os.environ['GAPP_PASSWD'] = GAPP_PASSWD
        print_msg('Temporary Enviornment variable set, please set the enviornment variable GAPP_PASSWD manually in your Host machine.')


# Check the price and update
if __name__ == '__main__':
    try:
        check_enviorn() # Check if enviornment variable is set or not
        # test()
        main()  # Check prices of all items in the sheet
        # OUTPUT_FILE.close()
    except:
        traceback.print_exc(file=OUTPUT_FILE)
    finally:
        OUTPUT_FILE.close()
