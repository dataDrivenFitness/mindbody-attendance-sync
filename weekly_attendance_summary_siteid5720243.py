import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict
import os

# ========== CONFIGURATION ==========
SOURCE_NAME = os.getenv("MINDBODY_SOURCE_NAME")
PASSWORD = os.getenv("MINDBODY_PASSWORD")
SITE_ID = "5720243"
PABBLY_WEBHOOK = os.getenv("PABBLY_WEBHOOK_URL")
# ===================================

# Calculate last week’s Monday to Sunday
today = datetime.today()
last_monday = today - timedelta(days=today.weekday() + 7)
last_sunday = last_monday + timedelta(days=6)

start_date = last_monday.strftime("%m/%d/%Y")
end_date = last_sunday.strftime("%m/%d/%Y")

week_start = last_monday.strftime("%Y-%m-%d")
week_end = last_sunday.strftime("%Y-%m-%d")

# Build SOAP request body
soap_body = f"""<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <FunctionDataXml xmlns="http://clients.mindbodyonline.com/api/0_5">
      <Request>
        <SourceCredentials>
          <SourceName>{SOURCE_NAME}</SourceName>
          <Password>{PASSWORD}</Password>
          <SiteIDs>
            <int>{SITE_ID}</int>
          </SiteIDs>
        </SourceCredentials>
        <XMLDetail>Full</XMLDetail>
        <PageSize>1000</PageSize>
        <CurrentPageIndex>0</CurrentPageIndex>
        <FunctionName>UtilityFunction_VisitsV4</FunctionName>
        <FunctionParams>
          <FunctionParam>
            <ParamName>@StartDate</ParamName>
            <ParamValue>{start_date}</ParamValue>
            <ParamDataType>datetime</ParamDataType>
          </FunctionParam>
          <FunctionParam>
            <ParamName>@EndDate</ParamName>
            <ParamValue>{end_date}</ParamValue>
            <ParamDataType>datetime</ParamDataType>
          </FunctionParam>
          <FunctionParam>
            <ParamName>@ModifiedDate</ParamName>
            <ParamValue>{start_date}</ParamValue>
            <ParamDataType>datetime</ParamDataType>
          </FunctionParam>
        </FunctionParams>
      </Request>
    </FunctionDataXml>
  </soap:Body>
</soap:Envelope>"""

headers = {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPAction": "http://clients.mindbodyonline.com/api/0_5/FunctionDataXml"
}

print(f"Pulling visits from {start_date} to {end_date}...")

response = requests.post(
    "https://clients.mindbodyonline.com/0_5/DataService.asmx",
    headers=headers,
    data=soap_body
)

if response.status_code == 200 and "<Status>Success</Status>" in response.text:
    root = ET.fromstring(response.text)
    namespace = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
    rows = root.findall('.//Row')

    visit_summary = defaultdict(lambda: {
        "first_name": "",
        "last_name": "",
        "email": "",
        "visit_count": 0,
        "week_start": week_start,
        "week_end": week_end
    })

    for row in rows:
        email = row.findtext('EmailName')
        if not email:
            continue
        first_name = row.findtext('FirstName', '')
        last_name = row.findtext('LastName', '')
        status = row.findtext('Status', '')

        # Only count actual visits (e.g., Signed-In, Completed)
        if status not in ['Signed-In', 'Completed', 'Arrived']:
            continue

        client = visit_summary[email.strip()]
        client["first_name"] = first_name
        client["last_name"] = last_name
        client["email"] = email.strip()
        client["visit_count"] += 1

    # Send to Pabbly
    for client_data in visit_summary.values():
        try:
            response = requests.post(PABBLY_WEBHOOK, json=client_data)
            print(f"Sent to Pabbly: {client_data['email']} – Status {response.status_code}")
        except Exception as e:
            print(f"Error sending data for {client_data['email']}: {str(e)}")
else:
    print("❌ Error pulling data from Mindbody:", response.text)
