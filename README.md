# Price_Tracker
A Price tracker application for popular sites like Amazon and Myntra.<br>
The Application will refer the list of items to be tracked from a **Google Sheet**, to fetch the latest price and details.<br>
Sheet will be updated with the latest Price; If price has been dropped for an Item then Email notification will be sent to the user.
![](./img/Price_Tracker_GSheet.png)

## Objective
In the Scrip we will perform below 3 tasks.<br>
1. Use Google Sheet as a Database and update it with price details.<br>
2. Use BeautifulSoup to perform Web scrapping and fetch the Item details.<br>
3. Send Email Notification to the User using smtplib module.<br>
 
## Installation

1. The application requires the below external Python Libraries, install them using pip.<br><br>
`pip install gspread`<br>
`pip install oaut2client`<br>
`pip install bs4`

2. Create a Project in your [Google Developer's Console](https://console.developers.google.com/) and download the JSON file to access Google Drive.
![](./img/JSON_Credentials.gif)
3. Also enable the Google sheets api in the project.

4. Generate an App Password from your [Google Account Security](https://myaccount.google.com/security) to send email from your Gmail client.
![](./img/GAPP_PASSWD.gif)

5. Save the App Password in your environment variable to avoid any hard coding and increased Usability with other projects(if any). 
![](img/Environment_Variable.GIF)
