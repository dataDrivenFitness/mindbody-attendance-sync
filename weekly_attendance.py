import requests
from datetime import datetime, timedelta

# ========== CONFIGURATION ==========
SOURCE_NAME = os.getenv("MINDBODY_SOURCE_NAME")
PASSWORD = os.getenv("MINDBODY_PASSWORD")
SITE_ID = "-99"
PABBLY_WEBHOOK = os.getenv("PABBLY_WEBHOOK_URL")
# ===================================

# 1. Calculate last week’s Monday to Sunday
today = datetime.today()
last_monday = today - timedelta(days=today.weekday() + 7)
last_sunday = last_monday + timedelta(days=6)

start_date = last_monday.strftime("%m/%d/%Y")
end_date = last_sunday.strftime("%m/%d/%Y")

# 2. Build SOAP request body
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
        <PageSize>50</PageSize>
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
    print("✅ Successfully pulled data from Mindbody")
    pabbly_response = requests.post(PABBLY_WEBHOOK, json={"mindbody_xml": response.text})
    if pabbly_response.status_code == 200:
        print("📨 Data forwarded to Pabbly successfully!")
    else:
        print("⚠️ Error forwarding to Pabbly:", pabbly_response.text)
else:
    print("❌ Error pulling data from Mindbody:", response.text)
